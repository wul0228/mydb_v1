#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/08
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download,extract,standard insert and select gene data from clinvar_variant

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(clinvar_variant_model,clinvar_variant_raw,clinvar_variant_store,clinvar_variant_db,clinvar_variant_map) = buildSubDir('clinvar_variant')

log_path = pjoin(clinvar_variant_model,'clinvar_variant.log')

# main code
def downloadData(redownload = False):
    '''
    this function is to download the raw data from go clinvar FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existgoFile) = lookforExisted(clinvar_variant_raw,'variant')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        ftp = connectFTP(**clinvar_varient_ftp_infos)

        filename = clinvar_varient_filename

        mt =  ftp.sendcmd('MDTM {}'.format(filename)).replace(' ','')

        savefilename = '{}_{}_{}.txt.gz'.format(filename.rsplit('.txt',1)[0].strip(),mt,today)

        remoteabsfilepath = pjoin(clinvar_varient_ftp_infos['logdir'],'{}'.format(filename))

        save_file_path = ftpDownload(ftp,filename,savefilename,clinvar_variant_raw,remoteabsfilepath)

        # gunzip file
        gunzip = 'gunzip {}'.format(save_file_path)

        os.popen(gunzip)

    # create log file
    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:

            json.dump({'clinvar_variant':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'

    filepath = save_file_path.split('.gz')[0].strip()

    return (filepath,today)

def extractData(filepath,date):

    filename = psplit(filepath)[1].strip()

    fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

    process = clinvar_parser(date)

    process.sum(filepath,fileversion)

    colhead = 'clinvar.variant'

    bkup_allCols('mydb_v1',colhead,clinvar_variant_db)

    print 'extract and insert completed'

    return (filepath,date)

def updateData(insert=False,_mongodb='../_mongodb/'):

    clinvar_variant_log = json.load(open(log_path))

    ftp = connectFTP(**clinvar_varient_ftp_infos)

    filename = clinvar_varient_filename

    mt =  ftp.sendcmd('MDTM {}'.format(filename)).replace(' ','')

    if mt != clinvar_variant_log['clinvar_variant'][-1][0]:

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        clinvar_variant_log['clinvar_variant'].append((mt,today,model_name))

        # create new log
        with open(log_path,'w') as wf:

            json.dump(clinvar_variant_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('clinvar_variant',mt)
        
    else:

        print  '{} {} is the latest !'.format('clinvar_variant',mt)

def selectData(querykey = 'GeneID',value='1'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'clinvar_variant_'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class dbMap(object):

    #class introduction

    def __init__(self,version):

        self.version = version

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb')

        colname = 'clinvar_variant_{}'.format(self.version)

        col = db.get_collection(colname)

        self.col = col

        self.docs = col.find({})

        self.colname = colname

    def mapGene2AlleleID(self):

        geneid2gensym = dict()

        geneid2alleleid = dict()

        genesym2alleleid = dict()

        for doc in self.docs:

            gene_id = doc.get('GeneID')
            gene_sym = doc.get('GeneSymbol')
            AlleleID = doc.get('AlleleID')

            if gene_id and gene_id != '-1':

                if gene_id not in geneid2gensym :

                    geneid2gensym[gene_id] = list()

                if gene_id not in geneid2alleleid :

                    geneid2alleleid[gene_id] = list()

                geneid2alleleid[gene_id].append(AlleleID)

                if gene_sym:

                    geneid2gensym[gene_id] += gene_sym

                    for sym in gene_sym:

                        if  sym not in genesym2alleleid:

                            genesym2alleleid[sym] = list()

                        genesym2alleleid[sym].append(AlleleID)

        genesym2geneid = value2key(geneid2gensym)

        map_dir = pjoin(clinvar_variant_map,self.colname)

        createDir(map_dir)

        save = {'geneid2gensym':geneid2gensym,'genesym2geneid':genesym2geneid,
                      'geneid2alleleid':geneid2alleleid, 'genesym2alleleid':genesym2alleleid }

        for name,dic in save.items():

            dedupdic = dict()

            for key,val in dic.items():

                dedupdic[key] = list(set(val))

            with open(pjoin(map_dir,'{}.json'.format(name)),'w') as wf:
                json.dump(dedupdic,wf,indent=2)

    def mapping(self):

        self.mapGene2AlleleID()

class clinvar_parser(object):

    """docstring for clinvar_parser"""
    def __init__(self, date):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        col = db.get_collection('clinvar_variant_{}'.format(version))

        self.db = db

        self.date = date

    def sum(self,filepath,fileversion):

        colname = 'clinvar.variant'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        
        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'variant_summary'})

        tsvfile = open(filepath)

        n = 0

        for line in tsvfile:

            if line.startswith('#'):

                keys = line.replace('#','',1).strip().split('\t')

                print keys

            else:

                data = [i.strip() for i in line.strip().split('\t')]

                dic = dict([(key,val) for key,val in zip(keys,data)])
            
                PhenotypeIDS = dic.pop('PhenotypeIDS')

                PhenotypeList = dic.pop('PhenotypeList')

                GeneSymbol = dic.pop('GeneSymbol')

                PhenotypeList_list = [ i.strip() for i in PhenotypeList.split(',') if i]
                PhenotypeIDS_list = [ i.strip() for i in PhenotypeIDS.split(',') if i]
                GeneSymbol_list = [ i.strip() for i in GeneSymbol.split(';') if i]

                dic.update({
                    'PhenotypeIDS':PhenotypeIDS_list,
                    'PhenotypeList':PhenotypeList_list,
                    'GeneSymbol':GeneSymbol_list
                    })

                col.insert(dic)

                print 'clinvar.variant line',n

            n += 1

def main():

    modelhelp = model_help.replace('&'*6,'CLINVAR_VARIANT').replace('#'*6,'clinvar_variant')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,clinvar_variant_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    
    main()
    # filepath,version = downloadData(redownload = True)

    # filepath = '/home/user/project/dbproject/mydb_v1/clinvar_variant/dataraw/variant_summary_21320171226220427_171228125338.txt'
    # version = '171228125338'
    # extractData(filepath,version)
    # man = dbMap('171208183634')
    # man.mapping()