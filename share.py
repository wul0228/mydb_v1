#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date:20171023
# author:wuling
# emai:ling.wu@myhealthgene.com

#+++++++++++++++++++++++++ packages ++++++++++++++++++++++++++++++++++++++#

from config import *

reload(sys)
sys.path.append('..')
sys.setdefaultencoding = ('utf-8')


#+++++++++++++++++++++++++ main code ++++++++++++++++++++++++++++++++++++++#

def createDir(dirpath):
    '''
    this function is to create directory if not exist
    '''
    if not os.path.exists(dirpath):

        os.mkdir(dirpath)

    return dirpath

def buildSubDir(name):
    '''
    this function is to build all sub-directory for specified
    '''
    db = pjoin(mydb_path,name)

    # _load = pjoin(mymol_path,name,'dataload')

    _raw = pjoin(mydb_path,name,'dataraw')

    _store =  pjoin(mydb_path,name,'datastore')

    _db = pjoin(mydb_path,name,'database')

    _map = pjoin(mydb_path,name,'datamap')


    for _dir in [ db,_raw,_store,_db,_map]:

        createDir(_dir)      

    return (db,_raw,_store,_db,_map)

def initLogFile(parser,modelname,storedir,mt=None,rawdir=None):

    with open(pjoin(storedir,'{}.log'.format(parser)),'w') as wf: 

        log_dict = dict()

        if any([parser.startswith(start) for start in [ 'ncbi','go','reactom','wiki'] ]):

            for filename in listdir(rawdir):

                if not filename.endswith('.gz'):
                    
                    name = filename.split('_213')[0].strip()

                else:
                    name = filename.split('_213')[0].strip() + '.gz'

                mt = '213 ' + filename.split('_213')[1].strip().split('_',1)[0].strip()

                date = filename.rsplit('_',1)[1].strip().split('.')[0].strip()

                if name not in log_dict:

                 log_dict[name] = list()

                log_dict[name].append((mt,date,modelname))

            json.dump(log_dict,wf,indent=2)

        elif parser.startswith('ensembl'):

            for filename in listdir(rawdir):

                mt = '213 ' + filename.split('_213')[1].strip().split('_',1)[0].strip()

                ver = ['GRCh37','GRCh38']

                for v in ver:

                    if filename.count(v):

                        for key,mark in ensembl_file_mark.items():

                            if key.count(v):

                                if filename.count(mark):

                                    log_dict[key] = list()

                                    log_dict[key].append((mt,today,modelname))

            json.dump(log_dict,wf,indent=2)

        elif parser.startswith('kegg'):

            for filename in listdir(rawdir):

                mt =filename.split('_',1)[1].strip().split('_',1)[0].strip()

                name =filename.split('_',1)[0].strip() + '.json'

                if name not in log_dict:

                    log_dict[name] = list()

                log_dict[name].append((mt,today,modelname))

            json.dump(log_dict,wf,indent=2)

def expanLogFile(log_path,modelname,rawdir):

        log_dict = json.load(open(log_path))

        for filename in os.listdir(rawdir):

            if not filename.endswith('.gz'):
                
                name = filename.split('_213')[0].strip()

            else:
                name = filename.split('_213')[0].strip() + '.gz'

            mt = '213 ' + filename.split('_213')[1].strip().split('_',1)[0].strip()

            date = filename.rsplit('_',1)[1].strip().split('.')[0].strip()

            if name not in log_dict:

                 log_dict[name] = list()

            log_dict[name].append((mt,date,modelname))

        with open(log_path,'w') as wf:

            json.dump(log_dict,wf,indent=2)


def lookforExisted(datadir,dirnamehead):

        existFile = filter(lambda x:x.startswith(dirnamehead),listdir(datadir))

        tips = '''
        there have been stored  editions of  below: \n
        {} \n
        if you still want to download again? 
        chose  y/n :'''.format(existFile)
     
        choice  = str(raw_input(tips))

        if choice != 'y':
            return  (None,None)

        else:
            return (choice,existFile)

def choseExisted(existFile):

    tips =  '''
    there are {}  edition below, please chose one of them to continue ?
    {}
    input a index like 0,1,2... (input 'q' to quit):'''.format(len(existFile), \
    [ "{} {} ".format(str(index),name) for index,name in enumerate(existFile) ])

    while True:

        index = raw_input(tips)

        if str(index) == 'q':
            return 'q'
        try:
            edition = int(index)
        except  Exception,e:
            print e

        if edition in range(len(existPubChemFile)):
            return edition

        else:
            print '\n !!! index out of range.please check again \n'

