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

def downloadData(redownload = False,rawdir = None):

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

        if not rawdir:

            rawdir = pjoin(kegg_pathway_raw,'pathway_{}'.format('171226090923'))

        process = kegg_parser(today)

        pathway_mt = process.getMt(kegg_pathway_web)

        #download pathway  and disease

        for url in [kegg_disease_web1,kegg_disease_web2,]:#kegg_pathway_download]:
            process.wget(url,rawdir)

    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:
            json.dump({'hsa00001.json':[(pathway_mt,today,model_name),]},wf,indent=2)

    print  'datadowload completed !'
    
    filepaths = [pjoin(rawdir,filename) for filename  in listdir(rawdir)]

    sleep(5)

    return (filepaths,(today,pathway_mt))

def extractData(filepaths,version):

    for name in ['info','gene','entry','reaction','relation','disease']:

        delCol('mydb_v1','kegg.pathway.{}'.format(name))

    for filepath in filepaths:
        
        filename = psplit(filepath)[1].strip()

        date = version[0]

        fileversion = version[1].replace('&','')

        pathway_raw = psplit(filepath)[0].strip()

        process = kegg_parser(date)

        if filename == 'hsa00001.json':
            #-------------------------------------------------------------------------------
                # kegg.path.gene
            all_path = process.pathway(filepath,fileversion)

        elif filename.startswith('br0840'):
            # kegg.path.disease
            process.pathway_disease(filepath,fileversion)

    #-------------------------------------------------------------------------------
        # get all  (XML FILE)

    # func = lambda x:process.pathway_relation(x,pathway_raw)

    # path_ids = all_path.keys()

    # multiProcess(func,path_ids,size=50)

    #-------------------------------------------------------------------------------
        # extract entry  reaction and relations data from xml file
    relation_filepaths = [pjoin(pathway_raw,filename) for filename in listdir(pathway_raw) if filename.endswith('.xml') ]
    
    for filepath in relation_filepaths:
        process.pathway_standar(filepath,fileversion,all_path)

    #-------------------------------------------------------------------------------
        # bkup all collections
    _mongodb = pjoin(kegg_pathway_db,'pathway_{}'.format(date))

    createDir(_mongodb)

    colhead = 'kegg.pathway'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    print 'relation extract and insert completed'

