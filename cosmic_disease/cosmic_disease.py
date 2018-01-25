#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/28
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

(cosmic_disease_model,cosmic_disease_raw,cosmic_disease_store,cosmic_disease_db,cosmic_disease_map) = buildSubDir('cosmic_disease')

log_path = pjoin(cosmic_disease_model,'cosmic_disease.log')

# main code
def downloadData():

    #function introduction
    #args:
    
    return

def extractData(filepath,date):
    
    process = cosmic_parser(version)

    process.tsv(filepath)
    
    print 'extract and insert completed'
    
    return (filepath,version)

    colhead = 'cosmic.disgene'

    bkup_allCols('mydb_v1',colhead,cosmic_disease_db)

    print 'extract and insert completed'

    return (filepath,date)

def updateData():

    #function introduction
    #args:

    return

def selectData():

    #function introduction
    #args:
    
    return

class cosmic_parser(object):
    """docstring for cosmic_parser"""
    def __init__(self, date):

        super(cosmic_parser, self).__init__()

        self.date = date

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

        self.date = date    

    def tsv(self):

        fileversion = ''

        tsvfile = open('/home/user/project/dbproject/mydb_v1/cosmic_disease/dataraw/cgc_final_anno.result.tsv')

        colname = 'cosmic.disgene'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        
        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'cgc_final_anno.result'})
        n = 0
        for line  in tsvfile:

            data = line.strip().split('\t')

            symbol = data[0]

            cosmicinfo = data[1]

            cosmic_dic = eval(cosmicinfo)

            col.insert(cosmic_dic)

            n += 1

            print 'cosmic.disgene line',n
    
class dbMap(object):

    #class introduction

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
        this function is to create a mapping relation between cosmic disease id  with HGNC Symbol
        '''
        # because cosmic gene id  is entrez id 
        entrez2symbol = self.process.entrezID2hgncSymbol()

        cosmic_disgene_gene_col = self.db_cols.get('cosmic.disgene')

        cosmic_disgene_gene_docs = cosmic_disgene_gene_col.find({})

        output = dict()

        hgncSymbol2cosmicDiseaseID = output

        for doc in cosmic_disgene_gene_docs:

            gene_id = doc.get('Entrez GeneId')

            gene_symbol = entrez2symbol.get(gene_id)
            
            if gene_symbol:

                for symbol in gene_symbol:

                    if symbol not in output:

                        output[symbol] = list()

                    output[symbol].append(gene_id)

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val    

        print 'hgncSymbol2cosmicDiseaseID',len(output)

        # with open('./hgncSymbol2cosmicDiseaseID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return (hgncSymbol2cosmicDiseaseID,'Entrez GeneId')
        
class dbFilter(object):

    """docstring for dbFilter"""

    def __init__(self):
        super(dbFilter, self).__init__()
        
    def gene_topic(self,doc):

        save_keys = ['Entrez GeneId','Somatic','Germline','Tumour Types(Somatic)','Tumour Types(Germline)','Cancer Syndrome','Tissue Type','Molecular Genetics','Role in Cancer','Mutation Types','Translocation Partner','Other Germline Mut','Other Syndrome','Hallmark','HallmarkInfo','categories']
        return filterKey(doc,save_keys)


def main():

    modelhelp = 'help document'

    funcs = (downloadData,extractData,updateData,selectData,dbMap,cosmic_disease_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # extractData('./','')
    # man = cosmic_parser('171220100108')
    # man.tsv()
    # man = dbMap()
    # man.dbID2hgncSymbol()