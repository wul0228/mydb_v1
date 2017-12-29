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

def extractData(filepath,version):
    
    process = disgenet_parser(version)

    process.tsv(filepath)
    
    print 'extract and insert completed'
    
    return (filepath,version)

def updateData():

    #function introduction
    #args:

    return

def selectData():

    #function introduction
    #args:
    
    return

class dbMap(object):

    #class introduction

    def __init__(self):
        pass


    def mapXX2XX(self):
        pass

    def mapping(self):

        self.mapXX2XX()

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
     
def main():

    modelhelp = 'help document'

    funcs = (downloadData,extractData,updateData,selectData,dbMap,cosmic_disease_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # man = cosmic_parser('171220100108')
    # man.tsv()
