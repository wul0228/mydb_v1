#!/usr/bin/env python
# -*-coding:utf-8-*-
# date: 2018/1/25
# author:wuling
# emai:ling.wu@myhealthgene.com

#this model set  to download,extract,standard insert and select variant data from cosmic

import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  
import paramiko

__all__ = ['downloadData','extractData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(cosmic_variant_model,cosmic_variant_raw,cosmic_variant_store,cosmic_variant_db,cosmic_variant_map) = buildSubDir('cosmic_variant')

log_path = pjoin(cosmic_variant_model,'cosmic_variant.log')

# main code

def downloadData(redownload=True):

    trans = paramiko.Transport(('sftp-cancer.sanger.ac.uk',22))
    trans.connect(username='201421107002@stu.hebut.edu.cn',password='lifeifei')
    sftp = paramiko.SFTPClient.from_transport(trans)

   #function introduction
    #args:
    
    return

def extractData():
    
    #function introduction
    #args:
    
    grch38_filepath = '/home/user/project/dbproject/mydb_v1/cosmic_variant/dataraw/v83/grch38/CosmicCodingMuts.vcf'
    grch37_filepath = '/home/user/project/dbproject/mydb_v1/cosmic_variant/dataraw/v83/grch37/CosmicCodingMuts.vcf'

    process = parser(today)

    process.variant_info([grch37_filepath,grch38_filepath])

    return

def updateData():

    #function introduction
    #args:

    return

def selectData():

    #function introduction
    #args:
    
    return

class parser(object):

    #this class is set to parser all raw file to extract content we need and insert to mongodb

    def __init__(self,date):

        super(parser,self).__init__()

        self.date = date
        pass

    def equalBase(self,chrom,pos,ref,ref_n,alt,alt_n,cos_id):

        # find the same base, mark the left max index and right min index in ref and alt 

        left_index = None
        index = 0
        for i,j in zip(ref,alt):
            if i == j:
                left_index = index
            else:
                break
            index += 1

        _ref = ref[ : :-1]
        _alt = alt[ : :-1]

        right_index = None
        index = 0
        for i,j in zip(_ref,_alt):
            if i == j:
                right_index = ref_n -(index + 1)
            else:
                break
            index += 1

        #-------------------------------------------------------------------------------------
        if left_index != None and right_index != None:

            ref = ref[left_index + 1:right_index]
            alt = alt[left_index + 1:right_index]

            pos_start = int(pos) + (left_index + 1)
            pos_end = pos_start + len(ref) -1

        elif left_index != None and right_index == None:
            # CAT --- CTG or CAT --- CAG
            ref = ref[left_index + 1:]
            alt = alt[left_index + 1:]

            pos_start = int(pos) + (left_index + 1)
            pos_end = pos_start + len(ref) -1

        elif left_index == None  and right_index != None:
 
            ref = ref[:right_index]
            alt = alt[:right_index]

            pos_start = pos
            pos_end = pos_start + len(ref) - 1

        elif  left_index == None and right_index == None:

            #CAT --- GAC # pos ref alt no change
            pos_start = pos
            pos_end = pos_start + len(ref) - 1

        var_id = '{}:{}:{}:{}:{}'.format(chrom,pos_start,pos_end,ref,alt)

        return var_id

    def nequalBase1(self,chrom,pos,ref,ref_n,alt,alt_n,cos_id):

        # ref_n > alt_n
        left_index = None
        index = 0
        for i,j in zip(ref,alt):
            if i == j:
                left_index =index
            else:
                break
            index += 1

        if left_index != None:
            remain = alt_n - (left_index + 1) # the remained base number after del the left equ base
            left_equ = left_index + 1 # the number of bases  is same in the left of  ref and alt
        else:
            remain = alt_n 
            left_equ = 0

        _ref = ref[::-1][:remain]
        _alt = alt[::-1][:remain]

        right_index = None
        index =0
        for i,j in zip(_ref,_alt):
            if i == j:
                right_index = ref_n -1 - index
                right = index
            else:
                break
            index += 1

        if right_index != None:
            right_equ =  ref_n - right_index
        else:
            right_equ = 0 # the number of bases  is same in the right of  ref and alt

        #----------------------------------------------------------------------------------------------------------------
        if left_index != None and right_index != None:

            ref = ref[left_index+1:right_index]
            alt  = alt[left_index+1:alt_n-right_equ]


            pos_start = int(pos) + left_index + 1
            pos_end = pos_start  +  len(ref) -1

        elif left_index == None and right_index != None:

            # no this condition
            ref = ref[:right_index]
            alt  = alt[:alt_n-1-right_equ]
            pos_start = pos
            pos_end = pos_start +  len(ref) -1

        elif left_index != None and right_index == None:

            ref = ref[left_index+1:]
            alt  = alt[left_index+1:]
        
            pos_start = int(pos) + left_index + 1
            pos_end = pos_start +  len(ref) -1

        elif left_index == None and right_index == None:
            # no this condition
            pos_start = pos
            pos_end = pos_start +  len(ref) -1

        if not alt:
                alt = '-'

        var_id = '{}:{}:{}:{}:{}'.format(chrom,pos_start,pos_end,ref,alt)

        return var_id

    def nequalBase2(self,chrom,pos,ref,ref_n,alt,alt_n,cos_id):

        # ref_n < alt_n
        left_index = None
        index = 0
        for i,j in zip(ref,alt):
            if i == j:
                left_index =index
            else:
                break
            index += 1

        if left_index != None: #!!!
            remain = ref_n - (left_index + 1) # the remained base number after del the left equ base
            left_equ = left_index + 1 # the number of bases  is same in the left of  ref and alt
        else:
            remain = ref_n #!!!
            left_equ = 0

        _ref = ref[::-1][:remain]
        _alt = alt[::-1][:remain]

        right_index = None
        index =0
        for i,j in zip(_ref,_alt):
            if i == j:
                right_index = alt_n -1 - index#!!!
                right = index
            else:
                break
            index += 1

        if right_index != None:
            right_equ =  alt_n - right_index#!!!
        else:
            right_equ = 0 # the number of bases  is same in the right of  ref and alt

        #----------------------------------------------------------------------------------------------------------------
        if left_index != None and right_index != None:

            
            ref = ref[left_index+1:ref_n-right_equ]#!!!
            alt  = alt[left_index+1:right_index]#!!!
            if not ref:
                ref = '-'
                pos_start = int(pos) + left_index#!!!
                pos_end = pos_start + 1
            else:
                pos_start = int(pos) + left_index + 1#!!!
                pos_end = pos_start + len(ref) -1

        elif left_index == None and right_index != None:

            ref = ref[:ref_n-right_equ]
            alt  = alt[:right_index]
            if not ref:
                pos_start = pos -1
                pos_end = pos
            else:
                pos_start = pos
                pos_end = pos_start + len(ref) -1
            # no this condition

        elif left_index != None and right_index == None:
            pos = int(pos) + left_index
            ref = ref[left_index+1:]
            alt  = alt[left_index+1:]
            if not ref:
                ref = '-'
                pos_start = int(pos) + left_index#!!!
                pos_end = pos_start + 1
            else:
                pos_start = int(pos) + left_index + 1#!!!
                pos_end = pos_start + len(ref) -1

        elif left_index == None and right_index == None:

            pos_start = pos
            pos_end = pos_start  + len(ref) -1
        
        var_id = '{}:{}:{}:{}:{}'.format(chrom,pos_start,pos_end,ref,alt)

        return var_id

    def variant_info(self,filepaths):

        f = open('./variant_id.txt','w')

        for filepath in filepaths:

            if filepath.endswith('gz'):

                gunzip = 'gunzip {}'.format(filepath)

                filepath = filepath.rsplit('.gz',1)[0].strip()

            grch = psplit(psplit(filepath)[0])[1].strip()

            tsvfile = open(filepath)

            n = 0

            for line in tsvfile:

                if line.startswith('##'):
                    continue

                elif line.startswith('#'):

                    keys = line.replace('#','',1).strip().split('\t')

                else:

                    data = line.strip().split('\t')

                    dic = dict([(key,val) for key,val in zip(keys,data)])

                    cos_id = dic.get('ID')

                    chrom = dic.get('CHROM')

                    pos = dic.get('POS')

                    pos = int(pos)

                    ref = dic.get('REF');ref_n = len(ref)

                    alt = dic.get('ALT');alt_n = len(alt)

                    # print cos_id
                    # print 'pos,ref,alt',pos,ref,alt
                    # print 'ref_n,alt,alt_n',ref_n,alt_n

                    if ref_n == alt_n:
                        var_id = self.equalBase(chrom,pos,ref,ref_n,alt,alt_n,cos_id)
                    else: #ref_n != alt_n:
                        if ref_n>alt_n:
                            var_id = self.nequalBase1(chrom,pos,ref,ref_n,alt,alt_n,cos_id)
                        else:
                             var_id = self.nequalBase2(chrom,pos,ref,ref_n,alt,alt_n,cos_id)

                    f.write(cos_id + '\t' + str(pos)+ '\t' +  ref +  '\t' + alt +  '\t' + var_id + '\n')
                    f.flush()

                n += 1
            
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


class PySFTP(object):

    def __init__(self):

        print('Create a SFTP Deload Project!')

    def connectSFTP(self,remotename,remoteport,loginname,loginpassword):

        try:
            sftp = paramiko.Transport(remotename,remoteport)
            print('connect success!')

        except Exception as e:
            print('connect failed,reasons are as follows:',e)
            return (0,'connect failed!')

        else:
            try:
                sftp.connect(username = loginname,password = loginpassword)
                print('login success!')

            except Exception as e:
                print('connect failed,reasons are as follows:',e)
                return (0,'login failed!')
            else:
                return (1,sftp)

    def download(self,remotename,remoteport,loginname,loginpassword,remoteaddress,localaddress):

        sftp = self.connectSFTP(remotename,remoteport,loginname,loginpassword)

        if sftp[0] != 1:
            print(sftp[1])
            sys.exit()

        sftp = paramiko.SFTPClient.from_transport(sftp[1])

        filelist = sftp.listdir(remoteaddress)

        filelist = filelist[:2]#测试时仅下载了2个文件

        print('begin downloading!')

        for i in filelist:
            try:              
                start = time.clock()
                sftp.get(remoteaddress+'/'+i,localaddress+'\\'+i)
                end = time.clock()
                print('success download %s,use time %fs' % (i,(end - start)))               
            except Exception as e:
                print('failed download %s,reason are as follows:' % i,e)
                with open(r'C:\Users\Neil\Desktop\Test\time.log','a') as f:
                    f.write('failed download %s,reason are as follows:' % i,e)
                continue #下载出错继续进行下一步
            else:
                with open(r'C:\Users\Neil\Desktop\Test\time.log','a') as f:
                    f.write('success download %s\n' % i)

    # def main():
        # sftp = PySFTP()
        # sftp.download(remotename = 'SFTP的host地址',
        #                           remoteport=21,     #SFTP的默认端口号是21
        #                           loginname = '用户名',
        #                           loginpassword = '密码',
        #                           remoteaddress='下载文件所在的路径',
        #                           localaddress = r'需要下载到的地址路径') 

if __name__ == '__main__':
    main()

def main():

    modelhelp = 'help document'

    funcs = (downloadData,extractData,updateData,selectData,dbMap,cosmic_variant_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    # main()

    # extractData()
    sftp = PySFTP()
    sftp.download(remotename = 'sftp-cancer.sanger.ac.uk',
                                  remoteport=21,     #SFTP的默认端口号是21
                                  loginname = '201421107002@stu.hebut.edu.cn',
                                  loginpassword = 'lifeifei',
                                  remoteaddress='/files/grch37/cosmic/v83/',
                                  localaddress = './dataraw/')
  # sftp.download(remotename = 'SFTP的host地址',
    #                               remoteport=21,     #SFTP的默认端口号是21
    #                               loginname = '用户名',
    #                               loginpassword = '密码',
    #                               remoteaddress='下载文件所在的路径',
    #                               localaddress = r'需要下载到的地址路径') 
