#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/08
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  set  to download,extract,standard insert and select gene data from proteinAtlas

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(proteinAtlas_model,proteinAtlas_raw,proteinAtlas_store,proteinAtlas_db,proteinAtlas_map) = buildSubDir('proteinAtlas')

log_path = pjoin(proteinAtlas_model,'proteinAtlas.log')

# main code
def downloadData(redownload=False):
    '''
    this function is to download the raw data from go gene FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existgoFile) = lookforExisted(proteinAtlas_raw,'proteinatlas')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        process = protein_parser(today)
    
        download_url,mt = process.getMt()   

        filepath = process.wget(download_url,mt,proteinAtlas_raw)

    if not os.path.exists(pjoin(proteinAtlas_model,'proteinAtlas.log')):

        with open(log_path,'w') as wf:
            json.dump({'proteinAtlas':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'

    return (filepath,today)

def extractData(filepath,date):

    filename = psplit(filepath)[1].strip()

    fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
    
    process = protein_parser(date)

    process.tsv(filepath,fileversion)

    # bkup all collections

    colhead = 'proteinatlas'

    bkup_allCols('mydb_v1',colhead,proteinAtlas_db)    

    print 'extract and insert completed'

    return (filepath,version)
    
def updateData(insert=False,_mongodb=proteinAtlas_db):

    proteinAtlas_log = json.load(open(log_path))

    process = protein_parser(today)

    (download_url,mt) = process.getMt()

    if mt != proteinAtlas_log['proteinAtlas'][-1][0]:

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        proteinAtlas_log['proteinAtlas'].append((mt,today,model_name))
        # create new log
        with open('./proteinAtlas.log','w') as wf:

            json.dump(proteinAtlas_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('proteinAtlas',mt)

        return 'update successfully'

    else:
        print  '{} is the latest !'.format('proteinAtlas')

        return 'new version is\'t detected'

def selectData(querykey = 'Ensembl',value='ENSG00000000003'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'proteinAtlas_'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class protein_parser(object):

    def __init__(self, date):

        self.date = date

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

    def getMt(self):

        headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36',}

        web = requests.get(protein_atlas_download_web,headers = headers,verify=False)

        soup = bs(web.content,'lxml')

        down = soup.find(text = 'proteinatlas.tsv.zip')

        a = down.findParent('a')

        href = a.attrs.get('href')

        tr = a.findParent('tr')

        mt = tr.text.split('version')[1].strip().split(' ')[0].strip()

        download_url = 'https://www.proteinatlas.org/' + href

        return (download_url,mt)

    def wget(self,url,mt,rawdir):

        filename = url.rsplit('/',1)[1].strip().replace('.tsv.zip','')

        savename = '{}_{}_{}.tsv.zip'.format(filename,mt.replace('.','*'),today)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,url)

        os.popen(command)

        # unzip file
        unzip = 'unzip -d {}  "{}" '.format(rawdir,storefilepath)

        os.popen(unzip)

        savefilepath = storefilepath.replace('.tsv.zip','.tsv',1)

        os.rename(pjoin(rawdir,'proteinatlas.tsv'),savefilepath)

        os.remove(storefilepath)

        return savefilepath

    def tsv(self,filepath,fileversion):

        colname = 'proteinatlas.geneanno'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'proteinAtlas'})        

        tsvfile = open(filepath)

        n = 0

        for line in tsvfile:

            if  n == 0:

                keys = [i.strip().replace(' ','&').replace('.','*') for i in line.strip().split('\t')]

            else:

                data =[i.strip() for i in  line.split('\t')]

                dic = dict([(key,val) for key,val in zip(keys,data)])


                synonym =  [i.strip() for i in dic.pop('Gene&synonym').split(',')]

                protein_class = [i.strip() for i in dic.pop('Protein&class').split(',')]

                Antibody = [i.strip() for i in dic.pop('Antibody').split(',')]

                Prognostic_p_value = [i.strip() for i in dic.pop('Prognostic&p-value').split(',')]

                RNA_TS_TPM  =  [i.strip() for i in dic.pop('RNA&TS&TPM').split(',')]

                RNA_CS_TPM =  [i.strip() for i in dic.pop('RNA&CS&TPM').split(';')]

                subcell_location = [i.strip() for i in dic.pop('Subcellular&location').split('<br>') if i]

                dic.update({
                    'Gene&synonym':synonym,
                    'Protein&class':protein_class,
                    'Antibody':Antibody,
                    'Prognostic&p-value':Prognostic_p_value,
                    'RNA&TS&TPM':RNA_TS_TPM,
                    'RNA&CS&TPM':RNA_CS_TPM,
                    'Subcellular&location':subcell_location,
                    })

                Ensembl = dic.get('Ensembl')

                Gene = dic.get('Gene')

                if Ensembl and Gene:

                    Prognostic_link = 'https://www.proteinatlas.org/{}-{}/pathology'.format(Ensembl,Gene)

                    dic['Prognostic&link'] = Prognostic_link

                col.insert(dic)

                print 'protein atlas line',n ,dic.get('Gene')

            n += 1

class dbMap(object):

    #class introduction

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
        this function is to create a mapping relation between proteinAtlas ensembl GeneID with HGNC Symbol
        '''

        ensembl2symbol = self.process.ensemblGeneID2hgncSymbol()

        proteinAtlas_col  = self.db_cols.get('proteinatlas.geneanno')

        proteinAtlas_docs = proteinAtlas_col.find({})

        output = dict()
        
        hgncSymbol2proteinAtlasGeneID = output

        for doc in proteinAtlas_docs:

            gene_id = doc.get('Ensembl')

            gene_symbol = ensembl2symbol.get(gene_id)

            if gene_symbol:

                for symbol in gene_symbol:
                    
                    if symbol not in output:
                        output[symbol] = list()

                    output[symbol].append(gene_id)
        
        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val      

        print 'hgncSymbol2proteinAtlasGeneID',len(output)

        # with open('./hgncSymbol2proteinAtlasGeneID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return(output,'Ensembl')

class dbFilter(object):
    """docstring for dbFilter"""
    def __init__(self, arg):
        super(dbFilter, self).__init__()
        self.arg = arg
        
def main():

    modelhelp = model_help.replace('&'*6,'PROTEIN ATLAS').replace('#'*6,'protein atlas')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,proteinAtlas_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # filepath = '/home/user/project/dbproject/mydb_v1/proteinAtlas/dataraw/proteinatlas_18_171225172243.tsv'
    # date = '171225172243'
    # extractData(filepath,date)

    man  = dbMap()
    man.dbID2hgncSymbol()
