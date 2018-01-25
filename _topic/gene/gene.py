#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/1/9
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to create gene topic db based on sub model
import json
import copy
from gene_config import *
from gene_share import *
version = '1.0'

model_name = psplit(os.path.abspath(__file__))[1]

current_path = psplit(os.path.abspath(__file__))[0]


class geneMap(object):

    """docstring for geneMap"""

    def __init__(self):

        super(geneMap, self).__init__()

    def hgncSymbol2allDB(self):

        '''
        this function is set to map all db ids to hgncSymbol with dbID2hgncSymbol under every sub model
        '''
        output = dict()

        hgncSymbol2allDBIDs = output

        for model in include_model:
            
            print '+'*50
            print model

            map_instance = modelMapClass.get(model)()

            hgncSymbl2dbID,db_key = map_instance.dbID2hgncSymbol()

            for symbol,dbIDs in hgncSymbl2dbID.items():

                if symbol not in output:

                    output[symbol] = dict()

                if model not in output[symbol]:

                    output[symbol][model] = dict()

                output[symbol][model]['dbKey'] = db_key

                output[symbol][model]['dbIDs'] = dbIDs

        print 'len(hgncSymbol2allDBIDs)',len(output)

        with open('./hgncSymbol2allDBIDs.json','w') as wf:

            json.dump(output,wf,indent=8)

        return hgncSymbol2allDBIDs

class geneFilter(object):

    """'this class is set to filter fileds from sub model  to  satisfiy  the build of gene topic """
    def __init__(self,db_name,topic_dbname,topic_name):

        super(geneFilter, self).__init__()

        conn = MongoClient('localhost',27017)

        mydb = conn.get_database(db_name)

        mytopic = conn.get_database(topic_dbname)

        # get all col_names in mydb_v1
        col_names = mydb.collection_names()

        #  store col_name and it's  version
        db_version = dict()
        #  store col_name and it's  col api
        db_cols = dict()

        for col_name in col_names:

            col = mydb.get_collection(col_name)
            db_cols[col_name] = col

            col_version = col.find_one()
            col_version.pop('_id')
            db_version[col_name.replace('.','*')] = col_version

            # create index for every included model,
            query = col_query.get(col_name)
            if query:
                index = dict.fromkeys(query.keys(),1)
                col.ensure_index(index.items())

        self.db_cols = db_cols
        self.db_version = db_version
        self.mydb = mydb
        self.mytopic = mytopic
        self.topic_dbname = topic_dbname
        self.topic_name = topic_name

    def filterKeys(self,dic,savekeys):

        '''
        this function is set to filter field of  a document in in col  according customize savekeys
        '''
        filter_dic = dict()

        for key in savekeys:

            val = dic.get(key)

            if not val and val != False:
                val = ''

            # replace ' ' with & , * with . in key 
            key = key.replace('&',' ').replace('*','.')

            filter_dic[key] = val

        return filter_dic

    def filterFiledAllDB(self):

        '''
        this function is set to filter filed  of all docs in diferent col in turn
        '''
        # create a col to store filted doc 
        gene_col = self.mytopic.get_collection(self.topic_name)

        # beforea create ,del old version
        gene_col.drop()
        gene_col = self.mytopic.get_collection(self.topic_name)

        # insert  all cols version as the gene topic db version
        gene_col.insert(self.db_version)

        # get the relation symbol with all dbs
        process = geneMap()
        hgncSymbol2allDBIDs = process.hgncSymbol2allDB()
        # hgncSymbol2allDBIDs = json.load(open('/home/user/project/dbproject/mydb_v1/_topic/gene/_dbID2hgncSymbol/hgncSymbol2allDBIDs.json'))
        
        hgnc_col =  self.db_cols.get('hgnc.gene')

        n = 0
        for sym,sym_it  in hgncSymbol2allDBIDs.items():

            n += 1
            print n,'gene topic  sym',sym

            # create a dict to store a symbol's content
            output = dict()
            #--------------------------------------------store symbol --------------------------------------------------------------------------------
            output['symbol'] = sym

            #---------------------------------------------store other db id of symbol--------------------------------------------------------------
            sym_otherID = hgnc_col.find_one({'symbol':sym})
            sym_otherID.pop('_id')
            output['symbol_ids'] = sym_otherID

            #---------------------------------------------extract content of symbol in col and subcols--------------------------------------------------------------
            for db,db_it in sym_it.items():

                # store according to dbname.dbid.colname like{symbol:TP53,ncbi_gene:{gene_id1:{ncbi*gene*info:[],ncbi*gene*pubmed:[]......},gene_id2:{}}}
                output[db] = dict()
                dbkey = db_it.get('dbKey')
                dbids =  db_it.get('dbIDs')

                for dbid in dbids:

                    output[db][dbid] = dict()

                    # get all sub col of a db like go:[go.info,go.geneanno]
                    col_names =  model_cols.get(db)

                    for colname  in col_names:

                        # because mongodb can't save a key thant string have .
                        dbcol = colname.replace('.','*')
                        output[db][dbid][dbcol] = list()

                        col = self.db_cols.get(colname)

                        # create a new query object to not alter the value in col_query
                        query = copy.deepcopy(col_query.get(colname))
                        savekeys = copy.deepcopy(col_savekeys.get(colname))

                        # create a query dict , because some sub col must select  the main key with GenID
                        query[dbkey] = dbid

                        if len(query) >= 2:

                            for key,val in query.items():

                                if not val:
                                    query[key] =sym_otherID.get(geneFiledConvetor.get(key))

                        docs = col.find(query)

                        for doc in docs:

                            doc = self.filterKeys(doc,savekeys)
                     
                            output[db][dbid][dbcol].append(doc)

            gene_col.insert(output)

            del output

        return (self.topic_dbname,self.topic_name)

