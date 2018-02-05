#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/1/31
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download,extract,standard insert and select variant data from pharmgkb

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(pharmgkb_variant_model,pharmgkb_variant_raw,pharmgkb_variant_store,pharmgkb_variant_db,pharmgkb_variant_map) = buildSubDir('pharmgkb_variant')

log_path = pjoin(pharmgkb_variant_model,'pharmgkb_variant.log')

# main code
def downloadData(redownload=False):
    '''
    this function is to download the raw data from  pharmgkb  WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        (choice,existFile) = lookforExisted(clinvar_variant_raw,'variant')

        if choice != 'y':
            return

    if redownload or not existgoFile or  choice == 'y':

        process = parser(today)

        # 1. download variant.zip file from pharmgkb download website and rsid2rsid file from ftp site
        (rawdir,mt) = process.getOne(pharmgkb_variant_raw)

    #--------------------------------------------------------------------------------------------------------------------
    # 2. generate .log file in current  path
    if not os.path.exists(log_path):

        with open(log_path,'w') as wf:

            json.dump(
                {
                'pharmgkb_variant':[(today,today,model_name)],
                pharmgkb_rsid_filename:[(mt,today,model_name)],
                },
                wf,indent=8)

    print  'datadowload completed !'
    #--------------------------------------------------------------------------------------------------------------------
    # 3.return filepaths to extract 
    filepaths = [pjoin(rawdir,filename) for filename in listdir(rawdir)]

    return (filepaths,today)

def extractData(filepaths,date):
    '''
    this function is set to distribute all filepath to parser to process
    args:
    filepaths -- all filepaths to be parserd
    date -- the date of  data download
    '''
    # rawdir = pslit(filepaths[0])[0].strip()
    # # 1. distribute filepaths for parser
    variant_ca_basic_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('variants')]

    variant_ca_mutid_paths = [path for path in filepaths if psplit(path)[1].strip().startswith('RsMergeArch')]
    
    # # 2. parser filepaths step by step
    process = parser(date)

    # # --------------------------------pharmGKB.variant.info---------------------------------------------------
    ca_links = process.variant_ca_basic(variant_ca_basic_paths)

    process.variant_ca_mutid(variant_ca_mutid_paths)

    ca_readnows = process.getCA(ca_links,rawdir)

    ca_readnows_info = process.getRead(ca_readnows,rawdir)

    # ca_readnows_info = json.load(open('./ca_readnow_info.json'))

    process.variant_ca_anno(ca_readnows_info)

    # # ----------------------------------------------------------------------------------------------
    # 3. bkup all collections
    colhead = 'pharmgkb.variant'

    bkup_allCols('mydb_v1',colhead,pharmgkb_variant_db)

def updateData():

    #function introduction
    #args:

    return

def selectData():

    #function introduction
    #args:
    
    return

class parser(object):
    '''
    this class is set to parser all raw file to extract content we need and insert to mongodb
    '''
    def __init__(self, date):

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

        self.date = date

    def login(self,sign_page=None):
        '''
        this function is set to  log in the web pharmgkb and return a  driver cursor
        '''
        if not sign_page:
            sign_page = pharmgkb_sign_page

        driver = webdriver.Chrome()
        driver.get(sign_page)

        try:
            email = WebDriverWait(driver,10,0.5).until(EC.presence_of_all_elements_located((By.NAME,'email')))
            password = WebDriverWait(driver,10,0.5).until(EC.presence_of_all_elements_located((By.NAME,'password')))
        finally:
            email  = driver.find_element_by_name('email')
            passwd = driver.find_element_by_name('password')
            email.send_keys('1169804109@qq.com')
            passwd.send_keys('1169804109@qq.com')

            buttons = driver.find_elements_by_tag_name('button')

            for b in buttons:
                if b.get_attribute('type') == 'submit':
                    try:
                        b.click()
                        print 'logged !'
                        return driver
                    except:
                        pass
            driver.close()

    def read(self,html):
        '''
        this function is set to parser clinical annotation info from web html 
        '''
        soup = bs(html,'lxml') 
        aset = dict()
        #-----------------------------------------------------------------
        fact_session = soup.find(name='div',attrs={'class':'fact-section'})
        facts = fact_session.findAll(attrs={'class':'fact'})

        for fact in facts:
            label = fact.find(attrs={'class':'fact-label'})
            val = fact.find(attrs={'class':'fact-content'})
            key = label.text.strip()
            val = [text for text in val.stripped_strings]
            aset[key] = val
        #-------------------------------------------------------------------
        table = soup.find(attrs={'class':'allele-phenotypes-table'})
        trs = table.findAll(name='tr')
        for tr in trs:
            tds= tr.findAll(name='td')
            if tds:
                try:
                    allele = tds[0].text.strip()
                    phenotype =  tds[1].text.strip()

                    if 'genotype' not in aset:
                        aset['genotype'] = list()
                    aset['genotype'].append({'ALLELE':allele,'PHENOTYPE':phenotype})
                except:
                    pass#no td
        #-------------------------------------------------------------------
        annos = soup.find(attrs={'class':'variant-annotations'})
        divs = annos.findAll(attrs={'class':'resource-detail variant-annotation-detail trim-facts'})

        if 'Evidence' not in aset:
            aset['Evidence'] = list()

        for div in divs:
            header = div.find(attrs={'class':'fact-section-header'}).text.strip()
            title = div.find(attrs={'class':'variant-annotation-title'}).text.strip()

            if title.split('.',1)[0].isnumeric():
                title = title.split('.',1)[1].strip()

            description = div.find(attrs={'id':'variant-ann-description'}).text.strip()
            publication = div.find(attrs={'id':'variant-ann-publication'})
            literatures= publication.findAll(attrs={'class':'literatureCitation'})

            publications = list()

            for lit in literatures:
                lit_text = lit.text.strip()

                if lit_text.count('.'):
                    tail = lit_text.rsplit('.',1)[1].replace('PubMed','').strip()
                    if tail.isnumeric():
                        lit_title_journal= lit_text.rsplit('.',1)[0].strip() + '.'
                        pubmed_id = lit_text.rsplit('.',1)[1].replace('PubMed','').strip()
                        pubmed_link ='https://www.ncbi.nlm.nih.gov/pubmed/{}'.format(pubmed_id)
                    else:
                        lit_title_journal = lit_text
                        pubmed_id,pubmed_link = '',''

                else:
                    lit_title_journal = lit_text
                    pubmed_id,pubmed_link = '',''

                publications.append({
                'publication':lit_title_journal,
                'pubmed_id':pubmed_id,
                'pubmed_link':pubmed_link,
                })
            
            aset['Evidence'] .append({
                'header':header,
                'title':title,
                'description':description,
                'publications':publications,  
            })

        return aset

    def getCA(self,ca_links=None,rawdir=None):

        ca_readnows_path = pjoin(rawdir,'ca_readnows.json')
        ca_readnows = dict()

        ca_readnows_txt_path = pjoin(rawdir,'ca_readnows.txt')
        ca_readnows_txt = open(ca_readnows_txt_path,'a')

        driver = webdriver.Chrome()

        for var_id,ca_link in ca_links.items():

            print '+'*50
            print var_id,ca_link

            driver.get(ca_link)

            # just after Scroll button ,the all read now  would be show
            js="var q=document.body.scrollTop=100000" 
            driver.execute_script(js)

            try:
                try:
                    elements = WebDriverWait(driver,30,0.5).until(EC.presence_of_all_elements_located((By.LINK_TEXT,'Read Now')))
                except:
                    pass
            finally:
                elements = driver.find_elements_by_link_text('Read Now')

                hrefs = [e.get_attribute('href') for e in elements]

                ca_readnows[var_id] = hrefs

            ca_readnows_txt.write(var_id + '\t' + json.dumps(hrefs) + '\n')
            ca_readnows_txt.flush()

        driver.close()
        ca_readnows_txt.close()

        with open(ca_readnows_path,'w') as wf:
            json.dump(ca_readnows,wf,indent=8)

        return ca_readnows

    def getOne(self,rawdir):

        '''
        this function is set to download variant.zip file from  "https://www.pharmgkb.org/downloads" with selenium
                                                               RsMergeArch.bcp.gz from ftp site
        '''
        # 1. -------------------------------------------------variant.zip------------------------------------------------------------------------------------------
        # set args for chrom driver
    
        options = webdriver.ChromeOptions()

        prefs = {'profile.default_content_settings.popups':0,'download.default_directory':rawdir}

        options.add_experimental_option('prefs',prefs)

        driver = webdriver.Chrome(chrome_options=options)

        # download variants data
        driver.get('https://www.pharmgkb.org/downloads')

        try:
            element = WebDriverWait(driver,10,0.5).until(EC.presence_of_all_elements_located((By.TAG_NAME,'button')))
            print '...all button load !'

        finally:
            buttons = driver.find_elements_by_tag_name('button')
            for button in buttons:
                if button.text == 'variants.zip':
                    button.click()
                    sleep(5)
                    break

            print '...variants.zip download !'

            # unzip file
            old_filepath = pjoin(rawdir,'variants.zip')
            new_filedirpath = pjoin(rawdir,'variants_{}'.format(today))
            createDir(new_filedirpath)

            unzip = 'unzip {} -d {}'.format(old_filepath,new_filedirpath)
            os.popen(unzip)
            print '...unzip file in  {} '.format(new_filedirpath)

            driver.close()

        # 2. ------------------------------------------------- RsMergeArch.bcp.gz------------------------------------------------------------------------------------------
        ftp = connectFTP(**pharmgkb_rsid_ftp_infos)
        print '...connectFTP pharmgkb_rsid_ftp !'

        mt =  ftp.sendcmd('MDTM {}'.format(pharmgkb_rsid_filename)).replace(' ','')

        savefilename = '{}_{}_{}.bcp.gz'.format(pharmgkb_rsid_filename.rsplit('.bcp',1)[0].strip(),mt,today)

        remoteabsfilepath = pjoin(pharmgkb_rsid_ftp_infos['logdir'],'{}'.format(pharmgkb_rsid_filename))

        savefilepath = pjoin(rawdir,savefilename)

        ftpDownload(ftp,pharmgkb_rsid_filename,savefilename,new_filedirpath,remoteabsfilepath)
        print '...RsMergeArch.bcp.gz download !'

        gunzip = 'gunzip {}'.format(savefilepath)

        os.popen(gunzip)

        return (new_filedirpath,mt)

    def getRead(self,ca_readnows=None):
        '''this function is set to get clinical annotation from pharmgkb web  with crawer'''
        driver = webdriver.Chrome()

        ca_readnow_info_path = pjoin(rawdir,'ca_readnow_info.json')
        ca_readnows_info = dict()

        ca_readnow_info_txt_path = pjoin(rawdir,'ca_readnow_info.txt')
        ca_readnow_info_txt = open(ca_readnow_info_txt_path,'w') 

        n = 0

        first = True

        for var_id,readnows in ca_readnows.items():

            for readnow in readnows:

                print '+'*50
                n += 1
                print n
                print var_id,readnow

                anno_id = readnow.rsplit('/',1)[1].strip()

                if (var_id,anno_id) in down:
                    continue

                driver.get(readnow)

                while first:
                    try:
                        rigister = WebDriverWait(driver,30,0.5).until(EC.presence_of_element_located((By.LINK_TEXT,'register or sign in')))
                        rigister = driver.find_element_by_link_text('register or sign in')
                        rigister.click()

                        email = driver.find_element_by_name('email')
                        password = driver.find_element_by_name('password')
                        email.send_keys('1169804109@qq.com')
                        password.send_keys('1169804109@qq.com')

                        buttons = driver.find_elements_by_tag_name('button')
                        for b in buttons:
                            if b.text.strip()  == 'Sign In':
                                b.click()
                                break
                        'registered!'

                        first = False
                    except:
                        print 'no register or sign in found! '

                try:
                    left_elements = WebDriverWait(driver,30,0.5).until(EC.presence_of_all_elements_located((By.CLASS_NAME,'fact-content')))
                    right_elements = WebDriverWait(driver,30,0.5).until(EC.presence_of_all_elements_located((By.CLASS_NAME,'phenotype')))
                    bottle_elements = WebDriverWait(driver,30,0.5).until(EC.presence_of_all_elements_located((By.CLASS_NAME,'variant-annotations')))

                finally:

                    web = driver.page_source

                    storepath = pjoin(pharmgkb_variant_store,'./web_{}_{}.html'.format(var_id,anno_id))
                    with open(storepath,'w') as wf:
                        wf.write(web.encode('utf-8'))

                    aset  = self.read(web)

                    #========================================================================
                    if var_id not in ca_readnows_info:
                        ca_readnows_info[var_id] = dict()
                    ca_readnows_info[var_id][readnow] = aset
                    ca_readnow_info_txt.write(var_id + '\t' + readnow + '\t' + json.dumps(aset) + '\n')
                    ca_readnow_info_txt.flush()

        with open(ca_readnow_info_path,'w') as wf:
            json.dump(ca_readnows_info,wf,indent=8)

        driver.close()

        return ca_readnows_info
    def variant_ca_basic(self,filepaths):
        '''
        this function is set parser variant_info 
        '''
        print '+'*50

        info_colname = 'pharmgkb.variant.ca'

        # before insert ,truncate collection
        delCol('mydb_v1',info_colname)

        info_col = self.db.get_collection(info_colname)

        info_col.ensure_index([('pharmgkb_VariantID',1),])

        filepath = filepaths[0] # just only one

        rawdir = psplit(filepath)[0]

        fileversion = psplit(filepath)[0].rsplit('_',1)[1].strip() # web site no version info ,so set the download date as the version

        info_col.insert({'dataVersion':fileversion,'dataDate':self.date,'colCreated':today,'file':'variants.zip'})

        #-----------------------------------------------------------------------------------------------------------------------------------------------------
        tsvfile = open(filepath)

        n = 0

        ca_links = dict()

        for line in tsvfile:

            if n == 0 :
                keys = [key.replace(' ','&').replace('.','*') for key in line.strip().split('\t')]
                print keys

            else:

                data = line.strip().split('\t')

                dic = dict([(key,val) for key,val in zip(keys,data)])

                var_id = dic.get('Variant&ID','')

                if var_id:
                    ca_link = 'https://www.pharmgkb.org/variant/{}/clinicalAnnotation'.format(var_id)
                else:
                    ca_link = ''

                rs_id = dic.get('Variant&Symbol','')
                
                ca_count = dic.get('CA&count','')
                if ca_count:
                    ca_count = int(ca_count)

                level_12_ca_count = dic.get('Level&1/2&CA&count','')
                if level_12_ca_count:
                    level_12_ca_count = int(level_12_ca_count)

                # just when ca_count!= 0  , the clinical annotations existed in pharmgkb web site 
                if ca_count != 0 and var_id:
                    ca_links[var_id] = ca_link

                info_col.insert({
                    'pharmgkb_VariantID':var_id,
                    'rs_id':rs_id,
                    'CA_count':ca_count,
                    'Level_1/2_CA_count':level_12_ca_count,
                    'CA_link':ca_link,
                    })
                print 'pharmgkb.variant.info.ca tsv line',n
        
            n += 1

        ca_links_path = pjoin(rawdir,'ca_links.json')

        with open(ca_links_path,'w') as wf:
            json.dump(ca_links,wf,indent=8)

        return ca_links

    def variant_ca_mutid(self,filepaths):
        '''
        this function is set  alter rsid and generate mutation id
        args:
        filepath -- the rsid transform file
        '''
        filepath = filepaths[0] # just only one
        #---------------------------------------------------------------------------------------------------
        print '...start to generate old_rsid2new_rsid'

        tsvfile = open(filepath)
        # 1. get all oldrsid2newrsid
        old_rsid2new_rsid = dict()

        for line in tsvfile:
            old_rsid = 'rs' +  line.split('\t')[0]
            new_rsid ='rs' +   line.split('\t')[1]
            old_rsid2new_rsid[old_rsid] = new_rsid
        #---------------------------------------------------------------------------------------------------
        # 2.  transform old rsid 2 new rsid according to RsMergeArch.bcp.gz
        # get all rsid from collection and alter it
        print '...start to alter old_rsid 2 new_rsid in pharmgkb.variant.info.ca '

        info_col = self.db.get_collection('pharmgkb.variant.ca')

        docs = info_col.find({}).skip(1)

        n = 0
        rs_ids = open('./rs_ids.txt','w')

        for doc in docs:

            _id = doc.get('_id')
            rs_id = doc.get('rs_id')

            if rs_id  in old_rsid2new_rsid:
                n += 1
                print n,rs_id,old_rsid2new_rsid[rs_id]

                rs_id = old_rsid2new_rsid[rs_id]
                info_col.update(
                    {'_id':_id},
                    {'$set':{'rs_id':rs_id}},
                    False,
                    True)

            print 'rs_id',rs_id
            rs_ids.write(rs_id + '\n')
            rs_ids.flush()
        rs_ids.close()
        #---------------------------------------------------------------------------------------------------
        # # 2.  generate mutation id with annotation from annovar
        # print '...start to generate annotation with rsid '
        # annovar = 'perl  {}convert2annovar.pl -format rsid rs_ids.txt -dbsnpfile {} > ./rs_snp.txt'.format(annovar_bin,dbsnpfilepath)
        # os.popen(annovar)
        # print '...complete '

        # add  mutation id

    def variant_ca_anno(self,ca_readnows_info):

        level_inplications = {
        "Level 1A":"Annotation for a variant-drug combination in a CPIC or medical society-endorsed PGx guideline, or implemented at a PGRN site or in another major health system.",
        "Level 1B":"Annotation for a variant-drug combination where the preponderance of evidence shows an association. The association must be replicated in more than one cohort with significant p-values, and preferably will have a strong effect size.",
        "Level 2A":"Annotation for a variant-drug combination that qualifies for level 2B where the variant is within a VIP (Very Important Pharmacogene) as defined by PharmGKB. The variants in level 2A are in known pharmacogenes, so functional significance is more likely.",
        "Level 2B":"Annotation for a variant-drug combination with moderate evidence of an association. The association must be replicated but there may be some studies that do not show statistical significance, and/or the effect size may be small.",
        "Level 3":"Annotation for a variant-drug combination based on a single significant (not yet replicated) study or annotation for a variant-drug combination evaluated in multiple studies but lacking clear evidence of an association.",
        "Level 4":"Annotation based on a case report, non-significant study or in vitro, molecular or functional assay evidence only."
        }

        info_col = self.db.get_collection('pharmgkb.variant.ca')
        var_ids = set()

        for var_id, it in ca_readnows_info.items():

            print var_id
            doc = info_col.find_one({'pharmgkb_VariantID':var_id})

            _id = doc.pop('_id')

            info_col.remove({'_id':_id})

            for readnow_link,info in it.items():

                dic = copy.deepcopy(doc)

                dic['readnow_link'] = readnow_link

                Level_of_Evidence = info.get('Level of Evidence',['',])[0]

                dic['Level_of_Evidence'] = Level_of_Evidence

                dic['Level_implication'] = level_inplications.get(Level_of_Evidence)

                dic['Type'] = info.get('Type',['',])[0]

                for key in ['Genes','Drugs','Phenotypes','genotype','Evidence']:

                    dic[key] = info.get(key,[[],])[0]

                info_col.insert(dic)

                dic.pop('_id')

class dbMap(object):

    # this class is set to map xxxxxx to other db

    def __init__(self):

        super(dbMap,self).__init__()

        pass

class dbFilter(object):

    #this class is set to filter part field of data in collections  in mongodb

    def __init__(self):

        super(dbFilter,self).__init__()

        pass


def main():

    modelhelp = 'help document'

    funcs = (downloadData,extractData,updateData,selectData,pharmgkb_variant_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    main()

    (filepaths,date) = downloadData(redownload=True)
    #---------------------------------------------------------------------------------------------------------------------------------------

    # rawdir = '/home/user/project/dbproject/mydb_v1/pharmgkb_variant/dataraw/variants_180205132245'
    # filepaths = [pjoin(rawdir,filename) for filename in listdir(rawdir)]
    # date = '180205132245'
    extractData(filepaths,date)
    # ---------------------------------------------------------------------------------------------------------------------------------------
    # man = parser(today)
    #---------------------------------------------------------------------------------------------------------------------------------------
    # man.getRead(ca_readnows)
    # man.login()
