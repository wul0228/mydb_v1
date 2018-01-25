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

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(miRTarBase_model,miRTarBase_raw,miRTarBase_store,miRTarBase_db,miRTarBase_map) = buildSubDir('miRTarBase')

log_path = pjoin(miRTarBase_model,'miRTarBase.log')

# main code
def downloadData(redownload = False):

    '''
    this function is to download the raw data from go gene FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existgoFile) = lookforExisted(miRTarBase_raw,'miRTarBase')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        #---------------------------------------------------------------------------------------------------------
        process = parser(today)
        # 1. get download url and mt
        download_url,mt = process.getMt()

        # 2. download raw file
        filepath = process.getOne(download_url,mt,miRTarBase_raw)
    
    #---------------------------------------------------------------------------------------------------------
    #  generate .log file in current  path

    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:
            json.dump({'miRTarBase':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'
    
    #---------------------------------------------------------------------------------------------------------
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

    process.regulation_info(filepath,fileversion)
    # ----------------------------------------------------------------------------------------------------
    # 3. bkup all collections
    colhead = 'mirtarbase'

    bkup_allCols('mydb_v1',colhead,miRTarBase_db)

    print 'extract and insert completed'

    return (filepath,version)

def updateData(insert=False):
    '''
    this function is set to update all file in log
    '''
    miRTarBase_log = json.load(open(log_path))

    process = parser(today)

    (download_url,mt) = process.getMt()

    if mt != miRTarBase_log['miRTarBase'][-1][0]:

        print 'mt',mt

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        miRTarBase_log['miRTarBase'].append((mt,today,model_name))

        # create new log
        with open('./miRTarBase.log','w') as wf:

            json.dump(miRTarBase_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('miRTarBase',mt)

        return 'update successfully'

    else:
        print  '{} is the latest !'.format('miRTarBase')

        return 'new version is\'t detected'

def selectData(querykey = 'miRTarBase&ID',value='MIRT042081'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'miRTarBase'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):
    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''
    def __init__(self, date):

        # super(parser, self).__init__()

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.db = db

    def getMt(self):
        '''
        this function is set to get the latest version of miRTarBase filefrom miRTarBase web site
        '''
        headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36',}

        web = requests.get(miRTarbase_download_web,headers = headers,verify=False)

        soup = bs(web.content,'lxml')

        down = soup.find(text = 'miRTarBase Download')

        a =  down.find_next(name='a')

        href  =a.attrs.get('href')

        mt  = href.split('download/')[1].split('/')[0].strip().replace('.','*')

        download_url = miRTarbase_homepage + href.split('/',1)[1].strip()

        return (download_url,mt) 

    def getOne(self,url,mt,rawdir):
        '''
        this function is to download  one file with a given url
        args:
        url --   url of raw file download 
        mt --  the latest version of file
        rawdir -- the directory to save download file
        '''
        filename = url.rsplit('/',1)[1].strip().replace('.xlsx','')

        savename = '{}_{}_{}.xlsx'.format(filename,mt.replace('.','*'),today)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,url)

        os.popen(command)

        return storefilepath

    def regulation_info(self,filepath,fileversion):
        '''
        this function is set parser mirgene_info 
        '''
        colname = 'mirtarbase.mirgene'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        collection = self.db.get_collection(colname)

        collection.ensure_index([('miRTarBase ID',1),])

        collection.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'miRTarBase_MTI'})

        #------------------------------------------------------------------------------------------------------------------------------------------------------
        excel = xlrd.open_workbook(filepath)

        for booksheet in excel.sheets():

            keys = list()

            for row in xrange(booksheet.nrows):

                # create keys list
                data = list()

                for col in xrange(booksheet.ncols):

                    cel = booksheet.cell(row, col)

                    val = cel.value

                    if row == 0:
                        keys.append(val)

                    else:
                        data.append(val)

                if row != 0:

                    _data = list()

                    for v in data:
                        if isinstance(v,float):
                            _data.append(str(int(v)))
                        else:
                            _data.append(v)

                    dic = dict([(key,val) for key,val in zip(
                        keys,_data)])

                    collection.insert(dic)

                    print 'miRTarBase line',row,len(dic)

class dbMap(object):
    '''
    this class is set to map ncbi gene id to other db
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
        this function is to create a mapping relation between mirTarBase id  with HGNC Symbol
        '''
        # because disgenet gene id  is entrez id 
        entrez2symbol = self.process.entrezID2hgncSymbol()

        mirtarbase_col = self.db_cols.get('mirtarbase.mirgene')

        mirtarbase_docs = mirtarbase_col.find({})

        output = dict()

        hgncSymbol2mirTarBaseID = output

        for doc in mirtarbase_docs:

            mirtarbase_id = doc.get('miRTarBase ID')

            gene_id = doc.get("Target Gene (Entrez ID)")

            if mirtarbase_id and gene_id:

                gene_symbol = entrez2symbol.get(gene_id)

                if gene_symbol:

                    for symbol in gene_symbol:

                        if symbol not in output:

                            output[symbol] = list()

                        output[symbol].append(mirtarbase_id)

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val    

        print 'hgncSymbol2mirTarBaseID',len(output)

        # with open('./hgncSymbol2mirTarBaseID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return (hgncSymbol2mirTarBaseID,'miRTarBase ID')
    
class dbFilter(object):

    '''this class is set to filter part field of data in collections  in mongodb '''
    
    def __init__(self):

        super(dbFilter, self).__init__()
    
    def gene_topic(self,doc):

        save_keys = ['Target Gene (Entrez ID)','miRNA','Species (Target Gene)','miRTarBase ID',
                                'References (PMID)','Experiments','Support Type','Target Gene']

        return filterKey(doc,save_keys)

def main():

    modelhelp = model_help.replace('&'*6,'miRTarBase').replace('#'*6,'miRTarBase')

    funcs = (downloadData,extractData,updateData,selectData,miRTarBase_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':

    main()

    # # filepath = '/home/user/project/dbproject/mydb_v1/miRTarBase/dataraw/miRTarBase_MTI_7*0_171211094532.xlsx'

    # # date = '171211094532'

    # # extractData(filepath,date)
    # man = dbMap()
    # man.dbID2hgncSymbol()
    # pass