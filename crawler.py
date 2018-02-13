#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/2/8
# author:wuling
# emai:ling.wu@myhealthgene.com

'''
this model is set to generate standard doc file for sub model 
'''
import os,re
import json
from config import *
from share import *

class crawler(object):

    """docstring for crawer"""

    def __init__(self, date):

        super(crawler, self).__init__()

        conn = MongoClient('localhost',27017)

        db = conn.get_database('mydb_v1')

        self.db = db

        self.date = date

    def kegg_web(self,link,rawdir):

        path_id = link.rsplit('map',1)[1].strip()

        savename = '{}.html'.format(path_id)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,link)

        os.popen(command)

    def kegg_des(self,kegg_html,path_names):

        kegg_des_tsv = pjoin('./','_crawer','kegg_path_des1')

        kegg_path_des = open(kegg_des_tsv,'w')

        n = 0

        for filename in listdir(kegg_html):

            path_id =filename.split('.html')[0].strip()

            filepath = pjoin(kegg_html,filename)

            path_html = open(filepath).read()

            soup = bs(path_html,'lxml')

            des_tag = soup.find(text='Description')

            if des_tag:

                des_con = des_tag.findNext(name='td').text.strip().replace('\n',' ').encode('utf-8')

            else:
                des_con = 'None'

            path_name = path_names.get(path_id)

            kegg_path_des.write(path_id + '\t' +path_name.encode('utf-8') + '\t' +  des_con + '\n')

            n += 1

            print n

        kegg_path_des.close()

    def kegg_png(self,link,rawdir):

        path_id = link.rsplit('map',1)[1].split('.png')[0].strip()

        savename = '{}.png'.format(path_id)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,link)

        os.popen(command)

    def kegg(self):

        '''crawer kegg description and png'''

        kegg_pathway_info = self.db.get_collection('kegg.pathway.info')

        docs = kegg_pathway_info.find({})

        path_links = dict()
        png_links = dict()
        path_names = dict()

        for doc in docs:

            path_id = doc.get('path_id')

            if path_id:

                path_name = doc.get('path_name','noname')

                path_link  = doc.get('path_map_link')

                png_link = 'http://www.genome.jp/kegg/pathway/map/map{}.png'.format(path_id)

                path_links[path_id] = path_link
                png_links[path_id] = png_link
                path_names[path_id] = path_name
        # #---------------------------------------------------------------------------------------------------

        kegg_html = pjoin('./','_crawer','kegg_path_html')

        # createDir(kegg_html)

        # func = lambda link:self.kegg_web(link,kegg_html)

        # multiProcess(func,path_links.values(),size=50)

        self.kegg_des(kegg_html,path_names)
        # #------------------------------------------------------------------------------------------------
        # kegg_map = pjoin('./','_crawer','kegg_path_map')

        # createDir(kegg_map)

        # func = lambda link:self.kegg_png(link,kegg_map)

        # multiProcess(func,png_links.values(),size=50)
        
        #----------------------------------------------------------------------------------------------
        # change name
        # for filename in listdir(kegg_map):

        #     filepath = pjoin(kegg_map,filename)

        #     path_id = filename.split('.png',1)[0].split('_')[0].strip()

        #     path_name = path_names.get(path_id,'noname').replace(' ','_').replace('/','&')

        #     newname = '{}_{}.png'.format(path_id,path_name)

        #     newpath = pjoin(kegg_map,newname)

        #     os.rename(filepath,newpath)

    def wiki_web(self,link,rawdir):

        path_id = link.rsplit('Pathway:',1)[1].strip()

        savename = '{}.html'.format(path_id)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,link)

        os.popen(command)

    def wiki_des(self,wiki_html,path_names):

        wiki_des_tsv = pjoin('./','_crawer','wiki_path_des')

        wiki_path_des = open(wiki_des_tsv,'w')

        n = 0

        for filename in listdir(wiki_html):

            print path_id

            path_id =filename.split('.html')[0].strip()

            filepath = pjoin(wiki_html,filename)

            path_html = open(filepath).read()

            soup = bs(path_html,'lxml')

            # des info
            des_tag = soup.find(name='div',attrs={'id':'descr'})

            if des_tag:

                des_con =' '.join([text.strip() for text in des_tag.stripped_strings]).replace('\n',' ')

                strings = ['</div>','View original pathway at: Reactome']

                for s in strings:
                    des_con = des_con.split(s)[0].strip()

            else:
                des_con = 'None'

            des_con = des_con.encode('utf-8')

            path_name = path_names.get(path_id)

            wiki_path_des.write(path_id + '\t' + path_name.encode('utf-8') + '\t' + des_con + '\n')

            n += 1

            print n

        wiki_path_des.close()  

    def wiki_png(self,path_links,path_names):
        #-----------------------------------------------------------------------------------------------------
        wiki_map = pjoin('./','_crawer','wiki_path_map')

        createDir(wiki_map)

        still = True

        while still:

            try:

                havedown = [filename.split('_')[0].strip() for filename in listdir(wiki_map)]
                
                options = webdriver.ChromeOptions()

                prefs = {'profile.default_content_settings.popups':0,'download.default_directory':wiki_map}

                options.add_experimental_option('prefs',prefs)

                driver = webdriver.Chrome(chrome_options=options)

                for path_id,link in path_links.items():

                    if path_id in havedown:
                        continue

                    print path_id,link

                    try:
                        driver.get(link)
                        down = driver.find_element_by_id('download-button')
                        svg = down.find_element_by_link_text('Scalable Vector Graphics (.svg)')
                        svg_href = svg.get_attribute('href')
                        driver.get(svg_href)
                    except:
                        pass
                        # print link
                still = False
            except:
                driver.close()
        # --------------------------------------------------------------------------------------------------------------------
        # change name

        for filename in listdir(wiki_map):

            filepath = pjoin(wiki_map,filename)

            path_id = filename.split('_',1)[0].strip()

            path_name = path_names.get(path_id,'noname').replace(' ','_').replace('/','&')

            newname = '{}_{}.svg'.format(path_id,path_name)

            newpath = pjoin(wiki_map,newname)

            print filepath
            print newpath
            os.rename(filepath,newpath)

    def wiki(self):
        #----------------------------------------------------------------------------------------------
        wiki_pathway_info = self.db.get_collection('wiki.pathway.info')

        docs = wiki_pathway_info.find({})

        path_links = dict()
        path_names = dict()

        for doc in docs:

            path_id = doc.get('path_id')
            path_name = doc.get('path_name')
            path_link = doc.get('path_link')

            if path_id and path_link:
                path_links[path_id] = path_link

            if path_id and path_name:
                path_names[path_id] = path_name

            if not path_link:
                print '===',path_id

        print len(path_links)
       #---------------------------------------------------------------------------------------------------
       # get description

        # wiki_html = pjoin('./','_crawer','wiki_path_html')

        # createDir(wiki_html)

        # func = lambda link:self.wiki_web(link,wiki_html)

        # multiProcess(func,path_links.values(),size=50)

        # self.wiki_des(wiki_html,path_names)

        #----------------------------------------------------------------------------------------------
        #get svg
        # self.wiki_png(path_links,path_names)

    def reactome_png(self,path_images,path_names):

        #-----------------------------------------------------------------------------------------------------
        reactome_map = pjoin('./','_crawer','reactome_path_map')

        createDir(reactome_map)
            
        options = webdriver.ChromeOptions()

        prefs = {'profile.default_content_settings.popups':0,'download.default_directory':reactome_map}

        options.add_experimental_option('prefs',prefs)

        driver = webdriver.Chrome(chrome_options=options)

        n = 100

        still = True

        while still and n:

            try:

                for path_id,link in path_images.items():

                    path_images.pop(path_id)

                    print path_id,link
                    
                    driver.get(link)

                    sleep(20)

                    select = driver.find_element_by_class_name('GMN4JDYAK')

                    select.click()

                    sleep(3)

                    buttons = driver.find_elements_by_tag_name('button')

                    for b in buttons:
                        if b.get_attribute('title') == 'Export image':
                            svg_b = b

                    svg_b.click()

                    sleep(1)

                    svg_save = driver.find_element_by_class_name('GMN4JDYLO')
                    svg_save.click()

                    

                still = False
            except:
                n =  n-1

            print 'n',n
        #--------------------------------------------------------------------------------------------------------------------
        # change name

        # for filename in listdir(wiki_map):

        #     filepath = pjoin(wiki_map,filename)

        #     path_id = filename.split('_',1)[0].strip()

        #     path_name = path_names.get(path_id,'noname').replace(' ','')

        #     newname = '{}_{}.svg'.format(path_id,path_name)

        #     newpath = pjoin(wiki_map,newname)

        #     os.rename(filepath,newpath)

    def reactome_des(self,path_sums,path_names):

        import re

        reactome_des_tsv = pjoin('./','_crawer','reactome_path_des1')

        reactome_path_des = open(reactome_des_tsv,'w')

        for path_id,path_sum in path_sums.items():

            path_sum = re.sub('<.{1,5}>',' ',path_sum)

            # for s in ['i','b','br','p','P','sub','li','ul','sup','font','font color=red','BR','I','ol','p align=center','br ']:
            #     path_sum = path_sum.replace('<{}>'.format(s),' ').replace('</{}>'.format(s),' ')

            path_id = path_id.encode('utf-8')
            path_name = path_names.get(path_id).encode('utf-8')
            path_sum = path_sum.replace('\n',' ').encode('utf-8')

            reactome_path_des.write(path_id + '\t' + path_name+ '\t' + path_sum + '\n')

        reactome_path_des.close()

    def reactome(self):
        #----------------------------------------------------------------------------------------------
        reactome_pathway_info = self.db.get_collection('reactom.pathway.info')

        docs = reactome_pathway_info.find({})

        path_links = dict()
        path_names = dict()
        path_images = dict()
        path_sums = dict()

        for doc in docs:

            path_id = doc.get('path_id')

            if path_id:

                path_name = doc.get('path_name','noname')
                path_sum = doc.get('path_summation','None')
                path_link = doc.get('path_link')
                path_image = doc.get('path_image')

                if path_link:

                    path_links[path_id] = path_link

                path_names[path_id] = path_name

                path_images[path_id] = path_image

                path_sums[path_id] = path_sum

        #--------------------------------------------------------------------------------------------------------------------------------------------
        # get des
        # self.reactome_des(path_sums,path_names)
        #--------------------------------------------------------------------------------------------------------------------------------------------------
        print len(path_images)

        rawdir = '/home/user/project/dbproject/mydb_v1/_crawer/reactome_path_map/'

        havedown = [filename.split('.png')[0].strip() for filename in listdir(rawdir)]

        for path_id,link in path_images.items():
            if path_id in havedown:
                path_images.pop(path_id)

        print len(path_images)

        # get path image
        self.reactome_png(path_images,path_names)

    def humancyc_html(self,ip_infos):

        print 'all_ips',len(ip_infos)

        effect_ip = list()

        n = 0

        for _ip,_port in ip_infos:

            print _ip,_port

            proxies = { "http": "http://{}:{}".format(_ip,_port)}

            try:
                # web = requests.get("http://www.kegg.jp/",verify=False)
                # web = requests.get("https://www.baidu.com/",proxies=proxies,verify=False)
                # web = requests.get("http://www.kegg.jp/",proxies=proxies,verify=False)
                web = requests.get("https://humancyc.org/HUMAN/class-instances?object=Pathways",proxies=proxies,verify=False)
                # web = requests.get("https://humancyc.org/HUMAN/class-instances?object=Pathways",headers=headers,verify=False)
            except Exception,e:
                print '='*50
                print e
                print '='*50
                continue

            soup = bs(web.content,'lxml')

            n += 1
            if soup.find(text='You have exceeded your monthly access limit.'):
                print 'forbiddend !' 
            else:
                # with open('./huamncyc_html','w') as wf:
                with open('./kegg.html','w') as wf:
                    wf.write(soup.prettify().encode('utf-8'))
                break

            print '-'*50

    def humancyc_web(self,links,ip,port):

        humancyc_html = pjoin('./','_crawer','humancyc_path_html_driver')

        createDir(humancyc_html)

        havedown = [filename.split('.html')[0].strip() for filename in listdir(humancyc_html)]

        print 'havedown',len(havedown)

        options = webdriver.ChromeOptions()

        prefs = {'profile.default_content_settings.popups':0,'download.default_directory':humancyc_html}

        options.add_experimental_option('prefs',prefs)

        options.add_argument('--proxy-server=http://{}:{}'.format(ip,port))

        options.add_experimental_option("excludeSwitches", ["ignore-certificate-errors"])

        driver = webdriver.Chrome(chrome_options=options)

        m = 0

        # still = True

        # while  still:

            # try:

        for path_id,link in links.items():

            m += 1
            if path_id  in havedown:
                continue

            print m,path_id,link

            driver.get(link)

            try:
                elements = WebDriverWait(driver,50,0.5).until(EC.presence_of_all_elements_located((By.CLASS_NAME,'ecocomment')))

            finally:

                web = driver.page_source

                soup = bs(web,'lxml')

                html_savepath = pjoin(rawdir,'{}.html'.format(path_id))

                with open(html_savepath,'w') as wf:

                    wf.write(soup.prettify().encode('utf-8'))

                links.pop(path_id)

                # still = False
            # except:
                # pass

    def humancyc_png(self,path_id,path_name,link,rawdir):

        savename = '{}_{}.gif'.format(path_id,path_name)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,link)

        os.popen(command)

    def humancyc(self):

        # url = 'https://humancyc.org/HUMAN/class-instances?object=Pathways'
        # web_page = requests.get(url,headers=headers,verify=False)

        web_page = open('./_crawer/humancyc_pathways.html').read()

        soup = bs(web_page,'lxml')

        path_links = dict()
        path_names = dict()
        path_images = dict()

        table = soup.find(name='table',attrs={'class':'sortableSAQPoutputTable'})

        tds = table.findAll('td')

        for td in tds:

            a = td.findChild('a')

            if a:
                path_link =   'https://humancyc.org' + a.attrs.get('href')
                path_name =' '.join([text.strip() for text in a.stripped_strings])
                path_id = path_link.rsplit('object=')[1].strip()

                if path_id:
                    path_links[path_id] = path_link
                    path_names[path_id] = path_name
                    path_image = 'https://humancyc.org/tmp/ptools-images/HUMAN/{}_PWY-DIAGRAM.gif'.format(path_id)
                    path_images[path_id] = path_image

        print 'path_links',len(path_links)
        print 'path_names',len(path_names)
        print 'path_images',len(path_images)

        return path_links
        # #----------------------------------------------------------------------------------------------------------------
        # get web  page

         # self.humancyc_web(path_links,humancyc_html,_ip,_port)



    def netpath_web(self,path_id,path_name,link,rawdir):
        pass

    def netpath_png(self):

        netpath_map = pjoin('./','_crawer','netpath_path_map')

        createDir(netpath_map)

        options = webdriver.ChromeOptions()

        prefs = {'profile.default_content_settings.popups':0,'download.default_directory':netpath_map}

        options.add_experimental_option('prefs',prefs)

        driver = webdriver.Chrome(chrome_options=options)

        f = open('./netpath_graph')

        n = 0

        for line in f:
            
            link = line.split('name:')[0].strip()

            name = line.split('name:')[1].strip()

            n += 1

            print n,name,link

            driver.get(link)

            num = 100 # try number

            still = True

            down = False

            while still and num:
                try:
                    elements = driver.find_elements_by_class_name('material-icons')

                    if elements:
                        for e in elements:
                            if e.text == 'file_download':
                                down = e
                        if down:
                            down.click()
                            still = False
                        else:
                            num = num -1
                            sleep(1)
                except:
                    pass # try again

            still = True
            #---------------------------------------------------------------------------------------------------------
            down = False

            while still and num:
                try:
                    buttons = driver.find_element_by_class_name('common-async-button-header')

                    export_image = False

                    if buttons:

                        for b in buttons:

                            if b.text.strip() == 'Image (PNG)':

                                export_image = b

                        if export_image:
                            export_image.click()
                            still = False
                        else:
                            num = num -1
                            sleep(1)
                except:
                    pass # try again
                    


    def netpath(self):

        path_links ={
        "Alpha6Beta4Integrin":"http://www.netpath.org/pathways?path_id=NetPath_1",
        "AndrogenReceptor":"http://www.netpath.org/pathways?path_id=NetPath_2",
        "BCR":"http://www.netpath.org/pathways?path_id=NetPath_12",
        "EGFR1":"http://www.netpath.org/pathways?path_id=NetPath_4",
        "FSH":"http://www.netpath.org/pathways?path_id=NetPath_25",
        "Hedgehog":"http://www.netpath.org/pathways?path_id=NetPath_10",
        "ID":"http://www.netpath.org/pathways?path_id=NetPath_5",
        "IL1":"http://www.netpath.org/pathways?path_id=NetPath_13",
        "IL2":"http://www.netpath.org/pathways?path_id=NetPath_14",
        "IL3":"http://www.netpath.org/pathways?path_id=NetPath_15",
        "IL4":"http://www.netpath.org/pathways?path_id=NetPath_16",
        "IL5":"http://www.netpath.org/pathways?path_id=NetPath_17",
        "IL6":"http://www.netpath.org/pathways?path_id=NetPath_18",
        "IL-7":"http://www.netpath.org/pathways?path_id=NetPath_19",
        "IL9":"http://www.netpath.org/pathways?path_id=NetPath_20",
        "KitReceptor":"http://www.netpath.org/pathways?path_id=NetPath_6",
        "Leptin":"http://www.netpath.org/pathways?path_id=NetPath_22",
        "Notch":"http://www.netpath.org/pathways?path_id=NetPath_3",
        "Prolactin":"http://www.netpath.org/pathways?path_id=NetPath_56",
        "RANKL":"http://www.netpath.org/pathways?path_id=NetPath_21",
        "TCR":"http://www.netpath.org/pathways?path_id=NetPath_11",
        "TGF_beta_Receptor":"http://www.netpath.org/pathways?path_id=NetPath_7",
        "TNFalpha":"http://www.netpath.org/pathways?path_id=NetPath_9",
        "TSH":"http://www.netpath.org/pathways?path_id=NetPath_23",
        "TSLP":"http://www.netpath.org/pathways?path_id=NetPath_24",
        "TWEAK":"http://www.netpath.org/pathways?path_id=NetPath_26",
        "Wnt":"http://www.netpath.org/pathways?path_id=NetPath_8",
        }

        netpathc_html = pjoin('./','_crawer','netpath_path_html_drive')

        createDir(netpathc_html)

        options = webdriver.ChromeOptions()

        prefs = {'profile.default_content_settings.popups':0,'download.default_directory':netpathc_html}

        options.add_experimental_option('prefs',prefs)

        driver = webdriver.Chrome(chrome_options=options)

        for  path_name,link in path_links.items():
            print link

            path_id = link.rsplit('path_id=',1)[1].strip()

            driver.get(link)

            try:
                elements = WebDriverWait(driver,30,0.5).until(EC.presence_of_element_located((By.CLASS_NAME,'pathwayhead')))
            finally:

                web = driver.page_source

                soup = bs(web,'lxml')

                html_savepath = pjoin(netpathc_html,'{}_{}.html'.format(path_id,path_name))

                with open(html_savepath,'w') as wf:

                    wf.write(soup.prettify().encode('utf-8'))

            # self.netpath_web(path_id,path_name,link,netpathc_html)

    def panther_web(self,link,rawdir):

        path_id = link.rsplit('clsAccession=',1)[1].strip()

        savename = '{}.html'.format(path_id)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,link)

        os.popen(command)

    def panther_des(self,panther_html,path_names):

        panther_des_tsv = pjoin('./','_crawer','panther_path_des')

        panther_path_des = open(panther_des_tsv,'w')

        n = 0

        for filename in listdir(panther_html):

            path_id =filename.split('.html')[0].strip()

            filepath = pjoin(panther_html,filename)

            path_html = open(filepath).read()

            soup = bs(path_html,'lxml')

            def_tag = soup.find(text='Definition')

            td1 = def_tag.findParent('td')

            des_con = td1.findNext('td').text.strip().replace('\n',' ').encode('utf-8').strip().replace('\n',' ')

            path_name = path_names.get(path_id).encode('utf-8') 

            if not des_con:
                des_con = 'None'

            panther_path_des.write(path_id + '\t' + path_name+ '\t' +  des_con + '\n')

            n += 1

            print n,path_id, des_con

    def panther_png(self,path_id,path_name,link,rawdir):

        savename = '{}_{}.png'.format(path_id.path_name)

        storefilepath = pjoin(rawdir,savename)

        command = 'wget -O {} {}'.format(storefilepath,link)

        os.popen(command)

    def panther(self):

        # get  all pathid2link
        tsvfile = open('./panther.tsv')

        path_links = dict()

        path_names = dict()

        for line in tsvfile:

            link = line.split('\t')[0].strip()

            path_id = link.rsplit('/',1)[1].strip()

            name_con = line.split('\t')[1].split(';')[0]

            if name_con.count('name'):
                path_name = name_con.split(':',1)[1].strip()
            else:
                path_name = 'noname'

            path_links[path_id] = link

            path_names[path_id] = path_name
        # #----------------------------------------------------------------------
        # get path map
        panther_map = pjoin('./','_crawer','panther_path_map')

        createDir(panther_map)

        path_images = dict()

        path_defs = dict()

        driver = webdriver.Chrome()

        for path_id,link in path_links.items():

            print path_id,link

            driver.get(link)

            imgs = driver.find_elements_by_tag_name('img')

            for img in imgs:

                src = img.get_attribute('src')

                if src and src.count('pathway'):

                    pathway_href = src

            if pathway_href:

                path_name = path_names.get(path_id)

                self.panther_png(path_id,path_name,pathway_href,panther_map)

            des = driver.find_element_by_link_text('Pathway Description')
            
            des_href = des.get_attribute('href').strip()

            path_defs[path_id] = des_href
        # #----------------------------------------------------------------------------------------------
        # get description html 
        # path_defs = open('/home/user/project/dbproject/mydb_v1/_crawer/panther_des_links')

        panther_html = pjoin('./','_crawer','panther_path_html')

        createDir(panther_html)

        func = lambda link:self.panther_web(link,panther_html)

        multiProcess(func,path_defs.values(),size=30)

        self.panther_des(panther_html,path_names)
        #---------------------------------------------------------------------------------------------------

    def smpdb(self):

        import csv

        f = open('./_crawer/smpdb_pathways.csv')

        smpdb_pathways_tsv = open('./_crawer/smpdb_pathways.tsv','w')

        reads = csv.reader(f)

        n = 0

        for read in reads:

            tsv_read= '\t'.join(read)

            smpdb_pathways_tsv.write(tsv_read + '\n')
        
            n += 1

    def countPng(self):

        allmap_tsv = open('./_crawer/allpath_map.tsv','w') 

        f = open('./_crawer/PathwayCommons9.All.hgnc.pathway2gene.txt')

        n = 0

        allpath = dict()

        for line in f:

            data = line.split('\t')

            path_name = data[1].split('name:',1)[1].split('datasource',1)[0].split(';',1)[0].strip()

            path_source = data[1].split('datasource:',1)[1].split(';',1)[0].strip()

            path_link  = data[0]

            if path_source not in allpath:
                allpath[path_source] = dict()

            if path_link not in allpath[path_source] :
                allpath[path_source][path_link] = path_name

        # print len(allpath)

        with open('./_crawer/allpath1.json','w') as wf:
            json.dump(allpath,wf,indent=8)

        for sour,it in allpath.items():

            if sour == 'wikipathways':
                sour = 'wiki'

            map_dir = pjoin('./_crawer/','{}_path_map'.format(sour))

            print map_dir

            if sour  in['kegg','panther','wiki']: 

                allmap_id = [filename.split('_',1)[0].strip() for filename in listdir(map_dir)]

                for link,name in it.items():

                    if sour == 'kegg':
                        path_id = psplit(link)[1].split('hsa')[1].strip()
                    else:
                        path_id = psplit(link)[1].strip()

                    if path_id in allmap_id:
        #                  # print path_id
                         have = 'Yes'
                    else:
                        have = 'No'
                    allmap_tsv.write(link + '\t' + sour + '\t'  + path_id + '\t' + name + '\t' +have + '\n' )

            elif sour  == 'netpath':

                allmap_name = [filename.split('.png',1)[0].strip() for filename in listdir(map_dir)]

                for link,name in  it.items():

                    if name in allmap_name:
                        have = 'Yes'
                    else:
                        have = 'No'

                    path_id = '-'

                    allmap_tsv.write(link + '\t' +sour + '\t'  + path_id + '\t' + name + '\t' +have + '\n' )

            elif sour ==  'humancyc':

                allmap_name = self.humancyc()

                for link, name in it.items():

                    if name.strip() in allmap_name.values():

                        have = 'Yes'
                    else:
                        have = 'No'

                    path_id = '-'
            
                    allmap_tsv.write(link + '\t' +sour + '\t'  + path_id + '\t' + name + '\t' +have + '\n' )

            elif  sour  in ['inoh','pid','reactome']:

                for link, name in it.items():

                    if sour == 'reactome':
                        path_id = psplit(link)[1].strip()
                    else:
                        path_id = '-'

                    have = 'No'

                    allmap_tsv.write(link + '\t' +sour + '\t'  + path_id + '\t' + name + '\t' +have + '\n' )


