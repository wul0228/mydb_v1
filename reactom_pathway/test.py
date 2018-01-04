

import os
import bs4
import json
from bs4 import BeautifulSoup as bs
import requests

notin_all_nodes = json.load(open('./notin_all_nodes.json'))

node_infos = dict()
node_notall = list()

n = 0

for node in notin_all_nodes:

    # dbId  = node.split('R-HSA-')[1].strip()
    dbId = str(node)

    # url = 'https://reactome.org/content/detail/R-ALL-%s#Homo apiens' % dbId
    url = 'https://reactome.org/content/detail/%s' % dbId

    headers = {'User-Agent':'ozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36'}

    web = requests.get(url,headers=headers,verify= False)

    soup = bs(web.content,'lxml')

    displayname = soup.find(name='h3')

    if displayname:
        displayname = displayname.text.strip()

    else:
        continue

    st_id_val,ty_val,com_val,syn_val,speciesID =('','','','','')

    st_id = soup.find(text='Stable Identifier')
    if st_id:
        st_id_val = st_id.findNext(name='div').text.strip()    

    ty = soup.find(text='Type')
    if ty:
        ty_val = ty.findNext(name='div').text.strip()

    com = soup.find(text='Compartment')
    if com:
        com_val = com.findNext(name='a').text.strip()    
        displayname = displayname + ' ' + '[' + com_val + ']'

    spe = soup.find(text='Species')
    if spe:
        spe_val = spe.findNext(name='div').text.strip()        
        if spe_val == 'Homo sapiens':
            speciesID = 48887

    syn = soup.find(text='Synonyms')
    if syn:
        syn_val =';'.join( [i.strip() for i in syn.findNext(name='div').text.strip().split(',') if i])

    
    node_infos.update({dbId:
        {
        'dbId':dbId,
       'entry_id':st_id_val,
       'schemaClass':ty_val,
       'speciesID':speciesID,
       'displayname':displayname,
       }})
    
    n +=1 

node_notall = list(set(node_notall))

with open('notin_all_nodes_info.json','w') as wf:
    json.dump(node_infos,wf,indent=8)

with open('notin_all_nodes_notall.json','w') as wf:
    json.dump(node_notall,wf,indent=8)

