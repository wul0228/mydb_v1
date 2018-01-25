#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/07
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download,extract,standard insert and select gene data from disgenet

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(disgenet_disease_model,disgenet_disease_raw,disgenet_disease_store,disgenet_disease_db,disgenet_disease_map) = buildSubDir('disgenet_disease')

log_disease = pjoin(disgenet_disease_model,'disgenet_disease.log')

# main code
def downloadData(redownload=False):
    '''
    this function is to download the raw data from disgenet  WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existgoFile) = lookforExisted(disgenet_disease_raw,'all_gene_disease')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        #--------------------------------------------------------------------------------------------------------------------
        # 1. donwload all_gene_disease_pmid_associations*.tsv
        process = parser(today)
    
        mt = process.getMt()   

        savefilepath = process.getOne(disgenet_download_url,mt,disgenet_disease_raw)
    
    #--------------------------------------------------------------------------------------------------------------------
    #  generate .log file in current  path
    if not os.path.exists(log_disease):

        with open(log_disease,'w') as wf:
            json.dump({'disgenet':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'
    #--------------------------------------------------------------------------------------------------------------------
    # return filepaths to extract 

    return (savefilepath,today)

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

    process.disease_info(filepath,fileversion)
     # ----------------------------------------------------------------------------------------------------
    # 3. bkup all collections
    colhead = 'disgenet.disgene'

    bkup_allCols('mydb_v1',colhead,disgenet_disease_db)

    print 'extract and insert completed'
    
    return (filepath,date)

def updateData(insert=False):
    '''
    this function is set to update all file in log
    '''
    disgenet_disease_log = json.load(open(log_disease))

    process = parser(today)

    mt = process.getMt()

    if mt != disgenet_disease_log['disgenet'][-1][0]:

        savefilepath,date = downloadData(redownload=True)

        extractData(savefilepath,date)

        disgenet_disease_log['disgenet'].append((mt,today,model_name))

        # create new log
        with open(log_disease,'w') as wf:

            json.dump(disgenet_disease_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('disgenet_disease',mt)

        return 'update successfully'

    else:
        print  '{} {} is the latest !'.format('disgenet_disease',mt)
        
        return 'new version is\'t detected'

def selectData(querykey = 'geneId',value='1'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'disgenet.disease'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):
    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''
    def __init__(self, date):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.db = db

    def getMt(self):
        '''
        this function is set to get the latest version of disgenet from DisGeNET web site
        '''
        web = requests.get(disgenet_download_web).content

        soup = bs(web,'lxml')

        version = soup.select('#content > div > div > div > div.span8 > div > ul > li:nth-of-type(1)')[0].text.split('version')[1].split(')')[0].strip()

        return version

    def getOne(self,url,mt,rawdir):
        '''
        this function is to download  one file with a given url
        args:
        url --   url of raw file download 
        mt --  the latest version of file
        rawdir -- the directory to save download file
        '''
        filename = url.rsplit('/',1)[1].strip().replace('.tsv.gz','')

        savename = '{}_{}_{}.tsv.gz'.format(filename,mt.replace('.','*'),today)

        savefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(savefilepath,url)

        os.popen(command)

        # gunzip file
        gunzip = 'gunzip {}'.format(savefilepath)

        os.popen(gunzip)

        return savefilepath.rsplit('.gz',1)[0].strip()

    def disease_info(self,savefilepath,fileversion):
        '''
        this function is set parser disease_info 
        '''
        colname = 'disgenet.disgene.curated'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        
        col.ensure_index([('diseaseId',1),])
        col.ensure_index([('geneId',1),])
        col.ensure_index([('diseaseId',1),('geneId',1)])

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'all_gene_disease_pmid_associations'})

        #--------------------------------------------------------------------------------------------------------------------------------------------------
        tsvfile = open(savefilepath)

        dis_aso_type = constance(db='disgenet_aso_type')

        n = 0

        for line in tsvfile:

            if n == 0:

                keys =[key.strip() for key in  line.split('\t') if key]

            else:

                data =[i.strip() for i in line.split('\t') if i]

                dic = dict([(key,val ) for key,val in zip(keys,data)])

                originalSource = dic.get('originalSource').strip()

                if originalSource not in ['CTD_human','HPO','ORPHANET','PSYGENET','UNIPROT']:

                    n += 1
                    continue

                diseaseId = dic.get('diseaseId')

                dic['diseaseId link'] = 'https://www.ncbi.nlm.nih.gov/medgen/{}'.format(diseaseId)

                aso_type = dic.get('associationType','').strip()

                dic['associationType implication'] = dis_aso_type.get(aso_type)

                pmid = dic['pmid'].strip()

                if pmid == 'NA':

                    dic.pop('pmid')

                else:

                    dic['pmid link']  = 'https://www.ncbi.nlm.nih.gov/pubmed/?term={}'.format(pmid)


                col.insert(dic)

                print 'disgenet line',n

            n += 1

class dbMap(object):
    '''
    this class is set to map ncbi gene id to other db
    '''
    def __init__(self):

        super(dbMap,self).__init__()

        import commap

        from commap import comMap

        (db,db_cols) = initDB('mydb_v1') 

        self.db = db

        self.db_cols = db_cols

        process = commap.comMap()

        self.process = process

    def dbID2hgncSymbol(self):
        '''
        this function is to create a mapping relation between disgenet disease id  with HGNC Symbol
        '''
        # because disgenet gene id  is entrez id 
        entrez2symbol = self.process.entrezID2hgncSymbol()

        disgenet_disgene_gene_col = self.db_cols.get('disgenet.disgene.curated')

        disgenet_disgene_gene_docs = disgenet_disgene_gene_col.find({})

        output = dict()

        hgncSymbol2disgenetDiseaseID = output

        for doc in disgenet_disgene_gene_docs:

            disease_id = doc.get('diseaseId')

            gene_id = doc.get('geneId')

            gene_symbol = entrez2symbol.get(gene_id)
            
            if gene_symbol:

                for symbol in gene_symbol:

                    if symbol not in output:

                        output[symbol] = list()

                    output[symbol].append(disease_id)

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val    

        print 'hgncSymbol2disgenetDiseaseID',len(output)

        # with open('./hgncSymbol2disgenetDiseaseID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return (hgncSymbol2disgenetDiseaseID,'diseaseId')

class dbFilter(object):

    '''this class is set to filter part field of data in collections  in mongodb '''

    def __init__(self, arg):
        super(dbFilter, self).__init__()
        self.arg = arg
        
def main():

    modelhelp = model_help.replace('&'*6,'DisGeNET').replace('#'*6,'disgenet')

    funcs = (downloadData,extractData,updateData,selectData,disgenet_disease_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # downloadData(redownload=True)
    # savefilepath ='/home/user/project/dbproject/mydb_v1/disgenet_disease/dataraw/all_gene_disease_pmid_associations_5*0_171228085059.tsv'
    # extractData(savefilepath,'171228085059') 
     # man.mapping()
  
 