class findIP(object):
    """docstring for findIP"""
    def __init__(self):

        super(findIP, self).__init__()
    
    def data5u(self):


        urls = [
        'http://www.data5u.com/free/index.shtml',
        'http://www.data5u.com/free/gngn/index.shtml',
        'http://www.data5u.com/free/gnpt/index.shtml',
        'http://www.data5u.com/free/gwgn/index.shtml',
        'http://www.data5u.com/free/gwpt/index.shtml'
        ]

        ip_infos = list()

        for url in urls:

            web = requests.get(url,headers=headers,verify=False)

            # soup = bs(web,'lxml')
            soup = bs(web.content,'lxml')

            iplist = soup.find(attrs={'style':'text-align:center;'})

            ips = iplist.findAll('ul')

            for p in ips[1:]:
                ip_info = tuple([text for text in p.stripped_strings][:2])
                ip_infos.append(ip_info)

        return ip_infos

    def superfaset(self):

        url = 'http://www.superfastip.com/'

        web = requests.get(url,headers=headers,verify=False)

        soup = bs(web.content,'lxml')

        iplist = soup.find(attrs={'id':'iptable11'})

        trs = iplist.findAll('tr')

        ip_infos = list()

        for tr in trs[1:]:

            ip_info = [text for text in tr.stripped_strings][2:4]

            ip_infos.append(tuple(ip_info))
    
        return ip_infos

    def mogu(self):

        url  = 'http://www.mogumiao.com/web'

        driver = webdriver.Chrome()

        driver.get(url)

        try:
            elements = WebDriverWait(driver,10,0.5).until(EC.presence_of_all_elements_located((By.CLASS_NAME,'el-table__row')))
        finally:
            # web = requests.get(url,headers=headers,verify=False)
            web = driver.page_source

            soup = bs(web,'lxml')

            trs = soup.findAll(attrs={'class':'el-table__row'})

            ip_infos = list()

            # for tr in trs[:5]:
            for tr in trs:

                ip_info = [text for text in tr.stripped_strings][:2]

                ip_infos.append(tuple(ip_info))

                print ip_info

            driver.close()

            return ip_infos

    def get(self):

        man = crawler(today)

        agent = 'http://api.xdaili.cn/xdaili-api//privateProxy/getDynamicIP/DD20182127891Ya29Q3/acbcbe34c5d911e7bcaf7cd30abda612?returnType=2'
        web = requests.get(agent)

        print web.content

        info =  eval(web.content )

        _ip = info.get('RESULT').get('wanIp')

        _port  = info.get('RESULT').get('proxyport')

        print '_ip,_port',_ip,_port

        path_links = man.humancyc()

        man.humancyc_web(path_links,_ip,_port)

