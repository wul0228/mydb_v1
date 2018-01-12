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

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(reactom_pathway_model,reactom_pathway_raw,reactom_pathway_store,reactom_pathway_db,reactom_pathway_map) = buildSubDir('reactom_pathway')

log_path = pjoin(reactom_pathway_model,'reactom_pathway.log')
# main code

def downloadData(redownload = False,rawdir = None):

    '''
    this function is to download the raw data from reactom web
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existreactomFile) = lookforExisted(reactom_pathway_raw,'pathway')

        if choice != 'y':
            return

    if redownload or not existreactomFile or  choice == 'y':

        if not rawdir:

            rawdir = pjoin(reactom_pathway_raw,'pathway_{}'.format(today))

            createDir(rawdir)

        process = reactom_parser(today)

        # get mt for every file,store in reactomfile_mt
        newest_mt = process.getMt()

        pathurl_mt,other_mt = process.getUrl() 

        # download graph file
        func  = lambda x:process.wget(x,pathurl_mt[x],rawdir)

        multiProcess(func,pathurl_mt.keys(),size=50)

        # download other file
        for url,mt in other_mt.items():
            process.wget(url,mt,rawdir)

    # create log file
    if not os.path.exists(log_path):

        with open('./reactom_pathway.log','w') as wf:
            json.dump({'reactom_pathway':[(newest_mt,today,model_name)]},wf,indent=8)

    print  'datadowload completed !'

    filepaths = [pjoin(rawdir,filename) for filename in rawdir]

    return (filepaths,today)

def extractData(filepaths,date):

    rawdirname = psplit(psplit(filepaths[0])[0])[1].strip()

    fileversion = rawdirname.split('_')[1].strip()

    process = reactom_parser(date)

    graphpaths,jsonpaths,infopaths,subpathwaypaths,genepaths,interactionpaths,eventpmidpaths = [],[],[],[],[],[],[]

    for filepath in filepaths:

        filename = psplit(filepath)[1].strip()

        if filename.endswith('.graph.json'):
            graphpaths.append(filepath)

        elif filename.endswith('.json'):
            jsonpaths.append(filepath)

        elif filename.startswith('ReactomPathways_') or filename.startswith('pathway2summation_'):
            infopaths.append(filepath)

        elif filename.startswith('ReactomePathwaysRelation_'):
            subpathwaypaths.append(filepath)

        elif filename.startswith('NCBI2Reactome_All_Levels_'):
            genepaths.append(filepath)

        elif filename.startswith('FIsInGene_'):
            interactionpaths.append(filepath)

        elif filename.startswith('ReactionPMIDS'):
            eventpmidpaths.append(filepath)

    # reactom.pathway.info (pathway2summation and reactompathway)
    all_paths =process.info(infopaths,fileversion)

    # reactom.pathway.entry
    all_nodes = process.entry(graphpaths,fileversion)

    # reactom.pathway.reaction
    all_events = process.event(graphpaths,eventpmidpaths,fileversion)

    # add subpathway to entry and reaction
    process.pathsub(graphpaths,fileversion,all_paths,all_nodes,all_events)

    # add reactom.pathway.subpathway 
    process.subpathway(subpathwaypaths,fileversion)

    # add reactom.pathway.subpathway 
    process.gene(genepaths,fileversion)

    # add reactom.pathway.interaction 
    process.interaction(interactionpaths,fileversion)

    # add reactom.pathway.graph 
    process.graph(jsonpaths,fileversion)

    # bkup collection in local
    _mongodb = pjoin(reactom_pathway_db,rawdirname)

    colhead = 'reactom.pathway'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    print 'extract and insert completed'

    return (filepaths,date)

def updateData(insert=False,_mongodb='../_mongodb/'):

    reactom_pathway_log = json.load(open(log_path))

    rawdir = pjoin(reactom_pathway_raw,'pathway_{}'.format(today))

    process = reactom_parser(today)

    newest_mt = process.getMt()

    new = False

    if newest_mt != reactom_pathway_log['reactom_pathway'][-1][0]:

        createDir(rawdir)

        new = True 

        filepaths,version = downloadData(redownload = True)

        extractData(filepaths,version)

        reactom_pathway_log['reactom_pathway'].append((newest_mt,today,model_name))

        print  '{} \'s new edition is {} '.format('reactom_pathway',newest_mt)

        bakeupCol('reactom_pathway_{}'.format(version),'reactom_pathway',_mongodb)

    else:

        print  '{} {} is the latest !'.format('reactom_pathway',newest_mt)

    if new:

        # create new log
        with open('./reactom_pathway.log','w') as wf:

            json.dump(reactom_pathway_log,wf,indent=2)

def selectData(querykey = 'stId',value='R-HSA-76071'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'reactom_pathway'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)


class reactom_parser(object):

    def __init__(self,date):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db
        
        self.date = date

    def Mt(self,text,filename):

        mt = text.split(filename)[1].strip().rsplit(' ',1)[0]

        for sym in [' ',':','-','.json','.txt']:

            mt = mt.replace(sym,'')

        mt = '213' + mt

        return mt

    def getMt(self):

        web = requests.get(reactome_download_web2)

        soup = bs(web.content,'lxml')

        trs = soup.select('body > table > tr ')

        for tr in trs:

            text = tr.text

            if text.count('diagram/'):

                 mt = self.Mt(text,'diagram/')

        return mt

    def getUrl(self):

        '''
        this function is to get all files update time from http://download web page
        '''
        # diagram file
        # for url in [reactome_download_web1,reactome_download_web2]:

        pathurl_mt = dict()

        other_mt = dict()
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

                mt = self.Mt(text,filename)
                key = reactome_download_web1 + filename + '.json'
                pathurl_mt[key] = mt
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

                mt = self.Mt(text,filename)

                key = reactome_download_web2 + filename + '.txt'

                other_mt[key] = mt 
        #------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # download interaction file 
        web = requests.get(reactome_download_web3)
        soup = bs(web.content,'lxml')
        head = soup.find(text='Functional interactions (FIs) derived from Reactome, and other pathway and interaction databases')
        li1 = head.findNext(name = 'li')
        mt = li1.text.split('Version')[1].strip()
        a = li1.find(name='a')
        href = a.attrs.get('href')
        other_mt[href] = mt

        return (pathurl_mt,other_mt)

    def wget(self,url,mt,rawdir):

        # filename = url.rsplit('/',1)[1].strip().replace('.graph.json','').replace('.txt','')
        filename = url.rsplit('/',1)[1].strip()

        if filename.endswith('graph.json'):

            name = filename.split('.graph.json')[0].strip()

            savename = '{}_{}.graph.json'.format(name,mt)

        elif filename.endswith('.txt'):

            name = filename.split('.txt')[0].strip()

            savename = '{}_{}.txt'.format(name,mt)

        elif filename.endswith('.json'):

            name = filename.split('.json')[0].strip()

            savename = '{}_{}.json'.format(name,mt)

        elif filename.endswith('.txt.zip'):

            name = filename.split('.txt.zip')[0].strip()

            savename = '{}_{}.txt.zip'.format(name,mt)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,url)

        os.popen(command)

    def node(self,dbId):

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

    def info(self,filepaths,fileversion):

        info_colname = 'reactom.pathway.info'

        delCol('mydb_v1',info_colname)

        info_col = self.db.get_collection(info_colname)

        info_col.ensure_index([('path_id',1)])

        all_paths = list()

        for filepath in filepaths:

            tsvfile = open(filepath)

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[1].strip().split('.',1)[0].strip()

            if not info_col.find_one({'dataVersion':fileversion}):

                info_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'ReactomPathways,pathway2summation,R-HSA-??????.graph'})

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

        # with open('./all_reactom_paths.json','w') as wf:
        #     json.dump(all_paths,wf,indent=8)

        return all_paths

    def entry(self,filepaths,fileversion):

        entry_colname = 'reactom.pathway.entry'

        delCol('mydb_v1',entry_colname)

        entry_col = self.db.get_collection(entry_colname)

        entry_col.ensure_index([('path_id',1),('entry_id',1)])

        entry_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'R-HSA-??????.graph'})

        all_nodes = dict()

        n = 0

        for filepath in filepaths:

            jsonfile = json.load(open(filepath))

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[1].strip().split('.',1)[0].strip()

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

        # with open('./all_reactom_nodes.json','w') as wf:
        #     json.dump(all_nodes,wf,indent=8)

        return all_nodes

    def event(self,filepaths,pmidpaths,fileversion):

        event_colname = 'reactom.pathway.event'

        delCol('mydb_v1',event_colname)

        event_col = self.db.get_collection(event_colname)

        event_col.ensure_index([('path_id',1),('event_id',1)])

        if not event_col.find_one({'dataVersion':fileversion}):

            event_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'R-HSA-??????.graph'})

        all_events = dict()

        n = 0

        for filepath in filepaths:

            jsonfile = json.load(open(filepath))

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[1].strip().split('.',1)[0].strip()

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

        # with open('./all_reactom_events.json','w') as wf:
        #     json.dump(all_events,wf,indent=8)

        return all_events

    def pathsub(self,filepaths,fileversion,all_paths,all_nodes,all_events):

        info_col = self.db.get_collection('reactom.pathway.info')

        entry_col = self.db.get_collection('reactom.pathway.entry')

        event_col = self.db.get_collection('reactom.pathway.event')

        n = 0

        notin_all_nodes = list()

        for filepath in filepaths:
            
            filename = psplit(filepath)[1].strip()

            jsonfile = json.load(open(filepath))

            fileversion = filename.rsplit('_',1)[1].strip().split('.',1)[0].strip()

            path_id = jsonfile.get('stId')

            subpathways = jsonfile.get('subpathways')

            if subpathways:

                for subpathway in subpathways:

                    subpath_id = subpathway.get('stId') # all subpathway id included in pathway.info
                    print 'subpath_id',subpath_id

                    info_col.update(
                        {'path_id':path_id},
                        {'$push':{'path_sub':subpath_id}},
                        True,
                        )

                    subpath_events = subpathway.get('events')

                    if subpath_events:

                        for event_id in subpath_events:

                            event_info  = all_events.get(event_id)

                            if event_info:

                                # bcause subpath also contain this event .so add to pathway.event

                                # if not event_col.find_one({'path_id':subpath_id,'event_id':event_id}):
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
                                        node_info = self.node(node_id)
                                        notin_all_nodes.append(node_id)

                                    [node_info.pop(key) for key  in ['_id','path_id','entry_id'] if key in node_info]

                                    entry_col.update(
                                        {'path_id':subpath_id,'entry_id':node_id},
                                        {'$set':node_info},
                                        True,
                                        False)

                            else:
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
                                                node_info = self.node(node_id)
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

        # notin_all_nodes = list(set(notin_all_nodes))
        # print notin_all_nodes
        # print len(notin_all_nodes)

        # with open('./notin_all_nodes.json','w') as wf:
        #     json.dump(notin_all_nodes,wf,indent=2)

    def subpathway(self,filepaths,fileversion):

        subpathway_colname = 'reactom.pathway.subpathway'

        delCol('mydb_v1',subpathway_colname)

        subpathway_col = self.db.get_collection(subpathway_colname)

        subpathway_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'ReactomePathwaysRelation'})

        filepath = filepaths[0] # only one file

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

    def gene(self,filepaths,fileversion):

        gene_colname = 'reactom.pathway.gene'

        delCol('mydb_v1',gene_colname)

        gene_col = self.db.get_collection(gene_colname)

        gene_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'NCBI2Reactome_All_Levels'})

        filepath = filepaths[0] # only one file

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


    def interaction(self,filepaths,fileversion):

        interaction_colname = 'reactom.pathway.interaction'

        delCol('mydb_v1',interaction_colname)

        interaction_col = self.db.get_collection(interaction_colname)

        interaction_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'IsInGene_022717_with_annotations'})

        filepath = filepaths[0] # only one file

        rawdir = psplit(filepath)[0].strip()

        if filepath.endswith('.zip'):

            # gunzip zip file
            unzip =  'unzip {} -d {}'.format(filepath,rawdir)

            os.popen(unzip)

        filepath = filepath.rsplit('.zip',1)[0].strip()
        
        # os.remove(filepath)

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

    def graph(self,filepaths,fileversion):

        graph_colname = 'reactom.pathway.graph'

        delCol('mydb_v1',graph_colname)

        graph_col = self.db.get_collection(graph_colname)

        graph_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'R-HSA-??????.json'})

        n = 0

        for filepath in filepaths:

            jsonfile = json.load(open(filepath))

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[1].strip().split('.',1)[0].strip()

            jsonfile['path_id'] = jsonfile.pop('stableId')
            jsonfile['path_org'] = 'Homo sapiens'

            graph_col.insert(jsonfile)

            print 'reactom.pathway.graph line',n


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

        with open('./hgncSymbol2reactomPathID.json','w') as wf:
            json.dump(output,wf,indent=8)

        return (hgncSymbol2reactomPathID,'path_id')

def main():

    modelhelp = model_help.replace('&'*6,'Reactom_Pathway').replace('#'*6,'reactom_pathway')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,reactom_pathway_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
    # filepaths,version = downloadData(redownload = True)
    # rawdir = '/home/user/project/dbproject/mydb_v1/reactom_pathway/dataraw/pathway_180108100817/'
    # filepaths = [pjoin(rawdir,filename) for filename in os.listdir(rawdir)]
    # date = '180108100817'
    # extractData(filepaths,date)
    # updateData()
    # pass
    # man = dbMap()
    # man.dbID2hgncSymbol()
    # man.mapping()

    # db,db_cols = initDB('mydb_v1')

    # reactom_entry_col = db_cols.get('reactom.pathway.entry')

    # docs = reactom_