#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2017/12/25
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download ,parser(extract,satndar,insert) and update ncbi gene data from ncbi ftp site

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

def downloadData(redownload = False):
    '''
    this function is to download the raw data from ncbi gene FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    #--------------------------------------------------------------------------------------------------------------------
    if  not redownload:

        (choice,existNcbiFile) = lookforExisted(ncbi_gene_raw,'gene')

        if choice != 'y':
            return

    if redownload or not existNcbiFile or  choice == 'y':

        rawdir = pjoin(ncbi_gene_raw,'gene_{}'.format(today))

        createDir(rawdir)

        process = parser(today)

        func = lambda x:process.getOne(ncbi_gene_ftp_infos,x,rawdir)

        #--------------------------------------------------------------------------------------------------------------------
        # 1. download gene_group ,gene_neibors, gene_pubmed ,gene_info
        multiProcess(func,ncbi_gene_filenames,size=10)

        #--------------------------------------------------------------------------------------------------------------------
        # 2. download gene_expression 
        ncbi_gene_ftp_infos['logdir'] =  ncbi_gene_expression_path

            # get expression filenames
        ftp = connectFTP(**ncbi_gene_ftp_infos)

        gene_expression_filenames = ftp.nlst()
        
            # download
        multiProcess(func,gene_expression_filenames,size=4)

        #--------------------------------------------------------------------------------------------------------------------
        # 3. download refseq filenames
        ncbi_gene_ftp_infos['logdir'] =  ncbi_gene_refseq_ftp_path

        ftp = connectFTP(**ncbi_gene_ftp_infos)

        gene_refseq_filenames = [filename for filename in ftp.nlst() if filename.endswith('.genomic.gbff.gz') ]

        multiProcess(func,gene_refseq_filenames,size=5)
        
    #--------------------------------------------------------------------------------------------------------------------
    #  generate .log file in current  path
    if not os.path.exists(log_path):
        initLogFile('ncbi_gene',model_name,ncbi_gene_model,rawdir=rawdir)
    else:
        expanLogFile(log_path,model_name,rawdir)

    #--------------------------------------------------------------------------------------------------------------------
    # generate .files file in database
    update_file_heads =dict()

    for filename in listdir(rawdir):

        head = filename.split('_213')[0].strip()

        update_file_heads[head] = pjoin(rawdir,filename)

    with open(pjoin(ncbi_gene_db,'gene_{}.files'.format(today)),'w') as wf:
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
    gene_info_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('gene_info')]
    gene_group_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('gene_group')]
    gene_neighbors_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('gene_neighbors')]
    gene_pubmed_paths =  [path for path in filepaths if psplit(path)[1].strip().startswith('gene2pubmed')]
    gene_expression_paths =  [path for path in filepaths if psplit(path)[1].strip().startswith('PRJ')]
    gene_refseq_paths =  [path for path in filepaths if psplit(path)[1].strip().startswith('gene2refseq')]
    gene_summary_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('refseqgene')]

    # 2. parser filepaths step by step
    process = parser(date)
    
    # --------------------------------ncbi.gene.info-------------------------------------------------------------------------
    process.gene_info(gene_info_paths)

    # --------------------------------ncbi.gene.group-------------------------------------------------------------------------
    process.gene_group(gene_group_paths)

    # --------------------------------ncbi.gene.neighbors-------------------------------------------------------------------------
    process.gene_neighbors(gene_neighbors_paths)

    # --------------------------------ncbi.gene.pubmed-------------------------------------------------------------------------
    process.gene_pubmed(gene_pubmed_paths)

    # --------------------------------ncbi.gene.expression-------------------------------------------------------------------------
    process.gene_expression(gene_expression_paths)
    
    # --------------------------------ncbi.gene.refseq-------------------------------------------------------------------------
    process.gene_refseq(gene_refseq_paths)

    # --------------------------------ncbi.gene.refseq-------------------------------------------------------------------------
    process.gene_summary(gene_summary_paths)

    print 'extract and insert complete '

    # 3. bkup all collections
    _mongodb = pjoin(ncbi_gene_db,'gene_{}'.format(date))

    createDir(_mongodb)

    colhead = 'ncbi.gene'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    return (filepaths,date)

def updateData(insert=True):
    '''
    this function is set to update all file in log
    '''
    ncbi_gene_log = json.load(open(log_path))

    updated_rawdir = pjoin(ncbi_gene_raw,'gene_{}'.format(today))

    #-----------------------------------------------------------------------------------------------------------------
    # get expression files
    expression_ftp_info = copy.deepcopy(ncbi_gene_ftp_infos)

    expression_ftp_info['logdir'] = ncbi_gene_expression_path

    ftp = connectFTP(**expression_ftp_info)

    gene_expression_filenames = ftp.nlst()
    #-----------------------------------------------------------------------------------------------------------------
    # get refseq files 
    refseq_ftp_info = copy.deepcopy(ncbi_gene_ftp_infos)

    refseq_ftp_info['logdir'] =  ncbi_gene_refseq_ftp_path

    ftp = connectFTP(**refseq_ftp_info)

    gene_refseq_filenames = [filename for filename in ftp.nlst() if filename.endswith('.genomic.gbff.gz') ]
    
    #-----------------------------------------------------------------------------------------------------------------
    new = False
    
    process = parser(today)

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

            createDir(updated_rawdir)

            process.getOne(download_ftp_infos,filename,updated_rawdir)

            ncbi_gene_log[filename].append((mt,today,model_name))

            print  '{} \'s new edition is {} '.format(filename,mt)

        else:
            print  '{} {} is the latest !'.format(filename,mt)  
    #-----------------------------------------------------------------------------------------------------------------
    if new:

        with open(log_path,'w') as wf:

            json.dump(ncbi_gene_log,wf,indent=2)

        (latest_filepath,version) = createNewVersion(ncbi_gene_raw,ncbi_gene_db,updated_rawdir,'gene_',today)
        
        if insert:

            extractData(latest_filepath.values(),version)

        return 'update successfully'

    else:

        return 'new version is\'t detected'

def selectData(querykey = 'GeneID',queryvalue='1'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'ncbi.gene'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):

    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''

    def __init__(self,date):

        super(parser,self).__init__()

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.conn = conn

        self.db = db

        self.date = date

    def getOne(self,ncbi_gene_ftp_infos,filename,rawdir):
        '''
        this function is to download  one file under  a given remote dir 
        args:
        ncbi_gene_ftp_infos --  a specified ftp connection info  
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

    def gene_info(self,filepaths):

        '''
        this function is set parser gene_info 
        '''
        print '+'*50

        colname = 'ncbi.gene.info'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('GeneID',1),])
        #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not col.find_one({'colCreated':{'$exists':True}}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'gene_info'})
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
            
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file
            tsvfile = open(filepath)
        
            n =0

            human_gene_num = 0

            for line in tsvfile:

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

                    human_gene_num += 1

                    print 'ncbi.gene.info',n,'human_gene_num',human_gene_num,'GeneID',data['GeneID']
                n += 1

        print 'ncbi.gene.info completed'

    def gene_group(self,filepaths):

        print '+'*50

        colname = 'ncbi.gene.group'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('GeneID',1),])
         #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not col.find_one({'colCreated':{'$exists':True}}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'gene_group'})
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
            
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file       
            tsvfile = open(filepath)

            n =0

            for line in tsvfile:

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

    def gene_neighbors(self,filepaths):

        print '+'*50

        colname = 'ncbi.gene.neighbors'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('GeneID',1),])
         #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not col.find_one({'colCreated':{'$exists':True}}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'gene_neighbors'})
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
            
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file       
            tsvfile = open(filepath)

            n =0

            for line in tsvfile:

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

    def gene_pubmed(self,filepaths):

        print '+'*50

        colname = 'ncbi.gene.pubmed'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('GeneID',1),])
         #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not col.find_one({'colCreated':{'$exists':True}}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'gene2pubmed'})
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
            
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file       
            tsvfile = open(filepath)

            n =0

            for line in tsvfile:

                data = line.strip().split('\t')
        
                if n == 0:
                    keys =[ key.replace('#','').strip().replace('.','*').replace(' ','&') for key  in  data]
                else:
                    data = dict(zip(keys,data))

                    # filter line not human's
                    if  data['tax_id'] != '9606':
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

    def gene_expression(self,filepaths):

        print '+'*50

        colname = 'ncbi.gene.expression'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)

        col.ensure_index([('GeneID',1),])
         #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not col.find_one({'colCreated':{'$exists':True}}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'gene_expression'})
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
            
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file       
            xmlfile = open(filepath)

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

                        print 'ncbi.gene.expression',filename,n,gene_id
                        col.insert(aset)

                    # dict clear
                    aset = dict()

                else:
                    key_val = line.split('<field name="')[1].split('</field>')[0].strip()
                    (key,val) = tuple(key_val.split('">'))
                    aset[key] = val

                n += 1
            
            print filename ,'done'

        print 'ncbi.gene.expressioncompleted'
        # PRJEB2445_GRCh38.p2_107_expression.xml    / 11191815
        # PRJNA280600_GRCh38.p7_108_expression.xml completed /  6510332
        # PRJNA270632_GRCh38.p7_108_expression.xml /17754426
        # PRJEB4337_GRCh38.p7_108_expression.xml /37083157

    def gene_refseq(self,filepaths):

        print '+'*50

        colname = 'ncbi.gene.refseq'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        col = self.db.get_collection(colname)
        col.ensure_index([('GeneID',1),])
         #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not col.find_one({'colCreated':{'$exists':True}}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'gene2refseq'})
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
            
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file       
            tsvfile = open(filepath)

            n =0

            for line in tsvfile:

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

    def gene_summary(self,filepaths):

        print '+'*50

        colname = 'ncbi.gene.refseq'

        # before insert ,truncate collection

        col = self.db.get_collection(colname)

        col.ensure_index([('GeneID',1),])
         #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not col.find_one({'colCreated':{'$exists':True}}):

                col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'refseqgene'})
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # gunzip file
            if filename.endswith('.gz'):

                command = 'gunzip  {}'.format(filepath)
            
                os.popen(command)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file
            tsvfile = open(filepath)

            locus = dict.fromkeys(['summary'],[])

            n = 0
            m = 0

            start = False

            for line in tsvfile:

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

            print filename,'completed'

