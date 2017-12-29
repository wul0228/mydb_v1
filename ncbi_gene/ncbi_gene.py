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

(ncbi_gene_model,ncbi_gene_raw,ncbi_gene_store,ncbi_gene_db,ncbi_gene_map) = buildSubDir('ncbi_gene')

log_path = pjoin(ncbi_gene_model,'ncbi_gene.log')

# main code
def downloadOne(ncbi_gene_ftp_infos,filename,rawdir):
    '''
    this function is to download  one file under  a given remote dir 
    args:
    ftp -- a ftp cursor for a specified
    filename --  the name of file need download
    rawdir -- the directory to save download file
    '''
    while  True:

        try:

            ftp = connectFTP(**ncbi_gene_ftp_infos)

            mt =  ftp.sendcmd('MDTM {}'.format(filename)).replace(' ','')

            savefilename = '{}_{}_{}.gz'.format(filename.rsplit('.',1)[0].strip(),mt,today)

            remoteabsfilepath = pjoin(ncbi_gene_ftp_infos['logdir'],'{}'.format(filename))

            save_file_path = ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath)

            print filename,'done'

            return (save_file_path,mt)

        except:

            ftp = connectFTP(**ncbi_gene_ftp_infos)

def downloadData(redownload = False):
    '''
    this function is to download the raw data from ncbi gene FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existNcbiFile) = lookforExisted(ncbi_gene_raw,'gene')

        if choice != 'y':
            return

    if redownload or not existNcbiFile or  choice == 'y':

        rawdir = pjoin(ncbi_gene_raw,'gene_{}'.format(today))

        createDir(rawdir)

        func = lambda x:downloadOne(ncbi_gene_ftp_infos,x,rawdir)

        # dodownload gene_group ,gene_neibors, gene_pubmed ,gene_info
        multiProcess(func,ncbi_gene_filenames,size=10)

        #download gene_expression 
        ncbi_gene_ftp_infos['logdir'] =  '/gene/DATA/expression/Mammalia/Homo_sapiens/'

        # get expression filenames
        ftp = connectFTP(**ncbi_gene_ftp_infos)

        gene_expression_filenames = ftp.nlst()
        
        # download
        multiProcess(func,gene_expression_filenames,size=4)

        # get refseq filenames
        ncbi_gene_ftp_infos['logdir'] =  ncbi_refseq_ftp_path

        ftp = connectFTP(**ncbi_gene_ftp_infos)

        gene_refseq_filenames = [filename for filename in ftp.nlst() if filename.endswith('.genomic.gbff.gz') ]

        multiProcess(func,gene_refseq_filenames,size=5)

    if not os.path.exists(log_path):

        initLogFile('ncbi_gene',model_name,ncbi_gene_model,rawdir=rawdir)

    else:

        expanLogFile(log_path,model_name,rawdir)

    update_file_heads =dict()

    for filename in listdir(rawdir):

        head = filename.split('_213')[0].strip()

        update_file_heads[head] = filename

    with open(pjoin(ncbi_gene_db,'gene_{}.files'.format(today)),'w') as wf:
        json.dump(update_file_heads,wf,indent=2)

    print  'datadowload completed !'

    filepaths = [pjoin(rawdir,filename) for filename in rawdir]

    return (filepaths,today)

def extractData(filepaths,date):

    for filepath in filepaths:

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

        process = gene_parser(filepath)

        head_fun = {
        'gene_info':process.gene_info,
        'gene_group':process.gene_group,
        'gene_neighbors':process.gene_neighbors,
        'gene2pubmed':process.gene_pubmed,
        'PRJ':process.gene_expression,
        'gene2refseq':process.gene_refseq,
        }

        for head in head_fun.keys():
            if filename.startswith(head):
                fun = head_fun.get(head)
                fun(fileversion,date)

        print filename,'done'

    for filepath in filepaths:

        filename = psplit(filepath)[1].strip()

        if filename.startswith('refseqgene'):

            version = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            process = gene_parser(filepath)

            process.gene_summary(version,date)

        print filename,'done'

        print 'extract and insert complete '

    # bkup all collections
    _mongodb = pjoin(ncbi_gene_db,'gene_{}'.format(date))

    createDir(_mongodb)

    colhead = 'ncbi.gene'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    return (filepaths,date)

def updateData(insert=False,_mongodb='../_mongodb/'):

    ncbi_gene_log = json.load(open(log_path))

    rawdir = pjoin(ncbi_gene_raw,'gene_{}'.format(today))

    #   EXPRESSION FILES
    expression_ftp_info = copy.deepcopy(ncbi_gene_ftp_infos)

    expression_ftp_info['logdir'] = ncbi_gene_expression_path

    ftp = connectFTP(**expression_ftp_info)

    gene_expression_filenames = ftp.nlst()

    # REFSEQ FILES 
    refseq_ftp_info = copy.deepcopy(ncbi_gene_ftp_infos)

    refseq_ftp_info['logdir'] =  ncbi_refseq_ftp_path

    ftp = connectFTP(**refseq_ftp_info)

    gene_refseq_filenames = [filename for filename in ftp.nlst() if filename.endswith('.genomic.gbff.gz') ]

    new = False

    filenames = ncbi_gene_filenames + gene_expression_filenames + gene_refseq_filenames

    for filename in filenames[::-1]:

        print '++++',filename

        if filename.startswith('gene'):

           ftp = connectFTP(**ncbi_gene_ftp_infos)
           download_ftp_infos = ncbi_gene_ftp_infos

        elif filename.startswith('refseqgene'):

           ftp = connectFTP(**refseq_ftp_info)
           download_ftp_infos = refseq_ftp_info

        else:
            # if no link with ftp for a while ,it may be break 
            ftp = connectFTP(**expression_ftp_info)
            download_ftp_infos = expression_ftp_info

        mt = ftp.sendcmd('MDTM {}'.format(filename)).strip()

        if mt != ncbi_gene_log.get(filename)[-1][0].strip():

            new = True

            createDir(rawdir)
            
            downloadOne(download_ftp_infos,filename,rawdir)

            ncbi_gene_log[filename].append((mt,today,model_name))

            print  '{} \'s new edition is {} '.format(filename,mt)

        else:
            print  '{} {} is the latest !'.format(filename,mt)

    if new:

        with open(log_path,'w') as wf:

            json.dump(ncbi_gene_log,wf,indent=2)

        (latest_file,version) = createNewVersion(ncbi_gene_raw,ncbi_gene_db,rawdir,'gene_',today)
        
        if insert:

            new_filepaths = [pjoin(rawdir,filename) for filename in os.listdir(rawdir)]

            # extractData(new_filepaths,version)

            insertUpdatedData(ncbi_gene_raw,latest_file,'gene_',version,extractData)

def selectData(querykey = 'GeneID',value='1'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'ncbi'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class gene_parser(object):
    
    def __init__(self,filepath):

        rawdir = psplit(filepath)[0].strip()

        filename = psplit(filepath)[1].strip()

        # gunzip file
        if filename.endswith('.gz'):

            command = 'gunzip  {}'.format(filepath)
            
            os.popen(command)

            filename = filename.replace('.gz','')

        tsvfile = open(pjoin(rawdir,filename))

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.rawdir = rawdir

        self.filename = filename

        self.tsvfile = tsvfile

        self.conn = conn

        self.db = db

        # print 'init completed !'

    def gene_info(self,version,date):

        print '+'*50
        print 'ncbi.gene.info started'
        colname = 'ncbi.gene.info'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        col.insert({'dataVersion':version,'dataDate':date,'colCreated':today,'file':'gene_info'})

        n =0

        gene_num = 0

        for line in self.tsvfile:

            data = line.strip().split('\t')

            if n == 0:
                keys =[ key.replace('#','').strip().replace('.','*').replace(' ','&') for key  in  data]
 
            else:
                data = dict(zip(keys,data))

                tax_id = data.get('tax_id')

                if tax_id != '9606':
                    continue

                # alter synonyms,dbxrefs,other_designations and feature_type
                '''
                Synonyms  list   '|',dbXrefs dict '|',':',Other_designations list '|',feature_type dict '|',':'
                '''
                data['Synonyms'] = data['Synonyms'].strip().split('|')
                data['Other_designations'] = data['Other_designations'].strip().split('|')

                dbXrefs = data['dbXrefs']

                if dbXrefs  != '-':
                    data['dbXrefs']  = dict([tuple(refs.split(':',1)) for refs in dbXrefs.split('|')])

                col.insert(data)

                gene_num += 1

                print 'ncbi.gene.info',n,gene_num,data['GeneID']

            n += 1

        print 'ncbi.gene.info completed'

    def gene_group(self,version,date):

        print '+'*50
        print 'ncbi.gene.group started'

        colname = 'ncbi.gene.group'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        col.insert({'dataVersion':version,'dataDate':date,'colCreated':today,'file':'gene_group'})
        # col.ensure_index({'GeneID':1})

        n =0

        # gene_group = dict()
        for line in self.tsvfile:

            data = line.strip().split('\t')
    
            if n == 0:
                keys =[ key.replace('#','').strip().replace('.','*').replace(' ','&') for key  in  data]

            else:
                data = dict(zip(keys,data))

                # filter line not human's
                other_tax_id = data['Other_tax_id']

                tax_id = data['tax_id']

                gene_id = data['GeneID']

                if  tax_id == '9606':
    
                    group = {
                    'relationship':data['relationship'],
                    'Other_tax_id':other_tax_id,
                    'Other_GeneID':data['Other_GeneID']
                     }

                elif other_tax_id == '9606':
    
                    gene_id = data['Other_GeneID']

                    group = {
                    'relationship':data['relationship'],
                    'Other_tax_id':tax_id,
                    'Other_GeneID':gene_id,
                     }

                else:
                    continue

                col.update(
                    {'GeneID':gene_id},
                    {'$push':{'gene_group':group}},
                    True,
                    )

                print 'ncbi.gene.group',n,gene_id

            n += 1

        print 'ncbi.gene.group completed'

    def gene_neighbors(self,version,date):

        print '+'*50
        print 'ncbi.gene.neighbors started'

        colname = 'ncbi.gene.neighbors'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':version,'dataDate':date,'colCreated':today,'file':'gene_neighbors'})

        n =0

        for line in self.tsvfile:

            data = line.strip().split('\t')
    
            if n == 0:
                keys =[ key.replace('#','').strip().replace('.','*').replace(' ','&') for key  in  data]

            else:

                data = dict(zip(keys,data))

                tax_id = data['tax_id']

                assembly = data['assembly']

                # filter tax_id
                if tax_id != '9606' or assembly == '-':
                    continue
                
                gene_id = data['GeneID']
         
                neighbors = dict()

                for key,val in data.items():

                    if val.count('|'):

                        val = val.strip().split('|')

                    neighbors[key] = val     

                col.insert(neighbors)

                print 'ncbi.gene.neighbors',n,gene_id #112312

            n += 1

        print 'ncbi.gene.neighbors completed'

    def gene_pubmed(self,version,date):

        print '+'*50
        print 'ncbi.gene.pubmed started'

        colname = 'ncbi.gene.pubmed'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':version,'dataDate':date,'colCreated':today,'file':'gene2pubmed'})
        # col.ensure_index({'GeneID':1})

        n =0

        for line in self.tsvfile:

            data = line.strip().split('\t')
    
            if n == 0:
                keys =[ key.replace('#','').strip().replace('.','*').replace(' ','&') for key  in  data]

            else:
                data = dict(zip(keys,data))

                # filter line not human's

                tax_id = data['tax_id']

                if  tax_id != '9606':
                    n += 1
                    continue

                gene_id = data['GeneID']
                pubmed_id = data['PubMed_ID']

                col.update(
                    {'GeneID':gene_id},
                    {'$push':{'PubMed_ID':pubmed_id}},
                    True,
                    )

                print 'ncbi.gene.pubmed',n ,gene_id

            n += 1

        print 'ncbi.gene.pubmed completed'

    def gene_expression(self,version,date):

        print '+'*50
        print 'ncbi.gene.expression started'

        colname = 'ncbi.gene.expression'


        col = self.db.get_collection(colname)

        allexists = True

        for project_desc in ['PRJNA280600','PRJNA270632','PRJEB4337','PRJEB2445']:

            result = col.find_one({'project_desc':project_desc})

            if not result:
                allexists = False

        if allexists:

            delCol('mydb_v1',colname)

        col.insert({'dataVersion':version,'dataDate':date,'colCreated':today,'file':'gene_expression'})

        xmlfile = self.tsvfile

        sample_source = dict()

        # can not parse by xml or lxml ,so deal as a txt file
        aset = dict()

        n = 0

        for line in xmlfile:

            line = line.strip()

            if not line or line == '<doc>':
                continue

            elif line == '</doc>' or line == '</doc><doc>':

                _id  = aset.get('id')

                if _id.startswith('metadata'):

                    doc_type = 'sample_infos'

                    sra_id = aset.get("sra_id")
                    sample_id = aset.get("sample_id")
                    source_name = aset.get("source_name").replace(',','_')

                    sample_source[sample_id] = {'source_name':source_name,'sra_id':sra_id}

                elif _id.split('_',1)[1].strip().startswith('SAM'):

                    doc_type = 'gene_infos'

                    gene_id = aset.get('gene')

                    sample_id = aset.get("sample_id")
                    sample = sample_source.get(sample_id)
                    if sample:
                        source_name = sample.get('source_name')
                        aset['source_name'] = source_name
                        
                        sra_id = sample.get('sra_id')
                        if sra_id :
                            aset['sra_id'] = sra_id

                    aset.pop('id')
                    aset.pop('gene')
                    aset['GeneID'] = gene_id


                    print 'ncbi.gene.expression',self.filename,n,gene_id
                    col.insert(aset)

                # dict clear
                aset = dict()

            else:
                key_val = line.split('<field name="')[1].split('</field>')[0].strip()
                (key,val) = tuple(key_val.split('">'))
                aset[key] = val

            n += 1
        
        print self.filename,'completed'

        # PRJEB2445_GRCh38.p2_107_expression.xml    / 11191815
        # PRJNA280600_GRCh38.p7_108_expression.xml completed /  6510332
        # PRJNA270632_GRCh38.p7_108_expression.xml /17754426
        # PRJEB4337_GRCh38.p7_108_expression.xml /37083157

    def gene_refseq(self,version,date):

        print '+'*50

        print 'ncbi.gene.refseq started'

        colname = 'ncbi.gene.refseq'

        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':version,'dataDate':date,'colCreated':today,'file':'gene2refseq'})

        # col.ensure_index({'GeneID':1})

        n = 0

        for line in self.tsvfile:

            data = line.strip().split('\t')

            if n == 0:
                keys =[ key.replace('#','').strip().replace('.','*').replace(' ','&') for key  in  data]
 
            else:

                data = dict(zip(keys,data))

                tax_id = data.get('tax_id')

                if tax_id != '9606':
                    n += 1
                    continue

                GeneID = data.get('GeneID')

                refseqid = data.get('genomic_nucleotide_accession*version')

                if refseqid:

                    refseqid = refseqid.replace('.','*')

                    col.update(
                        {'GeneID':GeneID},
                        {'$set':{'genomic_nucleotide_accession*version.{}'.format(refseqid):''}},
                        True,
                        )

                print 'ncbi.gene.refseq','tax_id',tax_id,'GeneID',GeneID,'refseqid',refseqid,'line',n

            n += 1

    def gene_summary(self,version,date):

        print '+'*50
        print 'ncbi.gene.summary started'

        colname = 'ncbi.gene.refseq'

        col = self.db.get_collection(colname)

        col.insert({'dataVersion':version,'dataDate':date,'colCreated':today,'file':'refseqgene'})

        locus = dict.fromkeys(['summary'],[])

        n = 0
        m = 0

        start = False

        for line in self.tsvfile:

            line = line.strip()

            if line.startswith('PRIMARY'):

                start = False

                version = locus['version'].replace('.','*')

                summary = locus['summary']

                if summary:

                    summary = ' '.join(locus['summary']).split('Summary:')[1].strip()

                else:
                    summary = ''

                docs = col.find({'genomic_nucleotide_accession*version.{}'.format(version):""})

                for doc in docs:

                    GeneID = doc.get('GeneID')

                    col.update(
                        {'GeneID':GeneID},
                        {'$set':{'genomic_nucleotide_accession*version.{}'.format(version):summary}},
                        False,
                        True
                        )

                    print GeneID

                m += 1

                print 'ncbi.gene.refseqgene line',n,'updated',m,'version',version

                # clear dict
                locus = dict.fromkeys(['summary'],[])

            else:

                if line.startswith('VERSION'):

                    version = line.split('VERSION')[1].strip()

                    locus['version'] = version

                elif line.startswith('Summary:'):

                    start = True

                if start:

                    locus['summary'].append(line)

            n += 1

        print self.filename,'completed'

class dbMap(object):

    '''
    this class is set to map ncbi gene id to other db
    '''

    def __init__(self):

        (db,db_cols) = initDB('mydb_v1') 

        self.db = db

        self.db_cols = db_cols

    def ncbiGeneID2hgncSymbol(self):
        '''
        this function is to create a mapping relation between NCBI GeneID with HGNC Symbol
        '''

        ncbi_gene_info_col = db_cols.get('ncbi.gene.info')

        hgnc_gene_col = db_cols.get('hgnc.gene')

        geneID2symbol = dict()

        ncbi_gene_info_docs = ncbi_gene_info_col.find({})

        for doc in ncbi_gene_info_docs:

            gene_id = doc.get('GeneID')

            hgnc_docs = hgnc_gene_col.find({})

   

    def mapping(self):

        # self.mapGeneID2Symbol()

        genid_refseq_summary = dict()

        n = 0

        for doc in self.docs:

            GenID = doc.get('GeneID')

            refseq = doc.get('genomic_nucleotide_accession*version')

            if refseq:
                
                for version,summary in refseq.items():

                    if summary:

                        if GenID not in genid_refseq_summary:

                            genid_refseq_summary[GenID] = dict()

                        genid_refseq_summary[GenID][version] = summary

            n += 1

            print n

        geneid_2orMoreSummary = dict()
        
        for geneid,infos in genid_refseq_summary.items():

            # infos = list(set(infos))

            genid_refseq_summary[geneid] = infos

            if len(infos) >= 2:

                geneid_2orMoreSummary[geneid] = infos

        with open('./geneid_refseq_summary.json','w') as wf:
            json.dump(genid_refseq_summary,wf,indent=8)

        with open('geneid_2orMoreSummary.json','w') as wf:
            json.dump(geneid_2orMoreSummary,wf,indent=8)

class filter(object):
    """docstring for filter"""
    def __init__(self, arg):
        super(filter, self).__init__()
        self.arg = arg
        
def main():

    modelhelp = model_help.replace('&'*6,'NCBI_GENE').replace('#'*6,'ncbi_gene')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,ncbi_gene_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # downloadData(redownload = True)
    # rawdir = '/home/user/project/dbproject/mydb_v1/ncbi_gene/dataraw/gene_171124120457/'
    # filepaths = [pjoin(rawdir,filename) for filename in os.listdir(rawdir)]
    # date = '171124120457'
    # extractData(filepaths,date)
    man = dbMap()



