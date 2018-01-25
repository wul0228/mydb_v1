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

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(clinvar_variant_model,clinvar_variant_raw,clinvar_variant_store,clinvar_variant_db,clinvar_variant_map) = buildSubDir('clinvar_variant')

log_path = pjoin(clinvar_variant_model,'clinvar_variant.log')

# main code
def downloadData(redownload = False):
    '''
    this function is to download the raw data from  clinvar FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existFile) = lookforExisted(clinvar_variant_raw,'variant')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        process = parser(today)

        #-----------------------------------------------------------------------------------------------------------------------------------
        # 1. download variant summary file
        filepath,mt = process.getOne(clinvar_varient_ftp_infos,clinvar_varient_filename,clinvar_variant_raw)

    #-----------------------------------------------------------------------------------------------------------------------------------
    #  generate .log file in current  path
    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:

            json.dump({'clinvar_variant':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'

    #--------------------------------------------------------------------------------------------------------------------
    # return filepaths to extract 

    return (filepath,today)

def extractData(filepath,date):
    '''
    this function is set to distribute all filepath to parser to process
    args:
    filepath -- the file to be parserd
    date -- the date of  data download
    '''
    # ----------------------------------------------------------------------------------------------------
    # 1. distribute filepaths for parser
    #  just only one file

    filename = psplit(filepath)[1].strip()

    fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
    # ----------------------------------------------------------------------------------------------------
    # 2. parser filepaths step by step
    process = parser(date)

    process.variant_info(filepath,fileversion)

    colhead = 'clinvar.variant'
    # ----------------------------------------------------------------------------------------------------
    # 3. bkup all collections
    bkup_allCols('mydb_v1',colhead,clinvar_variant_db)

    print 'extract and insert completed'

    return (filepath,date)

def updateData(insert=False):
    '''
    this function is set to update all file in log
    '''
    clinvar_variant_log = json.load(open(log_path))

    ftp = connectFTP(**clinvar_varient_ftp_infos)

    mt =  ftp.sendcmd('MDTM {}'.format(clinvar_varient_filename)).replace(' ','')

    if mt != clinvar_variant_log['clinvar_variant'][-1][0]:

        filepath,date = downloadData(redownload=True)

        extractData(filepath,date)

        clinvar_variant_log['clinvar_variant'].append((mt,today,model_name))

        # create new log
        with open(log_path,'w') as wf:

            json.dump(clinvar_variant_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('clinvar_variant',mt)

        return 'update successfully'
        
    else:

        print  '{} {} is the latest !'.format('clinvar_variant',mt)

        return 'new version is\'t detected'

def selectData(querykey = 'GeneID',value='1'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'clinvar.variant'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):
    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''
    def __init__(self, date):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        col = db.get_collection('clinvar_variant_{}'.format(version))

        self.db = db

        self.date = date

    def getOne(self,clinvar_variant_ftp_infos,filename,rawdir):
        '''
        this function is to download  one file under  a given remote dir 
        args:
        ftp_infos --  a specified ftp connection info 
        filename --  the name of file need download
        rawdir -- the directory to save download file
        '''
        while  True:

            try:

                ftp = connectFTP(**clinvar_variant_ftp_infos)

                mt =  ftp.sendcmd('MDTM {}'.format(filename)).replace(' ','')

                savefilename = '{}_{}_{}.txt.gz'.format(filename.rsplit('.txt',1)[0].strip(),mt,today)

                remoteabsfilepath = pjoin(clinvar_variant_ftp_infos['logdir'],'{}'.format(filename))

                save_file_path = ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath)

                print filename,'done'

                # gunzip file
                gunzip = 'gunzip {}'.format(save_file_path)

                os.popen(gunzip)

                save_file_path = save_file_path.rsplit('.gz',1)[0].strip()

                return (save_file_path,mt)

            except:

                ftp = connectFTP(**clinvar_variant_ftp_infos)

    def variant_info(self,filepath,fileversion):
        '''
        this function is set parser variant_info 
        '''
        colname = 'clinvar.variant'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        col.ensure_index([('GeneID',1),])
        col.ensure_index([('AlleleID',1),])
        col.ensure_index([('GeneID',1),('AlleleID',1)])
        
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

                dbvar= dic.get('nsv/esv (dbVar)')

                if dbvar and dbvar != '-':
                    dbvar_link = 'https://www.ncbi.nlm.nih.gov/dbvar/variants/{}/'.format(dbvar)
                else:
                    dbvar_link = ''
                
                rs = dic.get('RS# (dbSNP)')
                if rs and rs != '-1':
                    rs_link = 'https://www.ncbi.nlm.nih.gov/projects/SNP/snp_ref.cgi?searchType=adhoc_search&type=rs&rs=rs{}'.format(rs)
                else:
                    rs_link = ''
                dic.update({
                    'PhenotypeIDS':PhenotypeIDS_list,
                    'PhenotypeList':PhenotypeList_list,
                    'GeneSymbol':GeneSymbol_list,
                    'dbVar_link':dbvar_link,
                    'RS_link':rs_link,
                    })

                col.insert(dic)

                print 'clinvar.variant line',n

            n += 1

class dbMap(object):
    '''
    this class is set to map ncbi gene id to other db
    '''
    def __init__(self):

        super(dbMap, self).__init__()
        
        import commap

        from commap import comMap

        (db,db_cols) = initDB('mydb_v1') 

        self.db = db

        self.db_cols = db_cols

        process = commap.comMap()

        self.process = process

    def dbID2hgncSymbol(self):
        '''
        this function is to create a mapping relation between alle id  with HGNC Symbol
        '''
        
        hgnc2symbol = self.process.hgncID2hgncSymbol()

        clinvar_variant_col = self.db_cols.get('clinvar.variant')

        clinvar_variant_docs = clinvar_variant_col.find({})

        output = dict()

        hgncSymbol2clinvarVariantID = output

        for doc in clinvar_variant_docs:

            allele_id = doc.get('AlleleID')

            hgnc_id = doc.get('HGNC_ID')

            gene_symbol = hgnc2symbol.get(hgnc_id)

            if allele_id and gene_symbol:

                for symbol in gene_symbol:

                    if symbol not in output:

                        output[symbol] = list()

                    output[symbol].append(allele_id)

        for sym,alles in output.items():
            alles  = list(set(alles))
            output[sym] = alles
            
        print 'hgncSymbol2clinvarVariantID',len(output)

        # with open('./hgncSymbol2clinvarVariantID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return (hgncSymbol2clinvarVariantID,'AlleleID')

class dbFilter(object):

    '''this class is set to filter part field of data in collections  in mongodb '''

    def __init__(self):
        super(dbFilter, self).__init__()
    
    def gene_topic(self,doc):
        save_keys = ['GeneID','Assembly','Chromosome','Start' ,'Stop', 'ReferenceAllele','AlternateAllele',
                                'Type','RS# (dbSNP)','RS_link','nsv/esv (dbVar)','dbvar_link','OriginSimple','PhenotypeList',
                                'ClinicalSignificance','ReviewStatus']

        return filterKey(doc,save_keys)

def main():

    modelhelp = model_help.replace('&'*6,'CLINVAR_VARIANT').replace('#'*6,'clinvar_variant')

    funcs = (downloadData,extractData,updateData,selectData,clinvar_variant_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
