#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/27
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download ,parser(extract,satndar,insert) and update phenotype  data from hpo web site

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(hpo_phenotype_model,hpo_phenotype_raw,hpo_phenotype_store,hpo_phenotype_db,hpo_phenotype_map) = buildSubDir('hpo_phenotype')

log_path = pjoin(hpo_phenotype_model,'hpo_phenotype.log')

# main code
def downloadData(redownload=False):
    '''
    this function is to download the raw data from  hpo WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existhpoFile) = lookforExisted(hpo_phenotype_raw,'phenotype')

        if choice != 'y':
            return

    if redownload or not existhpoFile or  choice == 'y':

        rawdir = pjoin(hpo_phenotype_raw,'phenotype_{}'.format(today))

        createDir(rawdir)
        #------------------------------------------------------------------------------------------------------------------------
        process = parser(today)
    
        # 1. get the latest version of  raw file
        mt = process.getMt()   

        # 2. download raw files
        process.getAll(hpo_download_urls,mt,rawdir)
    #--------------------------------------------------------------------------------------------------------------------
    #  generate .log file in current  path
    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:
            json.dump({'hpo_phenotype':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'
    #--------------------------------------------------------------------------------------------------------------------
    # return filepaths to extract 
    filapths = [pjoin(rawdir,filename) for filename in listdir(rawdir)]

    return (filapths,today)

def extractData(filepaths,date):

    '''
    this function is set to distribute all filepath to parser to process
    args:
    filepaths -- all filepaths to be parserd
    date -- the date of  data download
    '''
    # 1. distribute filepaths for parser
    phenotype_info_paths = [path for path in filepaths if psplit(path)[1].strip().endswith('obo')]

    phenotype_gene_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('ALL_SOURCES')]

    phenotype_disease_paths = [path for path in filepaths if psplit(path)[1].strip().endswith('.tab')]

    phenotype_disgene_paths = [path for path in filepaths if psplit(path)[1].split('_',1).strip() in ['OMIM','ORPHA']]
   
    # 2. parser filepaths step by step
    process = parser(date)

    # --------------------------------hpo.phenotype.info-------------------------------------------------------------------------
    process.phenotype_info(phenotype_info_paths)

    # --------------------------------hpo.phenotype.gene-------------------------------------------------------------------------
    process.phenotype_gene(phenotype_gene_paths)

    # --------------------------------hpo.phenotype.disease-------------------------------------------------------------------------
    process.phenotype_disease(phenotype_disease_paths)

    # --------------------------------hpo.phenotype.disgene-------------------------------------------------------------------------
    process.phenotype_disgene(phenotype_disgene_paths)

    print 'extract and insert complete '

    # 3. bkup all collections
    _mongodb = pjoin(hpo_phenotype_db,'phenotype_{}'.format(date))

    createDir(_mongodb)

    colhead = 'hpo.phenotype'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    return (filepaths,date)

def updateData(insert=False,_mongodb='../_mongodb/'):

    hpo_phenotype_log = json.load(open(log_path))

    process = parser(today)

    mt = process.getMt()

    if mt != hpo_phenotype_log['hpo_phenotype'][-1][0]:

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        hpo_phenotype_log['hpo_phenotype'].append((mt,today,model_name))

        # create new log
        with open(log_path,'w') as wf:

            json.dump(hpo_phenotype_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('hpo_phenotype',mt)

        return 'update successfully'

    else:
        print  '{} {} is the latest !'.format('hpo_phenotype',mt)

        return 'new version is\'t detected'

def selectData(querykey = 'HPO-ID',value='HP:0011220'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'hpo.phenotype'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):
    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''
    def __init__(self, date):

        super(parser, self).__init__()

        self.date = date

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

    def getMt(self):
        '''
        this function is set to get the latest version of raw file from hpo web site
        '''
        headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36'}

        web = requests.get(hpo_download_web,headers = headers,verify=False)

        soup = bs(web.content,'lxml')

        h1 = soup.find(name='h1',attrs={'class':'build-caption page-headline'})

        mt = h1.text.strip().split('\n')[1].strip().split(')')[0].split('(')[1].strip().replace(':','').replace(' ','').replace(',','')

        return mt  
    
    def getAll(self,urls,mt,rawdir):
        '''
        this function is set to download raw files for  specified urls 
        args:
            urls -- the urls of download web page of files
            mt -- the latest version of hpo raw file
            rawdir -- the raw directoty to store download file
        '''
        for url in urls:

            filename = url.rsplit('/',1)[1].strip()

            if filename.endswith('obo'):

                savename = '{}_{}_{}.obo'.format(filename.split('.obo',1)[0].strip(),mt.replace('.','*'),today)

            elif filename.endswith('.tab'):

                savename = '{}_{}_{}.tab'.format(filename.split('.tab',1)[0].strip(),mt.replace('.','*'),today)

            else:
                savename = '{}_{}_{}.txt'.format(filename.split('.txt',1)[0].strip(),mt.replace('.','*'),today)

            storefilepath = pjoin(rawdir,savename)

            command = 'wget -O {} {}'.format(storefilepath,url)

            os.popen(command)

    def phenotype_info(self,filepaths):
        '''
        this function is set parser phenotype_info 
        '''
        print '+'*50
        colname = 'hpo.phenotype.info'

        # before insert ,truncate collection
        col = self.db.get_collection(colname)

        col.ensure_index([('HPO-ID',1),])

        filepath = filepaths[0]  # just only one file

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
        
        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'hp.obo'})

        #--------------------------------------------------------------------------------------------------------------------------------
        # read file
        obofile = open(filepath)

        # skip  term head 
        n = 1 

        for line in obofile:

            if line.count('[Term]'):

                break

            n += 1
        
        aset = dict()

        for line in obofile:

            if line.count('[Term]'):

                if aset:

                    # change filed id to HPO-ID
                    _id = aset.pop('id')
                    aset['HPO-ID'] = _id
                    aset['HPO-ID-LINK'] = 'http://compbio.charite.de/hpoweb/showterm?id={}'.format(_id)
                    col.insert(aset)
                     
                    print 'hpo_phenotype line','obo',n

                aset = dict()

            else:
                line = line.strip()

                if  bool(line):

                    (key,val) = tuple(line.strip().split(':',1))

                    key = key.strip()
                    val = val.strip()

                    if key == 'def':
                        val = standarString(val,'','')
                    else:
                        val = standarString(val,'','.')

                    if key in ['name','id']:
                        aset[key] = val

                    else:

                        if key not in aset:
                            aset[key] = list()
                        aset[key].append(val)

            n += 1

        if aset:

            # change filed id to HPO-ID
            _id = aset.pop('id')
            aset['HPO-ID'] = _id
            aset['HPO-ID-LINK'] = 'http://compbio.charite.de/hpoweb/showterm?id={}'.format(_id)

            col.insert(aset)
                     
            print 'hpo.phenotype.info line','obo',n

        print 'hpo.phenotype.info completed! '

    def phenotype_gene(self,filepath):
        '''
        this function is set parser phenotype_gene 
        '''
        print '+'*50
        colname = 'hpo.phenotype.gene'

        # before insert ,truncate collection
        col = self.db.get_collection(colname)

        col.ensure_index([('HPO-ID',1),])
        col.ensure_index([('Gene-ID',1),])
        col.ensure_index([('HPO-ID',1),('Gene-ID',1),])

        filepath = filepaths[0]  # just only one file

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
        
        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'ALL_SOURCES_ALL_FREQUENCIES_phenotype_to_genes'})

        #--------------------------------------------------------------------------------------------------------------------------------
        # read file
        tsvfile = open(filepath)

        keys = ['HPO-ID','HPO-Name','Gene-ID','Gene-Name']

        n = 0 

        for line in tsvfile:

            if line.startswith('#'):
                continue

            data = line.strip().split('\t')

            dic = dict([(key,val) for key,val in zip(keys,data)])

            col.insert(dic)

            n += 1
              
            print 'hpo.phenotype.gene txt line',n

    def phenotype_disease(self,filepath):
        '''
        this function is set parser phenotype_disease 
        '''
        print '+'*50
        colname = 'hpo.phenotype.disease'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        col.ensure_index([('HPO-ID',1),])

        filepath = filepaths[0]  # just only one file

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'phenotype_annotation'})

        #--------------------------------------------------------------------------------------------------------------------------------
        # read file
        tabfile = open(filepath)

        keys = ['DB','DB_Object_ID','DB_Name','Qualifier','HPO-ID','DB:Reference','Evidence_code','Onset_modifier','Frequency_modifier','with','Aspect','Synonym','Date','Assigned_by']

        n = 0 

        for line in tabfile:

            if line.startswith('#'):
                continue

            data = line.strip().split('\t')

            dic = dict([(key,val) for key,val in zip(keys,data)])

            dic.pop('with')

            Assigned_by = dic.pop('Assigned_by')

            dic['Assigned_by'] = Assigned_by.strip().split(';')

            col.insert(dic)

            print 'hpo.phenotype.disease tab line',n

            n += 1

    def phenotype_disgene(self,filepaths):
        '''
        this function is set parser phenotype_disgene 
        '''
        print '+'*50
        colname = 'hpo.phenotype.disgene'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        col.ensure_index([('HPO-ID',1),])
        col.ensure_index([('gene-id(entrez)',1),])

        #--------------------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            if not col.find_one({'dataVersion':fileversion}):
                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'OMIM_ALL_FREQUENCIES_diseases_to_genes_to_phenotypes,ORPHA_ALL_FREQUENCIES_diseases_to_genes_to_phenotypes'})
            #--------------------------------------------------------------------------------------------------------------------------------
            # read file
            tsvfile = open(filepath)

            keys = ['diseaseId','gene-symbol','gene-id(entrez)','HPO-ID','HPO-term-name']

            n = 0 

            for line in tsvfile:

                if line.startswith('#'):
                    continue

                data = line.strip().split('\t')

                dic = dict([(key,val) for key,val in zip(keys,data)])

                diseaseId = dic.get('diseaseId')

                db = diseaseId.split(':')[0].strip()

                dic['database'] = db

                col.insert(dic)
                  
                print 'hpo.phenotype.disgene txt line',n

                n += 1

class dbMap(object):

    '''
    this class is set to map hpo  id to other db
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
        '''
        this function is to create a mapping relation between hpo id with HGNC Symbol
        '''
        entrez2symbol = self.process.entrezID2hgncSymbol()

        hpo_phenotype_gene_col = self.db_cols.get('hpo.phenotype.gene')

        output = dict()

        hgncSymbol2hpoID = output

        hpo_phenotype_gene_docs = hpo_phenotype_gene_col.find({})

        for doc in hpo_phenotype_gene_docs:

            hpo_id = doc.get('HPO-ID')

            gene_id = doc.get('Gene-ID')

            gene_symbol = entrez2symbol.get(gene_id)

            if gene_symbol:
                
                for symbol in gene_symbol:

                    if symbol not in output:
                        output[symbol] = list()

                    output[symbol].append(hpo_id)

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val    

        print 'hgncSymbol2hpoID',len(output)

        # with open('./hgncSymbol2hpoID.json','w') as wf:
        #     json.dump(output,wf,indent=8)
            
        return  (output,'HPO-ID')

class dbFilter(object):

    '''this class is set to filter part field of data in collections  in mongodb '''

    def __init__(self, arg):
        super(dbFilter, self).__init__()
        self.arg = arg
        

def main():

    modelhelp = model_help.replace('&'*6,'HPO_Phenotypic').replace('#'*6,'hpo_phenotype')

    funcs = (downloadData,extractData,updateData,selectData,hpo_phenotype_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