def connectFTP(host,user=None,passwd=None,logdir=None):
    '''
    this function is to connect  ftp site 
    '''
    ftp = FTP(host)

    if user or passwd:

        ftp.login(user,passwd)

    else:

        ftp.login()

    ftp.cwd(logdir)

    return ftp

def  ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath):
    '''
    this function is to download specified file from ftp site
    '''
    bufsize=1024 

    save_file_path =pjoin(rawdir,savefilename)

    file_handle=open(save_file_path,'wb')

    ftp.retrbinary('RETR {}'.format(remoteabsfilepath) ,file_handle.write ,bufsize) 
   
    ftp.set_debuglevel(0) 

    return save_file_path


def connect2DB(server = 'mongodb',host='localhots',port=27017,dbname='ChEBI'):
    '''
    this function is set to connect  database mymol in localhost mysql server
    '''
    if server == 'mongodb':

        db = MongoClient('mongodb://{}:{}/{}'.format(host,port,dbname))

        return db

    elif server == 'mysql':

        connection = MySQLdb.connect(host=host,port=port,user='root',passwd='281625',db=dbname)

        cursor = connection.cursor()

        return cursor

    else:

        print  'no server input'

def atomPair(): 

    #构建需要replace的带电原子类型与其对应的中性原子的pair对
    patts= (
    # Imidazoles
    ('[n+;H]','n'),
    # Amines
    ('[N+;!H0]','N'),
    # Carboxylic acids and alcohols ('[$([O-]);!$([O-][#7])]','O'), # Thiols
    ('[S-;X1]','S'),
    # Sulfonamides 
    ('[$([N-;X2]S(=O)=O)]','N'), 
    # Enamines 
    ('[$([N-;X2][C,N]=C)]','N'), 
    # Tetrazoles 
    ('[n-]','[nH]'),
    # Sulfoxides 
    ('[$([S-]=O)]','S'),
    # Amides
    ('[$([N-]C=O)]','N'),
    #
    ('[O-;X1]',"O"),
    #
    ('[O+;X3]',"O"),
    #
    ('[$([O-]=C)]','O'),
    #20170308
    ('[C-;X3]','C'),
    #20170308
    # ('[Se-;H2]','Se'),
    ('[c-;X3]','c')
    )
    return [(Chem.MolFromSmarts(x),Chem.MolFromSmiles(y,False)) for x,y in patts]

def neutrCharge(smiles):
    """
    this function is to transform the charged smiles to electroneutral
    """
    try:
        mol = mfsmi(smiles)
    except:
        return smiles

    if not mol:
        return smiles
 
    atomPairs= atomPair()

    #circulate all pairs to find if there is a substructure in pre-defined pairs
    for i,(reactant, product) in enumerate( atomPairs):

        while mol.HasSubstructMatch(reactant): 

            #ReplaceSubstructures可选择Replacement = True（默认为False）一步替换所有
            rms = AllChem.ReplaceSubstructs(mol, reactant, product) 

            #rms是一个tuple,内含多个重复的mol，原因不明
            mol = rms[0] 

    # ****** C[O+](C)C
    # ****** [HH].CC1CCC2C(C(OC3C24C1CCC(O3)(O4)C)OC5C(C6CCC(C7C68C(O5)(OC(O8)(CC7)C)C)C)C)C
    try:
        return mtsmi(mol)
    except:
        print '******',smiles
        return smiles

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

def dataFromDB(database,colnamehead,querykey,queryvalue=None):

    '''
    this function is set to select data from mongodb
    '''
    # get all edition collection
    col_names =[col_name for col_name in  database.collection_names() if col_name.startswith(colnamehead)]

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

    col = database.get_collection(col_name)

    print '*'*80

    while True:

        queryvalue = str(raw_input('input %s  (q to quit) : ' %  querykey))
        
        if queryvalue == 'q' or queryvalue =='Q':

            break

        else:
            
            docs = col.find({querykey:queryvalue})
           
            n = 0

            if docs:

                print '\n','Result: ','\n'

                docnum = 0

                for doc in docs:
                    docnum += 1

                    pprint.pprint(doc,indent=4,width=80,depth=None)
                    
                    doc.pop('_id')
                    
                    # with open('./out_{}.json'.format(docnum),'w') as wf:
                    #     json.dump(doc,wf,indent=8)

                    print '~'*50
                   
                    n += 1
                
                print 'allfind:',n
       
            else:
                print 'No record'

            print '-'*80

