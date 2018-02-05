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

current_path = psplit(os.path.abspath(__file__))[0]

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

def standarString(i,leftjoin,rightjoin):

    '''
    this function is set to transform string " ... " to  ...  to delelet the ''  in the head or the tail
    '''

    return '{}'.format(rightjoin).join('{}'.format(leftjoin).join(i.split('"',1)).rsplit('"',1))

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
    # bufsize=1024 
    bufsize=8192 
    # bufsize=16384 
    # bufsize=24576
    # bufsize=32768 

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

    # col_names.sort(key = lambda x:x.split('_')[1].strip())
    
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
                    
                    doc.pop('_id')

                    docnum += 1

                    pprint.pprint(doc,indent=4,width=80,depth=None)
                    
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

    print '{} backup completed'.format(colname)
            
def delCol(db,colname):

    conn = MongoClient('localhost',27017)

    db = conn.get_database(db)

    col = db.get_collection(colname)

    col.drop()

    print db,colname,'dropped !'

class fram(object):
    """docstring for fram"""
    def __init__(self):

        super(fram, self).__init__()

        (db,db_cols) = initDB('mydb_v1')

        self.db = db

        self.db_cols = db_cols

        # self.db_colnames = db_colnames

    def  deval(self,dic):

        '''
        this function is  set to dedup the key with same value  and  just one key remained
        '''
        v  = list()

        for key,val in dic.items():
            if val :
                if   str(val) not in v:
                    v.append(str(val))

                else:
                    dic.pop(key)
        return dic

    def dekey(self,key,col,keyclass):

        '''
        this function is set to return keys in a dict and record the key with a dict value
        '''
        print keyclass

        key_fram = dict()

        dic_keys = list()

        docs = col.find({})

        n = len(keyclass)

        for doc in docs:

            for _class in keyclass:

                doc = doc.get(_class,{})

            if doc and isinstance(doc,dict):

                for k,v in doc.items():

                    if isinstance(v,unicode):
                        if k not in key_fram:
                            key_fram[k] = ''

                    if isinstance(v,list):

                        if all([isinstance(i,unicode) for i in v]):
                            if k not in key_fram:
                                key_fram[k] = ''

                        if all([isinstance(i,dict) for i in v]):
                            try:
                                if key not in key_fram:
                                    key_fram[k] = list()
                                    key_fram[k].append(dict.fromkeys(v[0].keys(),''))
                            except:
                                print '==============',v

                    elif isinstance(v,dict):
                        dic_keys.append(k)

        dic_keys = list(set(dic_keys))

        print '-'*4*n,key
        print '-'*4*n,'dic_keys',len(dic_keys)
        return (key_fram,dic_keys)

    def dbfram(self):

        framdir = pjoin(current_path,'_fram_{}'.format(today))
        createDir(framdir)

        # with open(pjoin(framdir,'fram.log'),'w') as wf:
        #     json.dump(self.db_colnames,wf,indent=4)

        for _db,_col in self.db_cols.items():

            # if _db  in ['clinvar_variant','disgenet_disease','miRTarBase','ensembl_gene','go_gene','hgnc_gene','ncbi_gene','protein_atlas','kegg_pathway','hpo_phenotypic']:
            if  _db  in ['igsr.variant',]:
                continue

            # if _db != 'ncbi_gene':
            #     continue
            print '*'*100
            print _db
            col_fram = self.framCreate(_col)

            for key in ['colCreated','dataVersion','file','dataDate','_id']:
                if key in col_fram:
                    col_fram.pop(key)

            with open(pjoin(framdir,'fram_{}.json'.format(_db)),'w') as wf:
                json.dump(col_fram,wf,indent=4)

    def framCreate(self,col):

        docs = col.find({})

        fram = dict()

        key_1  = list()

        for doc in docs:

            for key,val in doc.items():

                if key not in fram:

                    fram[key] = ''

                if val and isinstance(val,list):

                    if all([isinstance(i,dict) for i in val]):
                        fram[key] = list()
                        fram[key].append(dict.fromkeys(val[0].keys(),''))

                elif val and isinstance(val,dict):
                    key_1.append(key)
        
        key_1 = list(set(key_1))

        print len(fram)
        print len(key_1)
        print key_1

        print '-'*50

        if key_1:
            for key1 in key_1:

                (key1_fram,dic_key1s) = self.dekey(key1,col,[key1,])

                # if key1 in ['gene_neighbors','GO',]: # ncbi GO
                #     key1_fram ={key1_fram.keys()[0]:key1_fram[key1_fram.keys()[0]]}

                if dic_key1s:
                    # if key1 in ['gene','path_entry','path_reaction','DECIPHER','ORPHA','OMIM','GeneProduct','Metabolite','Rna','Other','Complex','Protein','Pathway']: #miRTarBase   kegg_pathway  hpo wiki 
                    #     dic_key1s =dic_key1s[10:11]

                    for key2 in dic_key1s:
                        (key2_fram,dic_key2s) = self.dekey(key2,col,[key1,key2])

                        # if key1 in ['project', ]: #ncbi
                        #     key2_fram ={key2_fram.keys()[0]:key2_fram[key2_fram.keys()[0]]}

                        if dic_key2s:

                            # if key2 == 'transcript' or key1 == 'nodes': # ensembl reactom
                            #     dic_key2s = dic_key2s[:1]

                            for key3 in dic_key2s:
                                (key3_fram,dic_key3s) = self.dekey(key3,col,[key1,key2,key3])

                                if dic_key3s:
                                    for key4 in dic_key3s:
                                     (key4_fram,dic_key4s) = self.dekey(key4,col,[key1,key2,key3,key4])

                                     if dic_key4s:

                                         # if key4 == 'exon':
                                         #    dic_key4s = dic_key4s[1:2]

                                            for key5 in dic_key4s:
                                             (key5_fram,dic_key5s) = self.dekey(key5,col,[key1,key2,key3,key4,key5])

                                             key4_fram[key5] = key5_fram

                                     key3_fram[key4] = key4_fram
                                key2_fram[key3] = key3_fram                        
                        key1_fram[key2] = key2_fram
                fram[key1] = key1_fram

        fram = self.deval(fram)
        return fram
          
    def colInstance(self):

        _instance_dir = pjoin('./','_instance_{}'.format(today))
        createDir(_instance_dir)

        for colname,col in self.db_cols.items():

            print colname

            docs = col.find({})

            n = 0

            for doc in docs:

                n += 1

                if n == 100:

                    doc.pop('_id')

                    save_path = pjoin(_instance_dir,'instance_{}.json'.format(colname))
                    with open(save_path,'w') as wf :
                        json.dump(doc,wf,indent=8)

                    break

