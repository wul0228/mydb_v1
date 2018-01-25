#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/1/16
# author:wuling
# emai:ling.wu@myhealthgene.com

'''
this model is set to generate standard doc file for sub model 
'''
import os
import json

current_path = os.path.split(os.path.abspath(__file__))[0]

class doc(object):
    """docstring for doc"""
    def __init__(self):

        super(doc, self).__init__()

        framdoc_dir = './_docs/_fram_180111094241/'

        self.framdoc_dir = framdoc_dir

    def dbDoc(self):

        doc_dir = './_docs/'

        dbs = list(set(['.'.join(filename.split('fram_')[1].split('.')[:2]) for filename in os.listdir(self.framdoc_dir)]))

        db_framfiles = dict()

        for db in dbs:
            frams = [os.path.join(self.framdoc_dir,filename) for filename in os.listdir(self.framdoc_dir) if filename.startswith('fram_{}.'.format(db))]
            db_framfiles[db] = frams

        go_info = db_framfiles.pop('go.info')
        go_anno = db_framfiles.pop('go.geneanno')
        db_framfiles['go'] = [go_info[0],go_anno[0]]

        dbs.remove('go.info')
        dbs.remove('go.geneanno')
        dbs.append('go')

        for db in dbs:

            docpath = doc_dir + '{}.readme'.format(db)
            readme = open(docpath,'w')
            
            head = True

            print db

            for framfile in db_framfiles.get(db):

                print framfile.rsplit('/',1)[1].strip()
                # try:
                # file = json.load(open(framfile))
                file = eval(open(framfile).read())

                db_name = file.pop('_db_name')
                db_des = file.pop('_db_description').replace('||||','\n'+'\t'*2).replace('////','\n' + '\t'*3).replace('----','\n' + '\t'*4)

                if head:
                    readme.write('*'*100 + '\n')
                    readme.write(db_name +'\n'*2 )
                    readme.write(db_des +'\n'*2 )

                    head = False

                subdb_name = file.pop('_subdb_name')
                subdb_des = file.pop('_subdb_description').replace('||||','\n'+'\t'*2).replace('////','\n' + '\t'*3).replace('----','\n' + '\t'*4)

                readme.write('='*80 +'\n' )
                readme.write(subdb_name +'\n'*2 )
                readme.write(subdb_des +'\n'*2 )

                readme.write('-'*100 +'\n' )

                for key,val in file.items():
                    readme.write(key + ':'+'\n')

                    val = val.replace('||||','\n'+'\t'*2).replace('////','\n' + '\t'*3).replace('----','\n' + '\t'*4)

                    readme.write('\t'*2 + val +'\n'*2)
                readme.write('\n' )

def main():
    man = doc()
    man.dbDoc()

if __name__ == '__main__':
    main()