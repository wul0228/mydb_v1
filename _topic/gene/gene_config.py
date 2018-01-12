#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/1/9
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to create gene topic db based on sub model
import os
import sys
sys.path.append('../../')
sys.setdefaultencoding = ('utf-8')

models =  [name for name in os.listdir('../../') if  not any([name.endswith(x) for x in ['.py','.pyc','.readme','.git']]) and not name.startswith('_')]

for model in models:

    import_model = "from {} import  {}".format(model,model)

    exec(import_model)
#----------------------------------------------------------------------------------------------------------
psplit = os.path.split

lisdir = os.listdir
#----------------------------------------------------------------------------------------------------------
# gene topic include all models  
include_model = [
'ncbi_gene','proteinAtlas','go_gene',
'kegg_pathway','reactom_pathway','wiki_pathway',
'disgenet_disease','cosmic_disease',
'dgidb_drug','miRTarBase',
'clinvar_variant','igsr_variant'
]

# key is model name .val is dbMap class in under model.py
modelMapClass = {
'ncbi_gene':ncbi_gene.dbMap,
'go_gene':go_gene.dbMap,
'proteinAtlas':proteinAtlas.dbMap,
'kegg_pathway':kegg_pathway.dbMap,
'reactom_pathway':reactom_pathway.dbMap,
'wiki_pathway':wiki_pathway.dbMap,
'disgenet_disease':disgenet_disease.dbMap,
'cosmic_disease':cosmic_disease.dbMap,
'dgidb_drug':dgidb_drug.dbMap,
'miRTarBase':miRTarBase.dbMap,
'clinvar_variant':clinvar_variant.dbMap,
'igsr_variant':igsr_variant.dbMap,
# 'hpo_phenotypic':hpo_phenotypic.dbMap,
# 'hgnc_gene':hgnc_gene.dbMap,
}

# map function in dbMap for gene_topic build
modelMapFun = 'dbID2hgncSymbol'

# relate cols for every model in gene_topic
model_cols = {
    'ncbi_gene':['ncbi.gene.info','ncbi.gene.expression'],
    'proteinAtlas':['proteinatlas.geneanno',],
    'go_gene':['go.info','go.geneanno',],
    'kegg_pathway':['kegg.pathway.info','kegg.pathway.gene','kegg.pathway.relation'],
    'reactom_pathway':['reactom.pathway.info','reactom.pathway.gene','reactom.pathway.event','reactom.pathway.interaction'],
    'wiki_pathway':['wiki.pathway.info','wiki.pathway.gene','wiki.pathway.interaction'],
    'disgenet_disease':['disgenet.disgene.curated',],
    'cosmic_disease':['cosmic.disgene',],
    'dgidb_drug':['dgidb.drug.info','dgidb.drug.gene'],
    'miRTarBase':['mirtarbase.mirgene'],
    'clinvar_variant':['clinvar.variant'],
    'igsr_variant':['igsr.variant'],
}