def filterKey(doc,save_keys):
    
    filter_doc = dict()

    for key in save_keys:

        val = doc.get(key)

        if not val:
            val = ''

        filter_doc[key] = val

    return filter_doc

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

def createNewVersion(rawdir,dbdir,updated_rawdir,latest_file_head,version):
    '''
    this function is to create a new .files in ****/database/  to record the newest  version
    args:
    updated_storedir -- the directory  store  updated data
    '''
    update_file_heads = dict()

    for filename in listdir(updated_rawdir):

        head = filename.split('_213')[0].strip()

        # ensembl gene
        if head.count('.chr.gtf'): 

            head = head.split('.chr.gtf')[0].rsplit('.',1)[0] + '.chr.gtf'

        update_file_heads[head] = pjoin(updated_rawdir,filename)

        # get the latest .files file that contain the latest files name in mongodb 
    filenames = [name for name in listdir(dbdir) if name.endswith('.files')]

    latest = sorted(filenames,key=lambda x:x.split(latest_file_head)[1].strip())[-1]
        
    latest_filepath = json.load(open(pjoin(dbdir,latest)))

    # update the latest  files   with  updated  file
    for head ,name in update_file_heads.items():

        latest_filepath[head] = name

    with open(pjoin(dbdir,'{}{}.files').format(latest_file_head,version),'w') as wf:

        json.dump(latest_filepath,wf,indent=2)

    return (latest_filepath,version)

