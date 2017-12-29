#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/11/28
# author:wuling
# emai:ling.wu@myhealthygene.com

#this model set  to download,extract,standard insert and select gene data from ensembl

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(ensembl_gene_model,ensembl_gene_raw,ensembl_gene_store,ensembl_gene_db,ensembl_gene_map) = buildSubDir('ensembl_gene')

log_path = pjoin(ensembl_gene_model,'ensembl_gene.log')
# main code
def downloadOne(ensembl_gene_ftp_infos,filename,rawdir):
    '''
    this function is to download  one file under  a given remote dir 
    args:
    ftp -- a ftp cursor for a specified
    filename --  the name of file need download
    rawdir -- the directory to save download file
    '''
    while  True:

        try:

            ftp = connectFTP(**ensembl_gene_ftp_infos)

            mt =  ftp.sendcmd('MDTM {}'.format(filename))

            print 'mt',mt

            savefilename = '{}_{}_{}.gz'.format(filename.rsplit('.',1)[0].strip(),mt,today).replace(' ','')

            remoteabsfilepath = pjoin(ensembl_gene_ftp_infos['logdir'],'{}'.format(filename))

            print filename,'start'

            save_file_path = ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath)

            print filename,'done'

            return (save_file_path,mt)

        except:

            ftp = connectFTP(**ensembl_gene_ftp_infos)

