#!/usr/bin/env python
# -*-coding:utf-8-*-
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

(dgidb_drug_model,dgidb_drug_raw,dgidb_drug_store,dgidb_drug_db,dgidb_drug_map) = buildSubDir('dgidb_drug')

log_path = pjoin(dgidb_drug_model,'dgidb_drug.log')

# main code

def downloadOne(url,page,per_page,name,mt,rawdir):

    _url = url.replace('[count]',str(per_page)).replace('[page]',str(page+1))

    _page = requests.get(_url).content

    _json = json.loads(_page)

    savename = '{}_{}_{}_{}.json'.format(name,str(page+1),mt,today)

    storefilepath = pjoin(rawdir,savename)

    with open(storefilepath,'w') as wf:

        json.dump(_json,wf,indent=8)

def downloadData(redownload = False):
    '''
    this function is to download the raw data from go dgidb FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existgoFile) = lookforExisted(dgidb_drug_raw,'variant')

        if choice != 'y':
            return

    if redownload or not existgoiFle or  choice == 'y':

        rawdir = pjoin(dgidb_drug_raw,'drug_{}'.format(today))
        createDir(rawdir)

        process = dgidb_parser(today)

        mt = process.getMt()

        download_urls = process.getAPI()

        key_name = {'drug_url':'dgidb_drug','inter_url':'dgidb_interaction'}

        for key,val  in download_urls.items():

            url = val[0]
            per_page = val[1].get('per_page')
            total_pages = val[1].get('total_pages')
            total_count = val[1].get('total_count')

            func = lambda x : downloadOne(url,x,per_page,key_name[key],mt,rawdir)

            multiProcess(func,list(range(int(total_pages))),size=50)

    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:
            json.dump({'dgidb_drug':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'

    filepaths = [pjoin(rawdir,filename) for filename in listdir(rawdir)]

    return (filepaths,today)

def extractData(filepaths,date):

    fileversion =psplit(filepaths[0])[1].rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

    process = dgidb_parser(date)

    drugpaths,interpaths = [],[]

    for filepath in filepaths:
    
        filename = psplit(filepath)[1].strip()

        if filename.startswith('dgidb_drug'):

            drugpaths.append(filepath)

        elif filename.startswith('dgidb_interaction'):

            interpaths.append(filepath)

    process.info(drugpaths,fileversion)

    process.gene(interpaths,fileversion)

    colhead = 'dgidb.drug'

    bkup_allCols('mydb_v1',colhead,dgidb_drug_db)

    print 'extract and insert completed'

    return (filepaths,date)

def updateData(insert=False,_mongodb='../_mongodb/'):

    dgidb_drug_log = json.load(open(log_path))

    process = dgidb_parser(today)

    mt = process.getMt()

    if mt != dgidb_drug_log['dgidb_drug'][-1][0]:

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        dgidb_drug_log['dgidb_drug'].append((mt,today,model_name))

        # create new log
        with open(log_path,'w') as wf:

            json.dump(dgidb_drug_log,wf,indent=8)

        print  '{} \'s new edition is {} '.format('dgidb_drug',mt)
        
    else:

        print  '{} {} is the latest !'.format('dgidb_drug',mt)

def selectData():

    #function introduction
    #args:
    
    return
class dgidb_parser(object):
    """docstring for dgidb_parser"""
    def __init__(self, date):

        super(dgidb_parser, self).__init__()

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.db = db

    def getMt(self):

        web = requests.get(dgidb_api_web,headers=headers,verify=False)

        soup = bs(web.content,'lxml')

        footer = soup.find(attrs={'id':'footer'})

        p = footer.find(name='p').text

        mt = p.split('(',1)[1].split('-',1)[0].strip()

        return mt

    def getAPI(self):

        web = requests.get(dgidb_api_web,headers=headers,verify=False)

        soup = bs(web.content,'lxml')

        #---------------------------------------------------------------------------------------------------------------------------------
        drug = soup.find(attrs={'id':'all-drugs'})

        drug_get = drug.find(text='GET')

        drug_api =  drug_get.findNext(name='pre').text.split('<parameters>')[0].strip()

        if not drug_api.startswith('http://'):

            drug_api = dgidb_web + drug_api

        print 'drug_api : ',drug_api

        drug_page = requests.get(drug_api).content

        drug_page_json = json.loads(drug_page)

        drug_meta = drug_page_json.get('_meta')

        drug_link = drug_meta.get('links',{}).get('next')

        drug_url = drug_link.split('count=')[0] +'count=[count]&page=[page]' 

        print 'drug_url : ',drug_url

        #---------------------------------------------------------------------------------------------------------------------------------

        inter = soup.find(attrs={'id':'search-interactions'})

        inter_get = inter.find(text='GET')

        inter_api =  inter_get.findNext(name='pre').text.split('<parameters>')[0].strip()

        if not inter_api.startswith('http://'):

            inter_api = dgidb_web + inter_api
            
        print 'inter_api : ',inter_api

        inter_page = requests.get(inter_api).content

        inter_page_json = json.loads(inter_page)

        inter_meta = inter_page_json.get('_meta')

        inter_link = inter_meta.get('links',{}).get('next')

        inter_url = inter_link.split('count=')[0] +'count=[count]&page=[page]' 

        print 'inter_url : ',inter_url  

        return {'drug_url':(drug_url,drug_meta),'inter_url':(inter_url,inter_meta)}

    def info(self,filepaths,fileversion):

        colname = 'dgidb.drug.info'

        delCol('mydb_v1',colname)

        info_col = self.db.get_collection(colname)
        
        info_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'dgidb_drug'})

        # reocords keys include [u'name', u'chembl_id', u'immunotherapy', u'alias', u'anti_neoplastic', u'fda_approved']

        page_num = 0

        drug_num = 0 

        for filepath in filepaths:

            jsonfile = json.loads((open(filepath)).read())

            drug_records = jsonfile.get('records')

            [drug.update({'drug_name':'{}'.format(drug.pop('name'))}) for drug in drug_records]
            [drug.update({'chembl_id_link':'https://www.ebi.ac.uk/chembl/compound/inspect/{}'.format(drug.get('chembl_id'))}) for drug in drug_records]
            [drug.update({'drug_link':'http://www.dgidb.org/drugs/{}'.format(drug.get('drug_name'))}) for drug in drug_records]

            drug_num += len(drug_records)

            info_col.insert(drug_records)

            page_num += 1

            print  'dgidb.drug.info page',page_num

        print 'drug_num',drug_num

    def gene(self,filepaths,fileversion):

        gene_colname = 'dgidb.drug.gene'

        delCol('mydb_v1',gene_colname)

        gene_col = self.db.get_collection(gene_colname)
        
        gene_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'dgidb_interation'})

        page_num = 0

        inter_num = 0

        dgidb_type_implication = constance('dgidb')

        # [u'entrez_id', u'sources', u'chembl_id', u'drug_name', u'publications', u'id', u'gene_name', u'interaction_types']
        for filepath in filepaths:

            jsonfile = json.loads((open(filepath)).read())

            gene_records = jsonfile.get('records')

            for gene in gene_records:

                gene['entrez_id'] = str(gene.pop('entrez_id'))
                
                _inter_types = list()

                interaction_types = gene.get('interaction_types')

                for inter_type in interaction_types:

                    _inter_types.append({'type':inter_type,'type_implication':dgidb_type_implication.get(inter_type)})

                gene['interaction_types'] = _inter_types

            inter_num += len(gene_records)

            gene_col.insert(gene_records)

            page_num += 1

            print  'dgidb.drug.gene',page_num

        print 'inter_num',inter_num

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
        this function is to create a mapping relation between disgenet disease id  with HGNC Symbol
        '''
        # because disgenet gene id  is entrez id 
        entrez2symbol = self.process.entrezID2hgncSymbol()

        dgidb_drug_col = self.db_cols.get('dgidb.drug.gene')

        dgidb_drug_docs = dgidb_drug_col.find({})

        output = dict()

        hgncSymbol2dgidbDrugID = output

        for doc in dgidb_drug_docs:

            chembl_id = doc.get('chembl_id')

            gene_id = doc.get('entrez_id')

            gene_symbol = entrez2symbol.get(str(gene_id))

            if gene_symbol:

                for symbol in gene_symbol:

                    if symbol not in output:

                        output[symbol] = list()

                    output[symbol].append(chembl_id)

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val    

        print 'hgncSymbol2dgidbDrugID',len(output)

        with open('./hgncSymbol2dgidbDrugID.json','w') as wf:
            json.dump(output,wf,indent=8)

        return (hgncSymbol2dgidbDrugID,'chembl_id')

