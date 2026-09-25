import json,urllib.request,urllib.error,time,pathlib,hashlib,datetime,xml.etree.ElementTree as ET
out=pathlib.Path('bg-transparency/data/raw'); manifest=[]
body={'query':'CY=BGR AND PD>=20230101 AND PD<=20230107','fields':['publication-number','publication-date'],'limit':60,'scope':'ALL'}
resp=urllib.request.urlopen(urllib.request.Request('https://api.ted.europa.eu/v3/notices/search',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=30).read()
(out/'discovery.json').write_bytes(resp)
for notice in json.loads(resp)['notices']:
 ident=notice['publication-number']; url=notice['links']['xml']['MUL']; time.sleep(.5)
 raw=urllib.request.urlopen(url,timeout=30).read(); root=ET.fromstring(raw)
 forms=[e for e in root.iter() if e.tag.endswith('F03_2014') and e.get('CATEGORY')=='ORIGINAL' and e.get('LG')=='BG']
 if not forms: continue
 (out/(ident+'.xml')).write_bytes(raw)
 manifest.append({'id':ident,'xml_url':url,'source_url':notice['links']['html']['BUL'],'publication_date':notice['publication-date'],'sha256':hashlib.sha256(raw).hexdigest(),'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 print(ident,'awards',sum(e.tag.endswith('AWARD_CONTRACT') for e in forms[0].iter()),flush=True)
 if len(manifest)>=12: break
(out/'manifest.json').write_text(json.dumps({'query':body,'coverage':'Curated sample: first 12 original Bulgarian F03 award notices encountered in TED search for 1-7 January 2023; not complete national coverage.','notices':manifest},indent=2),encoding='utf-8')
print('saved',len(manifest))
