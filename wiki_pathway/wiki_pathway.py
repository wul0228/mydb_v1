#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date: 2017/12/05
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download,extract,standard insert and select pathway data from wiki pathway

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(wiki_pathway_model,wiki_pathway_raw,wiki_pathway_store,wiki_pathway_db,wiki_pathway_map) = buildSubDir('wiki_pathway')

log_path = pjoin(wiki_pathway_model,'wiki_pathway.log')

# main code
def downloadData(redownload = False):

    '''
    this function is to download the raw data from wiki web
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existwikiFile) = lookforExisted(wiki_pathway_raw,'pathway')

        if choice != 'y':
            return

    if redownload or not existwikiFile or  choice == 'y':

        process = wiki_parser(today)

        (down_urls,mt) = process.getMt()

        # download file
        unzipdir = process.wget(down_urls,mt,wiki_pathway_raw)

    # create log file
    if not os.path.exists(log_path):

        with open('./wiki_pathway.log','w') as wf:
            json.dump({
                'wiki_pathway':[(mt,today,model_name),]
                },wf,indent=2)

    print  'datadowload completed !'

    filepaths = [pjoin(unzipdir,filename) for filename in unzipdir]

    return (filepaths,today)

def extractData(filepaths,date):

    rawdirname = psplit(psplit(filepaths[0])[0])[1].strip()

    fileversion = rawdirname.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

    gpmlpaths = [path for path in filepaths if path.endswith('.gpml')]

    xmlpaths = [path for path in filepaths if path.endswith('.xml')]

    genepaths = [path for path in filepaths if path.endswith('.gmt')]

    process = wiki_parser(date)

    # # create wiki.pathway.info
    process.info(xmlpaths,gpmlpaths,fileversion)

    # # create wiki.pathway.gene
    process.gene(genepaths,fileversion)

    # # create wiki.pathway.entry
    process.entry(gpmlpaths,fileversion)

    # create wiki.pathway.interaction
    process.interaction(gpmlpaths,fileversion)

    # bkup all collections
    _mongodb = pjoin(wiki_pathway_db,'pathway_{}'.format(date))

    createDir(_mongodb)

    colhead = 'wiki.pathway'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    print 'extract an insert completed!'

    return (filepaths,date)

def updateData(insert=False,_mongodb='../_mongodb/'):

    wiki_pathway_log = json.load(open(log_path))

    rawdir = pjoin(wiki_pathway_raw,'pathway_update_{}'.format(today))

    latest = wiki_pathway_log.get('wiki_pathway')[-1][0].strip()

    process = wiki_parser(today)

    (dowload_url,mt) = process.getMt()

    if mt != latest:

        createDir(rawdir)

        filepaths,version  = downloadData(redownload = True)

        extractData(filepaths,version)

        wiki_pathway_log['wiki_pathway'].append((mt,today,model_name))

        with open(log_path,'w') as wf:

            json.dump(wiki_pathway_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('wiki_pathway',mt)

        bakeupCol('wiki_pathway_{}'.format(version),'wiki_pathway',_mongodb)

    else:

        print  '{} {} is the latest !'.format('wiki_pathway',mt)

def selectData(querykey = 'name',value='EBV LMP1 signaling'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mydb

    colnamehead = 'wiki_pathway'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)


class dbMap(object):

    #class introduction

    def __init__(self,version):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb')

        colname = 'wiki_pathway_{}'.format(version)

        col = db.get_collection(colname)

        self.col = col

        self.version = version

        self.colname = colname

        self.docs =self.col.find({})

    def mappathid2pathname(self):

        pathid2pathname = dict()

        pathname2pathid = dict()

        geneid2pathid = dict()

        for doc in self.docs:

            path_id = doc.get('path_id')

            path_name = doc.get('path_name')

            genes  = doc.get('GeneProduct')

            if genes:
                
                for key,val in genes.items():

                    xref = val.get('xref')
                    if  xref:

                        for k,v  in xref.items():
                            geneid = k + ':' + v

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

        map_dir = pjoin(wiki_pathway_map,self.colname)

        createDir(map_dir)

        save = {'pathid2pathname':pathid2pathname,'pathname2pathid':pathname2pathid,
                    'geneid2pathid':geneid2pathid,'pathid2geneid':pathid2geneid}

        for name,dic in save.items():

            with open(pjoin(map_dir,'{}.json'.format(name)),'w') as wf:
                json.dump(dic,wf,indent=2)


    def mapping(self):

        self.mappathid2pathname()

class wiki_parser(object):

    def __init__(self, date):

        self.date = date

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

    def getMt(self):

        download_urls = list()
        #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # download gpml file
        headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36',}

        web = requests.get(wiki_pathway_download,headers = headers,verify=False)

        soup = bs(web.content,'lxml')

        down = soup.find(text = 'Current version: ')

        p =down.findParent('p')

        a = p.findChild('a')

        mt = a.text.split('(')[0].strip()

        href = a.attrs.get('href')

        pathinfo_url  = href + 'gpml/wikipathways-{}-gpml-Homo_sapiens.zip'.format(mt)
        
        mt = '213' + mt

        download_urls.append(pathinfo_url)
        #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        listpatway_url = 'https://webservice.wikipathways.org/listPathways?organism=Homo%20sapiens&format=json'
        pathwaygene_url = 'http://data.wikipathways.org/java-bots/gmt/current/gmt_wp_Homo_sapiens.gmt'
        download_urls.append(listpatway_url)
        download_urls.append(pathwaygene_url)
        #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

        return  (download_urls,mt)

    def wget(self,urls,mt,rawdir):


        pathinfo_url = [url for url in urls if url.endswith('.zip')][0]

        listpath_url = [url for url in urls if url.endswith('json')][0]

        pathgene_url = [url for url in urls if url.endswith('.gmt')][0]

        #---------------------------------------------------------------------------------------------------
        # download gpml file
        filename = pathinfo_url.rsplit('/',1)[1].strip().rsplit('.',1)[0].strip()
        savename = '{}_{}_{}.zip'.format(filename,mt,today)
        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,pathinfo_url)
        os.popen(command)

        # unzip file
        unzipdir = pjoin(wiki_pathway_raw,'pathway_{}_{}'.format(mt,today))
        createDir(unzipdir)

        unzip = 'unzip {} -d {}'.format(storefilepath,unzipdir)
        os.popen(unzip)

        # remove file
        remove = 'rm {}'.format(storefilepath)
        os.popen(remove)

        #---------------------------------------------------------------------------------------------------
        # download listpathway file

        savename = 'listpathway_{}_{}.xml'.format(mt,today)
        storefilepath = pjoin(unzipdir,savename)
        command = 'wget -O {} {}'.format(storefilepath,listpath_url)
        os.popen(command)
        #---------------------------------------------------------------------------------------------------
        # download listpathway file
        filename = pathgene_url.rsplit('/',1)[1].strip().rsplit('.',1)[0].strip()
        savename = '{}_{}_{}.txt.zip'.format(filename,mt,today) 
        storefilepath = pjoin(unzipdir,savename)
        command = 'wget -O {} {}'.format(storefilepath,pathgene_url)
        os.popen(command)

        return unzipdir

    def info(self,jsonpaths,gpmlpaths,fileversion):
        '''
            this  function is to parse the wiki human pathway infos 
            1. get the id,name,organism,link
            2. get the catogory and description in comment

        '''
        info_colname = 'wiki.pathway.info'

        delCol('mydb_v1',info_colname)

        info_col = self.db.get_collection(info_colname)

        info_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'wiki.pathway.files'})

        #------------------------------------------------------------------------------------------------------------------------------------------------
        # pathway.info in listpathway file
        # 1. get the id,name,organism,link
        jsonfile = parse(open(jsonpaths[0])) # just only one file

        pathways = jsonfile.get('ns1:listPathwaysResponse').get('ns1:pathways')

        n = 0 

        for pathway in pathways:

            pathinfo = dict()
            pathinfo.update({
            'path_id' :pathway.get('ns2:id'),
            'path_name' : pathway.get('ns2:name'),
            'path_link' : pathway.get('ns2:url'),
            'path_org' : pathway.get('ns2:species'),
            'path_revision' : pathway.get('ns2:revision'),
            })

            info_col.insert(pathinfo)

            n += 1

            print 'wiki.pathway.info line',n
        
        #------------------------------------------------------------------------------------------------------------------------------------------------
        # pathway.info in gpml file
        # 2. get the catogory and description in comment
        
        n  = 0

        for filepath in gpmlpaths:

            path = dict()

            filename = psplit(filepath)[1].strip().split('.gpml')[0].strip()

            jsonfile = parse(open(filepath))

            pathway = jsonfile.get('Pathway')
            #pathway keys include [u'@Name', u'@License', u'Label', u'State', u'Group', u'@Organism', u'@xmlns', u'@Data-Source', u'GraphicalLine', u'@Maintainer', u'DataNode', u'Graphics', u'Legend', u'Interaction', u'@Author', u'@Last-Modified', u'Biopax', u'@Version', u'@Email', u'Comment', u'Attribute', u'InfoBox', u'Shape', u'BiopaxRef']
            path_id =  filename.rsplit('_',2)[1].strip()

            #2. get the catogory and description in comment, sometimes  there is just one record of comment (dict), multi comment usally is dict but unicode included sometime
            comment = pathway.get('Comment')
            if comment:
                comment_info = self.info_comment(comment)

            biopax = pathway.get('Biopax')
            if biopax:
                biopax_info = self.info_biopax(biopax)

            path.update(comment_info)
            path.update(biopax_info)

            info_col.update(
                {'path_id':path_id},
                {'$set':path},
                True,
                False
                )

            n += 1

            print n,filename
        
    def info_comment(self,comment):
        #comment source included [u'WikiPathways-category', u'WikiPathways-description', u'GenMAPP remarks', u'GenMAPP notes', u'HomologyMapper', u'KeggConverter']
        comment_info = dict()

        if  isinstance(comment,dict): 

            comment = [comment,]

        for i in comment:

            if isinstance(i,dict):

                Source = i.get("@Source")

                # get all category, one or more catagory infos
                if Source == 'WikiPathways-category':

                    if  Source not in comment_info:
                        comment_info.update({Source:[i.get("#text"),]})
                    else:
                        comment_info[Source].append(i.get("#text"))

                if Source =='WikiPathways-description':

                    # get the longest description,one or more description infos 
                    if  Source not in comment_info:
                        comment_info.update({Source:i.get("#text")})
                    else:
                        text = i.get("#text")
                        # compare the length ,return the longest
                        compare_len = lambda x,y : x if len(x)>=len(y) else y
                        comment_info[Source] = compare_len(comment_info[Source],text)

        return comment_info

    def info_biopax(self,biopax):

        # biopax keys include [u'bp:openControlledVocabulary', u'bp:PublicationXref']

        biopax_info = dict()
        biopax_info['PublicationXref'] = list()
        biopax_info['openControlledVocabulary'] = list()

        pub_xref = biopax.get('bp:PublicationXref')

        if pub_xref:

            if isinstance(pub_xref,dict):
                pub_xref = [pub_xref,]

            xrefinfo = dict()

            for xref in pub_xref:

                key_val = {'bp:ID':'id','bp:DB':'db','bp:AUTHORS':'authors','bp:TITLE':'title','bp:SOURCE':'source','bp:YEAR':'year'}

                for key,val in key_val.items():

                    vals = xref.get(key)

                    if vals:

                        if isinstance(vals,dict):

                            vals = [vals,]

                        xref_vals = list()

                        [xref_vals.append(v.get('#text')) for v in vals if v.get('#text')]

                        xref_vals = list(set(xref_vals))

                        if val  == 'id':

                            db_links = ';'.join(['http://www.ncbi.nlm.nih.gov/pubmed/{}'.format(_id) for _id in xref_vals])

                            xrefinfo.update({'db_link':db_links})

                        xref_vals = ';'.join(xref_vals)

                    else:
                        xref_vals = ''

                    xrefinfo.update({val:xref_vals})

            biopax_info['PublicationXref'].append(xrefinfo)

        open_ctr = biopax.get('bp:openControlledVocabulary')

        if open_ctr:

            if isinstance(open_ctr,dict):
                open_ctr = [open_ctr,]

            for ctr in open_ctr:

                ctrinfo = dict()

                key_val = {'bp:TERM':'term','bp:ID':'id','bp:Ontology':'ontology'}

                for key,val in key_val.items():

                        vals = ctr.get(key)

                        if vals:

                            if isinstance(vals,unicode):
                                ctr_val = vals.strip()
                            elif isinstance(vals,dict):
                                ctr_val = vals.get('#text')
                            else:
                                print '!!!!!!!!!'
                        else:
                            ctr_val = ''

                        ctrinfo[val] = ctr_val
            
                biopax_info['openControlledVocabulary'].append(ctrinfo)

        return biopax_info

    def gene(self,filepaths,fileversion): 

        gene_colname = 'wiki.pathway.gene'

        delCol('mydb_v1',gene_colname)

        gene_col = self.db.get_collection(gene_colname)

        gene_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'gmt_wp_Homo_sapiens'})

        keys = ['path_name','version','path_id','path_org']

        for filepath in filepaths:

            tsvfile = open(filepath)

            n = 0

            for line in tsvfile:

                front = line.split('\t',1)[0].split('%')
                after = line.split('\t',1)[1].strip().split('\t')

                dic = dict([(key,val) for key,val in zip(keys,front)])

                for key in ['path_name','version']:

                    dic.pop(key)

                for gene_id in after[1:]:
                    dic['entrez_id'] = gene_id
                    gene_col.insert(dic)
                    dic.pop('_id')

                n += 1

                print 'wiki.pathway.gene line',n,dic.get('path_id'),len(after[1:])

    def entry(self,filepaths,fileversion):

        entry_colname = 'wiki.pathway.entry'

        delCol('mydb_v1',entry_colname)

        entry_col = self.db.get_collection(entry_colname)

        entry_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'wiki.pathway.files'})

        for filepath in filepaths:

            path = dict()

            filename = psplit(filepath)[1].strip().split('.gpml')[0].strip()

            jsonfile = parse(open(filepath))

            pathway = jsonfile.get('Pathway')
            #pathway keys include [u'@Name', u'@License', u'Label', u'State', u'Group', u'@Organism', u'@xmlns', u'@Data-Source', u'GraphicalLine', u'@Maintainer', u'DataNode', u'Graphics', u'Legend', u'Interaction', u'@Author', u'@Last-Modified', u'Biopax', u'@Version', u'@Email', u'Comment', u'Attribute', u'InfoBox', u'Shape', u'BiopaxRef']
            path_id =  filename.rsplit('_',2)[1].strip()

            #3. get the datanode infos and classfied to GeneProduct,Complex,Metabolite and so on according to the type info
            # a pathway must have more than one node
            datanode = pathway.get('DataNode')
            (nodetype,nodeinfo,groupId_nodeId) = self.gpml_datanode(datanode)

            group = pathway.get('Group')
            graphId_groupId = self.gpml_group(group)

            label = pathway.get('Label')
            graphId_label = self.gpml_label(label)

            anchorgraphId_pointgraphId = {}

            allgraphId_nodegraphId = self.gpml_allgraphId_nodegraphId(nodeinfo,groupId_nodeId,graphId_groupId,anchorgraphId_pointgraphId,graphId_label)

            for entry_id,info  in allgraphId_nodegraphId.items():

                #lable node
                if isinstance(info,unicode):
                    entry_col.insert({'path_id':path_id,'path_org':'Homo sapiens','name':info,'entry_id':entry_id,'type':''})

                if isinstance(info,list):
                    #datanode
                    if len(info) ==1:
                        node = info[0]
                        node['path_id'] = path_id
                        node['path_org'] = 'Homo sapiens'
                        node['entry_id'] = entry_id
                        entry_col.insert(node)
                        node.pop('_id')
                    else:
                        if  all([isinstance(i,dict) for i in info]):
                            # group
                            groupnode = dict()
                            groupnode['entry_id'] = entry_id
                            groupnode['name'] = '|'.join([n.get('name') for n in info if n.get('name')])
                            groupnode['path_id'] = path_id
                            groupnode['path_org'] = 'Homo sapiens'
                            groupnode['type'] = 'group'
                            entry_col.insert(groupnode)
                            groupnode.pop('_id')

                        else:
                            print '+'*50
                            print filename,entry_id,info

    def interaction(self,filepaths,fileversion):

        interaction_colname = 'wiki.pathway.interaction'

        delCol('mydb_v1',interaction_colname)

        interaction_col = self.db.get_collection(interaction_colname)

        interaction_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'wiki.pathway.files'})

        for filepath in filepaths:

            path = dict()

            filename = psplit(filepath)[1].strip().split('.gpml')[0].strip()

            jsonfile = parse(open(filepath))

            pathway = jsonfile.get('Pathway')
            #pathway keys include [u'@Name', u'@License', u'Label', u'State', u'Group', u'@Organism', u'@xmlns', u'@Data-Source', u'GraphicalLine', u'@Maintainer', u'DataNode', u'Graphics', u'Legend', u'Interaction', u'@Author', u'@Last-Modified', u'Biopax', u'@Version', u'@Email', u'Comment', u'Attribute', u'InfoBox', u'Shape', u'BiopaxRef']
            path_id =  filename.rsplit('_',2)[1].strip()

            #3. get the datanode infos and classfied to GeneProduct,Complex,Metabolite and so on according to the type info
            # a pathway must have more than one node
            datanode = pathway.get('DataNode')
            (nodetype,nodeinfo,groupId_nodeId) = self.gpml_datanode(datanode)

            group = pathway.get('Group')
            graphId_groupId = self.gpml_group(group)

            label = pathway.get('Label')
            graphId_label = self.gpml_label(label)

            # a pathway must have more than one interaction
            interaction = pathway.get('Interaction')
            anchorgraphId_pointgraphId = self.gpml_anchor(interaction)

            allgraphId_nodegraphId = self.gpml_allgraphId_nodegraphId(nodeinfo,groupId_nodeId,graphId_groupId,anchorgraphId_pointgraphId,graphId_label)   
            
            if interaction:
                if isinstance(interaction,dict):interaction = [interaction,]
                
                print path_id,'len(interaction)',len(interaction)

                for inter in interaction:
                    points = inter.get('Graphics',{}).get('Point')

                    # points must have more than 2 point that have 2 GraphId
                    if points and len(points) >= 2:

                        adic = dict()
                        adic['ArrowHead'] = dict()
                        adic['ArrowHead']['output'] = list()
                        adic['ArrowHead']['input'] = list()

                        m = 1 #group number
                        for p in points:
                            GraphId = p.get('@GraphRef')
                            if not GraphId:
                                continue

                            ArrowHead = p.get('@ArrowHead')
                            if  ArrowHead:
                                adic['ArrowHead']['type'] = ArrowHead

                            # look for nodeinfo
                            group_num = 'group{}_info'.format(m)

                            entry = allgraphId_nodegraphId.get(GraphId)

                            if entry and isinstance(entry,(unicode,list)):
                               adic[group_num] = entry 
                                
                            elif entry and  isinstance(entry,dict):
                                adic[group_num]= entry.values()

                            if ArrowHead:
                                adic['ArrowHead']['output'] .append(group_num.split('_info')[0])
                            else:
                                adic['ArrowHead']['input'].append(group_num.split('_info')[0])

                            m += 1

                            if  not ArrowHead:
                                adic['ArrowHead']['type'] = 'line'

                            del ArrowHead

                            # modify output 
                        if len(adic)  >=3:

                            adic = self.gpml_arrowhead(adic)
                            adic['path_id'] = path_id

                            group1_info = adic.get('group1_info')
                            if all([isinstance(i,dict) for i in group1_info]):
                                group1 = '|'.join([i.get('name') for i in group1_info if  i.get('name')])
                            else:
                                group1 = ''
                            group2_info = adic.get('group2_info')
                            if all([isinstance(i,dict) for i in group2_info]):
                                group2 = '|'.join([i.get('name') for i in group2_info if i.get('name')])
                            else:
                                group2 = ''
                            adic['group1'] = group1
                            adic['group2'] = group2

                            interaction_col.insert(adic)

    def gpml_datanode(self,datanode):

        # create a dict to store node info ,classfied to node type class
        nodetype = dict()

        # create a dict to store node info, with GraphId as the key
        nodeinfo = dict()

        # create a dict  to store groupref2nodeids
        groupId_nodeId = dict()

        for node in datanode:
            #----------------node graphid--------------------
            node_graphid = node.get('@GraphId')

            nodeinfo[node_graphid] = dict()

            #----------------node groupref--------------------
            node_groupref = node.get('@GroupRef')

            if node_groupref:

                if node_groupref not in groupId_nodeId:

                    groupId_nodeId[node_groupref] = list()

                groupId_nodeId[node_groupref].append(node_graphid)

            #----------------node type--------------------
            node_type = node.get('@Type')
            # some node hava no type
            if not node_type:

                node_type = 'Other'

            nodeinfo[node_graphid]['type'] = node_type

            # gene metabbolit complex pathway geneproduct protein
            if node_type not in nodetype:
                
                nodetype[node_type] = dict()

            node_lable =  node.get('@TextLabel').replace(' ','&').replace('.','*').strip()

            nodeinfo[node_graphid]['name'] = node_lable

            if node_lable not in nodetype[node_type]:

                nodetype[node_type][node_lable] = dict()

            node_comment = node.get('Comment')

            if node_comment:

                if isinstance(node_comment,unicode):
                    nodetype[node_type][node_lable]['comment'] = node_comment
                    nodeinfo[node_graphid]['comment'] = node_comment

                elif isinstance(node_comment,dict):
                    node_comment = [node_comment,]

                if isinstance(node_comment,list):

                    nodetype[node_type][node_lable]['comment'] = dict()
                    nodeinfo[node_graphid]['comment'] = dict()
                    for c in node_comment:
                        if isinstance(c,dict):
                            nodetype[node_type][node_lable]['comment'].update({c.get('@Source'):c.get("#text")})
                            nodeinfo[node_graphid]['comment'].update({c.get('@Source'):c.get("#text")})
                        else:
                             nodeinfo[node_graphid]['comment'].update({'other':c})

            node_xref = node.get("Xref")

            if node_xref:

                if isinstance(node_xref,dict): node_xref=[node_xref,]

                nodetype[node_type][node_lable]['xref'] = dict()
                
                nodeinfo[node_graphid]['xref'] = dict()

                for xref in node_xref:
                    db = xref.get('@Database')
                    _id = xref.get('@ID')

                    if db:
                        nodetype[node_type][node_lable]['xref'].update({db:_id})
                        nodeinfo[node_graphid]['xref'].update({db:_id})
        
        return (nodetype,nodeinfo,groupId_nodeId)

    def gpml_group(self,group):

        graphId_groupId = dict()

        if group:

            if isinstance(group,dict): group=[group,]

            for g in group:

                group_groupId =g.get('@GroupId')
                group_graphId = g.get('@GraphId')

                # a graphId to 2 or more group_groupId??
                graphId_groupId[group_graphId] = group_groupId

        # with open('./graphId_groupId.json','w') as wf:
        #     json.dump(graphId_groupId,wf,indent=2)

        return graphId_groupId

    def gpml_label(self,label):

        graphId_label = dict()

        if label:

            if isinstance(label,dict): label=[label,]

            for l in label:
                label_graphId =l.get('@GraphId')
                label_name = l.get('@TextLabel').strip()

                graphId_label[label_graphId] = label_name

        return graphId_label

    def gpml_anchor(self,interaction):

        if interaction:

            if isinstance(interaction,dict):interaction = [interaction,]

            anchorgraphId_pointgraphId = dict()

            for index,inter in enumerate(interaction):

                anchors = inter.get('Graphics',{}).get('Anchor')

                if anchors:

                    if isinstance(anchors,dict):anchors = [anchors,]

                    for anchor in anchors:

                        anchor_graphId = anchor.get('@GraphId')

                        anchorgraphId_pointgraphId[anchor_graphId] = list()

                        points = inter.get('Graphics',{}).get('Point')

                        # if points and len(points) >= 2:
                        if points:
                       
                            for p in points:

                                GraphId = p.get('@GraphRef')

                                if not GraphId:

                                    continue

                                anchorgraphId_pointgraphId[anchor_graphId].append(GraphId)
    
            return anchorgraphId_pointgraphId

    def gpml_arrowhead(self,adic):

        ArrowHead = adic.get('ArrowHead')

        _input = ArrowHead.get('input')

        _output = ArrowHead.get('output')

        arrow_type = ArrowHead.get('type')

        if not arrow_type:

            print adic

        if (_input and not _output) or  arrow_type.lower() == 'line':

            effect_type = '   [ -------- ]   '.join(_input)

        elif _output and not _input:

            effect_type = '   [ <------> ]   '.join(_output)

        elif _input and _output:

            if arrow_type.strip() == 'Arrow':
                arrow_type = " --------> " 

            if arrow_type.strip() == 'TBar': 
                arrow_type = ' --------| '

            effect_type = ','.join(_input)   + '   [ ' + arrow_type + ' ]   ' + ','.join(_output)
            # print effect_type
        else:
            pass

        adic.pop('ArrowHead')

        adic.update({'effect_type':effect_type})

        return adic

    def gpml_allgraphId_nodegraphId(self,nodeinfo,groupId_nodeId,graphId_groupId,anchorgraphId_pointgraphId,graphId_label):

        # print len(nodeinfo)
        # print len(graphId_groupId)
        # print len(anchorgraphId_pointgraphId)
        # print len(graphId_label)

        allgraphId_nodegraphId = dict()

        for node,val in nodeinfo.items():

            allgraphId_nodegraphId.update({node:[val,]})

        for graphId,groupId in graphId_groupId.items():

            allgraphId_nodegraphId[graphId] = list()

            group_nodes = groupId_nodeId.get(groupId)

            if group_nodes:

                for node_id in group_nodes:

                    node_info = nodeinfo.get(node_id)

                    if node_info:

                        allgraphId_nodegraphId[graphId].append(node_info)

        if anchorgraphId_pointgraphId:

            for graphId,graphIds in anchorgraphId_pointgraphId.items():

                allgraphId_nodegraphId[graphId] = dict()

                # print graphId

                for _gid in graphIds:

                    _gid_node = allgraphId_nodegraphId.get(_gid)

                    if _gid_node:

                        allgraphId_nodegraphId[graphId].update({
                            _gid:_gid_node
                            })

        allgraphId_nodegraphId.update(graphId_label)

        return allgraphId_nodegraphId

def main():

    modelhelp = model_help.replace('&'*6,'WIKI_PATHWAY').replace('#'*6,'wiki_pathway')

    funcs = (downloadData,extractData,updateData,selectData,dbMap,wiki_pathway_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':

    main()
    # downloadData(redownload=True)
    # rawdir = '/home/user/project/dbproject/mydb_v1/wiki_pathway/dataraw/pathway_21320171116_180103114842/'
    # filepaths = [pjoin(rawdir,filename) for filename in listdir(rawdir)]
    # date = '180103114842'
    # extractData(filepaths,date)
    # man = dbMap('171205101037')
    # man.mapping()
