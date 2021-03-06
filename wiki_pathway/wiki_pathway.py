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

__all__ = ['downloadData','extractData','updateData','selectData']

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
    '''
    if  not redownload:

        (choice,existwikiFile) = lookforExisted(wiki_pathway_raw,'pathway')

        if choice != 'y':
            return

    if redownload or not existwikiFile or  choice == 'y':

        process = parser(today)
        #--------------------------------------------------------------------------------------------------------------------

        # 1. get all urls and mt of raw files
        (down_urls,mt) = process.getMt()

        #--------------------------------------------------------------------------------------------------------------------
        # 2. download  raw files
        unzipdir = process.getAll(down_urls,mt,wiki_pathway_raw)
    
    #--------------------------------------------------------------------------------------------------------------------
    #  3. generate .log file in current  path
    if not os.path.exists(log_path):

        with open('./wiki_pathway.log','w') as wf:
            json.dump({
                'wiki_pathway':[(mt,today,model_name),]
                },wf,indent=8)

    print  'datadowload completed !'

    #--------------------------------------------------------------------------------------------------------------------
    # 4. generate .files file in database
    filepaths = [pjoin(unzipdir,filename) for filename in listdir(unzipdir)]

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
    rawdirname = psplit(psplit(filepaths[0])[0])[1].strip()

    fileversion = rawdirname.rsplit('_',1)[0].strip().rsplit('_',1)[1].strip()

    gpmlpaths = [path for path in filepaths if path.endswith('.gpml')]

    xmlpaths = [path for path in filepaths if path.endswith('.xml')]

    genepaths = [path for path in filepaths if path.endswith('.gmt')]
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 2. parser filepaths step by step
    process = parser(date)

    # # create wiki.pathway.info
    process.pathway_info(xmlpaths,gpmlpaths,fileversion)

    # # create wiki.pathway.gene
    process.pathway_gene(genepaths,fileversion)

    # # create wiki.pathway.entry
    process.pathway_entry(gpmlpaths,fileversion)

    # create wiki.pathway.interaction
    process.pathway_interaction(gpmlpaths,fileversion)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 3. bkup all collections
    _mongodb = pjoin(wiki_pathway_db,'pathway_{}'.format(date))

    createDir(_mongodb)

    colhead = 'wiki.pathway'

    bkup_allCols('mydb_v1',colhead,_mongodb)

    print 'extract an insert completed!'

    return (filepaths,date)

def updateData(insert=True):
    '''
    this function is set to update all file in log
    '''
    wiki_pathway_log = json.load(open(log_path))

    process = parser(today)
    #-----------------------------------------------------------------------------------------------------------------
    (dowload_url,mt) = process.getMt()

    if mt != wiki_pathway_log.get('wiki_pathway')[-1][0].strip():

        updated_rawdir = pjoin(wiki_pathway_raw,'pathway_{}_{}'.format(mt,today))

        createDir(updated_rawdir)

        filepaths,date  = downloadData(redownload = True)

        if insert:

            extractData(filepaths,date)

        wiki_pathway_log['wiki_pathway'].append((mt,today,model_name))

        with open(log_path,'w') as wf:

            json.dump(wiki_pathway_log,wf,indent=2)

        print  '{} \'s new edition is {} '.format('wiki_pathway',mt)

        return 'update successfully'

    else:

        print  '{} {} is the latest !'.format('wiki_pathway',mt)

        return 'new version is\'t detected'

def selectData(querykey = 'path_id',value='WP3879'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.get_database('mydb_v1')

    colnamehead = 'wiki.pathway'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)
    
class parser(object):
    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''
    def __init__(self, date):

        self.date = date

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

    def getMt(self):
        '''
        this function is set to get url's web page look for the current version 
        '''
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
        download_urls.append(wiki_pathway_info_url)
        download_urls.append(wiki_pathway_gene_url)
        #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

        return  (download_urls,mt)

    def getAll(self,urls,mt,rawdir):
        '''
        this function is set to download all raw file for  specified urls 
        args:
            urls -- the urls of download web page of files
            mt -- file's latest version
            rawdir -- the raw directoty to store download file
        '''
        pathinfo_url = [url for url in urls if url.endswith('.zip')][0]

        listpath_url = [url for url in urls if url.endswith('json')][0]

        pathgene_url = [url for url in urls if url.endswith('.gmt')][0]

        #---------------------------------------------------------------------------------------------------
        # 1. download gpml file
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
        # 2. download listpathway file

        savename = 'listpathway_{}_{}.xml'.format(mt,today)
        storefilepath = pjoin(unzipdir,savename)
        command = 'wget -O {} {}'.format(storefilepath,listpath_url)
        os.popen(command)
        #---------------------------------------------------------------------------------------------------
        # 3. download path gene  file
        filename = pathgene_url.rsplit('/',1)[1].strip().rsplit('.',1)[0].strip()
        savename = '{}_{}_{}.gmt'.format(filename,mt,today) 
        storefilepath = pjoin(unzipdir,savename)
        command = 'wget -O {} {}'.format(storefilepath,pathgene_url)
        os.popen(command)

        return unzipdir

    def pathway_info(self,xmlpaths,gpmlpaths,fileversion):
        '''
            this  function is to parse the wiki human pathway infos 
            1. get the id,name,organism,link
            2. get the catogory and description in comment
        '''
        print '+'*50
        info_colname = 'wiki.pathway.info'

        # before insert ,truncate collection
        delCol('mydb_v1',info_colname)

        info_col = self.db.get_collection(info_colname)

        info_col.ensure_index([('path_id',1),])

        info_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'wiki.pathway.files'})

        #------------------------------------------------------------------------------------------------------------------------------------------------
        # pathway.info in listpathway file
        # 1. get the id,name,organism,link
        filepath = xmlpaths[0] # just only one file

        file = open(filepath).read()
        
        jsonfile = parse(file) 
        
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
        
        process = self.pathway_gpml()

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
                comment_info = process.gpml_comment(comment)

            biopax = pathway.get('Biopax')
            if biopax:
                biopax_info = process.gpml_biopax(biopax)

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

    def pathway_gene(self,filepaths,fileversion): 
        '''
        this function is set parser pathway_gene 
        '''
        gene_colname = 'wiki.pathway.gene'

        # before insert ,truncate collection
        delCol('mydb_v1',gene_colname)

        gene_col = self.db.get_collection(gene_colname)

        gene_col.ensure_index([('path_id',1),('entrez_id',1)])
        gene_col.ensure_index([('path_id',1),])
        gene_col.ensure_index([('entrez_id',1),])

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

    def pathway_entry(self,filepaths,fileversion):
        '''
        this function is set parser pathway_entry 
        '''
        entry_colname = 'wiki.pathway.entry'

        # before insert ,truncate collection
        delCol('mydb_v1',entry_colname)

        entry_col = self.db.get_collection(entry_colname)

        entry_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'wiki.pathway.files'})

        process = self.pathway_gpml()

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
            (nodetype,nodeinfo,groupId_nodeId) = process.gpml_datanode(datanode)

            group = pathway.get('Group')
            graphId_groupId = process.gpml_group(group)

            label = pathway.get('Label')
            graphId_label = process.gpml_label(label)

            anchorgraphId_pointgraphId = {}

            allgraphId_nodegraphId = process.gpml_allgraphId_nodegraphId(nodeinfo,groupId_nodeId,graphId_groupId,anchorgraphId_pointgraphId,graphId_label)

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

    def pathway_interaction(self,filepaths,fileversion):
        '''
        this function is set parser pathway_interaction 
        '''
        interaction_colname = 'wiki.pathway.interaction'

        # before insert ,truncate collection
        delCol('mydb_v1',interaction_colname)

        interaction_col = self.db.get_collection(interaction_colname)

        interaction_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'wiki.pathway.files'})

        process = self.pathway_gpml()

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
            (nodetype,nodeinfo,groupId_nodeId) = process.gpml_datanode(datanode)

            group = pathway.get('Group')
            graphId_groupId = process.gpml_group(group)

            label = pathway.get('Label')
            graphId_label = process.gpml_label(label)

            # a pathway must have more than one interaction
            interaction = pathway.get('Interaction')
            anchorgraphId_pointgraphId = process.gpml_anchor(interaction)

            allgraphId_nodegraphId = process.gpml_allgraphId_nodegraphId(nodeinfo,groupId_nodeId,graphId_groupId,anchorgraphId_pointgraphId,graphId_label)   
            
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

                            adic = process.gpml_arrowhead(adic)
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

    class pathway_gpml(object):

        '''this function is set to parser gpml file and return a format content'''

        def gpml_comment(self,comment):

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

        def gpml_biopax(self,biopax):

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

            for graphId,info in allgraphId_nodegraphId.items():

                _info = list()
                if isinstance(info,list):

                    [_info.append(i) for i in info if i not in _info] 
                    allgraphId_nodegraphId[graphId] = _info

            return allgraphId_nodegraphId

class dbMap(object):
    '''
    this class is set to map wiki path id to other db
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
        this function is to create a mapping relation between wiki path id  with HGNC Symbol
        '''
        # because wiki gene id  is entrez id 
        entrez2symbol = self.process.entrezID2hgncSymbol()

        wiki_path_gene_col = self.db_cols.get('wiki.pathway.gene')

        wiki_path_gene_docs = wiki_path_gene_col.find({})

        output = dict()

        hgncSymbol2wikiPathID = output

        for doc in wiki_path_gene_docs:

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
            
        print 'hgncSymbol2wikiPathID',len(output)

        # with open('./hgncSymbol2wikiPathID.json','w') as wf:
        #     json.dump(output,wf,indent=8)

        return (hgncSymbol2wikiPathID,'path_id')

class dbFilter(object):

    '''this class is set to filter part field of data in collections  in mongodb '''

    def __init__(self, arg):
        super(dbFilter, self).__init__()
        self.arg = arg
        
def main():

    modelhelp = model_help.replace('&'*6,'WIKI_PATHWAY').replace('#'*6,'wiki_pathway')

    funcs = (downloadData,extractData,updateData,selectData,wiki_pathway_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()
