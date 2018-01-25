#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/04
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download,extract,standard insert and select pathway data from reactom pathway

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(reactom_pathway_model,reactom_pathway_raw,reactom_pathway_store,reactom_pathway_db,reactom_pathway_map) = buildSubDir('reactom_pathway')

log_path = pjoin(reactom_pathway_model,'reactom_pathway.log')

# main code
def downloadData(redownload = False ):

    '''
    this function is to download the raw data from reactom web
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existreactomFile) = lookforExisted(reactom_pathway_raw,'pathway')

        if choice != 'y':
            return

    if redownload or not existreactomFile or  choice == 'y':

        rawdir = pjoin(reactom_pathway_raw,'pathway_{}'.format(today))

        createDir(rawdir)

        process = parser(today)

        # 1.get all urls of raw files
        filename_urlmt = process.getUrl() 

        # 2. download all path graph.json , path json, txt, txt.zip
        func  = lambda x:process.getOne(x,rawdir)

        multiProcess(func,filename_urlmt.values(),size=50)

    #--------------------------------------------------------------------------------------------------------------------
    #  3. generate .log file in current  path
    if not os.path.exists(log_path):
        log = dict()
        for filename,urlmt in filename_urlmt.items():
            log[filename] = list()
            log[filename].append([urlmt.get('mt'),today,model_name])
        with open('./reactom_pathway.log','w') as wf:
            json.dump(log,wf,indent=8)

    print  'datadowload completed !'
    #--------------------------------------------------------------------------------------------------------------------
    # 4. generate .files file in database
    update_file_heads =dict()

    for filename in listdir(rawdir):

        head = filename.split('_213',1)[0].strip()
        tail = filename.rsplit('_',1)[1].split('.',1)[1]

        update_file_heads[head + tail] = pjoin(rawdir,filename)

    with open(pjoin(reactom_pathway_db,'pathway_{}.files'.format(today)),'w') as wf:
        json.dump(update_file_heads,wf,indent=2)
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
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 1. distribute filepaths for parser
    pathway_info_paths = [path for path in filepaths if psplit(path)[1].split('_',1)[0] in ['ReactomPathways','pathway2summation']]

    pathway_gene_paths = [path for path in filepaths if psplit(path)[1].startswith('NCBI2Reactome_All_Levels_')]

    pathway_eventpmid_paths = [path for path in filepaths if psplit(path)[1].startswith('ReactionPMIDS')]

    pathway_interaction_paths = [path for path in filepaths if psplit(path)[1].startswith('FIsInGene_')]

    pathway_subpathway_paths = [path for path in filepaths if psplit(path)[1].startswith('ReactomePathwaysRelation_')]

    pathway_graph_paths = [path for path in filepaths if psplit(path)[1].endswith('.graph.json')]

    pathway_json_paths = [path for path in filepaths if not psplit(path)[1].endswith('.graph.json') and psplit(path)[1].endswith('.json') ]

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 2. parser filepaths step by step
    process = parser(date)    

    # reactom.pathway.info (pathway2summation and reactompathway)
    all_paths =process.pathway_info(pathway_info_paths)

    # reactom.pathway.entry
    all_nodes = process.pathway_entry(pathway_graph_paths)

    # reactom.pathway.reaction
    all_events = process.pathway_event(pathway_graph_paths,pathway_eventpmid_paths)

    # add subpathway to entry and reaction
    process.pathway_supplement(pathway_graph_paths,all_paths,all_nodes,all_events)

    # add reactom.pathway.subpathway 
    process.pathway_gene(pathway_gene_paths)

    # add reactom.pathway.subpathway 
    process.pathway_subpath(pathway_subpathway_paths)

    # add reactom.pathway.interaction 
    process.pathway_interaction(pathway_interaction_paths)

    # add reactom.pathway.graph 
    process.pathway_graph(pathway_json_paths)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # bkup collection in local
    _mongodb = pjoin(reactom_pathway_db,'pathway_{}'.format(date))

    colhead = 'reactom.pathway'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    print 'extract and insert completed'

    return (filepaths,date)

def updateData(insert=False):

    '''
    this function is set to update all file in log
    '''

    reactom_pathway_log = json.load(open(log_path))

    updated_rawdir = pjoin(reactom_pathway_raw,'pathway_{}'.format(today))

    process = parser(today)

    filename_urlmt = process.getUrl()

    new = False

    new_urlmts = list()

    for filename,urlmt in filename_urlmt.items():

        mt = urlmt.get('mt')

        if mt != reactom_pathway_log.get(filename)[-1][0]:

            new = True 

            new_urlmts.append(urlmt)

            reactom_pathway_log[filename].append([mt,today,model_name])
            
            print  '{} \'s new edition is {} '.format(filename,mt)

        else:

            print  '{} {} is the latest !'.format(filename,mt)

    if new:

        createDir(updated_rawdir)

        func = lambda x:process.getOne(urlmt,updated_rawdir)

        multiProcess(fun,new_urlmts,size=50)

        # create new log
        with open('./reactom_pathway.log','w') as wf:

            json.dump(reactom_pathway_log,wf,indent=2)

        (latest_filepaths,version) = createNewVersion(reactom_pathway_raw,reactom_pathway_db,updated_rawdir,'pathway_',today)

        if insert:

            extractData(latest_filepaths.values(),version)

        return 'update successfully'

    else:

        return 'new version is\'t detected'

def selectData(querykey = 'path_id',value='R-HSA-76071'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'reactom_pathway'

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

    def getUrl(self):
        '''
        this function is set to get all download url of raw files
        '''
        filename_urlmt = dict()
        #------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # download R-HSA-?????.graph.json or  # download R-HSA-?????.json
        web = requests.get(reactome_download_web1)
        soup = bs(web.content,'lxml')
        trs = soup.select('body > table > tr ')

        for tr in trs:
            text = tr.text
            filename = text.split('.json')[0].strip()

            # if filename.startswith('R-HSA') and filename.endswith('.graph'):
            if filename.startswith('R-HSA'):

                mt = text.split(filename)[1].strip().rsplit(' ',1)[0]
                for sym in [' ',':','-','.json','.txt']:
                    mt = mt.replace(sym,'')
                mt = '213' + mt

                key = reactome_download_web1 + filename + '.json'

                name = filename + '.json'
                filename_urlmt.update({name:{'url':key,'mt':mt}})

        #------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # download pathway2summation,ReactomePathways,NCBI2Reactome_All_Levels,ReactomePathwaysRelation
        info_files = ['pathway2summation','ReactomePathways','NCBI2Reactome_All_Levels','ReactomePathwaysRelation','ReactionPMIDS']

        web = requests.get(reactome_download_web2)
        soup = bs(web.content,'lxml')
        trs = soup.select('body > table > tr ')

        for tr in trs:
            text = tr.text
            filename = text.split('.txt')[0].strip()

            if filename in info_files:

                mt = text.split(filename)[1].strip().rsplit(' ',1)[0]
                for sym in [' ',':','-','.json','.txt']:
                    mt = mt.replace(sym,'')
                mt = '213' + mt

                key = reactome_download_web2 + filename + '.txt'

                name = filename + '.txt'
                filename_urlmt.update({name:{'url':key,'mt':mt}})

        #------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # download interaction file 
        web = requests.get(reactome_download_web3)
        soup = bs(web.content,'lxml')
        head = soup.find(text='Functional interactions (FIs) derived from Reactome, and other pathway and interaction databases')
        li1 = head.findNext(name = 'li')
        mt = li1.text.split('Version')[1].strip()
        a = li1.find(name='a')
        href = a.attrs.get('href')

        mt = '213' + mt
        name = psplit(href)[1].strip()
        filename_urlmt.update({name:{'url':href,'mt':mt}})

        return filename_urlmt

    def getOne(self,urlmts,rawdir):

        '''
        this function is set to download raw file and rename  with a url and file's mt
        '''
        url = urlmts.get('url')
        mt = urlmts.get('mt')

        filename = url.rsplit('/',1)[1].strip()

        for tail in ['.graph.json','.json','.txt','.txt.zip']:

            if filename.endswith(tail):

                name = filename.split(tail)[0].strip()

                savename = '{}_{}_{}_{}'.format(name,mt,today,tail)

                break

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,url)

        os.popen(command)

    def getNode(self,dbId):
        '''
        this function is set to get a entry basic infos from reactom web site  that not in reactom.pathway.entry 
        '''
        node_info = dict()

        url = 'https://reactome.org/content/detail/%s' % dbId

        headers = {'User-Agent':'ozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36'}

        web = requests.get(url,headers=headers,verify= False)

        soup = bs(web.content,'lxml')

        displayname = soup.find(name='h3')

        if displayname:
            displayname = displayname.text.strip()
        else:
            return

        st_id_val,ty_val,com_val,syn_val,speciesID =('','','','','')

        st_id = soup.find(text='Stable Identifier')
        if st_id:
            st_id_val = st_id.findNext(name='div').text.strip()    

        ty = soup.find(text='Type')
        if ty:
            ty_val = ty.findNext(name='div').text.strip()

        com = soup.find(text='Compartment')
        if com:
            com_val = com.findNext(name='a').text.strip()    
            displayname = displayname + ' ' + '[' + com_val + ']'

        spe = soup.find(text='Species')
        if spe:
            spe_val = spe.findNext(name='div').text.strip()        
            if spe_val == 'Homo sapiens':
                speciesID = 48887

        syn = soup.find(text='Synonyms')
        if syn:
            syn_val =';'.join( [i.strip() for i in syn.findNext(name='div').text.strip().split(',') if i])
        
        entry_link = 'https://reactome.org/content/detail/%s' % st_id_val

        node_info.update(
            {
            'dbId':dbId,
           'entry_id':st_id_val,
           'entry_link':entry_link,
           'schemaClass':ty_val,
           'speciesID':speciesID,
           'displayName':displayname,
           })

        return node_info

    def pathway_info(self,filepaths):
        '''
        this function is set parser pathway_info 
        '''
        print '+'*50
        info_colname = 'reactom.pathway.info'

        # before insert ,truncate collection
        delCol('mydb_v1',info_colname)

        info_col = self.db.get_collection(info_colname)

        info_col.ensure_index([('path_id',1)])

        all_paths = list()

        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not info_col.find_one({'colCreated':{'$exists':True}}):
                info_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'ReactomPathways,pathway2summation,R-HSA-??????.graph'})
                       
            tsvfile = open(filepath)

            if filename.startswith('ReactomPathways'):

                keys = ['path_id','path_name','path_org']

            elif filename.startswith('pathway2summation'):

                keys = ['path_id','path_name','path_summation']

            n = 0

            for line in tsvfile:

                data = [i.decode('unicode_escape') for i in line.strip().split('\t') if i]

                dic = dict([(key,val) for key,val in zip(keys,data)])

                if not dic['path_id'].startswith('R-HSA'):
                    continue

                path_id = dic.pop('path_id')

                if path_id not in all_paths:
                    all_paths.append(path_id)

                dic['path_link'] = 'https://reactome.org/content/detail/{}'.format(path_id)

                dic['path_image'] = 'https://reactome.org/PathwayBrowser/#/{}'.format(path_id)

                info_col.update(
                    {'path_id':path_id},
                    {'$set':dic},
                    True
                    )
                n += 1

                print 'reactom.pathway.info',n,path_id

        return all_paths

    def pathway_gene(self,filepaths):
        '''
        this function is set parser pathway_gene 
        '''
        gene_colname = 'reactom.pathway.gene'

        # before insert ,truncate collection
        delCol('mydb_v1',gene_colname)

        gene_col = self.db.get_collection(gene_colname)

        gene_col.ensure_index([('path_id',1),('entrez_id',1)])

        #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
        filepath = filepaths[0] # only one file

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
        
        gene_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'NCBI2Reactome_All_Levels'})
        #-----------------------------------------------------------------------------------------------------------------------------------------------------------------

        tsvfile = open(filepath)

        n = 0

        keys = ['entrez_id','path_id','path_link','path_name','evidence','path_org']

        for line in tsvfile:

            data = [i.strip() for i in line.split('\t')]

            dic = dict([(key,val) for key,val in zip(keys,data)])

            path_org = dic.get('path_org')

            if path_org != 'Homo sapiens':
                continue

            for key in ['path_link','path_name']:
                dic.pop(key)

            gene_col.insert(dic)

            n += 1

            print 'reactom.pathway.gene line',n

    def pathway_graph(self,filepaths):
        '''
        this function is set parser path_graph 
        '''
        graph_colname = 'reactom.pathway.graph'

        # before insert ,truncate collection
        delCol('mydb_v1',graph_colname)

        graph_col = self.db.get_collection(graph_colname)
        graph_col.ensure_index([('path_id',1)])
        #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
        n = 0

        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            if not graph_col.find_one({'colCreated':{'$exists':True}}): 
                graph_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'R-HSA-??????.json'})

            #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
            jsonfile = json.load(open(filepath))

            jsonfile['path_id'] = jsonfile.pop('stableId')
            jsonfile['path_org'] = 'Homo sapiens'

            graph_col.insert(jsonfile)

            n += 1

            print 'reactom.pathway.graph line',n

    def pathway_subpath(self,filepaths):

        '''
        this function is set parser pathway_subpath 
        '''
        subpathway_colname = 'reactom.pathway.subpathway'

        # before insert ,truncate collection
        delCol('mydb_v1',subpathway_colname)

        subpathway_col = self.db.get_collection(subpathway_colname)

        subpathway_col.ensure_index([('parent_path',1),('child_path',1)])
        subpathway_col.ensure_index([('parent_path',1)])
        subpathway_col.ensure_index([('child_path',1)])
        
        #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
        filepath = filepaths[0] # only one file

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()
        
        subpathway_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'ReactomePathwaysRelation'})

        #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
        tsvfile = open(filepath)

        n = 0

        for line in tsvfile:

            data = [i.strip() for i in line.split('\t')]

            parent_path  = data[0]

            child_path = data[1]

            if parent_path.startswith('R-HSA') and child_path.startswith('R-HSA'):

                subpathway_col.insert(
                    {'parent_path':parent_path,
                    'child_path':child_path,
                    'path_org':'Homo sapiens'})

            n += 1

            print 'reactom.pathway.subpathway line',n

    def pathway_interaction(self,filepaths):
        '''
        this function is set parser pathway_interaction 
        '''
        interaction_colname = 'reactom.pathway.interaction'

        # before insert ,truncate collection
        delCol('mydb_v1',interaction_colname)

        interaction_col = self.db.get_collection(interaction_colname)
        interaction_col.ensure_index([('path_id',1)])

        #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
        filepath = filepaths[0] # only one file

        filename = psplit(filepath)[1].strip()

        fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

        interaction_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'IsInGene_022717_with_annotations'})
        #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
        
        rawdir = psplit(filepath)[0].strip()

        if filepath.endswith('.zip'):

            # unzip zip file
            unzip =  'unzip {} -d {}'.format(filepath,rawdir)

            os.popen(unzip)

            os.remove(filepath) # delete zip file

            filepath = filepath.rsplit('.zip',1)[0].strip()

            old_path = pjoin(rawdir,'FIsInGene_022717_with_annotations.txt')

            os.rename(old_path,filepath)
        #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
        tsvfile = open(filepath)

        n = 0

        for line in tsvfile:

            if n == 0:
                keys = [i.strip() for i in line.strip().split('\t') ]

            else:
                data = [i.strip() for i in line.strip().split('\t') ]
                dic = dict([(key,val) for key,val in zip(keys,data)])

                interaction_col.insert(dic)

                print 'reactom.pathway.interaction,line',n

            n += 1

    def pathway_entry(self,filepaths):
        '''
        this function is set parser pathway_entry 
        '''
        entry_colname = 'reactom.pathway.entry'

        # before insert ,truncate collection
        delCol('mydb_v1',entry_colname)

        entry_col = self.db.get_collection(entry_colname)

        entry_col.ensure_index([('path_id',1),('entry_id',1)])

        all_nodes = dict()

        n = 0

        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not entry_col.find_one({'colCreated':{'$exists':True}}):
                entry_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'R-HSA-??????.graph'})

            jsonfile = json.load(open(filepath))

            path_id = jsonfile.get('stId')

            nodes = jsonfile.get('nodes')

            for node in nodes:

                node['path_id'] = path_id
                node['path_org'] = 'Homo sapiens'

                node_dbid = node.get('dbId')

                node_id = node.pop('stId')

                node['entry_id'] = node_id
                node['entry_link'] = 'https://reactome.org/content/detail/%s' % node_id

                displayName = node.get('displayName')

                if displayName:

                    node['entry_name'] = displayName.split('[',1)[0].strip()

                entry_col.insert(node)

                # add to all nodes
                if node_dbid not in all_nodes:

                    node.pop('_id')

                    all_nodes[node_dbid] = node

            n += 1

            print 'reactom.pathway.entry file',n

        return all_nodes

    def pathway_event(self,filepaths,pmidpaths):

        '''
        this function is set parser pathway_event 
        '''
        event_colname = 'reactom.pathway.event'

        # before insert ,truncate collection
        delCol('mydb_v1',event_colname)

        event_col = self.db.get_collection(event_colname)

        event_col.ensure_index([('path_id',1),('event_id',1)])
        event_col.ensure_index([('event_id',1),])
        #-----------------------------------------------------------------------------------------------------------------------------------------------------------
        all_events = dict()

        n = 0

        for filepath in filepaths:

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # insert version info 
            if not event_col.find_one({'dataVersion':fileversion}):

                event_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'R-HSA-??????.graph'})

            jsonfile = json.load(open(filepath))

            path_id = jsonfile.get('stId')

            edges = jsonfile.get('edges')

            if edges:

                for e in edges:

                    dbId = e.get('dbId')
                    
                    event_id = e.pop('stId')

                    e['path_id'] = path_id
                    e['path_org'] = 'Homo sapiens'

                    e['event_id'] = event_id

                    e['event_link'] = 'https://reactome.org/content/detail/%s' % event_id

                    event_col.insert(e)

                    e.pop('_id')

                    if dbId not in all_events:

                        all_events[dbId] = e

            n += 1

            print 'reactom.pathway.event',n
        #-----------------------------------------------------------------------------------------------------------------------------------------------------------
        pmidpath = pmidpaths[0]
        reaction_pmid_file = open(pmidpath)

        n  = 0

        for line in reaction_pmid_file:
            event_id = line.split('\t')[0].strip()
            event_pmid = line.split('\t')[1].strip()

            event_col.update(
                {'event_id':event_id},
                {'$push':{'event_pmid':event_pmid}},
                False,
                True
                )

            n += 1

            print 'reactom.pathway.event.pmid line',n

        return all_events

    def pathway_supplement(self,filepaths,all_paths,all_nodes,all_events):

        '''
        this function is set to  supplement the path info ,entry,events  with subpathway infos

        '''
        info_col = self.db.get_collection('reactom.pathway.info')

        entry_col = self.db.get_collection('reactom.pathway.entry')

        event_col = self.db.get_collection('reactom.pathway.event')

        #------------------------------------------------------------------------------------------------------------------------------------------
        n = 0

        notin_all_nodes = list()

        for filepath in filepaths:
            
            filename = psplit(filepath)[1].strip()

            jsonfile = json.load(open(filepath))

            fileversion = filename.rsplit('_',1)[1].strip().split('.',1)[0].strip()

            path_id = jsonfile.get('stId')

            subpathways = jsonfile.get('subpathways')

            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            if subpathways:

                for subpathway in subpathways:

                    subpath_id = subpathway.get('stId') # all subpathway id included in pathway.info
                    # print 'subpath_id',subpath_id

                    info_col.update(
                        {'path_id':path_id},
                        {'$push':{'path_sub':subpath_id}},
                        True,
                        )

                    subpath_events = subpathway.get('events')

                    if subpath_events:

                        for event_id in subpath_events:

                            event_info  = all_events.get(event_id)

                            if event_info: # "event_id" is truely a event id
                                # bcause subpath also contain this event .so add to pathway.event
                                [event_info.pop(key) for key  in ['_id','path_id','event_id'] if key in event_info]

                                event_col.update(
                                    {'path_id':subpath_id,'event_id':event_id},
                                    {'$set':event_info},
                                    True,
                                    False)

                                # bcause subpath also contain this event  and it's nodes .so add to pathway.nodes
                                event_nodes = list()

                                for key in ['inputs','outputs','activators','catalysts','inhibitors']:
                                    val = event_info.get(key,[])
                                    event_nodes += val

                                event_nodes = list(set(event_nodes))

                                for node_id in event_nodes:

                                    node_info = all_nodes.get(node_id)

                                    if not node_info:
                                        node_info = self.getNode(node_id)
                                        notin_all_nodes.append(node_id)

                                    [node_info.pop(key) for key  in ['_id','path_id','entry_id'] if key in node_info]
                                    entry_col.update(
                                        {'path_id':subpath_id,'entry_id':node_id},
                                        {'$set':node_info},
                                        True,
                                        False)

                            else: # "event_id" is truely a path_id 
                                event_id = 'R-HSA-{}'.format(event_id)
                                path_id = event_id

                                docs = event_col.find({'path_id':path_id})

                                if docs:

                                    print event_id,'not in all_event but in path_id'
                                    # event is is not represent event but a pathway
                                    event = list()

                                    for doc in docs:
                                        
                                        doc.pop('_id')
                                        event_info = copy.deepcopy(doc)
                                        event_id = event_info.get('event_id')

                                        [event_info.pop(key) for key  in ['_id','path_id','event_id'] if key in event_info]

                                        event_col.update(
                                            {'path_id':subpath_id,'event_id':event_id},
                                            {'$set':event_info},
                                            True,
                                            False)

                                        event_nodes = list()

                                        for key in ['inputs','outputs','activators','catalysts','inhibitors']:
                                            val = event_info.get(key,[])
                                            event_nodes += val

                                        event_nodes = list(set(event_nodes))

                                        for node_id in event_nodes:

                                            node_info = all_nodes.get(node_id)

                                            if not node_info:
                                                node_info = self.getNode(node_id)
                                                notin_all_nodes.append(node_id)
                                            [node_info.pop(key) for key  in ['_id','path_id','entry_id'] if key in node_info]

                                            entry_col.update(
                                                {'path_id':subpath_id,'entry_id':node_id},
                                                {'$set':node_info},
                                                True,
                                                False)

                                else:
                                    print path_id,'not in path_id'
            n += 1

            print 'reactom.pathway.subpathway',n

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
        this function is to create a mapping relation between reactom path id  with HGNC Symbol
        '''
        # because reactom gene id  is entrez id 
        entrez2symbol = self.process.entrezID2hgncSymbol()

        reactom_path_gene_col = self.db_cols.get('reactom.pathway.gene')

        reactom_path_gene_docs = reactom_path_gene_col.find({})

        output = dict()

        hgncSymbol2reactomPathID = output

        for doc in reactom_path_gene_docs:

            path_id = doc.get('path_id')

            gene_id = doc.get('entrez_id')

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
            
        print 'hgncSymbol2reactomPathID',len(output)

        # with open('./hgncSymbol2reactomPathID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return (hgncSymbol2reactomPathID,'path_id')
        
class dbFilter(object):

    '''this class is set to filter part field of data in collections  in mongodb '''

    def __init__(self, arg):
        super(dbFilter, self).__init__()
        self.arg = arg
        
def main():

    modelhelp = model_help.replace('&'*6,'Reactom_Pathway').replace('#'*6,'reactom_pathway')

    funcs = (downloadData,extractData,updateData,selectData,reactom_pathway_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # filepaths,version = downloadData(redownload = True)
    # rawdir = '/home/user/project/dbproject/mydb_v1/reactom_pathway/dataraw/pathway_180123140434/'
    # filepaths = [pjoin(rawdir,filename) for filename in os.listdir(rawdir)]
    # date = '180123140434'
    # extractData(filepaths,date)
    # updateData()
    # pass
    # man = dbMap()
    # man.dbID2hgncSymbol()
    # man.mapping()

    # db,db_cols = initDB('mydb_v1')

    # reactom_entry_col = db_cols.get('reactom.pathway.entry')

    # docs = reactom_

    # man = parser(today)
    # (filename_urlmt,pathurl_mt,other_mt) = man.getUrl()
    # with open('./tmp.json','w') as wf:
    #     json.dump(filename_urlmt,wf,indent=8)
