#!/usr/bin/env python
# ---coding:utf-8---
# date:20171123
# author:wuling
# emai:ling.wu@myhealthgene.com

# this model is set to
import sys
sys.path.append('../..')
sys.setdefaultencoding = ('utf-8')
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from share import *
from config import *
from template import *

version = '1.0'

model_name = psplit(os.path.abspath(__file__))[1]

current_path = psplit(os.path.abspath(__file__))[0]

models =  [name for name in listdir('./') if  not any([name.endswith(x) for x in ['.py','.pyc','.readme','.git']]) and not name.startswith('_')]

for model in models:

    import_model = "from {} import  {}".format(model,model)
    exec(import_model)

class manager(object):

    #his class is to mange all models  under this directory 

    def __init__(self,modelname):

        self.modelname = modelname

    def helper(self):

        print  manage_help

    def initModel(self):
    
        #this function is to init a new model with specified model name
        #modelname --- the specified model's name
    
        # check to see if modelname  existed
        print '-'*50

        if self.modelname in models:

            tips = 'the model {} existed ,do  you still want to  create it ? (y/n) : '.format(self.modelname)

            choice = raw_input(tips)

            if choice == 'n':
                return
        # create major dir
        createDir(pjoin('./',self.modelname))

        # create dataload,dataraw,datastore and database  
        (_model,_raw,_store,_db,_map) = buildSubDir(self.modelname)
        createDir(pjoin(_db,'docs'))

        # create moldename.py
        pyload = open(pjoin(_model,'{}.py'.format(self.modelname)),'w')
        pyload.write(model_py.replace('*'*6,self.modelname).strip() + '\n')
        pyload.close()

        initload = open(pjoin(_model,'__init__.py'),'w')
        initload.close()

        introload = open(pjoin(_model,'{}.readme'.format(self.modelname)),'w')
        introload.write(model_readme.replace('*'*6,self.modelname) + '\n')
        introload.close()

        print 'model %s  created successfully !' % self.modelname

    def importModel(self,allupdate=False):
        '''
        this function is to return a update function of all model under current directory
        modelname --- the specified model's name
        allupdate -- default False,if set to true, update all model one by one
        '''
        updates = {
        'ncbi_gene':ncbi_gene.updateData,
        'ensembl_gene':ensembl_gene.updateData,
        'go_gene':go_gene.updateData,
        'hgnc_gene':hgnc_gene.updateData,
        'proteinAtlas':proteinAtlas.updateData,
        'kegg_pathway':kegg_pathway.updateData,
        'reactom_pathway':reactom_pathway.updateData,
        'wiki_pathway':wiki_pathway.updateData,
        'disgenet_disease':disgenet_disease.updateData,
        'miRTarBase':miRTarBase.updateData,
        'hpo_phenotype':hpo_phenotype.updateData,
        'clinvar_variant':clinvar_variant.updateData,
        'igsr_variant':igsr_variant.updateData,
        # 'trrust_gene':trrust_gene.updateData,
        # 'cosmic_disease':cosmic_disease.updateData,
        }

        return updates if allupdate else updates.get(self.modelname)

    def updateModel(self):
        '''
        this function is to update the specified mode 
        modelname ---the specified model's name,if == 'all',all model would be updated
        '''
        update_log = pjoin('./','_log')

        createDir(update_log)

        if self.modelname != 'all':

            update_log_path =  pjoin(update_log,'update_part_{}.log'.format(today))

            if self.modelname not in models:

                print 'No model named {} '.format(self.modelname)
                sys.exit()

            else:

                log = open(update_log_path,'w') 

                print '+'*50
                log.write('+'*50 + '\n')

                try:
                    update_fun = self.importModel(allupdate=False)
                    update_result = update_fun()
                    log.write(self.modelname  + '-'*(30-len(self.modelname)) + update_result + '\n'*2)
                    log.flush()

                except Exception,e:
                    print e
                    log.write(self.modelname  + '-'*(30-len(self.modelname)) + 'error' + '\n')
                    log.write(str(e) + '\n'*2)
                    log.flush()

        else:
            update_log_path =  pjoin(update_log,'update_all_{}.log'.format(today))

            log = open(update_log_path,'w') 

            update_funs =self.importModel(allupdate=True)

            n = 1
            log.write('+'*50 + '\n')

            for model,fun in update_funs.items():
                try:
                    print '*'*80
                    print n,model,'\n'
                    update_result = fun()
                    log.write(model  + '-'*(30-len(model)) + update_result + '\n'*2)
                    log.flush()

                except Exception,e:
                    print 'x'*50
                    print e
                    print 'x'*50
                    log.write(model  + '-'*(30-len(model)) + 'error' + '\n')
                    log.write(str(e) + '\n'*2)
                    log.flush()

                n += 1

        log.close()

        text = open(update_log_path).read()

        email_info = {
        'text':text,
        'mail_host':'smtp.mxhichina.com',
        'mail_port':25,
        'mail_user':'ling.wu@myhealthgene.com',
        'mail_pass':'281625WuLing',
        'sender':'ling.wu@myhealthgene.com',
        'receivers':['1169804109@qq.com',],
        'message_from':'wul\'s worl mail',
        'message_to':'wul\'s qq email',
        'message_subject':'update mydb_v1',
        }

        self.sendEmail(email_info)

    def sendEmail(self,email_info):

        message = MIMEText(email_info.get('text'), 'plain', 'utf-8')
        message['From'] = Header(email_info.get('message_from'), 'utf-8')
        message['To'] =  Header(email_info.get('message_to'), 'utf-8')
        message['Subject'] = Header(email_info.get('message_subject'), 'utf-8')
         
        try:
            smtpObj = smtplib.SMTP()

            smtpObj.connect(email_info.get('mail_host'),email_info.get('mail_port'))
            print 'connect done'

            smtpObj.login(email_info.get('mail_user'),email_info.get('mail_pass'))
            print 'login done'

            smtpObj.sendmail(email_info.get('sender'),email_info.get('receivers'), message.as_string())
            print "send email successful"

        except Exception,e:
            print "Error: can't send emai"
            print e

