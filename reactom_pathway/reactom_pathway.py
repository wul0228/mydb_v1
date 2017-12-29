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

        pathurl_mt,summary_mt = process.getUrl()

        # download graph file
        func  = lambda x:process.wget(x,pathurl_mt[x],rawdir)

        multiProcess(func,pathurl_mt.keys(),size=50)

        # download summary file
        for url,mt in summary_mt.items():

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

    graphpaths = [filepath for filepath in filepaths if  filepath.endswith('.graph.json') ]

    jsonpaths = [filepath for filepath in filepaths if not filepath.endswith('graph.json') and filepath.endswith('.json') ]

    sumpaths = [filepath for filepath in filepaths if filepath.endswith('.txt')]

    print len(graphpaths)
    print len(jsonpaths)
    print len(sumpaths)

    # # reactom.pathway.info (pathway2summation and reactompathway)
    # process.info(sumpaths,fileversion)

    # reactom.pathway.entry
    # all_nodes = process.entry(graphpaths,fileversion)

    # reactom.pathway.reaction
    # all_events = process.event(graphpaths,fileversion)

    # add subpathway to entry and reaction
    process.subpathway(graphpaths,fileversion)

    # deal json file 
    # for jsonpath in jsonpaths:
    #     process.graph(jsonpath,fileversion)
    
    # func = lambda x : process.graph(x)
    # multiProcess(func,jsonpaths,size=20)

    # _mongodb = pjoin(reactom_pathway_db,rawdirname)

    # colhead = 'reactom.pathway'

    # bkup_allCols('mydb_v1',colhead,_mongodb)

    # print 'extract and insert completed'

    # return (filepaths,version)

def updateData(insert=False,_mongodb='../_mongodb/'):

    reactom_pathway_log = json.load(open(log_path))

    rawdir = pjoin(reactom_pathway_raw,'pathway_update_{}'.format(today))

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

class dbMap(object):

    #class introduction

    def __init__(self,version):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb')

        colname = 'reactom_pathway_{}'.format(version)

        col = db.get_collection(colname)

        docs = col.find({})

        self.col = col

        self.docs = docs

        self.version = version

        self.colname = colname

    def mappathid2pathname(self):

        pathid2pathname = dict()

        pathname2pathid = dict()

        geneid2pathid = dict()

        for doc in self.docs:

            path_id = doc.get('stId')

            path_name = doc.get('name')

            genes  = doc.get('nodes',{}).get('EntityWithAccessionedSequence',{}).keys()

            if genes:

                for geneid in genes:

                    if geneid not in geneid2pathid:

                        geneid2pathid[geneid] = list()

                    geneid2pathid[geneid].append(path_id)

            if path_name:

                pathid2pathname.update({path_id:path_name})

                if path_name not in pathname2pathid:

                    pathname2pathid[path_name] = list()

                pathname2pathid[path_name].append(path_id)

            else:
                print path_id,'no name'

        pathid2geneid = value2key(geneid2pathid)

        map_dir = pjoin(reactom_pathway_map,self.colname)

        createDir(map_dir)

        save = {'pathid2pathname':pathid2pathname,'pathname2pathid':pathname2pathid,
                    'geneid2pathid':geneid2pathid,'pathid2geneid':pathid2geneid}

        for name,dic in save.items():

            with open(pjoin(map_dir,'{}.json'.format(name)),'w') as wf:
                json.dump(dic,wf,indent=2)

    def mapping(self):

        self.mappathid2pathname()

