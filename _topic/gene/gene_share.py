#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/1/19
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to create gene topic db based on sub model
import os
import sys
sys.path.append('../../')
sys.setdefaultencoding = ('utf-8')
from pymongo import  MongoClient
from gene_config import *


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

class doc(object):
    """docstring for doc"""
    def __init__(self):

        super(doc, self).__init__()

        framdoc_dir = '../../_docs/_fram_180111094241/'

        self.framdoc_dir = framdoc_dir

    def geneDoc(self):
        '''
        this function is set to build gene topic readme file with  sub model doc and  gene_config file
        '''
        genedoc = open('../_docs/gene_topic21.readme','w')
        genedoc.write('*'*100 + '\n')
        genedoc.write('GENE' +  '\n'*2)


        # get colname 2 col doc dict
        col_doc = dict()

        for filename in os.listdir(self.framdoc_dir):

            colname = filename.split('fram_')[1].split('.json')[0].strip()

            filepath = os.path.join(self.framdoc_dir,filename)

            doc_dic =eval(open(filepath).read())

            col_doc[colname] = doc_dic

        # get gene topic filed from gene_config  according to the final format 
        for anno_class in annotationClass: # like basicinfo
            genedoc.write('='*80 +  '\n')
            genedoc.write(anno_class +  '\n'*2)

            models = annotationClass_models.get(anno_class)  #like [ncbi_gene,hgnc_gene]


            for model in models:  #ncbi_gene
                model_def =    False

                genedoc.write('-'*100 +  '\n')
                genedoc.write(standardDBName.get(model) +  '\n'*2)
                
                cols = model_cols.get(model) #[ncbi.gene.info,necb.gene.expression]
                writekey = list()

                for col in cols: #ncbi.gene.info
                    print col
                    col_key = col_savekeys.get(col) #[GeneID,...]
                    key_def = col_doc.get(col)

                    # add the model description  like ncbi_gene's _db_description
                    if not model_def:
                        _db_def =  key_def.get('_db_description').replace('||||','\n'+'\t'*2).replace('////','\n' + '\t'*3).replace('----','\n' + '\t'*4)
                        if _db_def:
                            genedoc.write(_db_def +  '\n'*2)
                            genedoc.write('~'*30 +  '\n'*2)
                            model_def = True

                    if key_def:
                        for key in col_key:
                            if key not in writekey: # both [ncbi.gene.info,necb.gene.expression] have the filed GeneID ,just write once
                                writekey.append(key)
                                genedoc.write(key +':' +   '\n'*2)
                                defs = key_def.get(key,'').replace('||||','\n'+'\t'*2).replace('////','\n' + '\t'*3).replace('----','\n' + '\t'*4)
                                genedoc.write('\t'*2  + defs  +   '\n'*2)

                    else:
                        print '!!!!!!!!!!!!!!!!!!!!!!!!!!',col

            genedoc.flush()

        genedoc.close()

        print 'gene.readme generated ! the filepath:  {}'.format('\"../_docs/gene.readme\"')

def main():
    man = doc()
    man.geneDoc()

if __name__ == '__main__':
    main()