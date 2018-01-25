#!/usr/bin/env python
# ---coding:utf-8---
# date:20171123
# author:wuling
# emai:ling.wu@myhealthgene.com

# this model is set to
__all__ = ['manage_help','common_help','model_help','model_py','model_readme']

manage_help = '''

Usage: python manage.py  [OPTION]...[MODELNAME]...

Manage model and sub-model 

options:

-h, --help                 :give this help

-c, --collections          :show all collection in mydb

-i, --init     [modelname] :init a new model and create sub-model

-u,--update    [modelname] :update a model in current directory,if modelname=all,update all

-d, --database [modelname] : query data record from this model

-f, --field    [fieldname] : look for specified database with this field

-v, --value    [fieldvalue]: look for all database with filed = value

-o,-- output   [outdirec]  : the  directory  path to store query result 
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

model_py = '''

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

class parser(object):

    #this class is set to parser all raw file to extract content we need and insert to mongodb

    super(parser,self).__init__()

    def __init__(self):
        pass

class dbMap(object):

    # this class is set to map xxxxxx to other db

    super(dbMap,self).__init__()

    def __init__(self):
        pass

class dbFilter(object):

    #this class is set to filter part field of data in collections  in mongodb

    super(dbFilter,self).__init__()

    def __init__(self):
        pass

def main():

    modelhelp = 'help document'

    funcs = (downloadData,extractData,updateData,selectData,dbMap,******_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()

'''

model_readme = '''

++++++ ,****** Documentation ++++++

edited@xxxxxx

please direct all questions to author@xxxxxx.com

1. brief introduction of sub-files
.
├── database                 ---- contains the all version of collection 
├── datamap                  ---- contains the map relation between ****** with other db
├── dataraw                   ---- contains the raw data from xxxxxx site
├── datastore                 ---- contains the standard data convert from to  dataraw 
├── __init__.py                ---- the inited  file of package
├── __init__.pyc               ----the compiled file of  __init__.py
├── ******.log          ---- contains the database version,update date,model version
├── ******.py           ---- contains the main code of ******.'s process
├── ******.pyc          ----the compiled file of  ******.py
└── ******.readme  ---- model  introduction

2. description about ******-parser

the main job of ******-parser is to
 
Functions
 
(1) downloadData(redownload = False)
    description : download the raw data from xxxxxx 
    args:
        redownload ~ default False, check to see if exists an old edition before download
                               ~ if set to true, download directly with no check

(2) extractData(filepaths,date)
    description : this function is set to distribute all filepath to parser to process
    args:
        filepaths ~ all filepaths to be parserd
        date        ~ the date of  data download

(3) updateData(insert=True)
    description :this function is set to update all file in log
    args:
        insert ~ default False,with no extract  after download data
                   ~ if set tp true, extract all after download

(4) selectDate(querykey,queryvalue):
    description : supply a interface to select data from database
    args:
        querykey    ~ the filed name 
        queryvalue ~ the field value

Class

(1) parser
    
    description: parser all raw file to extract content we need and insert to mongodb
    
    functions:
        eg:
        a. getOne(self,ncbi_gene_ftp_infos,filename,rawdir)
            description:download  one file under  a given remote dir 
            args:
                ncbi_gene_ftp_infos ~ a specified ftp cursor  
                filename ~ the name of file need download
                rawdir ~ the directory to save download file

        b. gene_info(self,filepaths)
            description:  parser gene info files and  insert to mongdb
            args:
                filepaths ~ filepath of gene info files

(2) dbMap

    description: map xxxxxx to other db

    functions:

        a. dbID2xxxxxx(self)
            description:create a mapping relation between xxxxxx  with xxxxxx
            args:

(3) dbFilter

    description:  filter part field of data in collections  in mongodb

    functions:

        a. gene_topic(self)
            description: filter parts of filed of specified doc for gene topic creation 
            args:          

Design  

(1) downloadData
  
    1. download gene_group ,gene_neibors, gene_pubmed ,gene_info
    2. download gene_expression (get filename→ download )
    3. download refseq filenames (get filename→ download )
    4. generate a log file in current  path
    5. generate a record (.files) file in model database directory

(2) extractData
    
    1. distribute filepaths for parser
    2. parser filepaths step by step
    3. backup all collections
        
(3) updateData
    
    1. load the log file
    2. get the latest updated version from remote site
    3. compare with current local version in log file
    4. if remote updated, download from ftp site and store raw data into /dataraw/,then create a log,else End

(4) parser
    
    1. connect mongodb
    2. before create a col ,delete the col with the same name or the old edition
    3. create a col ,and create a index in col with the main identifier of this db model
    4. add a version doc in col head
    5. parser file content and insert data oneby one

(5) dbMap
    
    dbID2hgncSymbol
        1. connect mongodb
        2. get the map relation of entrez_id with hgnc_symbol
        3. map ncbi gene id to hgnc symbol

(6) dbFilter


Usage: python ******.py  [OPTION]...[NAME]...

Download,extract,standar,insert and update data automatically

-h, --help                         :give this help
-a, --all                             :excute download,extract,standar and insert
-u, --update                     :update database
-f, --field  [filedname]    :select data from mongodb      

++++++ ******.  Documentation ++++++
'''