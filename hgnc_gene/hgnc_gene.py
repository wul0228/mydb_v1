#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/25
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to xxxxxx

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(hgnc_gene_model,hgnc_gene_raw,hgnc_gene_store,hgnc_gene_db,hgnc_gene_map) = buildSubDir('hgnc_gene')

log_path = pjoin(hgnc_gene_model,'hgnc_gene.log')

# main code
def downloadData(redownload = False):

    '''
    this function is to download the raw data from go gene FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existHgncFile) = lookforExisted(hgnc_gene_raw,'gene')

        if choice != 'y':
            return

    if redownload or not existHgncFile or  choice == 'y':

        process = hgnc_parser(today)

        mt = process.getMt()

        ftp = connectFTP(**hgnc_gene_ftp_infos)

        filename = hgnc_genename_filename

        savefilename = '{}_{}_{}.txt'.format(filename.rsplit('.txt',1)[0].strip(),mt,today)

        remoteabsfilepath = pjoin(hgnc_gene_ftp_infos['logdir'],'{}'.format(filename))

        save_file_path = ftpDownload(ftp,filename,savefilename,hgnc_gene_raw,remoteabsfilepath)

    # create log file
    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:

            json.dump({'hgnc_gene':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'

    return (save_file_path,today)

def extractData(filepath,date):

    filename = psplit(filepath)[1].strip()

    fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

    process = hgnc_parser(date)

    process.tsv(filepath,fileversion)

    # bkup all collections

    colhead = 'hgnc.gene'
    
    bkup_allCols('mydb_v1',colhead,hgnc_gene_db)

    print 'extract and insert completed'

    return (filepath,date)

def updateData(insert=False,_mongodb=hgnc_gene_db):

    hgnc_gene_log = json.load(open(log_path))

    process = hgnc_parser(today)

    mt = process.getMt()

    if mt != hgnc_gene_log['hgnc_gene'][-1][0]:

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        hgnc_gene_log['hgnc_gene'].append((mt,today,model_name))

        # create new log
        with open(log_path,'w') as wf:

            json.dump(hgnc_gene_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('hgnc_gene',mt)
        
    else:

        print  '{} {} is the latest !'.format('hgnc_gene',mt)

def selectData(querykey = 'hgho_id',value='1'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'hgnc_gene'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class dbMap(object):

    #class introduction

    def __init__(self,version):

        self.version = version

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb')

        colname = 'hgnc_gene_{}'.format(version)

        col = db.get_collection(colname)

        self.col = col

        self.version = version

    def mapXX2XX(self):
        pass

    def mapping(self):

        self.mapXX2XX()

class hgnc_parser(object):

    """docstring for hgnc_parser"""
    def __init__(self,date):

        super(hgnc_parser, self).__init__()

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.db = db

    def getMt(self):

        ftp = connectFTP(**hgnc_gene_ftp_infos)

        mt =  ftp.sendcmd('MDTM {}'.format(hgnc_genename_filename)).replace(' ','')

        return mt

    def tsv(self,filepath,fileversion):

        tsvfile = open(filepath)

        colname = 'hgnc.gene'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'hgnc_complete_set'})

        n  = 0 

        for line in tsvfile:

            if n == 0:

                keys = [i.strip().replace('.','*').replace(' ','&') for i in line.strip().split('\t')]

                # for index,key in enumerate(keys):
                #     print index,key

            else:
                data = line.strip().split('\t')

                dic = dict([(key,val) for key,val in zip(keys,data)])

                locus_group = dic.get('locus_group')
                locus_type = dic.get('locus_type')
                status = dic.get('status')

                if any([i.count('withdrawn') for i in [locus_group,locus_type,status]]):

                    n += 1
                    continue

                col.insert(dic)

                print 'hgnc gene line',n

            n += 1

def main():

    modelhelp = ''

    funcs = (downloadData,extractData,updateData,selectData,dbMap,hgnc_gene_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    # main()
    (filepath,today) = downloadData(redownload = True)
    extractData(filepath,today)
    updateData()
