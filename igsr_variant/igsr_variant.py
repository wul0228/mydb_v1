#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/1/4
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

(igsr_variant_model,igsr_variant_raw,igsr_variant_store,igsr_variant_db,igsr_variant_map) = buildSubDir('igsr_variant')

log_path = pjoin(igsr_variant_model,'igsr_variant.log')

# main code
def downloadData(redownload = False):
    '''
    this function is to download the raw data from go igsr FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existgoFile) = lookforExisted(igsr_variant_raw,'ALL.wgs')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        process = igsr_parser(today)

        (mt,host,logdir) = process.getUrl()

        igsr_variant_ftp_infos['host'] = host

        igsr_variant_ftp_infos['logdir'] = logdir

        ftp = connectFTP(**igsr_variant_ftp_infos)

        files = ftp.nlst()

        filenames = [name for name in files if name.startswith('ALL.wgs') and name.endswith('sites.vcf.gz')]

        if filenames:
            filename = filenames[0]
        else:
            print 'no this file'
            return

        savefilename = '{}_{}_{}.vcf.gz'.format(filename.rsplit('.vcf',1)[0].strip(),mt,today)

        ftpurl = host + logdir + filename

        print ftpurl
    #     # remoteabsfilepath = pjoin(igsr_variant_ftp_infos['logdir'],'{}'.format(filename))

    #     # getfile = 'wget {} --ftp-user= --ftp-password=password'
    #     getfile = 'wget  -O {} {}  '.format(savefilepath,ftpurl)

    #     # save_file_path = ftpDownload(ftp,filename,savefilename,igsr_variant_raw,remoteabsfilepath)

    #     # gunzip file
    #     gunzip = 'gunzip {}'.format(save_file_path)

    #     os.popen(gunzip)

    # # create log file
    # if not os.path.exists(log_path):

    #     with open(log_path,'w') as wf:

    #         json.dump({'igsr_variant':[(mt,today,model_name)]},wf,indent=8)

    # print  'datadowload completed !'

    # filepath = save_file_path.split('.gz')[0].strip()

    # return (filepath,today)

def extractData(filepath,date):

    filename = psplit(filepath)[1].strip()

    fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

    process = igsr_parser(date)

    process.vcf(filepath,fileversion)

    # colhead = 'igsr.variant'

    # bkup_allCols('mydb_v1',colhead,igsr_variant_db)

    # print 'extract and insert completed'

    # return (filepath,date)

def updateData(insert=False,_mongodb='../_mongodb/'):

    igsr_variant_log = json.load(open(log_path))

    process = igsr_parser(today)

    (mt,host,logdir) = process.getUrl()

    if mt != igsr_variant_log['igsr_variant'][-1][0]:

        filepath,version = downloadData(redownload=True)

        extractData(filepath,version)

        igsr_variant_log['igsr_variant'].append((mt,today,model_name))

        # create new log
        with open(log_path,'w') as wf:

            json.dump(igsr_variant_log,wf,indent=8)

        print  '{} \'s new edition is {} '.format('igsr_variant',mt)
        
    else:

        print  '{} {} is the latest !'.format('igsr_variant',mt)

def selectData():

    #function introduction
    #args:
    
    return

class igsr_parser(object):
    """docstring for igsr_parser"""
    def __init__(self, date):

        super(igsr_parser, self).__init__()

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.date = date

        self.db = db

    def getUrl(self):

        web = requests.get(igsr_download_web,headers=headers,verify=False)

        soup = bs(web.content,'lxml')

        avala_data = soup.find(text='Available data')

        vcf = avala_data.findNext(name='tbody').find(name='tr').find(text='VCF')

        url  = vcf.findParent(name='a').attrs.get('href')

        mt = url.split('release/')[1].split('/')[0].strip()

        host = url.split('//')[1].split('/',1)[0].strip()

        logdir = url.split(host)[1].strip()

        return (mt,host,logdir) 

    def vcf(self,filepath,fileversion):

        colname = 'igsr.variant'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        
        col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'ALL.wgs.*.sites.vcf.gz'})

        if filepath.endswith('gz'):

            gunzip = 'gunzip {}'.format(filepath)
            os.popen(gunzip)

            print 'gunzip completed'

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

    #class introduction

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
        this function is to create a mapping relation between disgenet disease id  with HGNC Symbol
        '''
        # because disgenet gene id  is entrez id 
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
            print 'igsr.variant doc',n

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val    

        print 'hgncSymbol2igsrvariantID',len(output)

        for sym,rs in output.items():
            rs = list(set(rs))
            output[sym] = rs
            
        with open('./hgncSymbol2igsrvariantID.json','w') as wf:
            json.dump(output,wf,indent=8)

        return (hgncSymbol2igsrvariantID,'ID')

class filter(object):
    """docstring for filter"""
    def __init__(self):

        pass
        
    def gene_topic(self,doc):

        save_keys = ['ID','AF','EAS_AF','AMR_AF','AFR_AF','EUR_AF','SAS_AF']

        return filterKey(doc,save_keys)

def main():

    modelhelp = 'help document'

    funcs = (downloadData,extractData,updateData,selectData,dbMap,igsr_variant_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # downloadData(redownload=True)
    # filepath = '/home/user/project/dbproject/mydb_v1/igsr_variant/dataraw/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites_20130502_1801041729.vcf'
    # date = '1801041729'
    # extractData(filepath,date)
    # man = dbMap()
    # man.dbID2hgncSymbol()
  