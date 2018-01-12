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
        this function is set to map all db ids to hgncSymbol
        '''
        hgncSymbol2allDBIDs = dict()

        for model in include_model:
            
            print '+'*50
            print model

            map_instance = modelMapClass.get(model)()

            hgncSymbl2dbID,db_key = map_instance.dbID2hgncSymbol()

            for symbol,dbIDs in hgncSymbl2dbID.items():

                if symbol not in hgncSymbol2allDBIDs:

                    hgncSymbol2allDBIDs[symbol] = dict()

                if model not in hgncSymbol2allDBIDs[symbol]:

                    hgncSymbol2allDBIDs[symbol][model] = dict()

                hgncSymbol2allDBIDs[symbol][model]['dbKey'] = db_key

                hgncSymbol2allDBIDs[symbol][model]['dbIDs'] = dbIDs

        print 'len(hgncSymbol2allDBIDs)',len(hgncSymbol2allDBIDs)

        with open('./hgncSymbol2allDBIDs.json','w') as wf:

            json.dump(hgncSymbol2allDBIDs,wf,indent=8)

        return hgncSymbol2allDBIDs

class geneFilter(object):
    """docstring for ClassName"""
    def __init__(self):

        super(geneFilter, self).__init__()

        conn = MongoClient('localhost',27017)

        mydb = conn.get_database('mydb_v1')

        mytopic = conn.get_database('mytopic_v1')

        col_names = mydb.collection_names()

        db_cols = dict()

        for col_name in col_names:

            col = mydb.get_collection(col_name)

            db_cols[col_name] = col

            # create index
            query = col_query.get(col_name)

            if query:
                index = dict.fromkeys(query.keys(),1)

                print index

                col.ensure_index(index.items())

        self.db_cols = db_cols

        self.mydb = mydb

        self.mytopic = mytopic

    def filterKeys(self,dic,savekeys):

        filter_dic = dict()

        for key in savekeys:

            val = dic.get(key)

            if not val and val != False:
                val = ''

            key = key.replace('&',' ').replace('*','.')

            filter_dic[key] = val

        return filter_dic

    def filterFiledAllDB(self):

        gene_col = self.mytopic.get_collection('gene')
        gene_col.drop()
        gene_col = self.mytopic.get_collection('gene')

        hgncSymbol2allDBIDs = json.load(open('/home/user/project/dbproject/mydb_v1/_topic/gene/hgncSymbol2allDBIDs.json'))
        
        hgnc_col =  self.db_cols.get('hgnc.gene')

        n = 0

        for sym,sym_it  in hgncSymbol2allDBIDs.items():
        # sym = 'AAAS'
        # sym_it = hgncSymbol2allDBIDs[sym]

            output = dict()
            output['symbol'] = sym

            n += 1
            print n,'gene topic  sym',sym

            sym_otherID = hgnc_col.find_one({'symbol':sym})
            sym_otherID.pop('_id')
            output['symbol_ids'] = sym_otherID

            for db,db_it in sym_it.items():

                output[db] = dict()
                dbkey = db_it.get('dbKey')
                dbids =  db_it.get('dbIDs')

                for dbid in dbids:

                    output[db][dbid] = dict()

                    col_names =  model_cols.get(db)

                    for colname  in col_names:

                        dbcol = colname.replace('.','*')

                        output[db][dbid][dbcol] = list()

                        col = self.db_cols.get(colname)

                        # create a new query object to not alter the value in col_query
                        query = copy.deepcopy(col_query.get(colname))
                        savekeys = copy.deepcopy(col_savekeys.get(colname))

                        query[dbkey] = dbid

                        if len(query) >= 2:

                            for key,val in query.items():

                                if not val:
                                    query[key] =sym_otherID.get(geneFiledConvetor.get(key))

                        docs = col.find(query)

                        for doc in docs:

                            doc = self.filterKeys(doc,savekeys)
                     
                            output[db][dbid][dbcol].append(doc)

            # with open('AAAS.json','w') as wf:
            #     json.dump(output,wf,indent=8)
            gene_col.insert(output)

            del output

class geneFormat(object):
    """docstring for ClassName"""
    def __init__(self):

        super(geneFormat, self).__init__()

        conn = MongoClient('localhost',27017)

        mytopic = conn.get_database('mytopic_v1')

        mydb,db_cols = initDB('mydb_v1')

        self.mytopic = mytopic

        self.db_cols = db_cols

    def format(self,step=1):

        format_dir = os.path.join('./','_format{}'.format(step))
        # format_dir = os.path.join('./','_format')

        if not os.path.exists(format_dir):

            os.mkdir(format_dir)

        gene_col = self.mytopic.get_collection('gene')

        process = {
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
        }

        docs = gene_col.find({})

        n= 0

        for doc in docs:

            output = dict()

            n += 1

            doc.pop('_id')

            symbol = doc.get('symbol')
            symbol_ids = doc.get('symbol_ids')

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

            savepath = os.path.join(format_dir,'{}_{}.json'.format(symbol,step))

            with open(savepath,'w') as wf:
                json.dump(output,wf,indent=8)

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
                            relations[s] = list()

                        if relation not in relations[s]:

                            if s ==1 :
                                relations[s].append(relation)
                                infront_relations.append(relation)
                            else:
                                if  relation not in infront_relations:
                                    relations[s].append(relation)
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
                            interactions[s] = list()

                        if interaction not in interactions[s]:

                            if s ==1 :
                                interactions[s].append(interaction)
                                infront_interactions.append(interaction)
                            else:
                                if  interaction not in infront_interactions:
                                    interactions[s].append(interaction)
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

    def ncbi_gene(self,symbol,symbol_ids,model_info,output):

        # if len(model_info) != 1:

        #     print 'a symbol have 2 or more entrez id !!!!!!!!!'

        for gene_id,dbcolinfos in model_info.items():

            for dbcol,infos in dbcolinfos.items():

                colname = dbcol.replace('*','.')

                if colname =='ncbi.gene.info':

                    basicinfo = infos[0] # a symbol only have one entrez id

                    if basicinfo :

                        if 'basicinfo' not in output:

                            output['basicinfo'] = dict()

                        output['basicinfo']['NCBI'] = basicinfo

                elif colname == 'ncbi.gene.expression':

                    expression = dict()

                    for i in infos:

                        project_desc = i.get('project_desc')

                        source_name = i.get('source_name')

                        exp_rpkm = i.get('exp_rpkm')

                        if project_desc not in expression:
                            expression[project_desc] = dict()

                        if source_name not in expression[project_desc]:
                            expression[project_desc][source_name] = list()

                        expression[project_desc][source_name].append(exp_rpkm)

                    for project_desc,it in expression.items():

                        for source_name,exp_rpkms in it.items():

                            # exp_rpkms_sum = reduce(lambda x,y:float(x) + float(y),exp_rpkms)
                            exp_rpkms_sum = sum([float(i) for i in exp_rpkms])

                            exp_rpkm_mean = round(float(exp_rpkms_sum)/len(exp_rpkms),2)

                            expression[project_desc][source_name] = exp_rpkm_mean

                    if expression :

                        if  'expression' not in output:
                        
                            output['expression'] = dict()

                        output['expression']['NCBI'] = expression

        return output

    def proteinAtlas(self,symbol,symbol_ids,model_info,output):

        # if len(model_info) != 1:

        #     print 'a symbol have 2 or more ensembl id !!!!!!!!!1'

        for gene_id,dbcolinfos in model_info.items():

            for dbcol,infos in dbcolinfos.items():

                colname = dbcol.replace('*','.')

                if colname =='proteinatlas.geneanno':

                    basicinfo = infos[0]
                    if basicinfo:

                        if 'basicinfo' not in output:

                            output['basicinfo'] = dict()

                        output['basicinfo']['PROTEINATLAS'] = basicinfo

        return output

    def go_gene(self,symbol,symbol_ids,model_info,output):

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

            # gene_id = str(path_gene['gene_id'])

            path.update(path_gene)
            #-----------------------------------------------------------------------------------------------------------------
            # add path relation info
            path_relation = dbinfos.get('kegg*pathway*relation')

            path['relation'] = path_relation

            paths.append(path)

        if 'pathway' not in output:

            output['pathway'] = dict()

        output['pathway']['KEGG'] = paths

        return output

    def reactom_pathway(self,symbol,symbol_ids,model_info,output):

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
            
            gene_id = str(path_gene['entrez_id'])

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
            
            gene_id = str(path_gene['entrez_id'])

            path.update(path_gene)
            #-----------------------------------------------------------------------------------------------------------------
            # add path interaction
            path_interaction = dbinfos.get('wiki*pathway*interaction')

            path['interaction'] = path_interaction

            paths.append(path)

        if 'pathway' not in output:

            output['pathway'] = dict()

        output['pathway']['WIKI'] = paths

        return output

    def disgenet_disease(self,symbol,symbol_ids,model_info,output):

        disease = list()

        for diseaseId,dbcolinfos in model_info.items():

            disgenet = dbcolinfos.get('disgenet*disgene*curated') # only have one  for a geneid

            disease.append(disgenet[0])

        if 'disease' not in output:

            output['disease'] = dict()

        output['disease']['DisGeNET'] = disease

        return output

    def cosmic_disease(self,symbol,symbol_ids,model_info,output):

        disease = list()

        for geneid,dbcolinfos in model_info.items():

            cosmics = dbcolinfos.get('cosmic*disgene') # only have one  for a geneid

            disease.append(cosmics[0])

        if 'CGC' not in output:

            output['CGC'] = dict()

        output['CGC']['COSMIC'] = disease

        return output

    def dgidb_drug(self,symbol,symbol_ids,model_info,output):

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

        regulation = list()

        for mirid,dbcolinfos in model_info.items():

            mirtarbase = dbcolinfos.get('mirtarbase*mirgene') # only have one  for a mirid

            regulation.append(mirtarbase[0])

        if 'regulation' not in output:

            output['regulation'] = dict()

        output['regulation']['MIRTARBASE'] = regulation

        return output

    def clinvar_variant(self,symbol,symbol_ids,model_info,output):

        variant = list()

        for alleid,dbcolinfos in model_info.items():

                infos = dbcolinfos.get('clinvar*variant')

                for i in infos:

                    i['AlleleID'] = alleid

                    if i not in variant:

                        variant.append(i)

        if 'variant' not in output:

            output['variant'] = dict()

        output['variant']['CLINVAR'] = variant

        return output

    def igsr_variant(self,symbol,symbol_ids,model_info,output):

        variant = list()

        for rs_id,dbcolinfos in model_info.items():

                igsr_varia  = dbcolinfos.get('igsr*variant')

                variant.append(igsr_varia[0])

        if 'variant' not in output:

            output['variant'] = dict()

        output['variant']['IGSR_1000GENOMES'] = variant

        return output

def main():

    # man = geneMap()
    # man.hgncSymbol2allDB()

    # man = geneFilter()
    # man.filterFiledAllDB()

    man = geneFormat()
    man.format()

if __name__ == '__main__':
    main()
    pass
    
    # hgncSymbol2allDBIDs = json.load(open('/home/user/project/dbproject/mydb_v1/_topic/gene/hgncSymbol2allDBIDs.json'))
    # hgncSymbol2igsrvariantID=  json.load(open('/home/user/project/dbproject/mydb_v1/_topic/gene/hgncSymbol2igsrvariantID.json'))
    # print 'len(hgncSymbol2allDBIDs)',len(hgncSymbol2allDBIDs)
    # print 'len(hgncSymbol2igsrvariantID)',len(hgncSymbol2igsrvariantID)

    # for sym,ids in hgncSymbol2igsrvariantID.items():

    #     if sym not in hgncSymbol2allDBIDs:
    #         hgncSymbol2allDBIDs[sym] = dict()
    #     hgncSymbol2allDBIDs[sym]['igsr_variant'] = dict()
    #     hgncSymbol2allDBIDs[sym]['igsr_variant']['dbKey'] = 'ID'
    #     hgncSymbol2allDBIDs[sym]['igsr_variant']['dbIDs'] = ids

    # print len(hgncSymbol2allDBIDs)
    # with open('/home/user/project/dbproject/mydb_v1/_topic/gene/hgncSymbol2allDBIDs.json','w') as wf:
    #     json.dump(hgncSymbol2allDBIDs,wf,indent=8)

    #----------------------------------------------------------------------------------------------------------------------------------
    # rawdir = '/home/user/project/dbproject/mydb_v1/_topic/gene/_format/'
    # fllepaths = [os.path.join(rawdir,filename) for filename in os.listdir(rawdir)]

    # for fillepath in fllepaths:

    #     f = json.load(open(fillepath))

    #     variant = f.get('clinvar_variant')

    #     symbol = f.get('symbol')
    #     if variant:

    #         for alleid,dbinfos in variant.items():

    #             infos = dbinfos.get('clinvar*variant')

    #             if len(infos) != 2:
    #                 print alleid,symbol
    #----------------------------------------------------------------------------------------------------------------------------------
    # db,db_cols = initDB('mydb_v1')

    # wiki_inter_col = db_cols.get('wiki.pathway.interaction')

    # docs = wiki_inter_col.find({})

    # xref_keys = list()

    # gene_xref_keys = list()

    # for doc in docs:

    #     group1_info = doc.get('group1_info')

    #     group2_info = doc.get('group2_info')

    #     if group1_info and group2_info:

    #         for info in [group1_info,group2_info]:

    #             if all([isinstance(i,dict) for i in info]):

    #                 for i in info:

    #                     xrefkey = i.get('xref',{}).keys()

    #                     xref_keys += xrefkey

    #                     if i.get('type') == 'GeneProduct':
                            
    #                         gene_xref_keys += xrefkey

    #             elif all([isinstance(i,list) for i in info]):

    #                 for j in info: # i is a group list

    #                     for i in j:

    #                         xrefkey = i.get('xref',{}).keys()

    #                         xref_keys += xrefkey

    #                         if i.get('type') == 'GeneProduct':
                            
    #                             gene_xref_keys += xrefkey

    # xref_keys = list(set(xref_keys))
    # gene_xref_keys = list(set(gene_xref_keys))

    # print xref_keys
    # print len(xref_keys)

    # print gene_xref_keys
    # print len(gene_xref_keys)
