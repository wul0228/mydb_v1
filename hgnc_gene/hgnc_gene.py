#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/25
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download ,parser(extract,satndar,insert) and update hgnc gene data from hgnc ftp site

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(hgnc_gene_model,hgnc_gene_raw,hgnc_gene_store,hgnc_gene_db,hgnc_gene_map) = buildSubDir('hgnc_gene')

log_path = pjoin(hgnc_gene_model,'hgnc_gene.log')

# main code
def downloadData(redownload = False):

    '''
    this function is to download the raw data from hgnc FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existHgncFile) = lookforExisted(hgnc_gene_raw,'gene')

        if choice != 'y':
            return

    if redownload or not existHgncFile or  choice == 'y':

        process = parser(today)

        #------------------------------------------------------------------------------------------------------------------------
        # 1. download hgnc_complete_set.txt
        save_file_path = process.getOne(hgnc_gene_ftp_infos,hgnc_genename_filename,hgnc_gene_raw)
    
    #------------------------------------------------------------------------------------------------------------------------
    #  generate .log file in current  path
    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:

            json.dump({'hgnc_gene':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'

    return (save_file_path,today)

def extractData(filepath,date):

    '''
    this function is set to distribute all filepath to parser to process
    args:
    filepaths -- all filepaths to be parserd
    date -- the date of  data download
    '''
    process = parser(date)

    process.hgnc_info(filepath)

    # bkup all collections

    colhead = 'hgnc.gene'
    
    bkup_allCols('mydb_v1',colhead,hgnc_gene_db)

    print 'extract and insert completed'

    return (filepath,date)

def updateData(insert=True):
    '''
    this function is set to update all file in log
    '''
    hgnc_gene_log = json.load(open(log_path))

    ftp = connectFTP(**hgnc_gene_ftp_infos)

    mt =  ftp.sendcmd('MDTM {}'.format(hgnc_genename_filename)).replace(' ','')

    if mt != hgnc_gene_log['hgnc_gene'][-1][0]:

        filepath,version = downloadData(redownload=True)

        if insert:
            extractData(filepath,version)

        hgnc_gene_log['hgnc_gene'].append((mt,today,model_name))

        # create new log
        with open(log_path,'w') as wf:

            json.dump(hgnc_gene_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('hgnc_gene',mt)

        return 'update successfully'

    else:

        print  '{} {} is the latest !'.format('hgnc_gene',mt)

        return 'new version is\'t detected'

def selectData(querykey = 'hgnc_id',value='1'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'hgnc'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):

    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''

    def __init__(self,date):

        super(parser, self).__init__()

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.db = db

    def getOne(self,hgnc_gene_ftp_infos,filename,rawdir):
        '''
        this function is to download  one file under  a given remote dir 
        args:
        hgnc_gene_ftp_infos --  a specified ftp cursor  
        filename --  the name of file need download
        rawdir -- the directory to save download file
        '''
        while  True:

            try:

                ftp = connectFTP(**hgnc_gene_ftp_infos)

                mt =  ftp.sendcmd('MDTM {}'.format(hgnc_genename_filename)).replace(' ','')

                savefilename = '{}_{}_{}.txt'.format(filename.rsplit('.txt',1)[0].strip(),mt,today)

                remoteabsfilepath = pjoin(hgnc_gene_ftp_infos['logdir'],'{}'.format(filename))

                save_file_path = ftpDownload(ftp,filename,savefilename,hgnc_gene_raw,remoteabsfilepath)

                return save_file_path

            except:

                ftp = connectFTP(**hgnc_gene_ftp_infos)

    def hgnc_info(self,filepath):

        '''
        this function is set parser gene_info 
        '''
        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
        
        tsvfile = open(filepath)

        colname = 'hgnc.gene'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('hgnc_id',1),])

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'hgnc_complete_set'})

        n  = 0 

        for line in tsvfile:

            if n == 0:

                keys = [i.strip().replace('.','*').replace(' ','&') for i in line.strip().split('\t')]

            else:
                data = [''.join(''.join(i.split('"',1)).rsplit('"',1)).strip() for i in line.strip().split('\t')]

                dic = dict([(key,val) for key,val in zip(keys,data)])

                locus_group = dic.get('locus_group')
                locus_type = dic.get('locus_type')
                status = dic.get('status')

                if any([i.count('withdrawn') for i in [locus_group,locus_type,status]]):

                    n += 1
                    continue

                gene_family = dic.pop('gene_family')

                gene_family_id = dic.pop('gene_family_id')

                if gene_family and gene_family_id:

                    family = [i.strip() for i in gene_family.split('|') if i]

                    family_id = [i.strip() for i in gene_family_id.split('|') if i]

                    family_id_link = ['https://www.genenames.org/cgi-bin/genefamilies/set/{}'.format(_id) for _id in family_id]

                    dic['gene_family'] =  list()

                    for i,j,k in zip(family,family_id,family_id_link):

                        dic['gene_family'].append({
                            'family':i,
                            'family_id':j,
                            'family_id_link':k,
                            })

                col.insert(dic)

                print 'hgnc gene line',n

            n += 1

class dbMap(object):
    '''
    this class is set to map hgnc  id to other db
    '''
    def __init__(self):

        import commap

        from commap import comMap

        (db,db_cols) = initDB('mydb_v1') 

        self.db = db

        self.db_cols = db_cols

        process = commap.comMap()

        self.process = process

    def dbID2hgncSymbol(self):

        hgnc2symbol = self.process.hgncID2hgncSymbol()

        output = dict()

        hgncSymbol2hgncID = output

        for hgnc_id,symbol in hgnc2symbol.items():

            for sym in symbol:

                if sym not in output:

                    output[sym] = list()

                output[sym].append(hgnc_id)

        for key,val in output.items():

            val = list(set(val))

            output[key] = val

        # with open('./hgncSymbol2hgncID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        print 'hgncSymbol2hgncID',len(hgncSymbol2hgncID)

        return (hgncSymbol2hgncID,'hgnc_id')

class dbFilter(object):

    '''this class is set to filter part field of data in collections  in mongodb '''

    def __init__(self, arg):
        super(dbFilter, self).__init__()
        self.arg = arg
        
        
def main():

    modelhelp = model_help.replace('&'*6,'HGNC_GENE').replace('#'*6,'hgnc_gene')

    funcs = (downloadData,extractData,updateData,selectData,hgnc_gene_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