class dbMap(object):
    '''
    this class is set to map ncbi gene id to other db
    '''
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
        this function is to create a mapping relation between NCBI GeneID with HGNC Symbol
        '''
        entrez2symbol = self.process.entrezID2hgncSymbol()

        ncbi_gene_info_col = self.db_cols.get('ncbi.gene.info')

        output = dict()

        hgncSymbol2ncbiGeneID = output

        ncbi_gene_info_docs = ncbi_gene_info_col.find({})

        for doc in ncbi_gene_info_docs:

            gene_id = doc.get('GeneID')

            gene_symbol = entrez2symbol.get(gene_id)

            if gene_symbol:
                
                for symbol in gene_symbol:

                    if symbol not in output:
                        output[symbol] = list()

                    output[symbol].append(gene_id)

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val    

        print 'hgncSymbol2ncbiGeneID',len(output)

        # with open('./hgncSymbol2ncbiGeneID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return  (output,'GeneID')

class dbFilter(object):

    '''this class is set to filter part field of data in collections  in mongodb '''

    def __init__(self, arg):
        super(filter, self).__init__()
        self.arg = arg
    
    def gene_topic(self):
        '''
        this function is set to filter filed of doc for gene_topic 
        '''
        pass

def main():

    modelhelp = model_help.replace('&'*6,'NCBI_GENE').replace('#'*6,'ncbi_gene')

    funcs = (downloadData,extractData,updateData,selectData,ncbi_gene_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()