# col keys in model for gene_topic
col_savekeys = {
    'ncbi.gene.info':['GeneID','chromosome' ,'type_of_gene' ,'description','Synonyms' ,'dbXrefs' ,'summary'],
    'ncbi.gene.expression':['GeneID','exp_rpkm','source_name','project_desc'],
    'proteinatlas.geneanno':['Ensembl','Protein&class','Subcellular&location','Prognostic&p-value','Prognostic&link'],
    'go.geneanno':['DB_Object_ID','GO ID','Annotation Properties','Annotation Properties implication','DB:Reference','DB:Reference Link'],
    'go.info':['GO ID','name','go id link','namespace','def'],
    'kegg.pathway.info':['path_id','path_name','path_link','path_org','path_image','path_map_link','path_class','path_subclass'],
    'kegg.pathway.gene':['gene_id','path_id'],
    'kegg.pathway.relation':['path_id','entry1','entry2','relation_type','relation_subtype'],
    'reactom.pathway.info':['path_id','path_name','path_org','path_summation','path_link','path_image'],
    'reactom.pathway.gene':['path_id','entrez_id','evidence'],
    'reactom.pathway.event':['path_id','event_id','event_link','displayName','schemaClass','preceding','following','inputs','outputs','activators','catalysts','inhibitors','event_pmid'],
    'reactom.pathway.interaction':['Gene1','Gene2','Annotation','Direction','Score'],
    'wiki.pathway.info':['path_id','path_name','path_org','path_link','WikiPathways-description','WikiPathways-category','openControlledVocabulary','PublicationXref'],
    'wiki.pathway.gene':['path_id','entrez_id'],
    'wiki.pathway.interaction':['path_id','group1','group1_info','group2','group2_info','effect_type'],
    'disgenet.disgene.curated':['diseaseId','diseaseName','diseaseId link','associationType','associationType implication','sentence','pmid'],
    'cosmic.disgene':['Entrez GeneId','Somatic','Germline','Tumour Types(Somatic)','Tumour Types(Germline)','Cancer Syndrome','Tissue Type','Molecular Genetics','Role in Cancer','Mutation Types','Translocation Partner','Other Germline Mut','Other Syndrome','Hallmark','HallmarkInfo','categories'],
    'dgidb.drug.info':['drug_name','drug_link','chembl_id','immunotherapy','chembl_id_link','alias','anti_neoplastic','fda_approved'],
    'dgidb.drug.gene':['entrez_id','drug_name','chembl_id','sources','publications','interaction_types'],
    'mirtarbase.mirgene':['Target Gene (Entrez ID)','miRNA','Species (Target Gene)','miRTarBase ID','References (PMID)','Experiments','Support Type','Target Gene'],
    'clinvar.variant':['GeneID','Assembly','Chromosome','Start' ,'Stop', 'ReferenceAllele','AlternateAllele','Type','RS# (dbSNP)','RS_link','nsv/esv (dbVar)','dbVar_link','OriginSimple','PhenotypeList','ClinicalSignificance','ReviewStatus'],
    'igsr.variant':['ID','AF','EAS_AF','AMR_AF','AFR_AF','EUR_AF','SAS_AF'],
}
col_query = {
    'ncbi.gene.info':{'GeneID':''},
    'ncbi.gene.expression':{'GeneID':''},
    'proteinatlas.geneanno':{'Ensembl':''},
    'go.info':{'GO ID':''},
    'go.geneanno':{'GO ID':'','DB_Object_ID':''},
    'kegg.pathway.info':{'path_id':'',},
    'kegg.pathway.gene':{'path_id':'','gene_id':'',},
    'kegg.pathway.relation':{'path_id':''},
     'reactom.pathway.info':{'path_id':''},
     'reactom.pathway.gene':{'path_id':'','entrez_id':''},
     'reactom.pathway.event':{'path_id':''},
     'reactom.pathway.interaction':{'path_id':''},
     'wiki.pathway.info':{'path_id':''},
     'wiki.pathway.gene':{'path_id':'','entrez_id':''},
     'wiki.pathway.interaction':{'path_id':''},
     'disgenet.disgene.curated':{'diseaseId':'','geneId':''},
     'cosmic.disgene':{'Entrez GeneId':''},
     'dgidb.drug.info':{'chembl_id':''},
     'dgidb.drug.gene':{'chembl_id':'','entrez_id':''},
     'mirtarbase.mirgene':{'miRTarBase ID':''},
     'clinvar.variant':{'AlleleID':'','HGNC_ID':''},
     'igsr.variant':{'ID':''},
}

geneFiledConvetor = {
    'DB_Object_ID':'uniprot_ids',
    'geneId':'entrez_id',
    'entrez_id':'entrez_id',
    'HGNC_ID':'hgnc_id',
    'gene_id':'entrez_id',
}


wiki_xrefdb_field ={
    'miRBase Sequence':'mirbase',
    'RefSeq':'refseq_accession',
    'Uniprot-TrEMBL':'uniprot_ids',
    'Uniprot-SwissProt':'uniprot_ids',
    'Ensembl':'ensembl_gene_id',
    'EcoGene':'ensembl_gene_id',
    'Ensembl Human':'ensembl_gene_id',
    'Entrez Gene':'entrez_id',
    'HGNC':'symbol',
    'Enzyme Nomenclature':'enzyme_id',
    }