#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/1/9
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to create gene topic db based on sub model
import os
import sys
sys.path.append('../../')
sys.setdefaultencoding = ('utf-8')
from pymongo import  MongoClient


def initDB(db):

    conn = MongoClient('localhost',27017)

    db = conn.get_database(db)

    cols = db.collection_names()

    db_cols = dict()

    db_colnames = dict()

    for colname in cols:

        modelname = colname.rsplit('_',1)[0].strip()

        db_cols[modelname] = db.get_collection(colname)

        # db_colnames[modelname] = colname

    # return (db,db_cols,db_colnames)
    return (db,db_cols)