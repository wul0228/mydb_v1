#!/usr/bin/env python
# ---coding:utf-8---
# date:20171123
# author:wuling
# emai:ling.wu@myhealthgene.com

# this model is set to
__all__ = ['manage_help','common_help','model_help','py_template','model_intros']

manage_help = '''

Usage: python manage.py  [OPTION]...[MODELNAME]...

Manage model and sub-model 

options:

-h, --help                :give this help

-i, --init    [modelname] :init a new model and create sub-model

-u,--update  [modelname] :update a model in current directory,if modelname=all,update all

-d, --database [modelname] : query data record from this model

-f, --field               : look for specified database with this field

-v, --value               : look for all database with filed = value

-o,-- output              : the  directory  path to store query result 
    eg:
        python manage.py  -d  ensembl  -f  gene_name  -v  TP53 -o  _result/
'''

common_help = '''
'''
model_help ='''
Usage: python mydb_v1  [OPTION]...[NAME]...

Download,extract,standar,insert and update &&&&&& automatically

-h, --help               :give this help
-a, --all                :excute download,extract, and insert data
-u, --update             :update ###### database
-f, --field              :look for database with this field
'''
py_template = '''

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

(******_model,******_raw,******_store,******_db,******_map) = buildSubDir('******')

log_path = pjoin(******_model,'******.log')

# main code
def downloadData():

    #function introduction
    #args:
    
    return

def extractData():
    
    #function introduction
    #args:
    
    return

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

def main():

    modelhelp = 'help document'

    funcs = (downloadData,extractData,updateData,selectData,dbMap,******_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()

'''

model_intros = '''
++++++ mydb_v1 Documentation ++++++

edited@xxxxxx

please direct all questions to author@xxxxxx.com

1. brief introduction of sub-files

2. description about mydb_v1-parser

the main job of mydb_v1-parser is to

Functions
 
(1) downloadData(redownload = False)
    ===function : download the raw data from mydb_v1 FTP WebSite
    ===parameter:
         redownload ~ default False, check to see if exists an old edition before download
                    ~ if set to true, download directly with no check

(2) extractData()
    ===function :
    ===parameter:

(3) standarData(filepath)
    ===function :
    ===parameter:

(4) insertData()
    ===function : 
    ===parameter:

(5) updateData(insert=True)
    ===function :
    ===parameter:

(6) selectDate():
    ===function :
    ===parameter:
       
Design  

Usage: python mydb_v1.py  [OPTION]...[NAME]...

Download,extract,standar,insert and update data automatically

-h, --help                         :give this help
-a, --all                             :excute download,extract,standar and insert
-u, --update                     :update database
-q, --query  [filedname]  :select data from mongodb      

++++++ mydb_v1  Documentation ++++++
'''