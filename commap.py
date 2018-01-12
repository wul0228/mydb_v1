#!/usr/bin/env python
# -*- coding:utf-8 -*-
# date:20180108
# author:wuling
# emai:ling.wu@myhealthgene.com

from share import initDB

class comMap(object):

    """docstring for commenMap"""
    def __init__(self):

        super(comMap, self).__init__()

        (db,db_cols) = initDB('mydb_v1')

        self.db = db
        self.db_cols = db_cols
        
    def hgncID2hgncSymbol(self):
        '''
        this function is set to map hgnc id to hgnc symbol
        '''
        hgnc = self.db_cols.get('hgnc.gene')

        hgnc_docs = hgnc.find({})

        hgnc2symbol = dict()

        for doc in hgnc_docs:

            hgnc = doc.get('hgnc_id')

            symbol = doc.get('symbol')

            if hgnc and symbol:

                if hgnc not in hgnc2symbol:

                    hgnc2symbol[hgnc] = list()
                hgnc2symbol[hgnc].append(symbol)

        print 'hgnc2symbol',len(hgnc2symbol)

        return hgnc2symbol

    def entrezID2hgncSymbol(self):

        '''
        this function is set to map entrez id to hgnc symbol
        '''
        # all  record 41298(a log record) ,have entrez id 41269(no entrez id 29) ,is "" 85,remain  41182,(41184,2 duplicated)
        # a
        hgnc = self.db_cols.get('hgnc.gene')

        hgnc_docs = hgnc.find({})

        entrez2symbol = dict()

        for doc in hgnc_docs:

            entrez = doc.get('entrez_id')

            symbol = doc.get('symbol')

            # a entrez id maybe to 2 or more symbol  (440993,653067)
            if entrez and symbol:

                if entrez not in entrez2symbol:

                    entrez2symbol[entrez] = list()

                entrez2symbol[entrez].append(symbol)

        print 'entrez2symbol',len(entrez2symbol)

        return entrez2symbol

    def ensemblGeneID2hgncSymbol(self):

        # all  record 41298 ,have entrez id 41063 ,is "" 3652,remain  37408(37411 ,3 duplicated ENSG00000230417,ENSG00000268062,ENSG00000283607)

        hgnc = self.db_cols.get('hgnc.gene')

        hgnc_docs = hgnc.find({})

        ensembl2symbol = dict()

        for doc in hgnc_docs:

            ensembl = doc.get('ensembl_gene_id')

            symbol = doc.get('symbol')

            if ensembl and symbol:

                if ensembl not in ensembl2symbol:

                    ensembl2symbol[ensembl] = list()

                ensembl2symbol[ensembl].append(symbol)

        print 'ensembl2symbol',len(ensembl2symbol)

        return ensembl2symbol

    def uniprotGeneID2hgncSymbol(self):

        # all  record 41298 ,have uniprot_ids 37035(no uniprot_ids 4263) ,is "" 17020,remain 19875(20015,140 duplicated and 81 have more than one symbol)

        hgnc = self.db_cols.get('hgnc.gene')

        hgnc_docs = hgnc.find({})

        uniprot2symbol = dict()

        uniprots = list()

        for doc in hgnc_docs:

            uniprot = doc.get('uniprot_ids')

            symbol = doc.get('symbol')

            uniprots.append(uniprot)

            if uniprot and symbol:

                if uniprot not in uniprot2symbol:

                    uniprot2symbol[uniprot] = list()

                uniprot2symbol[uniprot].append(symbol)

        print 'uniprot2symbol',len(uniprot2symbol)

        return uniprot2symbol

    def rsID2hgncSymbol(self):
        '''
        this function is to create a mapping relation between rs id  with HGNC Symbol
        '''
        # because disgenet gene id  is entrez id 
        hgnc2symbol = self.hgncID2hgncSymbol()

        clinvar_variant_col = self.db_cols.get('clinvar.variant')

        clinvar_variant_docs = clinvar_variant_col.find({})

        rsID2hgncSymbol = dict()

        for doc in clinvar_variant_docs:

            rs_id = doc.get('RS# (dbSNP)')

            hgnc_id = doc.get('HGNC_ID')

            gene_symbol = hgnc2symbol.get(hgnc_id)

            if rs_id and rs_id != '-1' and gene_symbol:

                rs_id = 'rs' + rs_id

                if rs_id not in rsID2hgncSymbol:

                    rsID2hgncSymbol[rs_id] = list()

                rsID2hgncSymbol[rs_id] += gene_symbol

        print 'rsID2hgncSymbol',len(rsID2hgncSymbol)

        return rsID2hgncSymbol

def main():
    man = comMap()
    man.entrezID2hgncSymbol()
    man.ensemblGeneID2hgncSymbol()
    man.uniprotGeneID2hgncSymbol()
    man.rsID2hgncSymbol()

if  __name__ == '__main__':
    main()