#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/27
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to xxxxxx

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
def downloadData( redownload=False ):
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

        process = hpo_parser(today)
    
        mt = process.getMt()   

        print mt

        for  url in hpo_download_urls:

            process.wget(url,mt,rawdir)

    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:
            json.dump({'hpo_phenotype':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'

    filapths = [pjoin(rawdir,filename) for filename in listdir(rawdir)]

    return (filapths,today)

def extractData(filepaths,date):
    
    process = hpo_parser(date)

    for info in ['info','disgene','disease','gene','ontology','annotation']:

        delCol('mydb_v1','hpo.phenotype.{}'.format(info))

    for filepath in filepaths:

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

        if filename.endswith('obo'):

            process.info(filepath,fileversion)

        elif filename.endswith('.tab'):

            process.disease(filepath,fileversion)

        elif filename.startswith('ALL_SOURCES'):

            process.gene(filepath,fileversion)

        elif filename.startswith('OMIM') or filename.startswith('ORPHA') :

            process.disgene(filepath,fileversion)

    # bkup all collections
    _mongodb = pjoin(hpo_phenotype_db,'phenotype_{}'.format(date))

    createDir(_mongodb)

    colhead = 'hpo.phenotype'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    return (filepaths,date)

    print 'extract and insert complete '

    # return (filepaths,version)

def updateData(insert=False,_mongodb='../_mongodb/'):

    hpo_phenotype_log = json.load(open(log_path))

    process = hpo_parser(today)

    mt = process.getMt()

    if mt != hpo_phenotype_log['hpo_phenotype'][-1][0]:

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        hpo_phenotype_log['hpo_phenotype'].append((mt,today,model_name))

        # create new log
        with open(log_path,'w') as wf:

            json.dump(hpo_phenotype_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('hpo_phenotype',mt)

        bakeupCol('hpo_phenotype_{}'.format(version),'hpo_phenotype',_mongodb)

    else:
        print  '{} {} is the latest !'.format('hpo_phenotype',mt)

def selectData(querykey = 'id',value='HP:0011220'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'hpo_phenotype_'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class dbMap(object):

    #class introduction

    def __init__(self,version):

        self.version = version

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb')

        colname = 'hpo_phenotype_{}'.format(version)

        col = db.get_collection(colname)

        self.col = col

        self.docs = col.find({})

        self.colname = colname

    def maphpoid2geneid(self):
            
        hpoid2geneid =dict()
        hpoid2diseaseid = dict()
        diseaseid2hpoid = {'OMIM':{},'ORPHA':{},'DECIPHER':{}}
        diseaseid2geneid= {'OMIM':{},'ORPHA':{}}
        geneid2disease= dict()

        for doc in self.docs:

            hpoid = doc.get('id')

            ORPHA = doc.get('ORPHA')

            OMIM = doc.get('OMIM')

            DECIPHER = doc.get('DECIPHER')

            if  OMIM:

                diseaseid = OMIM.keys()

#----------------diseaseid2hpoid and hpoid2diseaseid-------------------

                for disid in diseaseid:

                    if disid not in diseaseid2hpoid['OMIM']:

                        diseaseid2hpoid['OMIM'][disid] = list()

                    diseaseid2hpoid['OMIM'][disid].append(hpoid)

                if hpoid not in hpoid2diseaseid:

                    hpoid2diseaseid[hpoid] = dict()

                hpoid2diseaseid[hpoid]['OMIM'] = diseaseid

#----------------diseaseid2geneid and hpoid2geneid and geneid2disease-------------------

                for omimid,val in OMIM.items():

                    gene_list = val.get('gene')

                    if not gene_list:
                        continue

                    for gene in gene_list:

                        geneid = gene.get('gene-id(entrez)')
                        genesym = gene.get('gene-symbol')

                        if omimid not in  diseaseid2geneid['OMIM']:
                            diseaseid2geneid['OMIM'][omimid] = list()

                        diseaseid2geneid['OMIM'][omimid].append(geneid)

                        if hpoid not in hpoid2geneid:

                            hpoid2geneid[hpoid] = list()

                        hpoid2geneid[hpoid].append(geneid)

                        if geneid not in geneid2disease:

                            geneid2disease[geneid] = dict()

                        if 'OMIM' not  in geneid2disease[geneid]:

                            geneid2disease[geneid]['OMIM'] = list()

                        geneid2disease[geneid]['OMIM'].append(omimid)


            if  ORPHA:

                diseaseid = ORPHA.keys()

#----------------diseaseid2hpoid and hpoid2diseaseid-------------------

                for disid in diseaseid:

                    if disid not in diseaseid2hpoid['ORPHA']:

                        diseaseid2hpoid['ORPHA'][disid] = list()

                    diseaseid2hpoid['ORPHA'][disid].append(hpoid)

                if hpoid not in hpoid2diseaseid:

                    hpoid2diseaseid[hpoid] = dict()

                hpoid2diseaseid[hpoid]['ORPHA'] = diseaseid

#----------------diseaseid2geneid and hpoid2geneid and geneid2disease-------------------

                for orphaid,val in ORPHA.items():

                    gene_list = val.get('gene')

                    if not gene_list:
                        continue

                    for gene in gene_list:

                        geneid = gene.get('gene-id(entrez)')
                        genesym = gene.get('gene-symbol')

                        if orphaid not in  diseaseid2geneid['ORPHA']:
                            diseaseid2geneid['ORPHA'][orphaid] = list()

                        diseaseid2geneid['ORPHA'][orphaid].append(geneid)

                        if hpoid not in hpoid2geneid:

                            hpoid2geneid[hpoid] = list()

                        hpoid2geneid[hpoid].append(geneid)

                        if geneid not in geneid2disease:

                            geneid2disease[geneid] = dict()

                        if 'ORPHA' not  in geneid2disease[geneid]:

                            geneid2disease[geneid]['ORPHA'] = list()

                        geneid2disease[geneid]['ORPHA'].append(orphaid)

            if  DECIPHER:

                diseaseid = DECIPHER.keys()

                for disid in diseaseid:

                    if disid not in diseaseid2hpoid['DECIPHER']:

                        diseaseid2hpoid['DECIPHER'][disid] = list()

                    diseaseid2hpoid['DECIPHER'][disid].append(hpoid)

                if hpoid not in hpoid2diseaseid:

                    hpoid2diseaseid[hpoid] = dict()

                hpoid2diseaseid[hpoid]['DECIPHER'] = diseaseid
        
        geneid2hpoid = value2key(hpoid2geneid)

        map_dir = pjoin(hpo_phenotype_map,self.colname)

        createDir(map_dir)

        save = {'hpoid2diseaseid':hpoid2diseaseid,'diseaseid2hpoid':diseaseid2hpoid,
                        'diseaseid2geneid':diseaseid2geneid,'geneid2disease':geneid2disease,
                        'hpoid2geneid':hpoid2geneid,'geneid2hpoid':geneid2hpoid}

        for name,dic in save.items():

            if name in ['diseaseid2geneid','diseaseid2hpoid','geneid2disease']:
                dic = dedupDicVal(dic)

            elif name in ['geneid2hpoid']:
                for key,val in dic.items():
                    dic[key] = list(set(val))
                    
            with open(pjoin(map_dir,'{}.json'.format(name)),'w') as wf:
                json.dump(dic,wf,indent=2)

    def mapping(self):

        self.maphpoid2geneid()

class hpo_parser(object):
    """docstring for hpo_parser"""
    def __init__(self, date):

        super(hpo_parser, self).__init__()

        self.date = date

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

    def getMt(self):

        headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36'}

        web = requests.get(hpo_download_web,headers = headers,verify=False)

        soup = bs(web.content,'lxml')

        h1 = soup.find(name='h1',attrs={'class':'build-caption page-headline'})

        mt = h1.text.strip().split('\n')[1].strip().split(')')[0].split('(')[1].strip().replace(':','').replace(' ','').replace(',','')

        return mt  
    
    def wget(self,url,mt,rawdir):

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

        return storefilepath

    def info(self,filepath,fileversion):

        colname = 'hpo.phenotype.info'

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'hp.obo'})

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

                    col.insert(aset)
                     
                    print 'hpo_phenotype line','obo',n

                aset = dict()

            else:

                line = line.strip()

                if  bool(line):

                    (key,val) = tuple(line.strip().split(':',1))

                    key = key.strip()
                    val = val.strip()

                    if key in ['name','id']:

                        aset[key] = val

                    else:

                        if key not in aset:

                            aset[key] = list()

                        aset[key].append(val)

            n += 1

        if aset:

            col.insert(aset)
                     
            print 'hpo.phenotype.info line','obo',n

        print 'hpo.phenotype.info completed! '

    def disgene(self,filepath,fileversion):

        colname = 'hpo.phenotype.disgene'

        col = self.db.get_collection(colname)

        if not col.find_one({'dataVersion':fileversion}):
            col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'OMIM_ALL_FREQUENCIES_diseases_to_genes_to_phenotypes,ORPHA_ALL_FREQUENCIES_diseases_to_genes_to_phenotypes'})

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

    def disease(self,filepath,fileversion):

        colname = 'hpo.phenotype.disease'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'phenotype_annotation'})

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

    def gene(self,filepath,fileversion):

        colname = 'hpo.phenotype.gene'

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'ALL_SOURCES_ALL_FREQUENCIES_phenotype_to_genes'})

        tsvfile = open(filepath)

        keys = ['HPO-ID','HPO-Name','Gene-ID','Gene-Name']

        n = 0 

        for line in tsvfile:

            if line.startswith('#'):
                continue

            data = line.strip().split('\t')

            dic = dict([(key,val) for key,val in zip(keys,data)])

            col.insert(dic)
              
            print 'hpo.phenotype.gene txt line',n

            n += 1

def main():

    modelhelp = model_help.replace('&'*6,'HPO_Phenotypic').replace('#'*6,'hpo_phenotype')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,hpo_phenotype_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # filepaths,date = downloadData(redownload=True)
    rawdir = '/home/user/project/dbproject/mydb_v1/hpo_phenotype/dataraw/phenotype_171228100957/'
    filepaths = [pjoin(rawdir,filename) for filename in listdir(rawdir)]
    extractData(filepaths,'171227151339')

    # man = dbMap('171212143159')
    # man.mapping()