class query(object):

    """docstring for query"""
    
    def __init__(self):

        conn = MongoClient('localhost',27017)

        db  = conn.get_database('mydb_v1')

        self.db = db

    def showColInDB(self):

        col_names =  self.db.collection_names() 

        col_names.sort()

        for i ,colname in enumerate(col_names):

            index = i + 1
            print index,' '*(5-len(str(index))),colname

    def showColField(self):
        pass


    def selectFromModel(self,modelname,field,value,outputdir):

        # default selcet from the newest edition
        createDir(outputdir)

        storedir = pjoin(outputdir,'{}_{}_{}'.format(modelname,field,value))

        createDir(storedir)

        col = self.db.get_collection(modelname)

        docs = col.find({field:value})

        n = 0 

        for doc in docs:

            doc.pop('_id')

            with open(pjoin(storedir,'{}.json'.format(n)),'w') as wf:

                json.dump(doc,wf,indent=8)

                n += 1

        print 'allfind ',n

def main():
    
    try:

        (opts,args) = getopt.getopt(sys.argv[1:],"hci:u:d:f:v:o:",['--help','--collections','--init=','--update=','--database=','--field=','--value=','--output='])

        (base,field,val,out) = ("","","","")

        for op,value in opts:

            man = manager(value)

            if op in ("-h","--help"):
                man.helper()

            elif op in ('-i','--init'):
                man.initModel()

            elif op in ('-u','--update'):
                man.updateModel()

            elif op in ('-c','--collections'):
                man = query()
                man.showColInDB()

            elif op in ('-d','--database'):
                base = value

            elif op in ('-f','--field'):
                field = value
                
            elif op in ('-v','--value'):
                val = value

            elif op in ('-o','--output'):
                out = value

            if all([bool(i) for i in [base,field,val,out]]):
            # if base and field and val and out:
                man = query()
                man.selectFromModel(base,field,val,out)

    except getopt.GetoptError:

        sys.exit()

if __name__ == '__main__':

    main()