def updateData(insert=False,_mongodb='../_mongodb/'):

    kegg_pathway_log = json.load(open(log_path))

    rawdir = pjoin(kegg_pathway_raw,'pathway_update_{}'.format(today))

    process = kegg_parser(today)

    mt = process.getMt()

    if mt != kegg_pathway_log.get('hsa00001.json')[-1][0]:

        createDir(rawdir)

        (filepath,version)= downloadData(redownload=True,rawdir=rawdir)

        extractData(filepath,version)

        _map = dbMap(version)

        _map.mapping()

        kegg_pathway_log['hsa00001.json'].append((mt,today,model_name))

        with open(log_path,'w') as wf:
            json.dump(kegg_pathway_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('kegg_pathway',mt)

        bakeupCol('kegg_pathway_{}'.format(version),'kegg_pathway',_mongodb)
        
    else:
        print  '{} {} is the latest !'.format('kegg_pathway',mt)

def selectData(querykey = 'path_id',value='00010'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'kegg_pathway'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class kegg_parser(object):

    def __init__(self,date):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

        self.date = date

    def getMt(self,url):

        headers = {'User_Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36'}

        web = requests.get(url,headers=headers,verify=False)

        soup = bs(web.content,'lxml')

        mt = soup.select('body')[0].text.split('Last updated: ')[1].strip().replace(' ','&').replace(',','#')

        return mt

    def wget(self,url,rawdir):

            # download pathway  and disease file
        options = webdriver.ChromeOptions()

        prefs = {'profile.default_content_settings.popups':0,'download.default_directory':rawdir}

        options.add_experimental_option('prefs',prefs)

        driver = webdriver.Chrome(chrome_options=options)

        driver.get(url)

        download = driver.find_element_by_link_text('Download json')

        download.click()

        sleep(5)

        driver.close()

    def pathway(self,filepath,fileversion):

        gene_colname = 'kegg.pathway.gene'

        delCol('mydb_v1',gene_colname)

        gene_col = self.db.get_collection(gene_colname)

        gene_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'hsa00001'})

        # insert basic info in kegg.pathway.info

        info_colname = 'kegg.pathway.info'

        delCol('mydb_v1',info_colname)

        info_col = self.db.get_collection(info_colname)

        info_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'hsa00001,relation_hsa?????.xml'})

        jsonfile = json.load(open(filepath))

        filname = jsonfile.get('name')

        childrens = jsonfile.get('children')

        all_path = dict()

        n = 0
        for path_class in childrens:
            
            path_class_name = path_class.get('name')
            path_class_children = path_class.get('children')

            # print path_class_name

            for path_subclass in  path_class_children:
                path_subclass_name = path_subclass.get('name')
                path_subclass_children = path_subclass.get('children')

                n  += len(path_subclass_children)

                for path in path_subclass_children:
                    
                    path_name_info = path.get('name')
                    path_gene_info = path.get('children')

                    path_id = path_name_info.split(' ',1)[0].strip()
                    path_name = path_name_info.rsplit('[PATH')[0].replace(path_id,'').strip()

                    path_map_link = 'http://www.genome.jp/dbget-bin/www_bget?map{}'.format(path_id)

                    path = {
                    'path_id':path_id,
                    'path_name':path_name,
                    'path_org':'hsa',
                    'path_class':path_class_name,
                    'path_subclass':path_subclass_name,
                    'path_map_link':path_map_link
                    }

                    info_col.insert(path)

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

                            print 'kegg.pathway.gene:',gene_id

                            path.update({'gene':genes})

                    all_path[path_id] = path

        print 'pathways:' ,n
    
        print 'pathway extract and insert completed'
        
        return all_path

    def pathway_relation(self,path_id,rawdir):

        # download relation xml file
        url = 'http://rest.kegg.jp/get/hsa{}/kgml'.format(path_id)

        savefile_path = pjoin(rawdir,'relation_hsa{}.xml'.format(path_id))

        wget = 'wget --retry-connrefused  -O {} {}'.format(savefile_path,url)

        os.popen(wget)

    def pathway_disease(self,savefile_path,fileversion):

        colname = 'kegg.pathway.disease'

        disease_col = self.db.get_collection(colname)

        if not disease_col.find_one({'dataVersion':fileversion}):

            disease_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'br0840*'})
        
        jsonfile = json.load(open(savefile_path))

        disease = jsonfile.get('children')

        print '*'*50

        for dis in disease:

            dis_class = dis.get('name')

            dis_class_info = dis.get('children')

            # print dis_class

            for dis_sub in dis_class_info:

                dis_subclass = dis_sub.get('name')

                dis_subclass_info = dis_sub.get('children')

                # print ' '*4,dis_subclass

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

                        # print ' '*8,dis_id
                        # print ' '*8,dis_name
                        # print ' '*8,dis_path
                        # print ' '*8, '-'*20
         
    def pathway_standar(self,savefile_path,fileversion,all_path):

        colname = 'kegg.pathway.info'

        info_col = self.db.get_collection(colname)

        # parser relation in xml file
        xmlfile = open(savefile_path)

        try:
            dictfile = parse(xmlfile)
        except:
            # print savefile_path,'relation xml file is blank'
            return
        #-------------------------------------------------------------------------------------------------------------------------------------------------------
        # create pathway.info
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

        #-------------------------------------------------------------------------------------------------------------------------------------------------------
        #create pathway.entry
        entry = pathway_info.get('entry')

        colname = 'kegg.pathway.entry'

        entry_col = self.db.get_collection(colname)

        if not entry_col.find_one({'file':'relation_hsa?????.xml'}):
            entry_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'relation_hsa?????.xml'})

        entrydict= dict()

        if entry:

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

        #-------------------------------------------------------------------------------------------------------------------------------------------------------
        #create pathway.reaction
        colname = 'kegg.pathway.reaction'

        reaction_col = self.db.get_collection(colname)

        if not reaction_col.find_one({'file':'relation_hsa?????.xml'}):
            reaction_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'relation_hsa?????.xml'})

        reaction = pathway_info.get('reaction')

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

        #-------------------------------------------------------------------------------------------------------------------------------------------------------
        #create pathway.relation
        colname = 'kegg.pathway.relation'

        relation_col = self.db.get_collection(colname)

        if not relation_col.find_one({'file':'relation_hsa?????.xml'}):
            relation_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'relation_hsa?????.xml'})

        relation = pathway_info.get('relation')

        relationlist = list()

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
        this function is to create a mapping relation between kegg path id  with HGNC Symbol
        '''
        # because kegg gene id  is entrez id 
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

        with open('./hgncSymbol2keggPathID.json','w') as wf:
            json.dump(output,wf,indent=8)

        return (hgncSymbol2keggPathID,'path_id')
    
def main():

    modelhelp = model_help.replace('&'*6,'KEGG_PATHWAY').replace('#'*6,'kegg_pathway')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,kegg_pathway_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':

    main()
    # downloadData(redownload = True)
    # rawdir = '/home/user/project/dbproject/mydb_v1/kegg_pathway/dataraw/pathway_171226090923/'

    # filepaths = [pjoin(rawdir,filename) for filename  in listdir(rawdir)]

    # version = ('171226090923','December&25#&2017')

    # extractData(filepaths,version)
    man = dbMap()
    man.dbID2hgncSymbol()