class reactom_parser(object):

    def __init__(self,date):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        # colname = 'reactom_pathway_{}'.format(version)

        # col = db.get_collection(colname)

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

        info_files = ['pathway2summation','ReactomePathways']

        pathurl_mt = dict()

        summary_mt = dict()

        for url in [reactome_download_web1,reactome_download_web2]:
        # for url in [reactome_download_web1]:#,reactome_download_web2]:
            
            web = requests.get(url)

            soup = bs(web.content,'lxml')

            trs = soup.select('body > table > tr ')

            for tr in trs:

                text = tr.text

                filename = text.split('.json')[0].strip()

                # if filename.startswith('R-HSA') and filename.endswith('.graph'):
                if filename.startswith('R-HSA'):

                    mt = self.Mt(text,filename)

                    key = url + filename + '.json'

                    pathurl_mt[key] = mt

                elif filename.split('.txt')[0].strip() in info_files:

                    mt = self.Mt(text,'pathway2summation.txt')

                    key = url + 'pathway2summation.txt'

                    summary_mt[key] = mt

        return (pathurl_mt,summary_mt)

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

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,url)

        os.popen(command)

    def info(self,filepaths,fileversion):

        info_colname = 'reactom.pathway.info'

        delCol('mydb_v1',info_colname)

        info_col = self.db.get_collection(info_colname)

        path_ids = list()

        for filepath in filepaths:

            tsvfile = open(filepath)

            filename = psplit(filepath)[1].strip()

            fileversion = filename.rsplit('_',1)[1].strip().split('.',1)[0].strip()

            if not info_col.find({'dataVersion':fileversion}):

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

                if path_id not in path_ids:
                    path_ids.append(path_id)

                dic['path_link'] = 'https://reactome.org/content/detail/{}'.format(path_id)

                dic['path_image'] = 'https://reactome.org/PathwayBrowser/#/{}'.format(path_id)

                info_col.update(
                    {'path_id':path_id},
                    {'$set':dic},
                    True
                    )
                n += 1

                print 'reactom.pathway.info',n,path_id

        with open('./all_reactom_paths.json','w') as wf:
            json.dump(path_ids,wf,indent=8)

        return path_ids

    def entry(self,filepaths,fileversion):

        entry_colname = 'reactom.pathway.entry'

        delCol('mydb_v1',entry_colname)

        entry_col = self.db.get_collection(entry_colname)

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

                node_id = node.get('stId')

                children = node.get('children')

                if children:
                    node['children'] = ['R-HSA-{}'.format(i) for i in children]

                parents = node.get('parents')

                if parents:
                    node['parents'] = ['R-HSA-{}'.format(i) for i in parents]


                node['path_id'] = path_id

                node.pop('dbId')

                node['entry_id'] = node.pop('stId')

                entry_col.insert(node)

                # add to all nodes
                if node_id not in all_nodes:

                    node.pop('_id')

                    all_nodes[node_id] = node

            n += 1

            print 'reactom.pathway.entry file',n

        with open('./all_reactom_nodes.json','w') as wf:
            json.dump(all_nodes,wf,indent=8)

        return all_nodes

    def event(self,filepaths,fileversion):

        event_colname = 'reactom.pathway.event'

        delCol('mydb_v1',event_colname)

        event_col = self.db.get_collection(event_colname)

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

                    dbId = e.pop('dbId')
                    
                    event_id = e.pop('stId')

                    e['path_id'] = path_id

                    e['event_id'] = event_id

                    for key in ['inputs','outputs','activators','catalysts','inhibitors','following','preceding']:

                        val = e.get(key)

                        if val:
                            e[key]  = ['R-HSA-{}'.format(i) for i in  val]

                    event_col.insert(e)

                    e.pop('_id')

                    if event_id not in all_events:
                        all_events[event_id] = e

        with open('./all_reactom_events.json','w') as wf:
            json.dump(all_events,wf,indent=8)

        return all_events

    def subpathway(self,filepaths,fileversion):

        entry_col = self.db.get_collection('reactom.pathway.entry')

        event_col = self.db.get_collection('reactom.pathway.event')

        all_paths = json.load(open('./all_reactom_paths.json'))

        all_nodes = json.load(open('./all_reactom_nodes.json'))

        all_events = json.load(open('./all_reactom_events.json'))

        n = 0

        for filepath in filepaths:
            
            filename = psplit(filepath)[1].strip()

            jsonfile = json.load(open(filepath))

            fileversion = filename.rsplit('_',1)[1].strip().split('.',1)[0].strip()

            path_id = jsonfile.get('path_id')

            subpathways = jsonfile.get('subpathways')

            if subpathways:

                for subpathway in subpathways:

                    subpath_id = subpathway.get('stId') # all subpathway id included in pathway.info

                    subpath_events = subpathway.get('events')

                    if subpath_events:

                        for event_id in subpath_events:

                            event_id = 'R-HSA-{}'.format(event_id)

                            event_info  = all_events.get(event_id)

                            if event_info:
                                # bcause subpath also contain this event .so add to pathway.envent
                                event_info['path_id'] = subpath_id
                                # envent_col.insert(event_info)

                                # bcause subpath also contain this event  and it's nodes .so add to pathway.nodes
                                envent_nodes = list()

                                for key in ['inputs','outputs','activators','catalysts','inhibitors']:
                                    val = event_info.get(key,[])
                                    envent_nodes += val

                                envent_nodes = list(set(envent_nodes))

                                for node_id in envent_nodes:
                                    node_info = all_nodes.get(node_id)

                                    if node_info:
                                        node_info['path_id'] = subpath_id
                                    else:
                                        print 'event_id',event_id,'    ',node_id,'is not in all_nodes'
                                    # entry_col.insert(event_info)
                                # print subpath_id,envent_nodes

                            else:

                                print event_id,'not in all_event'
                                # event is is not represent event but a pathway

                                path_id = event_id

                                docs = event_col.find({'path_id':path_id})

                                if docs:

                                    event = list()

                                    for doc in docs:
                                        
                                        doc.pop('_id')
                                        envent_info = doc
                                        envent_info['path_id'] =  subpath_id
                                        # envent_col.insert(event_info)

                                        envent_nodes = list()

                                        for key in ['inputs','outputs','activators','catalysts','inhibitors']:
                                            val = event_info.get(key,[])
                                            envent_nodes += val

                                        envent_nodes = list(set(envent_nodes))

                                        for node_id in envent_nodes:
                                            node_info = all_nodes.get(node_id)
                                            node_info['path_id'] = subpath_id
                                            # entry_col.insert(event_info)

                                else:

                                    print path_id,'not in path_id'
                            print 

    def graph(self,filepath,fileversion):

        #--------------------------------------------------------------------------------------------------------------------------------------------------------------------

        entry_colname = 'reactom.pathway.entry'

        delCol('mydb_v1',colname)

        entry_col = self.db.get_collection(entry_colname)
        
        entry_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'R-HSA-??????.graph'})
        #--------------------------------------------------------------------------------------------------------------------------------------------------------------------

        dic = json.load(open(filepath))

        # delete origin nodes list
        nodes = dic.pop('nodes')

        # create new nodes dict
        nodeinfo = dict()

        for node in nodes:

            schemaClass = node.pop('schemaClass')

            if not schemaClass:

                schemaClass = 'Other'


            dbId = node.pop('dbId')

            if schemaClass not in nodeinfo:

                nodeinfo[schemaClass] = dict()

            if dbId not in nodeinfo[schemaClass]:

                nodeinfo[schemaClass][str(dbId)] = node

        dic.update({'nodes':nodeinfo})

        # with open(pjoin(storedir,filename) ,'w') as wf:
        #     json.dump(dic,wf,indent=2)

        col.insert(dic)
        # pprint.pprint(dic)
    
    def sum(self,filepath,fileversion):
        #--------------------------------------------------------------------------------------------------------------------------------------------------------------------
        info_colname = 'reactom.pathway.info'

        delCol('mydb_v1',info_colname)

        info_col = self.db.get_collection(info_colname)
        
        info_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'R-HSA-??????.graph,pathway2summation'})
        
        tsvfile = open(filepath)

        keys = ['stId','name','summation']

        for line in tsvfile:

            if line.startswith('#'):
                continue

            data =[i.strip() for i in  line.strip().split('\t') if i]

            dic = dict([(key,val) for key,val in zip(keys,data)])

            stId = dic.get('stId')

            stId_link = 'https://reactome.org/content/detail/{}'.format(stId)

            dic['stId_link'] = stId_link

            summation = dic['summation'].decode('unicode_escape').encode('utf8')

            dic['summation'] = summation

            info_col.insert(dic)