def insertUpdatedData(rawdir,latest_file,dir_head,version,extractData): 
    '''
    this function is to generate a  new collection in mongodb PubChem  with updated date and the old
    args:
    latest_file -- the file record the latest file names in newest version
    '''
    # update mongodb ,create new edition

        # all file name in new vrsion
    insertFiles = latest_file.values()

    _rawdirs =[dir_name for dir_name in listdir(rawdir) if dir_name.startswith(dir_head)]

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
    
    (downloadData,extractData,updateData,selectData,model_store) = funcs
    try:

        (opts,args) = getopt.getopt(sys.argv[1:],"hauf:",['--help',"--all","--update","--field=="])

        querykey,queryvalue=("","")

        for op,value in opts:

            if op in ("-h","--help"):

                print modelhelp

            elif op in ('-a','--all'):

                save,date = downloadData(redownload=True)
                store,date = extractData(save,date)

            elif op in ('-u','--update'):
                updateData()

            elif op in ('-f','--field'):
                selectData(value)
               
    except getopt.GetoptError:

        sys.exit()
      
# class DateEncoder(json.JSONEncoder):  
  
#     def __init__(self):

#         if isinstance(obj, datetime):  

#             return obj.strftime('%Y-%m-%d %H:%M:%S')  

#         # elif isinstance(obj, date):  

#         #     return obj.strftime("%Y-%m-%d")  

#         else:  