def bkup_allCols(dbname,colhead,_mongodb='../_mongodb/'):

    conn = MongoClient('localhost',27017)

    db = conn.get_database(dbname)

    col_names =[col_name for col_name in  db.collection_names() if col_name.startswith(colhead)]

    for col_name in col_names:
        
        col = db.get_collection(col_name)

        col_infos = col.find().limit(1)

        for doc in col_infos:

            dataVersion = doc.get('dataVersion')

            dataDate = doc.get('dataDate')

            colCreated = doc.get('colCreated')

            BK_VERSION = '{}_{}_{}'.format(dataVersion,dataDate,colCreated)

            bakeupCol('mydb_v1',col_name,BK_VERSION,_mongodb)

            break

def bakeupCol(dbname,colname,fileversion,_mongodb='../_mongodb/'):

    savefile = pjoin(_mongodb,'{}_{}.json'.format(colname,fileversion))
    
    # bakeup new version to _mongodb directory
    bakeup =  '/usr/local/mongodb/bin/mongoexport -d {}  -c  "{}"   -o  {}'.format(dbname,colname,savefile)

    print bakeup

    os.popen(bakeup)

    print '{} bakeup completed'.format(colname)
            
def delCol(db,colname):

    conn = MongoClient('localhost',27017)

    db = conn.get_database(db)

    col = db.get_collection(colname)

    col.drop()

    print db,colname,'dropped !'

def value2key(dic):
    '''
    this function is to overture a value as the key and the key as vaule, just like {a:[1,2],b:[3,2]} return {1:a,2:[a,b],3:b}
    note that the value of key must be list and the element of list must be hashable
    '''
    value_key = dict()

    for key,val in dic.items():

        if isinstance(val,unicode):

            if val not in value_key:
                value_key[val] = list()
            value_key[val].append(key)

        elif isinstance(val,list):

            for v in val :
                if v not in value_key:
                    value_key[v] = list()
                value_key[v].append(key)

    return value_key

def deBlankDict(dic):
    '''
    this function is to 
    a. delete key from dic if val is None
    b. if val is list but only contain  a element  so list transfer to this element
    c. if val is list  and have multi elements ,first dedup ,an then  if dict included , iterate to deblank
    d. if val is dict but only have one key , so ,delete the key from parent-dict and update with sub-dict
    '''
    
    for key,val in dic.items():

        if not val:
            
            dic.pop(key)

        elif isinstance(val,list):

            if len(val) == 1:

                dic[key] =val[0]

            else:
                # dedup
                _val = list()

                for v in val:

                    if v not in _val:

                        if isinstance(v,dict):

                            v = deBlankDict(v)

                        _val.append(v)

                dic[key] = _val

        elif isinstance(val,dict):

            if len(val.keys()) ==1:

                val_key = val.keys()[0]

                val_val = val[val_key]

                dic.pop(key)

                dic[val_key] = val_val

            else:
                deBlankDict(val)

    return dic


def dedupDicVal(dic):

    newdic = dict()

    for key,val in dic.items():

        newdic[key] = dict()

        for k,v in val.items():
            newdic[key][k] = list(set(v))

    return newdic

def strAndList(content):
    '''
    this function is to combine the unicode and list containing multi unicode like ['a',['b','c']] ,return a ['a','b','c']
    '''
    all_unicode = list()
    
    for i in content:

        if isinstance(i,unicode):

            all_unicode.append(i)

        elif isinstance(i,list):

            all_unicode += i

    return list(set(all_unicode))

def strAndDict(content,key):
    '''
    this function is to combine the unicode and dict value containing multi unicode like ['a',{'b':'c'}] ,return a and the valule of specified key like 'b', ['a','c']
    '''

    if isinstance(content,dict):

        return [content[key],]

    elif isinstance(content,list):

        tmpfunc = lambda x:x[key] if isinstance(x,dict) else x

        return [tmpfunc(i) for i in content]

def retuOneDictValue(content,key):

    if isinstance(content,dict):

        return content.get(key)

    elif isinstance(content,list):

       for i in content:
            if isinstance(i,dict):
                 return i.get(key)

