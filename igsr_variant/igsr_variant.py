#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/1/4
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download ,parser(extract,satndar,insert) and update clinvar variant data from igsr ftp site

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(igsr_variant_model,igsr_variant_raw,igsr_variant_store,igsr_variant_db,igsr_variant_map) = buildSubDir('igsr_variant')

log_path = pjoin(igsr_variant_model,'igsr_variant.log')

# main code
def downloadData(redownload = False):
    '''
    this function is to download the raw data from go igsr FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existgoFile) = lookforExisted(igsr_variant_raw,'ALL.wgs')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        #----------------------------------------------------------------------------------------------------------
        # 1. download ALL.wgs.phase**.vcf
        process = parser(today)

        (mt,host,logdir) = process.getUrl()

        igsr_variant_ftp_infos['host'] = host

        igsr_variant_ftp_infos['logdir'] = logdir

        print 'the latest version is :',mt
        print 'the host  is :',host
        print 'the logdir  is :',logdir

        filepath = process.getOne(igsr_variant_ftp_infos,igsr_variant_raw)

    #--------------------------------------------------------------------------------------------------------------------
    #  generate .log file in current  path
    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:

            json.dump({'igsr_variant':[(mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'
    #--------------------------------------------------------------------------------------------------------------------
    # return filepaths to extract 

    return (filepath,today)

def extractData(filepath,date):
    '''
    this function is set to distribute all filepath to parser to process
    args:
    filepath -- the file to be parserd
    date -- the date of  data download
    '''
    # ----------------------------------------------------------------------------------------------------
    # 1. distribute filepaths for parser
    #  just only one file
    filename = psplit(filepath)[1].strip()

    fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
    # ----------------------------------------------------------------------------------------------------
    # 2. parser filepaths step by step
    process = parser(date)

    process.variant_info(filepath,fileversion)
    # ----------------------------------------------------------------------------------------------------
    # 3. bkup all collections
    colhead = 'igsr.variant'

    bkup_allCols('mydb_v1',colhead,igsr_variant_db)

    print 'extract and insert completed'

    return (filepath,date)

def updateData(insert=False):
    '''
    this function is set to update all file in log
    '''
    igsr_variant_log = json.load(open(log_path))

    process = parser(today)

    (mt,host,logdir) = process.getUrl()

    if mt != igsr_variant_log['igsr_variant'][-1][0]:

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        igsr_variant_log['igsr_variant'].append((mt,today,model_name))

        # create new log
        with open(log_path,'w') as wf:

            json.dump(igsr_variant_log,wf,indent=8)

        print  '{} \'s new edition is {} '.format('igsr_variant',mt)

        return 'update successfully'

    else:

        print  '{} {} is the latest !'.format('igsr_variant',mt)

        return 'new version is\'t detected'

def selectData(querykey = 'ID',value='rs100001'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'igsr.variant'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):
    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''
    def __init__(self, date):

        super(parser, self).__init__()

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.db = db

    def getUrl(self):
        '''
        this function is set to get the latest version and ftp host and ftp logdir of igsr variant
        '''
        web = requests.get(igsr_download_web,headers=headers,verify=False)

        soup = bs(web.content,'lxml')

        avala_data = soup.find(text='Available data')

        vcf = avala_data.findNext(name='tbody').find(name='tr').find(text='VCF')

        url  = vcf.findParent(name='a').attrs.get('href')

        mt = url.split('release/')[1].split('/')[0].strip()

        host = url.split('//')[1].split('/',1)[0].strip()

        logdir = url.split(host)[1].strip()

        return (mt,host,logdir) 

    def getOne(self,igsr_variant_ftp_infos,igsr_variant_raw):
        '''
        this function is to download  one file under  a given remote dir 
        args:
        igsr_variant_ftp_infos --  a specified ftp connection info 
        filename --  the name of file need download
        rawdir -- the directory to save download file
        '''       
        ftp = connectFTP(**igsr_variant_ftp_infos)

        files = ftp.nlst()

        filenames = [name for name in files if name.startswith('ALL.wgs') and name.endswith('sites.vcf.gz')]

        if filenames:
            filename = filenames[0]
            mt =  ftp.sendcmd('MDTM {}'.format(filename)).replace(' ','')

        else:
            print 'no this file'
            return

        print '...start download ',filename

        savefilename = '{}_{}_{}.vcf.gz'.format(filename.rsplit('.vcf',1)[0].strip(),mt,today)
        print '...savefilename ',savefilename

        remoteabsfilepath = pjoin(igsr_variant_ftp_infos['logdir'],'{}'.format(filename))
        print '...remoteabsfilepath ',remoteabsfilepath

        savefilepath = pjoin(igsr_variant_raw,savefilename)
        print '...savefilepath ',savefilepath
        
        try:
             print 'try ftp download...'
             ftpDownload(ftp,filename,savefilename,igsr_variant_raw,remoteabsfilepath)
        except:
            print 'try wget download...'
            ftpurl = igsr_variant_ftp_infos['host'] + igsr_variant_ftp_infos['logdir'] + filename
            getfile = 'wget  -O {} {}  '.format(savefilepath,ftpurl)

        print '...end download '

        # gunzip file
        print '...start gunzip file '
        gunzip = 'gunzip {}'.format(savefilepath)

        os.popen(gunzip)
        print '...end gunzip file '

        savefilepath = savefilepath.rsplit('.',1)[0].strip()

        return savefilepath

    def variant_info(self,filepath,fileversion):
        '''
        this function is set parser variant_info 
        '''
        colname = 'igsr.variant'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('ID',1),])

        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'ALL.wgs.*.sites.vcf'})

        #-------------------------------------------------------------------------------------------------------------------------------------
        vcffile = open(filepath)

        n = 0

        front_keys = ['chr','pos','ID','ref','alt','QUAL','filter']

        for line in vcffile:

            if line.startswith('#'):
                n += 1
                continue

            front = line.strip().split('\t')[:-1]

            front_dic = dict([(key,val) for key,val in zip(front_keys,front)])

            after = line.strip().split('\t')[-1].split(';')

            # after_dic =dict([tuple(it.split('=')[:2]) for it in after])
            after_dic = dict()

            for it in after:

                if it.count('='):
                    key = it.split('=')[0].strip()
                    val = it.split('=')[1].strip()
                else:
                    key = it.strip()
                    val = False

                after_dic[key] = val

            # after_dic =dict([tuple(it.split('=')[:2]) for it in after])
            after_dic.update(front_dic)

            col.insert(after_dic)

            after_dic.pop('_id')

            n += 1
            
            print 'igsr.variant line',n,len(after_dic)

class dbMap(object):
    '''
    this class is set to map ncbi gene id to other db
    '''
    def __init__(self):

        import commap

        from commap import comMap

        (db,db_cols) = initDB('mydb_v1') 

        self.db = db

        self.db_cols = db_cols

        process = commap.comMap()

        self.process = process

    def dbID2hgncSymbol(self):
        '''
        this function is to create a mapping relation between igsr  id  with HGNC Symbol
        '''

        rsID2hgncSymbol = self.process.rsID2hgncSymbol()

        igsr_variant_col = self.db_cols.get('igsr.variant')

        igsr_variant_docs = igsr_variant_col.find({})

        output = dict()

        hgncSymbol2igsrvariantID = output

        n = 0

        for doc in igsr_variant_docs:

            rs_id = doc.get("ID")

            gene_symbol = rsID2hgncSymbol.get(rs_id)

            if rs_id and  gene_symbol:

                for symbol in gene_symbol:

                    if symbol not in output:

                        output[symbol] = list()

                    output[symbol].append(rs_id)

            n += 1
            # print 'igsr.variant doc',n

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val    

        print 'hgncSymbol2igsrvariantID',len(output)

        for sym,rs in output.items():
            rs = list(set(rs))
            output[sym] = rs
            
        # with open('./hgncSymbol2igsrvariantID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return (hgncSymbol2igsrvariantID,'ID')

class dbFilter(object):

    '''this class is set to filter part field of data in collections  in mongodb '''

    def __init__(self):
        
        super(dbFilter,self).__init__()
        
    def gene_topic(self,doc):

        save_keys = ['ID','AF','EAS_AF','AMR_AF','AFR_AF','EUR_AF','SAS_AF']

        return filterKey(doc,save_keys)

def main():

    modelhelp = model_help.replace('&'*6,'IGSR_VARIANT').replace('#'*6,'igsr_variant')

    funcs = (downloadData,extractData,updateData,selectData,igsr_variant_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # filepath = '/home/user/project/dbproject/mydb_v1/igsr_variant/dataraw/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites_21320150818133316_180124113638.vcf'
    # date = '180124113638'
    # extractData(filepath,date)