class geneFormat(object):

    """this class is set to standard symbol content after  geneFilter,to generate an output formated file """

    def __init__(self,db_name,topic_dbname,topic_name):

        super(geneFormat, self).__init__()

        conn = MongoClient('localhost',27017)

        mytopic = conn.get_database(topic_dbname)

        mydb,db_cols = initDB(db_name)

        self.mytopic = mytopic

        self.db_cols = db_cols

        self.topic_name = topic_name

    def format(self,step=1):

        format_col = self.mytopic.get_collection('{}.format'.format(self.topic_name))
        format_col.drop()
        format_col = self.mytopic.get_collection('{}.format'.format(self.topic_name))

        # format_dir = os.path.join('./','_{}_format_step{}'.format(self.topic_name,step))

        # if not os.path.exists(format_dir):

        #     os.mkdir(format_dir)

        gene_col = self.mytopic.get_collection(self.topic_name)

        process = {
        'hgnc_gene':self.hgnc_gene,
        'ncbi_gene':self.ncbi_gene,
        'proteinAtlas':self.proteinAtlas,
        'go_gene':self.go_gene,
        'kegg_pathway':self.kegg_pathway,
        'wiki_pathway':self.wiki_pathway,
        'reactom_pathway':self.reactom_pathway,
        'disgenet_disease':self.disgenet_disease,
        'cosmic_disease':self.cosmic_disease,
        'dgidb_drug':self.dgidb_drug,
        'clinvar_variant':self.clinvar_variant,
        'igsr_variant':self.igsr_variant,
        'hpo_phenotype':self.hpo_phenotype
        }

        docs = gene_col.find({})

        n= 0

        for doc in docs:

            doc.pop('_id')

            if n ==  0:
                format_col.insert(doc) # insert col version 
                n += 1
                continue

            output = dict()

            n += 1
            symbol = doc.get('symbol')
            symbol_ids = doc.get('symbol_ids')

            output['symbol'] = symbol
            output['symbol_ids'] = symbol_ids

            print '+'*50
            print n,symbol
          
            for model,model_info in doc.items():

                func = process.get(model)

                if func:

                   output = func(symbol,symbol_ids,model_info,output)

            #  filter kegg relation and wiki interaction
            # get gene id
            if step >= 1:

                output = self.format_kegg_step(symbol_ids,output,step)
                output = self.format_wiki_step(symbol_ids,output,step)

            # savepath = os.path.join(format_dir,'{}.json'.format(symbol))
            # with open(savepath,'w') as wf:
            #     json.dump(output,wf,indent=8)

            format_col.insert(output)

    def format_kegg_step(self,symbol_ids,output,step):

        kegg_paths = output.get('pathway',{}).get('KEGG',{})

        if not kegg_paths:
            return output
        
        new_kegg_path = list()

        for kegg_path in kegg_paths:

            kegg_relation = kegg_path.get('relation')

            if not kegg_relation:

                new_kegg_path.append(kegg_path)
                continue

            path_id = kegg_path.get('path_id')

            gene_id = symbol_ids.get('entrez_id')

            relations = dict()
            infront_geneids = list()
            infront_relations = list()

            for s in range(step+1)[1:]: # step =3 [1,2,3]

                stepnumber = 'step{}'.format(s)

                if s == 1:

                    gene_ids = [gene_id,] # find the relate reaction with gene_ids
                    infront_geneids.append('hsa:{}'.format(gene_id))

                next_gene_ids = list()

                # print 's ,path_id,gene_ids,next_gene_ids',s,path_id,gene_ids,next_gene_ids

                for relation in kegg_relation:

                    save = False # ctrol if this relation is needed

                    entry1_name = relation['entry1']['entry_name'].strip()
                    entry2_name = relation['entry2']['entry_name'].strip()

                    if s == 1:# when s == 1  gene_id is number like 597 .if s >1 gene_id is format like hsa:5970|hsa:4790
                        name1 = [i.replace('|','').strip() for i in entry1_name.split('hsa:') ]
                        name2 = [i.replace('|','').strip() for i in entry2_name.split('hsa:') ]

                        for gene_id in gene_ids:

                            if gene_id in name1:
                                save = True
                                next_gene_ids.append(entry2_name)

                            elif gene_id in name2:
                                save = True
                                next_gene_ids.append(entry1_name)
                    else :

                        for gene_id in gene_ids:

                            if gene_id == entry1_name:
                                save = True
                                next_gene_ids.append(entry2_name)
                            elif gene_id == entry2_name:
                                save = True
                                next_gene_ids.append(entry1_name)

                    if save:
                        if s not in relations:
                            relations[stepnumber] = list()

                        if relation not in relations[stepnumber]:

                            if s ==1 :
                                relations[stepnumber].append(relation)
                                infront_relations.append(relation)
                            else:
                                if  relation not in infront_relations:
                                    relations[stepnumber].append(relation)
                                    infront_relations.append(relation)

                gene_ids = list(set(next_gene_ids) - set(infront_geneids))

                infront_geneids += next_gene_ids

                # print '===',gene_ids

                if not gene_ids:
                    break

            kegg_path['relation'] = relations

            new_kegg_path.append(kegg_path)

        output['pathway']['KEGG'] = new_kegg_path

        return output

    def format_wiki_step(self,symbol_ids,output,step):

        wiki_paths = output.get('pathway',{}).get('WIKI',{})

        if not wiki_paths:
            return output
        
        new_wiki_path = list()

        for wiki_path in wiki_paths:

            wiki_interaction = wiki_path.get('interaction')

            if not wiki_interaction:

                new_wiki_path.append(wiki_path)

                continue

            path_id = wiki_path.get('path_id')
            interactions = dict()

            infront_groupinfo = list()
            infront_interactions = list()

            for s in range(step+1)[1:]: # step =3 [1,2,3]

                stepnumber = 'step{}'.format(s)

                if s==1:
                    group_infos  = list()

                next_group_infos = list()

                for interaction in wiki_interaction:

                    save = False # ctrol if this interaction is needed

                    group1_info = interaction.get('group1_info')

                    group2_info = interaction.get('group2_info')

                    if s == 1:

                        for index,info in enumerate([group1_info,group2_info]):

                            if all([isinstance(i,dict) for i in info]):

                                for i in info:

                                    xref = i.get('xref',{})

                                    for ref,val in xref.items():

                                        if ref in wiki_xrefdb_field and symbol_ids.get(wiki_xrefdb_field[ref]) == val.strip():

                                            save = True


                                            if index == 0:
                                                infront_groupinfo.append(group1_info)
                                                next_group_infos.append(group2_info)
                                            else:
                                                infront_groupinfo.append(group2_info)
                                                next_group_infos.append(group1_info)

                            elif all([isinstance(i,list) for i in info]):

                                for j in info: # i is a group list

                                    for i in j:

                                        xref = i.get('xref',{})

                                        for ref,val in xref.items():

                                            if ref in wiki_xrefdb_field and symbol_ids.get(wiki_xrefdb_field[ref]) == val.strip():

                                                save = True


                                                if index == 0:
                                                    infront_groupinfo.append(group1_info)
                                                    next_group_infos.append(group2_info)
                                                else:
                                                    infront_groupinfo.append(group2_info)
                                                    next_group_infos.append(group1_info)

                    else:
                        for group_info in group_infos :

                            if group_info == group1_info:

                                save = True
                                next_group_infos.append(group2_info)

                            elif group_info == group2_info:
                                save = True
                                next_group_infos.append(group1_info)

                    if save:
                        if s not in interactions:
                            interactions[stepnumber] = list()

                        if interaction not in interactions[stepnumber]:

                            if s ==1 :
                                interactions[stepnumber].append(interaction)
                                infront_interactions.append(interaction)
                            else:
                                if  interaction not in infront_interactions:
                                    interactions[stepnumber].append(interaction)
                                    infront_interactions.append(interaction)

                group_infos = [ i for i in next_group_infos if i not in infront_groupinfo]
                # group_infos = list()

                dedup_group_infos = list()

                for i in group_infos:
                    if i not in dedup_group_infos:
                        dedup_group_infos.append(i)

                group_infos = dedup_group_infos

                infront_groupinfo += next_group_infos
                # print '===',group_infos
                # print 
                # print 's ,path_id,len(group_infos)',s ,path_id,len(group_infos)
                # print '*'*100

                if not group_infos:
                    break

            wiki_path['interaction'] = interactions

            new_wiki_path.append(wiki_path)

        output['pathway']['WIKI'] = new_wiki_path

        return output        

    def hgnc_gene(self,symbol,symbol_ids,model_info,output):

        '''
        this function is set to format hgnc_gene in basicinfo {symbol:TP53,basicinfo:{HGNC:{}}}
        '''
        for hgnc_id,dbcolinfos in model_info.items():

            infos = dbcolinfos.get('hgnc*gene')

            basicinfo = infos[0] # a symble just  to a hgnc_id

            if 'basicinfo' not in output:

                output['basicinfo'] = dict()

            output['basicinfo']['HGNC'] = basicinfo

        return output

    def ncbi_gene(self,symbol,symbol_ids,model_info,output):
        '''
        this function is set to format ncbi_gene in basicinfo {symbol:TP53,basicinfo:{NCBI:{}}}
        '''
        #-------------------------------------------basicinfo NCBI---------------------------------------------------------------------------
        for gene_id,dbcolinfos in model_info.items():

            ncbi_gene_info = dbcolinfos.get('ncbi*gene*info')

            basicinfo = ncbi_gene_info[0] # a symbol only have one entrez id

            if basicinfo :

                if 'basicinfo' not in output:

                    output['basicinfo'] = dict()

                output['basicinfo']['NCBI'] = basicinfo

            #-------------------------------------------expression NCBI---------------------------------------------------------------------------
            ncbi_gene_expression = dbcolinfos.get('ncbi*gene*expression')

            expression = dict()

            for i in ncbi_gene_expression:

                project_desc = i.get('project_desc')

                source_name = i.get('source_name')

                exp_rpkm = i.get('exp_rpkm')

                if project_desc not in expression:
                    expression[project_desc] = dict()

                if source_name not in expression[project_desc]:
                    expression[project_desc][source_name] = list()

                expression[project_desc][source_name].append(exp_rpkm)

            # get the mean of exp_rpkm of source_name in a project
            for project_desc,it in expression.items():

                for source_name,exp_rpkms in it.items():

                    exp_rpkms_sum = sum([float(i) for i in exp_rpkms])

                    exp_rpkm_mean = round(float(exp_rpkms_sum)/len(exp_rpkms),2)

                    expression[project_desc][source_name] = exp_rpkm_mean

            if expression :

                if  'expression' not in output:
                
                    output['expression'] = dict()

                output['expression']['NCBI'] = expression

        return output

    def proteinAtlas(self,symbol,symbol_ids,model_info,output):
        '''
        this function is set to format proteinAtlas in basicinfo {symbol:TP53,basicinfo:{PROTEINATLAS:{}}}
        '''
        for gene_id,dbcolinfos in model_info.items():

            prot_geneanno = dbcolinfos.get('proteinatlas*geneanno')

            basicinfo = prot_geneanno[0] #  a symbol just have one ensembl id in proteinAtlas

        if basicinfo:

            if 'basicinfo' not in output:

                output['basicinfo'] = dict()

            output['basicinfo']['PROTEINATLAS'] = basicinfo

        return output

    def go_gene(self,symbol,symbol_ids,model_info,output):
        '''
        this function is set to format go_gene in function {symbol:TP53,function:{GoOntology:{}}}
        '''
        function = dict()

        for go_id,dbinfos in model_info.items():

            function[go_id] = dict()

           #-----------------------------------------------------------------------------------------------------------------
            # add go info  from go geneanno
            go_info = dbinfos.get('go*info')[0] #only have one

            go_info.pop('GO ID')

            function[go_id].update(go_info)

            go_anno = dbinfos.get('go*geneanno')

            #-----------------------------------------------------------------------------------------------------------------
            # add evidence from go geneanno
            evidence = dict()

            for anno in go_anno:

                anno_pro = anno.pop('Annotation Properties')

                if anno_pro not in evidence:

                    evidence[anno_pro] = dict()
                    evidence[anno_pro]['db_ref'] = list()
                    evidence[anno_pro]['Annotation Properties implication'] = anno.pop('Annotation Properties implication')

                for key in ['DB_Object_ID','GO ID','Annotation Properties implication']:
                    if key in anno:
                        anno.pop(key)

                evidence[anno_pro]['db_ref'].append(anno)

            for annp_pro,it in evidence.items():

                db_ref = it.get('db_ref',[])

                dedup_db_ref = list()

                [dedup_db_ref.append(i) for i in db_ref if i not in dedup_db_ref]

                evidence[annp_pro]['db_ref'] = dedup_db_ref

            function[go_id]['evidence'] = evidence
            #-----------------------------------------------------------------------------------------------------------------

        if 'function'  not in output:
            output['function'] = dict()

        output['function']['GeneOntology'] = function

        return output

    def kegg_pathway(self,symbol,symbol_ids,model_info,output):
        '''
        this function is set to format kegg_pathway in pathway {symbol:TP53,pathway:{KEGG:{}}}
        '''
        paths = list()

        for path_id,dbinfos in model_info.items():

            path = dict()
            #-----------------------------------------------------------------------------------------------------------------
            # add path basic info
            path_info = dbinfos.get('kegg*pathway*info')[0] #only have one

            path.update(path_info)
            #-----------------------------------------------------------------------------------------------------------------
            # add path gene info
            path_gene = dbinfos.get('kegg*pathway*gene')[0] #only have one

            path.update(path_gene)
            #-----------------------------------------------------------------------------------------------------------------
            # add path relation info
            path['relation'] = dbinfos.get('kegg*pathway*relation')

            paths.append(path)

        if 'pathway' not in output:

            output['pathway'] = dict()

        output['pathway']['KEGG'] = paths

        return output

    def reactom_pathway(self,symbol,symbol_ids,model_info,output):
        '''
        this function is set to format reactom_pathway in pathway {symbol:TP53,pathway:{REACTOM:{}}}
        '''
        paths = list()

        for path_id,dbinfos in model_info.items():

            path = dict()
            #-----------------------------------------------------------------------------------------------------------------
            # add path basic info
            path_info = dbinfos.get('reactom*pathway*info')[0] #only have one

            path.update(path_info)
            #-----------------------------------------------------------------------------------------------------------------
            # add path gene info
            path_gene = dbinfos.get('reactom*pathway*gene')[0] #only have one
            
            path.update(path_gene)
            #-----------------------------------------------------------------------------------------------------------------
            # add path event info
            path_event = dbinfos.get('reactom*pathway*event')

            # find symbol's dbId in reactom entry
            reactom_entry_col = self.db_cols.get('reactom.pathway.entry')

            docs = reactom_entry_col.find({'entry_name':symbol})

            if docs:
                symbol_dbId = ''
                for doc in docs:
                    symbol_dbId = doc.get('dbId','')
                    if symbol_dbId:
                        path['symbol_dbId'] = symbol_dbId
                        break

                if symbol_dbId:

                    # filter event that keys  ['inputs','outputs','activators','catalysts','inhibitors'] contain symbol_dbId
                    for event in path_event:

                        event_nodes = list()
                        for key in ['inputs','outputs','activators','catalysts','inhibitors']:
                            val = event.get(key,[])
                            event_nodes += val

                        if symbol_dbId in event_nodes:

                            if 'event' not in path:

                                path['event'] = list()

                            path['event'].append(event)

            else:
                print 'reactom.pathway.gene entrez id %s \'s symbol not in entry names'

            paths.append(path)

        if 'pathway' not in output:

            output['pathway'] = dict()

        output['pathway']['REACTOM'] = paths

        return output

    def wiki_pathway(self,symbol,symbol_ids,model_info,output):
        '''
        this function is set to format wiki_pathway in pathway {symbol:TP53,pathway:{WIKI:{}}}
        '''
        paths = list()

        for path_id,dbinfos in model_info.items():

            path = dict()
            #-----------------------------------------------------------------------------------------------------------------
            # add path basic info
            path_info = dbinfos.get('wiki*pathway*info')[0] #only have one

            path.update(path_info)
            #-----------------------------------------------------------------------------------------------------------------
            # add path gene info
            path_gene = dbinfos.get('wiki*pathway*gene')[0] #only have one

            path.update(path_gene)
            #-----------------------------------------------------------------------------------------------------------------
            # add path interaction
            path['interaction'] = dbinfos.get('wiki*pathway*interaction')

            paths.append(path)

        if 'pathway' not in output:

            output['pathway'] = dict()

        output['pathway']['WIKI'] = paths

        return output

    def disgenet_disease(self,symbol,symbol_ids,model_info,output):

        '''
        this function is set to format disgenet_disease in disease {symbol:TP53,disease:{DISGENET:[]}}
        '''
        diseases = list()

        for diseaseId,dbcolinfos in model_info.items():

            disgenet = dbcolinfos.get('disgenet*disgene*curated') # only have one  for a geneid  with a diseaseId

            diseases.append(disgenet[0])

        if 'disease' not in output:

            output['disease'] = dict()

        output['disease']['DisGeNET'] = diseases

        return output

    def cosmic_disease(self,symbol,symbol_ids,model_info,output):

        '''
        this function is set to format cosmic_disease in disease {symbol:TP53,CGC:{COSMIC:[]}}
        '''
        disease = list()

        for geneid,dbcolinfos in model_info.items():

            cosmics = dbcolinfos.get('cosmic*disgene') # only have one  for a geneid

            disease.append(cosmics[0])

        if 'CGC' not in output:

            output['CGC'] = dict()

        output['CGC']['COSMIC'] = disease

        return output

    def dgidb_drug(self,symbol,symbol_ids,model_info,output):

        '''
        this function is set to format dgidb_drug in drug {symbol:TP53,drug:{DGIDB:[]}}
        '''
        drug = list()

        for drug_id,dbcolinfos in model_info.items():

            # drug_info = dbcolinfos.get('dgidb*drug*info')

            drug_gene = dbcolinfos.get('dgidb*drug*gene')[0] # only have one

            drug_name = drug_gene.get('drug_name')

            if drug_name:
                drug_link = 'http://www.dgidb.org/drugs/' + drug_name
            else:
                drug_link = ''

            chembl_id = drug_gene.get('chembl_id')

            if chembl_id:
                chembl_id_link = 'https://www.ebi.ac.uk/chembl/compound/inspect/' + chembl_id
            else:
                chembl_id_link = ''

            drug_gene['chembl_id_link'] = chembl_id_link

            drug.append(drug_gene)

        if 'drug' not in output:

            output['drug'] = dict()

        output['drug']['DGIDB'] = drug

        return output   

    def miRTarBase(self,symbol,symbol_ids,model_info,output):

        '''
        this function is set to format miRTarBase in regulation {symbol:TP53,regulation:{miRTarBase:[]}}
        '''
        regulations = list()

        for mirid,dbcolinfos in model_info.items():

            mirtarbase = dbcolinfos.get('mirtarbase*mirgene') # only have one  for a mirid

            regulations.append(mirtarbase[0])

        if 'regulation' not in output:

            output['regulation'] = dict()

        output['regulation']['MIRTARBASE'] = regulations

        return output

    def clinvar_variant(self,symbol,symbol_ids,model_info,output):
        '''
        this function is set to format clinvar_variant in variant {symbol:TP53,variant:{CLINVAR:[]}}
        '''
        variants = list()

        for alleid,dbcolinfos in model_info.items():

                infos = dbcolinfos.get('clinvar*variant')

                for i in infos:

                    i['AlleleID'] = alleid

                    if i not in variants:

                        variants.append(i)

        if 'variant' not in output:

            output['variant'] = dict()

        output['variant']['CLINVAR'] = variants

        return output

    def igsr_variant(self,symbol,symbol_ids,model_info,output):

        '''
        this function is set to format igsr_variant in variant {symbol:TP53,variant:{1000_GENEMOES:[]}}
        '''
        variants = list()

        for rs_id,dbcolinfos in model_info.items():

                igsr_varia  = dbcolinfos.get('igsr*variant')

                variants.append(igsr_varia[0])

        if 'variant' not in output:

            output['variant'] = dict()

        output['variant']['IGSR_1000GENOMES'] = variants

        return output

    def hpo_phenotype(self,symbol,symbol_ids,model_info,output):
        
        '''
        this function is set to format hpo_phenotype in phenotype {symbol:TP53,phenotype:{HPO:[]}}
        '''
        phenotypes = list()

        for hpo_id,dbcolinfos in model_info.items():

            hpo_info = dbcolinfos.get('hpo*phenotype*info') # a hpo_id 2 a hpo_info record

            hpo_gene = dbcolinfos.get('hpo*phenotype*gene') # a hpo_id and a gene_id 2a hpo_gene record

            hpo_info[0].update(hpo_gene[0])

            if hpo_info not in phenotypes:

                phenotypes.append(hpo_info)

        if 'phenotype' not in output:

            output['phenotype'] = dict()

        output['phenotype']['HPO'] = phenotypes

        return output

