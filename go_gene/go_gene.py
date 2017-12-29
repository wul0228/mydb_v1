#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/25
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download,extract,standard insert and select gene data from go

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(go_gene_model,go_gene_raw,go_gene_store,go_gene_db,go_gene_map) = buildSubDir('go_gene')


log_path = pjoin(go_gene_model,'go_gene.log')

# main code

def downloadOne(go_gene_ftp_infos,filename,rawdir):
    '''
    this function is to download  one file under  a given remote dir 
    args:
    ftp -- a ftp cursor for a specified
    filename --  the name of file need download
    rawdir -- the directory to save download file
    '''
    while  True:

        try:

            ftp = connectFTP(**go_gene_ftp_infos)

            mt =  ftp.sendcmd('MDTM {}'.format(filename)).replace(' ','')

            if not filename.endswith('.gz'):

                savefilename = '{}_{}_{}'.format(filename,mt,today)

            else:
                savefilename = '{}_{}_{}.gz'.format(filename.rsplit('.',1)[0].strip(),mt,today)

            remoteabsfilepath = pjoin(go_gene_ftp_infos['logdir'],'{}'.format(filename))

            save_file_path = ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath)

            print filename,'done'

            return (save_file_path,mt)

        except:

            ftp = connectFTP(**go_gene_ftp_infos)