#             return json.JSONEncoder.default(self, obj) 


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
    
    dgidb  = {
'activator':  'An activator interaction is when a drug activates a biological response from a target, although the mechanism by which it does so may not be understood.    [DrugBank examples: PMID12070353]',
'adduct': 'An adduct interaction is when a drug-protein adduct forms by the covalent binding of electrophilic drugs or their reactive metabolite(s) to a target protein.   [PMID16199025]',
'agonist':    'An agonist interaction occurs when a drug binds to a target receptor and activates the receptor to produce a biological response.   [Wikipedia - Agonist]',
'allosteric modulator':  ' An allosteric modulator interaction occurs when drugs exert their effects on their protein targets via a different binding site than the natural (orthosteric) ligand site. [PMID24699297]',
'antagonist': 'An antagonist interaction occurs when a drug blocks or dampens agonist-mediated responses rather than provoking a biological response itself upon binding to a target receptor. [Wikipedia - Receptor Antagonist]',
'antibody':   'An antibody interaction occurs when an antibody drug specifically binds the target molecule.    [Wikipedia - Antibody]',
'antisense oligonucleotide':  'An antisense oligonucleotide interaction occurs when a complementary RNA drug binds to an mRNA target to inhibit translation by physically obstructing the mRNA translation machinery.  [PMID10228554]',
'binder': 'A binder interaction has drugs physically binding to their target.  [DrugBank examples: PMID12388666 PMID7584665 PMID14507470]',
'blocker':    'Antagonist interactions are sometimes referred to as blocker interactions; examples include alpha blockers, beta blockers, and calcium channel blockers.    [Wikipedia - Receptor Antagonist]',
'chaperone':  'Pharmacological chaperone interactions occur when substrates or modulators directly bind to a partially folded biosynthetic intermediate to stabilise the protein and allow it to complete the folding process to yield a functional protein.   [PMID17597553]',
'cleavage':   'Cleavage interactions take place when the drug promotes degeneration of the target protein through cleaving of the peptide bonds.   [DrugBank example: PMID10666203]',
'cofactor':   'A cofactor is a drug that is required for a target protein\'s biological activity.   [Wikipedia - Cofactor]',
'competitive':    'Competitive antagonists (also known as surmountable antagonists) are drugs that reversibly bind to receptors at the same binding site (active site) on the target as the endogenous ligand or agonist, but without activating the receptor. [Wikipedia - Receptor Antagonist]',
'immunotherapy':  'In immunotherapy interactions, the result of the drug acting on the target is an induction, enhancement, or suppression of an immune response.  [Wikipedia - Immunotherapy]',
'inducer':    'In inducer interactions, the drug increases the activity of its target enzyme.  [Wikipedia - Enzyme Inducer]',
'inhibitor':  'In inhibitor interactions, the drug binds to a target and decreases its expression or activity. Most interactions of this class are enzyme inhibitors, which bind an enzyme to reduce enzyme activity.  [Wikipedia - Enzyme Inhibitor]',
'inhibitory allosteric modulator':    'In inhibitory allosteric modulator interactions, also called negative allosteric modulator interactions, the drug will inhibit activity of its target enzyme.   [PMID24699297]',
'inverse agonist':    'An inverse agonist interaction occurs when a drug binds to the same target as an agonist, but induces a pharmacological response opposite to that of the agonist.   [Wikipedia - Inverse Agonist]',
'ligand': 'In ligand interactions, a drug forms a complex with its target protein to serve a biological function.  [Wikipedia - Ligand]',
'modulator':  'In modulator interactions, the drug regulates or changes the activity of its target. In contrast to allosteric modulators, this interaction type may not involve any direct binding to the target.  [Modulators. Segen\'s Medical Dictionary. (2011). Retrieved online October 9 2015.]',
'multitarget':    'In multitarget interactions, drugs achieve a physiological effect through simultaneous interaction with multiple gene targets.  [PMID22768266]',
'n/a':    'In a negative modulator interaction, the drug negatively regulates the amount or activity of its target. In contrast to an inhibitory allosteric modulator, this interaction type may not involve any direct binding to the target. [Wikipedia - Allosteric modulator]',
'other/unknown':  'This is a label given by the reporting source to an interaction that doesn\'t belong to other interaction types, as defined by the reporting source. [N/A]',
'partial agonist':   ' In a partial agonist interaction, a drug will elicit a reduced amplitude functional response at its target receptor, as compared to the response elicited by a full agonist.    [Wikipedia - Receptor Antagonist]',
'partial antagonist': 'In a partial antagonist interaction, a drug will only partially reduce the amplitude of a functional response at its target receptor, as compared to the reduction of response by a full antagonist.    [PMID6188923]',
'positive allosteric modulator':  'In a positive allosteric modulator interaction, the drug increases activity of the target enzyme.   [PMID24699297]',
'potentiator':    'In a potentiator interaction, the drug enhances the sensitivity of the target to the target\'s ligands.  [Wikipedia - Potentiator]',
'product of': 'These "interactions" occur when the target gene produces the endogenous drug.   [N/A]',
'stimulator':' In a stimulator interaction, the drug directly or indirectly affects its target, stimulating a physiological response.  [DrugBank Examples: PMID23318685 PMID17148649 PMID15955613]',
'suppressor': 'In a suppressor interaction, the drug directly or indirectly affects its target, suppressing a physiological process.   [DrugBank Examples: PMID8386571 PMID14967460]',
'vaccine':   ' In vaccine interactions, the drugs stimulate or restore an immune response to their target.   [N/A]',
}
    dic = {'go_ano_pro':go_ano_pro,'go_namespace':go_namespace,'go_dbref_link':go_dbref_link,'disgenet_aso_type':disgenet_aso_type,'dgidb':dgidb}

    return dic.get(db)

def main():
    pass
    # print neutrCharge('c1ccccc1CC([NH3+])C(=O)[O-]')
    # colFram('mydb_v1')

    # ncbi_gene_ftp_infos = {
    # 'host' : 'ftp.ncbi.nlm.nih.gov' ,
    # 'user':'anonymous',
    # 'passwd' : '',
    # 'logdir' : '/gene/DATA/'
    # }
    # ftp = connectFTP(**ncbi_gene_ftp_infos)
    # filename = 'gene_info.gz'
    # savefilename = 'gene_info_8192.gz'
    # rawdir = '/home/user/'
    # remoteabsfilepath = '/gene/DATA/gene_info.gz'

    # start = time.clock()
    # print start
    # ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath)
    # end = time.clock()
    # print end
    # print end-start

if __name__ == '__main__' :

    main()
    # man = fram()
    # man.dbfram()
    # man.colInstance()
    # 
    # print 


