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
def downloadData(redownload = False):

    '''
    this function is to download the raw data from ensembl gene FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existensemblFile) = lookforExisted(ensembl_gene_raw,'gene')

        if choice != 'y':
            return

    if redownload or not existensemblFile or  choice == 'y':

        rawdir = pjoin(ensembl_gene_raw,'gene_{}'.format(today))

        createDir(rawdir)

        process = parse(today)
        #-----------------------------------------------------------------------------------------------------------------
        # download gtfGRch38 file
        ensembl_gene_ftp_infos['logdir'] = ensembl_gtfGRch38_ftp_path
        process.getOne(ensembl_gene_ftp_infos,filename_gtfGRch38,rawdir)

        # # download regulatorGRch38 files
        # ensembl_gene_ftp_infos['logdir'] = ensembl_regulatorGRch38_ftp_path
        # func = lambda x:downloadOne(ensembl_gene_ftp_infos,x,rawdir)
        # multiProcess(func,filenames_regulatorGRch38,size=16)

        #-----------------------------------------------------------------------------------------------------------------
          # download gtfGRch37 file
        ensembl_gene_ftp_infos['logdir'] = ensembl_gtfGRch37_ftp_path
        downloadOne(ensembl_gene_ftp_infos,filename_gtfGRch37,rawdir)

        # # download regulatorGRch37 files
        # ensembl_gene_ftp_infos['logdir'] = ensembl_regulatorGRch37_ftp_path
        # func = lambda x:downloadOne(ensembl_gene_ftp_infos,x,rawdir)
        # multiProcess(func,filenames_regulatorGRch37,size=16)

    #-----------------------------------------------------------------------------------------------------------------
    # generate a log file in current  path
    if not os.path.exists(log_path):

        initLogFile('ensembl_gene',model_name,ensembl_gene_model,rawdir=rawdir)

    #-----------------------------------------------------------------------------------------------------------------
    # create every version files included
    update_file_heads =dict()

    for filename in listdir(rawdir):

        head = filename.split('_213')[0].strip()

        if head.count('.chr.gtf'):

            head = head.split('.chr.gtf')[0].rsplit('.',1)[0] + '.chr.gtf'

        update_file_heads[head] = pjoin(rawdir,filename)

    with open(pjoin(ensembl_gene_db,'gene_{}.files'.format(today)),'w') as wf:
        json.dump(update_file_heads,wf,indent=2)

    print  'datadowload completed !'

    #-----------------------------------------------------------------------------------------------------------------
    # generate filepaths to next step extractData
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
    gene_transcript_paths = [path for path in filepaths if psplit(path)[1].strip().count('chr.gtf') ]

     # 2. parser filepaths step by step
    process = parser(date)
    
    # --------------------------------ensembl.gene.transcript-------------------------------------------------------------------------
    process.gene_transcript(gene_transcript_paths)

    print 'extract and insert complete '

    # -------------------------------------------------------------------------------------------------------------------------------------------
     # 3. bkup all collections

    colhead = 'ensembl.gene'

    bkup_allCols('mydb_v1',colhead,ensembl_gene_db)

    return (filepaths,date)

def updateData(insert=True):
    '''
    this function is set to update all file in log
    '''
    ensembl_gene_log = json.load(open(log_path))

    updated_rawdir = pjoin(ensembl_gene_raw,'gene_{}'.format(today))

    # -------------------------------------------------------------------------------------------------------------------------------------------
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

                    createDir(updated_rawdir)
                
                    downloadOne(ftp_infos,filename,updated_rawdir)   

                    ensembl_gene_log[file].append((mt,today,model_name))

                    print  '{} \'s new edition is {} '.format(filename,mt)

                else:
                    print  '{} {} is the latest !'.format(filename,mt)

    if new:

        with open(log_path,'w') as wf:

            json.dump(ensembl_gene_log,wf,indent=2)

        (latest_filepaths,version) = createNewVersion(ensembl_gene_raw,ensembl_gene_db,updated_rawdir,'gene_',today)
        
        if insert:

            extractData(latest_filepaths.values(),version)

        return 'update successfully'

    else:
        
        return 'new version is\'t detected'


def selectData(querykey = 'gene_id',value='ENSG00000243485'):

    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'ensembl'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):

    """docstring for parser"""
    def __init__(self,date):

        self.date = date

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

    def getOne(self,ensembl_gene_ftp_infos,filename,rawdir):
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

                savefilename = '{}_{}_{}.gz'.format(filename.rsplit('.',1)[0].strip(),mt,today).replace(' ','')

                remoteabsfilepath = pjoin(ensembl_gene_ftp_infos['logdir'],'{}'.format(filename))

                print filename,'start'

                save_file_path = ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath)

                print filename,'done'

                return (save_file_path,mt)

            except:

                ftp = connectFTP(**ensembl_gene_ftp_infos)


    def gene_transcript(self,filepaths):

        colname = 'ensembl.gene.transcript'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('transcript_id',1),])

        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            if not col.find_one({'dataVersion':fileversion}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'Homo_sapiens.GRCh?.?.chr.gtf'})
            
            #-----------------------------------------------------------------------------------------------------------------------
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
                
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()
            #-----------------------------------------------------------------------------------------------------------------------

            grch = filename.split('_sapiens.')[1].split('_213')[0].strip().split('.',1)[0]

            file = open(filepath)

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

class dbMap(object):

    """docstring for dbMap"""

    def __init__(self, arg):
        super(dbMap, self).__init__()
        self.arg = arg
        

class dbFilter(object):
    """docstring for dbFilter"""
    def __init__(self, arg):
        super(dbFilter, self).__init__()
        self.arg = arg
        
        
def main():

    modelhelp = model_help.replace('&'*6,'ENSEMBL_GENE').replace('#'*6,'ensembl_gene')

    funcs = (downloadData,extractData,updateData,selectData,ensembl_gene_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
 