def downloadData(redownload = False):
    '''
    this function is to download the raw data from go gene FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existgoFile) = lookforExisted(go_gene_raw,'gene')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        rawdir = pjoin(go_gene_raw,'gene_{}'.format(today))

        createDir(rawdir)

        func = lambda x:downloadOne(go_gene_ftp_infos,x,rawdir)

        # download gpa and gpi file
        multiProcess(func,go_gene_filenames,size=16)

        # download obo file
        func = lambda x:downloadOne(go_obo_ftp_infos,x,rawdir)

        multiProcess(func,go_obo_filenames,size=16)

    if not os.path.exists(log_path):

        initLogFile('go_gene',model_name,go_gene_model,rawdir=rawdir)

    update_file_heads =dict()

    for filename in listdir(rawdir):

        head = filename.split('_213')[0].strip()

        update_file_heads[head] = filename


    with open(pjoin(go_gene_db,'gene_{}.files'.format(today)),'w') as wf:
        json.dump(update_file_heads,wf,indent=2)

    #gunzip all file
    gunzip = 'gunzip {}/*'.format(rawdir)

    os.popen(gunzip)

    print  'datadowload completed !'

    filepaths = [pjoin(rawdir,filename) for filename in rawdir]

    return (filepaths,today)

def extractData(filepaths,date):

    for filepath in filepaths:

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

        process = gene_parser(filepath,date)

        if filename.count('gpa'):

            process.gpa(fileversion)

        elif filename.count('obo'):

            process.obo(fileversion)
            
        else:
            pass

        print filename,'done'

    # bkup all collections
    _mongodb = pjoin(go_gene_db,'gene_{}'.format(date))

    createDir(_mongodb)

    colhead = 'go.'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    print 'extract and insert complete '

    return (filepaths,version)

def updateData(insert=False,_mongodb='../_mongodb/'):

    go_gene_log = json.load(open(log_path))

    rawdir = pjoin(go_gene_raw,'gene_{}'.format(today))

    new = False

    filenames = go_gene_filenames + go_obo_filenames

    for filename in filenames:

        if filename.count('gpa'):

            ftp = connectFTP(**go_gene_ftp_infos)
            ftp_infos = go_gene_ftp_infos

        elif filename.count('obo'):

            ftp = connectFTP(**go_obo_ftp_infos)
            ftp_infos = go_obo_ftp_infos

        mt =  ftp.sendcmd('MDTM {}'.format(filename))

        if mt != go_gene_log.get(filename)[-1][0]:

            new = True

            createDir(rawdir)

            downloadOne(ftp_infos,filename,rawdir)

            go_gene_log[filename].append((mt,today,model_name))

            print  '{} \'s new edition is {} '.format(filename,mt)

        else:
            print  '{} {} is the latest !'.format(filename,mt)

    if new:

        with open(log_path,'w') as wf:

            json.dump(go_gene_log,wf,indent=2)

        (latest_file,version) = createNewVersion(go_gene_raw,go_gene_db,rawdir,'gene_',today)

        if insert:

            insertUpdatedData(go_gene_raw,latest_file,'gene_',version,extractData)

def selectData(querykey = 'id',queryvalue='GO:0005765'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'go'

    col_names =[col_name for col_name in  db.collection_names() if col_name.startswith(colnamehead)]

    col_names.sort(key = lambda x:x.split('_')[1].strip())
    
    print  '*'*80
    print 'existed collections','\n'

    for index,ver in enumerate(col_names):

        print  'index {}  edition {} '.format(index,ver)
        print ''

    edition = raw_input('chose edition index or enter to latest : ')

    if edition == '':
        col_name = col_names[-1]
    else:
        # col_name = col_names[-1]
        col_name = col_names[int(edition)]

    col = db.get_collection(col_name)

    print '*'*80

    while True:

        queryvalue = str(raw_input('input %s  (q to quit) : ' %  querykey))
        
        if queryvalue == 'q' or queryvalue =='Q':

            break

        else:
            # select with go id
            if querykey == 'id':

                # get go_id basic info
                basic_docs = col.find({querykey:queryvalue})
               
               # gene annotation info
                annotation_docs = col.find({'GO.{}'.format(queryvalue):{'$exists':'true'}})
                
                print 'annotation_info:'
                # out put anotions info
                for doc in annotation_docs:

                    print doc.get('DB_Object_ID')
                    
                    annos = doc['GO'][queryvalue]

                    for a in annos:

                        print a ,'\n'

                    print '-'*50

               # out put basic info
                print '~'*100

                print 'basic_info:','\n'

                for doc in basic_docs:

                    for key,val in doc.items():

                        if key in ['_id',]:
                            continue

                        print key,':',val,'\n'

            elif querykey == 'gene_id':

                annotation_docs = col.find({'DB_Object_ID':queryvalue})

                for doc in annotation_docs:

                    gos = doc.get('GO')

                    for go_id,annos in gos.items():

                        print '~'*100

                        go_basic = col.find_one({'id':go_id})

                        # output go_basic
                        print 'basic_info:','\n'

                        for key,val in go_basic.items():
                            if key in ['_id',]:
                                continue
                            print key,' : ',val
                            print 

                        print '-'*50

                        print 'annotation_info:','\n'

                        # output annotations
                        for a in annos:
                            print a
                            print 

class dbMap(object):

    #class introduction

    def __init__(self,version):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb')

        colname = 'go_gene_{}'.format(version)

        col = db.get_collection(colname)

        self.col = col

        self.colname = colname

    def mapGeneID2GOID(self):

        docs = self.col.find({})

        geneid2goid = dict()

        for doc in docs:

            geneid = doc.get('DB_Object_ID')

            goid = doc.get('GO',{}).keys()

            if geneid and geneid not in geneid2goid:

                geneid2goid[geneid] = list()

            if goid:
                geneid2goid[geneid] += goid

        goid2geneid = value2key(geneid2goid)

        map_dir = pjoin(go_gene_map,self.colname)

        createDir(map_dir)

        with open(pjoin(map_dir,'geneid2goid.json'),'w') as wf:
            json.dump(geneid2goid,wf,indent=8)

        with open(pjoin(map_dir,'goid2geneid.json'),'w') as wf:
            json.dump(goid2geneid,wf,indent=8)

    def mapping(self):

        self.mapGeneID2GOID()

class gene_parser(object):
    """docstring for gene_parser"""
    def __init__(self,filepath,date):

        file = open(filepath)

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.file = file

        self.db = db

    def gpa(self,fileversion):

            colname = 'go.geneanno'

            delCol('mydb_v1',colname)

            col = self.db.get_collection(colname)

            col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'go_annotation'})

            n = 0  #440715

            keys = [
            'DB','DB_Object_ID','Qualifier','GO ID','DB:Reference',
            'ECO evidence code','With/From','Interacting taxon ID','Date',
            'Assigned_by','Annotation Extension','Annotation Properties']

            go_dbref_link = constance('go_dbref_link')

            go_ano_pro = constance('go_ano_pro')

            for line in self.file:

                if line.startswith('!'):
                    continue

                line = line.strip().split('\t')

                data = dict([key,val] for key,val in zip(keys,line))

                db_ref = data.get('DB:Reference')

                if db_ref:
                    db = db_ref.split(':')[0].strip()
                    ref = db_ref.split(':')[1].strip()

                    db_ref_link = go_dbref_link[db].replace(db,ref)

                    data['DB:Reference Link'] = db_ref_link

                an_pro = data.get('Annotation Properties')

                if an_pro:

                    an_pro  = an_pro.split('go_evidence=')[1].strip()

                    data['Annotation Properties'] = an_pro

                    data['Annotation Properties implication'] = go_ano_pro.get(an_pro)

                col.insert(data)

                n += 1

                print 'go.geneanno line',n

    def obo(self,fileversion):

        colname =  ('go.info')

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'go_ontology'})

        # skip  term head 
        n = 1 #633722

        for line in self.file:

            if line.count('[Term]'):

                break

            n += 1
        
        aset = dict()

        go_namespace = constance('go_namespace')

        for line in self.file:

            if line.count('[Term]') or line.count('[Typedef]'):

                if aset:

                    go_id = aset.pop('id')

                    aset['GO ID'] = go_id

                    go_id_link = 'https://www.ebi.ac.uk/QuickGO/term/{}'.format(go_id)

                    aset['go id link'] = go_id_link

                    namespace = aset.get('namespace')

                    if namespace:

                        aset['namespace'] = go_namespace.get(namespace)

                    col.insert(aset)
                     
                    print 'go.obo line',n,go_id

                aset = dict()

                if line.count('[Typedef]'):
                    break

            else:

                line = line.strip()

                if  bool(line):

                    (key,val) = tuple(line.strip().split(':',1))

                    key = key.strip()
                    val = val.strip()

                    if key in ['name','namespace','def','id']:

                        aset[key] = val

                    else:

                        if key not in aset:

                            aset[key] = list()

                        aset[key].append(val)

            n += 1
            
        print 'go.info completed! '

def main():

    modelhelp = model_help.replace('&'*6,'GO_GENE').replace('#'*6,'go_gene')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,go_gene_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()

    # rawdir = '/home/user/project/dbproject/mydb_v1/go_gene/dataraw/gene_171225162503/'

    # filepaths = [pjoin(rawdir,filename) for filename in os.listdir(rawdir)]

    # date = '171225162503'

    # extractData(filepaths,date)
    
    # man = dbMap('171129140122')

    # man.mapping()