def main():

    modelhelp = model_help.replace('&'*6,'Reactom_Pathway').replace('#'*6,'reactom_pathway')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,reactom_pathway_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    # main()
    # filepaths,version = downloadData(redownload = True)
    # pass
    rawdir = '/home/user/project/dbproject/mydb_v1/reactom_pathway/dataraw/pathway_171229091519/'
    filepaths = [pjoin(rawdir,filename) for filename in os.listdir(rawdir)]
    extractData(filepaths,version)
    # man = dbMap('171207120739')
    # man.mapping()

    # rawdir = '/home/user/project/dbproject/mydb_v1/reactom_pathway/dataraw/pathway_171229091519/'
    
    # jsonfiles = [pjoin(rawdir,filename) for filename in os.listdir(rawdir) if filename.endswith('.json')]

    # edge_type = list()
    # node_type = list()
    # json_keys = list()

    # pathway_ids = list()

    # subpathway_ids  = list()

    # for jsonfile in jsonfiles:

    #     dic = json.load(open(jsonfile))

    #     for key in dic.keys():
    #         if key not in json_keys:
    #             json_keys.append(key)

    #     json_keys = list(set(json_keys))
    #     stId = dic.get('stId')

    #     pathway_ids.append(stId)

    #     subpathways = dic.get('subpathways')

    #     if subpathways:

    #         subpathway_id = [subpathway.get('stId') for subpathway in subpathways]

    #         subpathway_ids += subpathway_id

    # print 'len(pathway_ids)',len(pathway_ids)
    # print 'len(subpathway_ids)',len(subpathway_ids)

    # # print subpathway_ids
    # pathway_ids = list(set(pathway_ids))
    # subpathway_ids = list(set(subpathway_ids))

    # print 'dedup len(pathway_ids)',len(pathway_ids)
    # print 'dedup len(subpathway_ids)',len(subpathway_ids)


    # _all = pathway_ids + subpathway_ids

    # print '_all',len(_all)

    # dedup_all = list(set(_all))


    # print 'len(dedup_all)',len(dedup_all)

    # with open('./all_reactom_pathwayID.json','w') as wf:
    #     json.dump(dedup_all,wf,indent=8)

    # print subpathway_ids

    #     nodes = dic.get('nodes')

    #     if nodes:

    #         for n in nodes:

    #             schemaClass = n.get('schemaClass')

    #             if schemaClass not in node_type:

    #                 node_type.append(schemaClass)

    #     edges = dic.get('edges')

    #     if edges:

    #         for e in edges:

    #             schemaClass = e.get('schemaClass')

    #             if schemaClass not in edge_type:

    #                 edge_type.append(schemaClass)


    # print json_keys

    # print len(json_keys)

    # print edge_type

    # print 'edge_type',len(edge_type)

    # print node_type

    # print 'node_type',len(node_type)