def main(test=False):

    if test:
        # man = geneMap()
        # man.hgncSymbol2allDB()

        # man = geneFilter('mydb_v1','mytopic_v1','gene_test')
        # man.filterFiledAllDB()

        man = geneFormat('mydb_v1','mytopic_v1','gene')
        man.format()

if __name__ == '__main__':

    main(test=False)
    
    # conn = MongoClient('localhost',27017)

    # # db = conn.get_database('mydb_v1')
    # db = conn.get_database('mytopic_v1')

    # col = db.get_collection('gene')
    # # col = db.get_collection('reactom.pathway.graph')

    # docs = col.find({})

    # f = open('./_mongodb/gene.tsv','w')
    # # f = open('./_mongodb/reactom.pathway.graph.json.tsv','w')

    # n = 0

    # for doc in docs:
        
    #     doc.pop('_id')
    #     # doc = json.dumps(doc)
    #     # f.write(doc+ '\n')

    #     if n == 0:
    #         doc = json.dumps(doc)
    #         f.write('version' + '\t' +doc + '\n' )
    #     else:
    #         symbol = doc.pop('symbol')
    #         doc.pop('symbol_ids')
    #         doc = json.dumps(doc)
    #         f.write(symbol + '\t' +doc + '\n' )

    #     n += 1
    #     print 'gene to tsv file,doc ',n
    #     # print 'gene.format to tsv file,doc ',n
    #     # print 'reactom.pathway.graph,doc ',n

    #     f.flush()