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
def downloadData(redownload = False):
    '''
    this function is to download the raw data from go gene FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existgoFile) = lookforExisted(go_gene_raw,'gene')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        rawdir = pjoin(go_gene_raw,'gene_{}'.format(today))

        createDir(rawdir)

        #------------------------------------------------------------------------------------------------------------
        process = parse(today)
        
        func = lambda x:process.getOne(go_gene_ftp_infos,x,rawdir)
        #------------------------------------------------------------------------------------------------------------
        # 1. download gpa file
        multiProcess(func,go_gene_filenames,size=1)
        #------------------------------------------------------------------------------------------------------------
        # 2. download obo file
        func = lambda x:downloadOne(go_obo_ftp_infos,x,rawdir)
        multiProcess(func,go_obo_filenames,size=1)
    #------------------------------------------------------------------------------------------------------------
    #  generate .log file in current  path
    if not os.path.exists(log_path):

        initLogFile('go_gene',model_name,go_gene_model,rawdir=rawdir)

    update_file_heads =dict()

    #------------------------------------------------------------------------------------------------------------
    # generate .files file in database
    for filename in listdir(rawdir):

        head = filename.split('_213')[0].strip()

        update_file_heads[head] = pjoin(rawdir,filename)

    with open(pjoin(go_gene_db,'gene_{}.files'.format(today)),'w') as wf:
        json.dump(update_file_heads,wf,indent=2)

    print  'datadowload completed !'

    #--------------------------------------------------------------------------------------------------------------------
    # return filepaths to extract 
    filepaths = [pjoin(rawdir,filename) for filename in rawdir]

    return (filepaths,today)

def extractData(filepaths,date):

    '''
    this function is set to distribute all filepath to parser to process
    args:
    filepaths -- all filepaths to be parserd
    date -- the date of  data download
    '''
    # 1. distribute filepaths for parser
    go_info_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('go.obo')]
    go_anno_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('goa_human.gpa')]

    # 2. parser filepaths step by step
    process = parser(date)
    
    # --------------------------------go.info-------------------------------------------------------------------------
    process.go_info(go_info_paths)

    # --------------------------------go.geneanno-------------------------------------------------------------------------
    process.go_geneanno(go_anno_paths)  

    # bkup all collections
    _mongodb = pjoin(go_gene_db,'gene_{}'.format(date))

    createDir(_mongodb)

    colhead = 'go.'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    print 'extract and insert complete '

    return (filepaths,version)

def updateData(insert=True):
    '''
    this function is set to update all file in log
    '''
    go_gene_log = json.load(open(log_path))

    updated_rawdir = pjoin(go_gene_raw,'gene_{}'.format(today))

    #-----------------------------------------------------------------------------------------------------------------
    new = False

    process = parser(today)

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

            createDir(updated_rawdir)

            process.getOne(ftp_infos,filename,updated_rawdir)

            go_gene_log[filename].append((mt,today,model_name))

            print  '{} \'s new edition is {} '.format(filename,mt)

        else:
            print  '{} {} is the latest !'.format(filename,mt)
    # updated_rawdir = '/home/user/project/dbproject/mydb_v1/go_gene/dataraw/gene_180122165624/'
    # today = '180122165624'
    # new = True

    if new:

        with open(log_path,'w') as wf:

            json.dump(go_gene_log,wf,indent=2)

        (latest_filepaths,version) = createNewVersion(go_gene_raw,go_gene_db,updated_rawdir,'gene_',today)

        if insert:

            extractData(latest_filepaths.values(),version)

        return 'update successfully'

    else:

        return 'new version is\'t detected'

def selectData(querykey = 'GO ID',queryvalue='GO:0005765'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'go'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):
    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''
    def __init__(self,date):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.db = db

    def getOne(self,go_gene_ftp_infos,filename,rawdir):
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

    def go_info(self,filepaths):
        '''
        this function is set parser go_info 
        '''
        colname =  'go.info'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('GO ID',1),])
        #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not col.find_one({'colCreated':{'$exists':True}}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'go.obo'})
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
            
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file
            tsvfile = open(filepath)

            # skip  term head 
            n = 1 #633722

            for line in tsvfile:

                if line.count('[Term]'):

                    break

                n += 1
            
            aset = dict()

            go_namespace = constance('go_namespace')

            for line in tsvfile:

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

                        if key == 'def':
                            val = standarString(val,'','')
                        else:
                            val = standarString(val,'','.')

                        if key in ['name','namespace','def','id']:

                            aset[key] = val

                        else:

                            if key not in aset:

                                aset[key] = list()

                            aset[key].append(val)

                n += 1
                
            print 'go.info completed! '

    def go_geneanno(self,filepaths):
        '''
        this function is set parser go_geneanno 
        '''
        colname = 'go.geneanno'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('GO ID',1),])
        #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not col.find_one({'colCreated':{'$exists':True}}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'goa_human.gpa'})
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
            
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file
            tsvfile = open(filepath)

            n = 0  #440715

            keys = [
            'DB','DB_Object_ID','Qualifier','GO ID','DB:Reference',
            'ECO evidence code','With/From','Interacting taxon ID','Date',
            'Assigned_by','Annotation Extension','Annotation Properties']

            go_dbref_link = constance('go_dbref_link')

            go_ano_pro = constance('go_ano_pro')

            for line in tsvfile:

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

class dbMap(object):

    #class introduction
    def __init__(self):

        super(dbMap,self).__init__()

        import commap

        from commap import comMap

        (db,db_cols) = initDB('mydb_v1') 

        self.db = db

        self.db_cols = db_cols

        process = commap.comMap()

        self.process = process

    def dbID2hgncSymbol(self):
        '''
        this function is to create a mapping relation between go ID with HGNC Symbol
        '''
        uniprot2symbol = self.process.uniprotGeneID2hgncSymbol()

        go_gene_anno_col = self.db_cols.get('go.geneanno')

        go_gene_anno_docs = go_gene_anno_col.find({})

        output = dict()

        hgncSymbol2goID = output

        no = 0

        for doc in go_gene_anno_docs:

            gene_id = doc.get('DB_Object_ID')

            go_id = doc.get('GO ID')

            gene_symbol = uniprot2symbol.get(gene_id)

            if gene_symbol and go_id:

                for symbol in gene_symbol:

                    if symbol not in output:
                        output[symbol] = list()

                    output[symbol].append(go_id)

            else:
                no += 1

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val

        # print 'go uniprot gene id can\'t be found in hgnc uniprot_ids',no

        print 'hgncSymbol2goID',len(output)

        # with open('./hgncSymbol2goID.json','w') as wf:
        #     json.dump(hgncSymbol2goID,wf,indent=8)
            
        return (hgncSymbol2goID,'GO ID')

class dbFilter(object):
    """docstring for dbFilter"""
    def __init__(self, arg):
        super(dbFilter, self).__init__()
        self.arg = arg
        
def main():

    modelhelp = model_help.replace('&'*6,'GO_GENE').replace('#'*6,'go_gene')

    funcs = (downloadData,extractData,updateData,selectData,go_gene_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
