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

(miRTarBase_model,miRTarBase_raw,miRTarBase_store,miRTarBase_db,miRTarBase_map) = buildSubDir('miRTarBase')

log_path = pjoin(miRTarBase_model,'miRTarBase.log')

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

        (choice,existgoFile) = lookforExisted(miRTarBase_raw,'miRTarBase')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        process = mirtarbase_parser(today)

        download_url,mt = process.getMt()

        filepath = process.wget(download_url,mt,miRTarBase_raw)

    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:
            json.dump({'miRTarBase':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'

    return (filepath,today)

def extractData(filepath,date):

    filename = psplit(filepath)[1].strip()

    fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

    process = mirtarbase_parser(date)

    process.xlsx(filepath,fileversion)

    colhead = 'mirtarbase'

    bkup_allCols('mydb_v1',colhead,miRTarBase_db)

    print 'extract and insert completed'

    return (filepath,version)

def updateData(insert=False,_mongodb=miRTarBase_db):

    miRTarBase_log = json.load(open(log_path))

    process = mirtarbase_parser(today)

    (download_url,mt) = process.getMt()

    if mt != miRTarBase_log['miRTarBase'][-1][0]:

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        miRTarBase_log['miRTarBase'].append((mt,today,model_name))

        print  '{} \'s new edition is {} '.format('miRTarBase',mt)
        # create new log
        with open('./miRTarBase.log','w') as wf:

            json.dump(miRTarBase_log,wf,indent=2)

    else:
        print  '{} is the latest !'.format('miRTarBase')

def selectData(querykey = 'miRTarBase&ID',value='MIRT042081'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'miRTarBase'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class mirtarbase_parser(object):

    def __init__(self, date):

        # super(mirtarbase_parser, self).__init__()

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.db = db

    def getMt(self):

        headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36',}

        web = requests.get(miRTarbase_download_web,headers = headers,verify=False)

        soup = bs(web.content,'lxml')

        down = soup.find(text = 'miRTarBase Download')

        a =  down.find_next(name='a')

        href  =a.attrs.get('href')

        mt  = href.split('download/')[1].split('/')[0].strip()

        download_url = miRTarbase_homepage + href.split('/',1)[1].strip()

        return (download_url,mt) 

    def wget(self,url,mt,rawdir):

        filename = url.rsplit('/',1)[1].strip().replace('.xlsx','')

        savename = '{}_{}_{}.xlsx'.format(filename,mt.replace('.','*'),today)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,url)

        os.popen(command)

        return storefilepath

    def xlsx(self,filepath,fileversion):

        colname = 'mirtarbase.mirgene'

        delCol('mydb_v1',colname)

        collection = self.db.get_collection(colname)

        collection.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'miRTarBase_MTI'})

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

    #class introduction

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

        with open('./hgncSymbol2mirTarBaseID.json','w') as wf:
            json.dump(output,wf,indent=8)

        return (hgncSymbol2mirTarBaseID,'miRTarBase ID')
    
class filter(object):
    """docstring for gene_topic"""
    def __init__(self):

        super(filter, self).__init__()
    
    def gene_topic(self,doc):

        save_keys = ['Target Gene (Entrez ID)','miRNA','Species (Target Gene)','miRTarBase ID',
                                'References (PMID)','Experiments','Support Type','Target Gene']

        return filterKey(doc,save_keys)

def main():

    modelhelp = model_help.replace('&'*6,'miRTarBase').replace('#'*6,'miRTarBase')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,miRTarBase_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':

    main()

    # filepath = '/home/user/project/dbproject/mydb_v1/miRTarBase/dataraw/miRTarBase_MTI_7*0_171211094532.xlsx'

    # date = '171211094532'

    # extractData(filepath,date)
    man = dbMap()
    man.dbID2hgncSymbol()
    pass