def multiProcess(func,args,size=16):
    '''
    this function is to concurrent processing
    size -- run  processes all at once
    func --- the  function to run
    args  -- argument for function
    '''

    pool = ThreadPool(size)

    results = pool.map(func,args)

    pool.close

    pool.join

def createNewVersion(rawdir,dbdir,updated_storedir,latest_file_head,version):
    '''
    this function is to create a new .files in ****/database/  to record the newest  version
    args:
    updated_storedir -- the directory  store  updated data
    '''
    update_file_heads = dict()

    for filename in listdir(updated_storedir):

        head = filename.split('_213')[0].strip()

        update_file_heads[head] = filename

        # get the latest .files file that contain the latest files name in mongodb 
    filenames = [name for name in listdir(dbdir) if name.endswith('.files')]

    # print 'filenames',filenames

    latest = sorted(filenames,key=lambda x:x.split(latest_file_head)[1].strip())[-1]
        
    latest_file = json.load(open(pjoin(dbdir,latest)))

        # update the latest  files   with  updated  file
    for head ,name in update_file_heads.items():

        latest_file[head] = name

    with open(pjoin(dbdir,'{}{}.files').format(latest_file_head,version),'w') as wf:

        json.dump(latest_file,wf,indent=2)

    return (latest_file,version)

def insertUpdatedData(rawdir,latest_file,latest_file_head,version,extractData): 
    '''
    this function is to generate a  new collection in mongodb PubChem  with updated date and the old
    args:
    latest_file -- the file record the latest file names in newest version
    '''
    # update mongodb ,create new edition

        # all file name in new vrsion
    insertFiles = latest_file.values()

    _rawdirs =[dir_name for dir_name in listdir(rawdir) if dir_name.startswith(latest_file_head)]

    num = 0

    filepaths = list()
    # circulate to insert all files in insertFiles
    for _dir  in _rawdirs:

        dir_path = pjoin(rawdir,_dir)

        for filename in listdir(dir_path):

            if filename in insertFiles:

                filepath = pjoin(dir_path,filename)

                filepaths.append(filepath)

    # print filepaths

    extractData(filepaths,version)

    print 'insertUpdated completed'

def getOpts(modelhelp,funcs,insert=True):
    
    (downloadData,extractData,updateData,selectData,dbMap,model_store) = funcs
    try:

        (opts,args) = getopt.getopt(sys.argv[1:],"haumf:",['--help',"--all","--update","--map","--field=="])

        querykey,queryvalue=("","")

        for op,value in opts:

            if op in ("-h","--help"):

                print modelhelp

            elif op in ('-a','--all'):

                save,version = downloadData(redownload=True)
                store,version = extractData(save,version)

                _map = dbMap(version)
                _map.mapping()

            elif op in ('-u','--update'):
                updateData()

            elif op in ('-f','--field'):
                selectData(value)
               
    except getopt.GetoptError:

        sys.exit()
      
class DateEncoder(json.JSONEncoder):  

    def default(self, obj):  

        if isinstance(obj, datetime):  

            return obj.strftime('%Y-%m-%d %H:%M:%S')  

        # elif isinstance(obj, date):  

        #     return obj.strftime("%Y-%m-%d")  

        else:  

            return json.JSONEncoder.default(self, obj) 