def downloadData(redownload = False):

    '''
    this function is to download the raw data from ensembl gene FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existensemblFile) = lookforExisted(ensembl_gene_raw,'gene')

        if choice != 'y':
            return

    if redownload or not existensemblFile or  choice == 'y':

        rawdir = pjoin(ensembl_gene_raw,'gene_{}'.format(today))

        createDir(rawdir)

        # download gtfGRch38 file
        ensembl_gene_ftp_infos['logdir'] = ensembl_gtfGRch38_ftp_path
        downloadOne(ensembl_gene_ftp_infos,filename_gtfGRch38,rawdir)

        # # download regulatorGRch38 files
        # ensembl_gene_ftp_infos['logdir'] = ensembl_regulatorGRch38_ftp_path
        # func = lambda x:downloadOne(ensembl_gene_ftp_infos,x,rawdir)
        # multiProcess(func,filenames_regulatorGRch38,size=16)

          # download gtfGRch37 file
        ensembl_gene_ftp_infos['logdir'] = ensembl_gtfGRch37_ftp_path
        downloadOne(ensembl_gene_ftp_infos,filename_gtfGRch37,rawdir)

        # # download regulatorGRch37 files
        # ensembl_gene_ftp_infos['logdir'] = ensembl_regulatorGRch37_ftp_path
        # func = lambda x:downloadOne(ensembl_gene_ftp_infos,x,rawdir)
        # multiProcess(func,filenames_regulatorGRch37,size=16)

    # create log file
    if not os.path.exists(log_path):

        initLogFile('ensembl_gene',model_name,ensembl_gene_model,rawdir=rawdir)

    # create every version files included
    update_file_heads =dict()

    for filename in listdir(rawdir):

        head = filename.split('_213')[0].strip()

        update_file_heads[head] = filename

    with open(pjoin(ensembl_gene_db,'gene_{}.files'.format(today)),'w') as wf:
        json.dump(update_file_heads,wf,indent=2)

    print  'datadowload completed !'

    # generate filepaths to next step extractData
    filepaths = [pjoin(rawdir,filename) for filename in rawdir]

    return (filepaths,today)

def extractData(filepaths,date):

    colname = 'ensembl.gene.transcript'

    delCol('mydb_v1',colname)

    #  deal the gtf file to  insert basic info
    for filepath in filepaths:

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

        name = filename.split('_sapiens.')[1].split('_213')[0].strip()

        grch = name.split('.',1)[0]

        process = gene_parser(date)

        if  name.endswith('chr.gtf'):

            process.gtf(filepath,grch,fileversion)

        print name,'completed'

        # bkup all collections
    colhead = 'ensembl.gene'

    bkup_allCols('mydb_v1',colhead,ensembl_gene_db)

    return (filepaths,date)

def updateData(insert=False,_mongodb=ensembl_gene_db):

    ensembl_gene_log = json.load(open(log_path))

    rawdir = pjoin(ensembl_gene_raw,'gene_{}'.format(today))

    new = False

    for  file,ftpsite in ensembl_file_ftplogdir.items():

        ftp_infos = copy.deepcopy(ensembl_gene_ftp_infos)

        ftp_infos['logdir'] = ftpsite

        ftp = connectFTP(**ftp_infos)

        filenames = ftp.nlst()

        for filename in filenames:

            if filename.count(ensembl_file_mark.get(file)):

                mt = ftp.sendcmd('MDTM {}'.format(filename))

                if mt != ensembl_gene_log.get(file)[-1][0]:

                    new = True

                    createDir(rawdir)
                
                    downloadOne(ftp_infos,filename,rawdir)   

                    ensembl_gene_log[file].append((mt,today,model_name))

                    print  '{} \'s new edition is {} '.format(filename,mt)

                else:
                    print  '{} {} is the latest !'.format(filename,mt)

        print '~'*50

    if new:

        with open(log_path,'w') as wf:

            json.dump(ensembl_gene_log,wf,indent=2)

        (latest_file,version) = createNewVersion(ensembl_gene_raw,ensembl_gene_db,rawdir,'gene_',today)
        
        if insert:

            insertUpdatedData(ensembl_gene_raw,latest_file,'gene_',version,extractData)

def selectData(querykey = 'gene_id',value='ENSG00000243485'):

    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'ensembl'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class dbMap(object):

    #class introduction

    def __init__(self,version):

        self.version = version

        conn = MongoClient('127.0.0.1',27017)

        db = conn.get_database('mydb')

        colname = 'ensembl_gene_{}'.format(self.version)

        col = db.get_collection(colname)

        docs = col.find({})

        self.docs  = docs

        self.colname = colname

    def mapgeneid2genesym(self):
        '''
        this function is to create a mapping relation between GeneID with Symbol
        '''
        geneid2genesym = dict()

        genesym2geneid = dict()

        n = 0

        for doc in self.docs:

            gene_id = doc.get('gene_id')

            symbol = doc.get('gene_name')

            geneid2genesym[gene_id] = symbol

            if symbol not in genesym2geneid:

                genesym2geneid[symbol] = list()
            
            genesym2geneid[symbol].append(gene_id)

            n += 1

        for key,val in genesym2geneid.items():
            if len(val) >= 2:
                print key,val

        map_dir = pjoin(ensembl_gene_map,self.colname)

        createDir(map_dir)

        with open(pjoin(map_dir,'geneid2genesym.json'),'w') as wf:
            json.dump(geneid2genesym,wf,indent=2)
            
        with open(pjoin(map_dir,'genesym2geneid.json'),'w') as wf:
            json.dump(genesym2geneid,wf,indent=2)

    def mapping(self):

        self.mapgeneid2genesym()

class gene_parser(object):

    """docstring for gene_parser"""
    def __init__(self,date):

        self.date = date

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

    def gtf(self,filepath,grch,fileversion):

        rawdir = psplit(filepath)[0].strip()

        filename = psplit(filepath)[1].strip()
        #-----------------------------------------------------------------------------------------------------------------------

        # gunzip file
        if filename.endswith('.gz'):

            command = 'gunzip  {}'.format(filepath)
            
            os.popen(command)

            filename = filename.replace('.gz','')

        #-----------------------------------------------------------------------------------------------------------------------
        colname = 'ensembl.gene.transcript'

        col = self.db.get_collection(colname)

        if not col.find_one({'dataVersion':fileversion}):

            col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'Homo_sapiens.GRCh?.?.chr.gtf'})

        file = open(pjoin(rawdir,filename))
        
        print '-'*50

        n = 0

        gene_info = dict()

        assembly = 'ensembl_{}'.format(grch)

        for line in file:

            if line.startswith('#'):
                continue

            # the front of line ,delimited by tab and have no key, and the latter delimited by ; with the format key space value("") 

            front_keys = ['chr','data_source','entry','start','end','score','strand','fields']

            front = line.split('gene_id')[0].strip().split('\t')

            front_dic = dict([(key,val) for key,val in zip(front_keys,front)])

            # transform the string to int in start and end
            front_dic['start' ] = int(front_dic['start' ])
            front_dic['end' ] = int(front_dic['end' ])

            latter = [i.strip() for i in line.strip().split('gene_id')[1].strip().split(';') if i ]

            latter_dic = dict([(i.split(' ')[0],i.split(' ')[1].replace('"','')) for i in latter[1:] ])

            gene_id = latter[0].replace('"','')

            entry = front_dic.get('entry')

            if  entry == 'gene':

                latter_dic['gene_id'] = gene_id

                latter_dic.update(front_dic)

                for key in ['data_source','entry','score','fields']:

                    latter_dic.pop(key)

                latter_dic['assembly'] = assembly

                gene_info[gene_id] = latter_dic

            elif entry == 'transcript':

                latter_dic['transcript_start'] = front_dic.get('start')
                latter_dic['transcript_end'] = front_dic.get('end')

                for key in latter_dic.keys():
                    if key.startswith('gene'):
                        latter_dic.pop(key)

                latter_dic.update(gene_info.get(gene_id))

                col.insert(latter_dic)

            elif entry in ['Selenocysteine','five_prime_utr','three_prime_utr']:

                transcript_id = latter_dic.get('transcript_id')

                col.update(
                    {'transcript_id':transcript_id,'assembly':assembly},
                    {'$set':
                        {'{}_start'.format(entry):front_dic.get('start'),
                         '{}_end'.format(entry):front_dic.get('end')}
                         })

            elif entry == 'exon':

                transcript_id = latter_dic.get('transcript_id')

                for key in latter_dic.keys():

                    if not key.startswith('exon'):
                        latter_dic.pop(key)

                latter_dic['exon_start'] = front_dic.get('start')
                latter_dic['exon_end'] = front_dic.get('end')

                col.update(
                    {'transcript_id':transcript_id,'assembly':assembly},
                    {'$push':{'exon':latter_dic} },
                    False,
                    True
                     )

            elif entry == 'CDS':

                cds_aset = dict()

                transcript_id = latter_dic.get('transcript_id')

                cds_aset['cds_start'] = front_dic.get('start')

                cds_aset['cds_end'] = front_dic.get('end')

                cds_aset['protein_id'] = latter_dic['protein_id']

                cds_aset['protein_version'] = latter_dic['protein_version']

                col.update(
                    {'transcript_id':transcript_id,'assembly':assembly},
                    {'$push':{'cds':cds_aset}},
                    False,
                    True)
            
            elif entry == 'start_codon' or entry == 'stop_codon':

                transcript_id = latter_dic.get('transcript_id')

                col.update(
                    {'transcript_id':transcript_id,'assembly':assembly},
                    {'$set':
                        {'{}_start'.format(entry):front_dic.get('start'),
                         '{}_end'.format(entry):front_dic.get('end')}
                         },
                    False,
                    True)
 
            else:
                print '================================',entry

            latter_dic = dict()
            
            n += 1
            print grch,'gtf line',n,entry,gene_id

def main():

    modelhelp = model_help.replace('&'*6,'ENSEMBL_GENE').replace('#'*6,'ensembl_gene')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,ensembl_gene_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # updateData()
    # downloadData(True)
    # rawdir = '/home/user/project/dbproject/mydb_v1/ensembl_gene/dataraw/gene_171127151418/'
    # filepaths = [pjoin(rawdir,filename) for filename in os.listdir(rawdir)]
    # date = '171127151418'
    # extractData(filepaths,date)
    # man = dbMap('171127151418')
    # man.mapping()
 