def main():

    man = findIP()
    man.get()
    # pass
    # man.kegg()
    # man.wiki()
    # man.reactome()
    # man.humancyc()
    # man.netpath()
    # man.netpath_png()
    # man.panther()
    # man.smpdb()
    # man.countPng()
    # man = findIP()
    # ip_infos1= man.data5u()
    # ip_infos2 = man.superfaset()
    # ip_infos3 = man.mogu()

    # ip_infos3 =  [('117.28.144.145','29261'),]

    # agent3 = 'http://api.xdaili.cn/xdaili-api//privateProxy/getDynamicIP/DD20182127891Ya29Q3/5deabaf620e611e79ff07cd30abda612?returnType=2'
    # agent2= 'http://api.xdaili.cn/xdaili-api//privateProxy/getDynamicIP/DD20182127891Ya29Q3/f77ddfbf108111e79ff07cd30abda612?returnType=2'
    # #120.40.134.240 45327 
    # #27.153.128.89 49232
    # agent4='http://api.xdaili.cn/xdaili-api//privateProxy/getDynamicIP/DD20182127891Ya29Q3/acbff77ec5d911e7bcaf7cd30abda612?returnType=2'
    # agent1 = 'http://api.xdaili.cn/xdaili-api//privateProxy/getDynamicIP/DD20182127891Ya29Q3/acbbc7f5c5d911e7bcaf7cd30abda612?returnType=2'
    

    

#         # func = lambda x: man.humancyc_web(links,_ip,_port)
#         # multiProcess(func,remain,size=10)

if __name__ == '__main__':
    main()
    # pass
 