class filter(object):
    """docstring for gene_topic"""
    def __init__(self):

        super(filter, self).__init__()
    
    def gene_topic_info(self,doc):

        save_keys = ['drug_name','drug_link ','chembl_id','immunotherapy','chembl_id_link','alias','anti_neoplastic','fda_approved']

        return filterKey(doc,save_keys)

    def gene_topic_gene(self,doc):

        save_keys = ['entrez_id','drug_name ','chembl_id','sources','publications','interaction_types']

        return filterKey(doc,save_keys)
        
def main():

    modelhelp = 'help document'

    funcs = (downloadData,extractData,updateData,selectData,dbMap,dgidb_drug_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':

    main()
    # updateData()
    # downloadData(redownload=True)
    # rawdir  ='/home/user/project/dbproject/mydb_v1/dgidb_drug/dataraw/drug_180104152534/'

    # date = '180104152534'

    # filepaths = [pjoin(rawdir,filename) for filename in listdir(rawdir)]

    # extractData(filepaths,date)

    # f = open('/home/user/project/dbproject/mydb_v1/dgidb_drug/dataraw/dgidb_drug_v3.0.1_180104135642.json').read()
    # print f.count("name")
#     man = dbMap()
#     man.dbID2hgncSymbol()

#     doc = {
#     "entrez_id" : 3326,
#     "drug_name" : "RETASPIMYCIN",
#     "chembl_id" : "CHEMBL1184904",
#     "sources" : [
#         "MyCancerGenome",
#         "TdgClinicalTrial"
#     ],
#     "publications" : [ ],
#     "id" : "26f9aa35-c529-412d-a7fc-33795930f9af",
#     "gene_name" : "HSP90AB1",
#     "interaction_types" : [
#         {
#             "type_implication" : "In inhibitor interactions, the drug binds to a target and decreases its expression or activity. Most interactions of this class are enzyme inhibitors, which bind an enzyme to reduce enzyme activity.  Wikipedia - Enzyme Inhibitor",
#             "type" : "inhibitor"
#         }
#     ]
# }
    
#     man = filter()
#     print man.gene_topic_gene(doc)


# drug_api http://dgidb.orghttp://dgidb.org/api/v2/drugs