#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/26
# author:ling.wu
# emai:ling.wu@myhealthpathway.com

#this model set  to download,extract,standard insert and select pathway data from kegg pathway

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(kegg_pathway_model,kegg_pathway_raw,kegg_pathway_store,kegg_pathway_db,kegg_pathway_map) = buildSubDir('kegg_pathway')

log_path = pjoin(kegg_pathway_model,'kegg_pathway.log')

# main code
def downloadData(redownload = False ):

    '''
    this function is to download the raw data from kegg web
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existkeggFile) = lookforExisted(kegg_pathway_raw,'pathway')

        if choice != 'y':
            return

    if redownload or not existkeggFile or  choice == 'y':

        rawdir = pjoin(kegg_pathway_raw,'pathway_{}'.format(today))

        createDir(rawdir)
        #--------------------------------------------------------------------------------------------------------------------
        process = parser(today)

        # mt = process.getMt(kegg_pathway_web)

        # 1. download pathway  and disease

        process.getAll(keggfilename_web,rawdir)
    #--------------------------------------------------------------------------------------------------------------------
    #  generate .log file in current  path

    if not os.path.exists(log_path):
        initLogFile('kegg_pathway',model_name,kegg_pathway_model,rawdir=rawdir)
    else:
        expanLogFile(log_path,model_name,rawdir)
    #--------------------------------------------------------------------------------------------------------------------
    # generate .files file in database
    update_file_heads =dict()

    for filename in listdir(rawdir):

        head = filename.split('_213')[0].strip()

        update_file_heads[head] = pjoin(rawdir,filename)

    with open(pjoin(kegg_pathway_db,'pathway_{}.files'.format(today)),'w') as wf:
        json.dump(update_file_heads,wf,indent=2)

    #--------------------------------------------------------------------------------------------------------------------
    # return filepaths to extract     
    filepaths = [pjoin(rawdir,filename) for filename  in listdir(rawdir)]

    return (filepaths,today)

    print  'datadowload completed !'

def extractData(filepaths,date):
    '''
    this function is set to distribute all filepath to parser to process
    args:
    filepaths -- all filepaths to be parserd
    date -- the date of  data download
    '''
    # 1. distribute filepaths for parser
    pathway_info_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('hsa00001')]

    pathway_disease_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('br0840')]

    pathway_xml_paths = [path for path in filepaths if psplit(path)[1].strip().endswith('.xml')]

    pathway_gene_paths = pathway_info_paths

    # 2. parser filepaths step by step
    process = parser(date)
    
    # --------------------------------kegg.pathway.info-----------------------------------------------------------------------------
    path_ids,fileversion = process.pathway_info(pathway_info_paths) 

    # --------------------------------kegg.pathway.gene-----------------------------------------------------------------------------
    process.pathway_gene(pathway_gene_paths) 

    # --------------------------------kegg.pathway.disease-------------------------------------------------------------------------
    process.pathway_disease(pathway_disease_paths)

    #---------------------------------kegg.pathway.entry,reaction,relation-----------------------------------------------------
    # 3. get all  (XML FILE) according to path_ids
    if not pathway_xml_paths:

        pathway_raw = psplit(filepaths[0])[0].strip()

        func = lambda x:process.getRelation(x,fileversion,pathway_raw)

        multiProcess(func,path_ids,size=50)

        pathway_xml_paths = [path for path in filepaths if psplit(path)[1].strip().endswith('.xml')]

    process.pathway_xml(pathway_xml_paths)

    #-------------------------------------------------------------------------------
    # backup all collections
    _mongodb = pjoin(kegg_pathway_db,'pathway_{}'.format(date))

    createDir(_mongodb)

    colhead = 'kegg.pathway'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    print 'relation extract and insert completed'

def updateData(insert=True):
    
    '''
    this function is set to update all file in log
    '''
    kegg_pathway_log = json.load(open(log_path))

    updated_rawdir = pjoin(kegg_pathway_raw,'pathway_{}'.format(today))

    process = parser(today)

    #-----------------------------------------------------------------------------------------------------------------
    new = False

    filename_url = dict()

    for filename,url in keggfilename_web.items():

        mt = process.getMt(url)

        if mt != kegg_pathway_log.get(filename)[-1][0]:

            new = True

            createDir(updated_rawdir)

            filename_url[filename] = url

            kegg_pathway_log[filename].append((mt,today,model_name))

            print  '{} \'s new edition is {} '.format(filename,mt)

        else:
            print  '{} {} is the latest !'.format(filename,mt)  

    #-----------------------------------------------------------------------------------------------------------------
    if new:

        process = parser(today)

        process.getAll(filename_url,updated_rawdir)

        with open(log_path,'w') as wf:

            json.dump(kegg_pathway_log,wf,indent=8)            

        (latest_filepaths,version) = createNewVersion(kegg_pathway_raw,kegg_pathway_db,updated_rawdir,'pathway_',today)

        if insert:

            extractData(latest_filepaths.values(),version)

        return 'update successfully'

    else:
        
        return 'new version is\'t detected'

def selectData(querykey = 'path_id',value='00010'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'kegg.pathway'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class parser(object):
    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''
    def __init__(self,date):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

        self.date = date

    def getMt(self,url):
        '''
        this function is set to get url's web page the last updated time
        args:
            url --  the url of download web page of file
        '''
        headers = {'User_Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36'}

        web = requests.get(url,headers=headers,verify=False)

        soup = bs(web.content,'lxml')

        mt = soup.select('body')[0].text.split('Last updated: ')[1].strip().replace(' ','').replace(',','').split('»'.decode('utf-8'))[0].strip()

        mt = '213' + mt

        return mt

    def getOne(self,filename,url,rawdir):

        '''
        this function is set to download the data file by wget when a url given
        agrs:
        filename ~ the filename of download file
        url ~ the url of download web page of file
        rawdir ~ the raw directotr to store download file
        '''
        # set args for chrom driver
        options = webdriver.ChromeOptions()

        prefs = {'profile.default_content_settings.popups':0,'download.default_directory':rawdir}

        options.add_experimental_option('prefs',prefs)

        driver = webdriver.Chrome(chrome_options=options)

        # 1. get file last updated time
        mt = self.getMt(url)

        # 2. download file with chrom driver
        driver.get(url)

        download = driver.find_element_by_link_text('Download json')

        download.click()

        sleep(5)

        driver.close()

        # 3.rename for download file
        newfilename ='{}_{}_{}.json'.format(filename.split('.json')[0],mt,today)

        old_path = pjoin(rawdir,filename)

        new_path = pjoin(rawdir,newfilename)

        os.rename(old_path,new_path)

    def getAll(self,filename_urls,rawdir):
        '''
        this function is set to download json file for  specified urls that have 'download json'
        args:
            urls -- the urls of download web page of files
            rawdir -- the raw directoty to store download file
        '''
        # 1. set args for chrom driver
        options = webdriver.ChromeOptions()

        prefs = {'profile.default_content_settings.popups':0,'download.default_directory':rawdir}

        options.add_experimental_option('prefs',prefs)

        driver = webdriver.Chrome(chrome_options=options)

        filenames_mt = dict()

        for filename,url in filename_urls.items():

            mt = self.getMt(url)

            filenames_mt[filename]= mt

            # 2. download file with chrom driver
            driver.get(url)

            download = driver.find_element_by_link_text('Download json')

            download.click()

        sleep(5)

        driver.close()

        # 3.rename for download files
        for filename in listdir(rawdir):

            newfilename ='{}_{}_{}.json'.format(filename.split('.json')[0],filenames_mt[filename],today)

            old_path = pjoin(rawdir,filename)

            new_path = pjoin(rawdir,newfilename)

            os.rename(old_path,new_path)

    def getRelation(self,path_id,fileversion,rawdir):

        '''this function is set to download relation xml file  with specified path_id'''

        url = 'http://rest.kegg.jp/get/hsa{}/kgml'.format(path_id)

        savefile_path = pjoin(rawdir,'relation_hsa{}_{}_{}.xml'.format(path_id,fileversion,today))

        wget = 'wget --retry-connrefused  -O {} {}'.format(savefile_path,url)

        os.popen(wget)

    def pathway_info(self,filepaths):
        '''
        this function is set parser pathway_info 
        '''
        print '+'*50
        info_colname = 'kegg.pathway.info'

        # before insert ,truncate collection
        delCol('mydb_v1',info_colname)

        info_col = self.db.get_collection(info_colname)

        info_col.ensure_index([('path_id',1),])
        #----------------------------------------------------------------------------------------------------------------------
        path_ids = list()

        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not info_col.find_one({'colCreated':{'$exists':True}}):
                info_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'hsa00001,relation_hsa?????.xml'})

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file
            childrens = json.load(open(filepath)).get('children')

            n = 0

            for path_class in childrens:
                
                path_class_name = path_class.get('name')
                path_class_children = path_class.get('children')

                for path_subclass in  path_class_children:
                    path_subclass_name = path_subclass.get('name')
                    path_subclass_children = path_subclass.get('children')

                    n  += len(path_subclass_children)

                    for path in path_subclass_children:
                        
                        path_name_info = path.get('name')

                        path_id = path_name_info.split(' ',1)[0].strip()

                        path_name = path_name_info.rsplit('[PATH')[0].replace(path_id,'').strip()

                        path_map_link = 'http://www.genome.jp/dbget-bin/www_bget?map{}'.format(path_id)
                        
                        # insert basic info in kegg.pathway.info
                        path = {
                        'path_id':path_id,
                        'path_name':path_name,
                        'path_org':'hsa',
                        'path_class':path_class_name,
                        'path_subclass':path_subclass_name,
                        'path_map_link':path_map_link
                        }

                        info_col.insert(path)

                        path_ids.append(path_id)

        path_ids = list(set(path_ids))

        print 'path_ids',len(path_ids)

        return (path_ids,fileversion)

    def pathway_gene(self,filepaths):
        '''
        this function is set parser pathway_gene 
        '''
        print '*'*50
        gene_colname = 'kegg.pathway.gene'

        # before insert ,truncate collection
        delCol('mydb_v1',gene_colname)

        gene_col = self.db.get_collection(gene_colname)

        gene_col.ensure_index([('path_id',1),('gene_id',1)])

        #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not gene_col.find_one({'colCreated':{'$exists':True}}):
                gene_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'hsa00001'})

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file
            childrens = json.load(open(filepath)).get('children')

            for path_class in childrens:
                
                path_class_children = path_class.get('children')

                for path_subclass in  path_class_children:

                    path_subclass_children = path_subclass.get('children')

                    for path in path_subclass_children:
                        
                        path_name_info = path.get('name')
                        path_gene_info = path.get('children')

                        path_id = path_name_info.split(' ',1)[0].strip()

                        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                        if path_gene_info:

                            genes = dict()

                            for gene in path_gene_info:

                                gene_id,gene_symbol,gene_name,ko_entry,ko_entry,definition= ('','','','','','')

                                gene_name_info = gene.get('name')

                                ko_head= gene_name_info.split('\t')[0]

                                if gene_name_info.count('\t'):
                                    ko_tail= gene_name_info.split('\t')[1]
                                else:
                                    ko_tail = ''
                                
                                if ko_head.count(';'):
                                    (gene_id,gene_symbol) = tuple(ko_head.split(';',1)[0].strip().split(' ',1))
                                    gene_name = ko_head.split(';',1)[1].strip()

                                else:
                                    gene_id = ko_head.split(' ',1)[0]
                                    gene_name = ko_head.split(' ',1)[1].strip()

                                gene={
                                'gene_symbol':gene_symbol,
                                'gene_name':gene_name,
                                }
                                if ko_tail:
                                    (ko_entry,ko_name) = tuple(ko_tail.split(';',1)[0].strip().split(' ',1))
                                    definition = ko_tail.split(';',1)[1].strip()
                                    gene.update({
                                        'ko_entry':ko_entry,
                                        'ko_name':ko_name,
                                        'definition':definition
                                        })
                                else:
                                    print 'no ko ',gene_name_info

                                gene_col.insert({
                                    'path_id':path_id,
                                    'path_org':'hsa',
                                    'gene_id':gene_id,
                                    'gene_symbol':gene_symbol,
                                    'gene_name':gene_name,
                                    'ko_entry':ko_entry,
                                    'ko_name':ko_name,
                                    'definition':definition,
                                })

                                genes[gene_id] = gene

                                # print 'kegg.pathway.gene:',gene_id

    def pathway_disease(self,filepaths):
        '''
        this function is set parser pathway_disease 
        '''        
        print '*'*50
        colname = 'kegg.pathway.disease'

        # before insert ,truncate collection
        delCol('mydb_v1',colname)

        disease_col = self.db.get_collection(colname)

        disease_col.ensure_index([('path_id',1),])       
        #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not disease_col.find_one({'colCreated':{'$exists':True}}):
                disease_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'br08401,br08402'})

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # read file
            disease = json.load(open(filepath)).get('children')

            for dis in disease:

                dis_class = dis.get('name')
                dis_class_info = dis.get('children')

                for dis_sub in dis_class_info:

                    dis_subclass = dis_sub.get('name')
                    dis_subclass_info = dis_sub.get('children')

                    for _info in dis_subclass_info:

                        dis_info = _info.get('name')
                        dis_id = dis_info.split(' ')[0].strip()

                        if dis_info.count('[PATH:hsa') :

                            dis_path = dis_info.split('[PATH:hsa')[1].strip().replace(']','')
                            dis_name =dis_info.split('[PATH:')[0].replace(dis_id,'').strip()

                            disease_col.insert({
                                'path_id':dis_path,
                                'path_org':'hsa',
                                'disease_id':dis_id,
                                'disease_name':dis_name,
                                'disease_class':dis_class,
                                'disease_subclass':dis_subclass
                                })

    def pathway_entry(self,path_id,entry,entry_col):

        '''this function is set to parser entry info in  xml file'''

        entrydict= dict()

        if entry:
            #------------------------------------------------------------------------------------------------------------
            # get every entry basic info
            for e in entry:

                component = e.get('component')

                if component:
                    comps = [dic.get("@id") for dic in component ]

                else:
                    comps = []

                graphics = e.get('graphics')

                if graphics:
                    graphics_dic = dict([(key.replace('@',''),val) for key,val in graphics.items()])

                else:
                    graphics_dic = dict()
                entrydict.update({
                    e.get('@id'):{
                    'entry_name':e.get('@name'),
                    'entry_type':e.get('@type'),
                    'entry_reaction':e.get('@reaction'),
                    'component':comps,
                    'graphics':graphics_dic,
                    }})
            
            #-----------------------------------------------------------------------------------------------------------
            # transform component id to entry name info
            for entry_id,val  in entrydict.items():

                component = val.pop('component')

                if component:

                    comps_names = [entrydict.get(entry_id,{}).get('entry_name') for entry_id in component ]

                    if val.get('entry_type') == 'group':

                        val['entry_name'] = '|'.join(comps_names)

                entrydict[entry_id] = val

                val.update({
                    'path_id':path_id,
                    'path_org':'hsa',
                    'entry_id':entry_id
                    })

                entry_col.insert(val)

        return entrydict

    def pathway_reaction(self,path_id,reaction,reaction_col):

        '''this function is set to parser reaction info in  xml file'''

        if reaction:

            for rxn in reaction:

                reaction_substrate = rxn.get('substrate')

                reaction_product = rxn.get('product')

                reaction_sp_dic = {'reaction_substrate':reaction_substrate,'reaction_product':reaction_product}

                reaction_sp_val_dic = {'reaction_substrate':[],'reaction_product':[]}

                for reaction_sp,val in reaction_sp_dic.items():

                    if isinstance(val,dict):

                        reaction_sp_val_dic[reaction_sp] = [val.get('@name'),]

                    elif isinstance(val,list):

                        [reaction_sp_val_dic[reaction_sp].append(sp.get('@name')) for sp in val]
                           
                reaction_col.insert({
                    'path_id':path_id,
                    'path_org':'hsa',
                    'reaction_id':rxn.get('@id'),
                    'reaction_name':rxn.get('@name'),
                    'reaction_type':rxn.get('@type'),
                    'reaction_substrate':reaction_sp_val_dic['reaction_substrate'],
                    'reaction_product': reaction_sp_val_dic['reaction_product'],
                        })

    def pathway_relation(self,path_id,relation,relation_col,entrydict):

        '''this function is set to parser relation info in  xml file'''

        if relation:

            # just one relation 
            if isinstance(relation,dict):
                relation = [relation,]

            for re in relation:

                entry1_id = re.get('@entry1')
                entry2_id = re.get('@entry2')
                relation_type = re.get('@type')
                relation_subtype = re.get('subtype',{})

                entry1 = entrydict.get(entry1_id)
                entry2 = entrydict.get(entry2_id)

                for entry in [entry1,entry2]:

                    for key,val in entry.items():

                        if key not in ['entry_name','entry_type']:
                            entry.pop(key)

                relation_subtype_value = list()

                if isinstance(relation_subtype,dict):

                    subtype_entry_type = relation_subtype.get('@name')
                    subtype_entry_value = relation_subtype.get('@value')

                    try:
                        entry_value = int(subtype_entry_value)
                        subtype_entry_value = entrydict.get(str(entry_value),{}).get('entry_name')

                    except:
                        pass

                    relation_subtype_value = [{
                        'subtype_entry_type':subtype_entry_type,
                        'subtype_entry_value':subtype_entry_value,
                        },]

                elif isinstance(relation_subtype,list):

                    for subtype in relation_subtype:

                        subtype_entry_type = subtype.get('@name')
                        subtype_entry_value = subtype.get('@value')

                        try:
                            entry_value = int(subtype_entry_value)
                            subtype_entry_value = entrydict.get(str(entry_value),{}).get('entry_name')

                        except:
                            pass

                        relation_subtype_value.append({
                        'subtype_entry_type':subtype_entry_type,
                        'subtype_entry_value':subtype_entry_value,
                        }
                    )

                relation_col.insert({
                    'path_id':path_id,
                    'path_org':'hsa',
                    'entry1':entry1,
                    'entry2':entry2,
                    'relation_type':relation_type,
                    'relation_subtype':relation_subtype_value,
                    })

    def pathway_xml(self,filepaths):

        '''this function is set to parser xml file'''

        print '*'*50
        info_col = self.db.get_collection('kegg.pathway.info')

        # before insert ,truncate collection
        for it in ['entry','reaction','relation']:

            colname = 'kegg.pathway.{}'.format(it)

            delCol('mydb_v1',colname)

            col = self.db.get_collection(colname)
            col.ensure_index([('path_id',1),])       

        entry_col = self.db.get_collection('kegg.pathway.entry')
        reaction_col = self.db.get_collection('kegg.pathway.reaction')
        relation_col = self.db.get_collection('kegg.pathway.relation')

        #----------------------------------------------------------------------------------------------------------------------
        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            for col in [entry_col,reaction_col,relation_col]:
                if not col.find_one({'colCreated':{'$exists':True}}):
                    col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'relation_hsa?????.xml'})

            xmlfile = open(filepath)

            try:
                dictfile = parse(xmlfile)
            except:
                # print filepath,'relation xml file is blank'
                continue
            #-----------------------------------------------------------------------------------------------------------------------
            # add pathway.info
            pathway_info  = dictfile.get('pathway')

            path_id = pathway_info.get('@number')
            path_image = pathway_info.get('@image')
            path_link = pathway_info.get('@link')
            info_col.update(
                {'path_id':path_id},
                {'$set':{'path_image':path_image,'path_link':path_link}},
                False,
                True
                )

            # add pathway.entry
            entry = pathway_info.get('entry')
            entrydict = self.pathway_entry(path_id,entry,entry_col)

            #add pathway.reaction
            reaction = pathway_info.get('reaction')
            self.pathway_reaction(path_id,reaction,reaction_col)

            #add pathway.relation
            relation = pathway_info.get('relation')
            self.pathway_relation(path_id,relation,relation_col,entrydict)

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
        this function is to create a mapping relation between kegg path id  with hgnc symbol
        '''
        # because kegg gene id  is entrez id ,so entrez2symbol imported
        entrez2symbol = self.process.entrezID2hgncSymbol()

        kegg_path_gene_col = self.db_cols.get('kegg.pathway.gene')

        kegg_path_gene_docs = kegg_path_gene_col.find({})

        output = dict()

        hgncSymbol2keggPathID = output

        for doc in kegg_path_gene_docs:

            path_id = doc.get('path_id')

            gene_id = doc.get('gene_id')

            gene_symbol = entrez2symbol.get(gene_id)
            
            if gene_symbol:

                for symbol in gene_symbol:

                    if symbol not in output:

                        output[symbol] = list()

                    output[symbol].append(path_id)

        # dedup val for every key
        for key,val in output.items():
            val = list(set(val))
            output[key] = val    

        print 'hgncSymbol2keggPathID',len(output)

        # with open('./hgncSymbol2keggPathID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return (hgncSymbol2keggPathID,'path_id')


class dbFilter(object):
    '''this class is set to filter part field of data in collections  in mongodb '''
    def __init__(self, arg):
        super(dbFilter, self).__init__()
        self.arg = arg

def main():

    modelhelp = model_help.replace('&'*6,'KEGG_PATHWAY').replace('#'*6,'kegg_pathway')

    funcs = (downloadData,extractData,updateData,selectData,kegg_pathway_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()