def constance(db):

    go_ano_pro = {
    'EXP':'Experimental evidence code:Inferred from Experiment',
    'IDA':'Experimental evidence code:Inferred from Direct Assay',
    'IPI':'Experimental evidence code:Inferred from Physical Interaction',
    'IMP':'Experimental evidence code:Inferred from Mutant Phenotype',
    'IGI':'Experimental evidence code:Inferred from Genetic Interaction',
    'IEP':'Experimental evidence code:Inferred from Expression Pattern',
    'ISS':'Computational analysis evidence codes:Inferred from Sequence or structural Similarity',
    'ISO':'Computational analysis evidence codes:Inferred from Sequence Orthology',
    'ISA':'Computational analysis evidence codes:Inferred from Sequence Alignment',
    'ISM':'Computational analysis evidence codes:Inferred from Sequence Model',
    'IGC':'Computational analysis evidence codes:Inferred from Genomic Context',
    'IBA':'Computational analysis evidence codes:Inferred from Biological aspect of Ancestor',
    'IBD':'Computational analysis evidence codes:Inferred from Biological aspect of Descendant',
    'IKR':'Computational analysis evidence codes:Inferred from Key Residues',
    'IRD':'Computational analysis evidence codes:Inferred from Rapid Divergence',
    'RCA':'Computational analysis evidence codes:Inferred from Reviewed Computational Analysis',
    'TAS':'Author statement codes:Traceable Author Statement',
    'NAS':'Author statement codes:Non-traceable Author Statement',
    'IC':'Curatorial statement evidence codes:Inferred by Curator',
    'ND':'Curatorial statement evidence codes:No biological Data available (ND) evidence code',
    'IEA':'Automatically-Assigned evidence:Inferred from Electronic Annotation',
}
    go_dbref_link = {'GO_REF':'https://github.com/geneontology/go-site/blob/master/metadata/gorefs/goref-GO_REF.md',
                                'PMID':'https://www.ncbi.nlm.nih.gov/pubmed/?term=PMID',
                                'Reactome':'https://reactome.org/content/detail/Reactome',
                                'DOI':'http://dx.doi.org/DOI'}

    go_namespace = {'biological_process':'BP','cellular_component':'CC','molecular_function':'MF'}

    disgenet_aso_type = {
    'Therapeutic': 'This relationship indicates that the gene/protein has a therapeutic role in the amelioration of the disease.',
    'Biomarker': 'This relationship indicates that the gene/protein either plays a role in the etiology of the disease (e.g. participates in the molecular mechanism that leads to disease) or is a biomarker for a disease.',
    'GenomicAlterations': 'This relationship indicates that a genomic alteration is linked to the gene associated with the disease phenotype.',
    'GeneticVariation': 'This relationship indicates that a sequence variation (a mutation, a SNP) is associated with the disease phenotype, but there is still no evidence to say that the variation causes the disease.',
    'CausalMutation': 'This relationship indicates that there are allelic variants or mutations known to cause the disease.',
    'GermlineCausalMutation': 'This relationship indicates that there are germline allelic variants or mutations known to cause the disease, and they may be passed on to offspring.',
    'SomaticCausalMutation': 'This relationship indicates that there are somatic allelic variants or mutations known to cause the disease, but they may not be passed on to offspring.',
    'ChromosomalRearrangement': 'This relationship indicates that a gene is included in a chromosomal rearrangement associated with a particular manifestation of the disease.',
    'FusionGene': 'This relationship indicates that the fusion between two different genes (between promoter and/or other coding DNA regions) is associated with the disease.',
    'SusceptibilityMutation': 'This relationship indicates that a gene mutation in a germ cell that predisposes to the development of a disorder, and that is necessary but not sufficient for the manifestation of the disease.',
    'ModifyingMutation': 'This relationship indicates that a gene mutation is known to modify the clinical presentation of the disease.',
    'GermlineModifyingMutation': 'This relationship indicates that a germline gene mutation modifies the clinical presentation of the disease, and it may be passed on to offspring.',
    'SomaticModifyingMutation': 'This relationship indicates that a somatic gene mutation modifies the clinical presentation of the disease, but it may not be passed on to offspring.',
    'AlteredExpression': 'This relationship indicates that an altered expression of the gene is associated with the disease phenotype.',
    'Post-translationalModification': 'This relationship indicates that alterations in the function of the protein by means of post-translational modifications (methylation or phosphorylation of the protein) are associated with the disease phenotype.',
}

    dic = {'go_ano_pro':go_ano_pro,'go_namespace':go_namespace,'go_dbref_link':go_dbref_link,'disgenet_aso_type':disgenet_aso_type}

    return dic.get(db)

def main():

    print neutrCharge('c1ccccc1CC([NH3+])C(=O)[O-]')
    # ncbi_seq_ftp_infos = {
    # 'host' : 'ftp.ncbi.nlm.nih.gov' ,
    # 'user':'anonymous',
    # 'passwd' : '',
    # 'logdir' : '/blast/db/FASTA/'
    # }
    # ftp = connectFTP(**ncbi_seq_ftp_infos)
    # filename = 'nr.gz'
    # savefilename = 'nr.gz'
    # rawdir = '/home/user/'
    # remoteabsfilepath = '/blast/db/FASTA/nr.gz'

    # ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath)

if __name__ == '__main__' :

    main()