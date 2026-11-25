#!/usr/bin/env python3
"""Build bounded page-level text indexes from verified Internet Archive OCR files."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
UA = "AddressChronicle/1.0 (https://coolcode.ca/addresschronicle/; https://github.com/jsdyer/addresschronicle)"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}")


def download(url, dest, limit=160_000_000):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": UA}), timeout=90) as response, open(dest,"wb") as output:
                size = 0
                while block := response.read(512 * 1024):
                    size += len(block)
                    if size > limit:
                        raise ValueError("Source exceeds bounded download limit")
                    output.write(block)
            return size
        except HTTPError as error:
            if error.code not in (429,500,502,503,504) or attempt == 2:
                raise
            delay=error.headers.get('Retry-After','2')
            time.sleep(min(20,int(delay) if delay.isdecimal() else 2)*(attempt+1))
    raise RuntimeError("Download exhausted")


def validate_config(config):
    volumes = config.get('volumes',[])
    if not 1 <= len(volumes) <= 50:
        raise ValueError('Configure between1and50volumes')
    seen = set()
    for volume in volumes:
        if not ID.fullmatch(volume.get('id','')) or volume['id'] in seen:
            raise ValueError('Invalid or duplicate item identifier')
        seen.add(volume['id'])
        if type(volume.get('year')) is not int or not 1700<=volume['year']<=1930:
            raise ValueError('Review historical edition year before indexing')
        for key in ['city','title','edition_evidence','scope']:
            if not isinstance(volume.get(key),str) or not volume[key].strip():
                raise ValueError('Missing volume context')
        for span in volume.get('directory_leaf_ranges',[]):
            if not isinstance(span,list) or len(span)!=2 or any(type(n) is not int for n in span) or not 0<=span[0]<=span[1]:
                raise ValueError('Invalid reviewed directory leaf range')
    return config


def parse_ocr(path):
    pages=[];seen=set();reader_index=0
    # ElementTree does not resolve external entities. Reject internal declarations too.
    with open(path,'rb') as handle:
        head=handle.read(4096)
        if b'<!ENTITY' in head or b'SYSTEM ' in head:
            raise ValueError('Unexpected XML entity declaration')
    for _,obj in ET.iterparse(path,events=('end',)):
        if obj.tag!='OBJECT':
            continue
        page_file=obj.attrib.get('usemap','')
        match=re.search(r'_(\d+)\.djvu$',page_file)
        if not match:
            raise ValueError('Cannot identify source leaf number')
        leaf=int(match.group(1))
        if leaf in seen:
            raise ValueError('Duplicate source page')
        seen.add(leaf)
        lines=[' '.join(''.join(w.itertext()).strip() for w in line.findall('.//WORD')).strip() for line in obj.findall('.//LINE')]
        text='\n'.join(line for line in lines if line)
        if len(text)>250_000:
            raise ValueError('Unexpected oversized OCR page')
        if text:
            pages.append({'leaf':leaf,'reader_index':reader_index,'text':text})
        reader_index+=1
        obj.clear()
    if len(pages)<5:
        raise ValueError('OCR source contains too few searchable pages')
    return pages


def parse_labels(path):
    labels={}
    root=ET.parse(path).getroot()
    for page in root.findall('.//pageData/page'):
        leaf=page.attrib.get('leafNum','')
        if leaf.isdecimal():
            labels[int(leaf)]=page.findtext('pageNumber') or None
    return labels


def collect(config,stage):
    validate_config(config)
    retrieved=datetime.now(timezone.utc).isoformat()
    volumes=[]
    with tempfile.TemporaryDirectory() as temporary:
        temp=Path(temporary)
        for volume in config['volumes']:
            item=volume['id'];meta_path=temp/'metadata.json'
            download(f'https://archive.org/metadata/{item}',meta_path,8_000_000)
            meta=json.loads(meta_path.read_text());metadata=meta.get('metadata',{})
            if metadata.get('identifier')!=item or metadata.get('mediatype')!='texts':
                raise ValueError('Source item identity/type mismatch')
            candidates=[f for f in meta.get('files',[]) if f.get('format')=='Djvu XML' and '/' not in f.get('name','')]
            if len(candidates)!=1:
                raise ValueError(f'{item}: expected one publicly available DjVu XML file')
            source=candidates[0];source_url=f'https://archive.org/download/{item}/{quote(source["name"],safe="")}'
            xml_path=temp/'ocr.xml';size=download(source_url,xml_path)
            with open(xml_path,'rb') as source_file:
                digest=hashlib.file_digest(source_file,'sha256').hexdigest()
            pages=parse_ocr(xml_path)
            label_files=[f for f in meta.get('files',[]) if f.get('format')=='Scandata' and '/' not in f.get('name','')]
            if label_files:
                scan=temp/'scan.xml';download(f'https://archive.org/download/{item}/{quote(label_files[0]["name"],safe="")}',scan,8_000_000)
                labels=parse_labels(scan)
                for p in pages:
                    if labels.get(p['leaf']):p['printed_page']=labels[p['leaf']]
            publication={**volume,'item_url':f'https://archive.org/details/{item}','ocr_url':source_url,'source_title':metadata.get('title'),'source_catalogue_date':metadata.get('date'),'source_volume':metadata.get('volume'),'contributor':metadata.get('contributor'),'rights_statement':metadata.get('rights') or metadata.get('possible-copyright-status') or 'Consult the source item;historical publication indexed for research.','retrieved_at':retrieved,'source_sha256':digest,'source_bytes':size,'page_count':len(pages),'index_path':f'./data/volumes/{item}.json'}
            parts=[];chunk=[];chunk_bytes=0
            for page in pages:
                size=len(json.dumps(page,ensure_ascii=False).encode('utf-8'))
                if chunk and chunk_bytes+size>750_000:
                    name=f'{item}-{len(parts)+1}.json'
                    (stage/'volumes'/name).write_text(json.dumps({'schema_version':1,'id':item,'pages':chunk},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
                    parts.append({'path':f'./data/volumes/{name}','page_count':len(chunk)})
                    chunk=[];chunk_bytes=0
                chunk.append(page);chunk_bytes+=size
            if chunk:
                name=f'{item}-{len(parts)+1}.json'
                (stage/'volumes'/name).write_text(json.dumps({'schema_version':1,'id':item,'pages':chunk},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
                parts.append({'path':f'./data/volumes/{name}','page_count':len(chunk)})
            publication.pop('index_path',None)
            publication['index_parts']=parts
            volumes.append(publication)
            print(f'{item}: {len(pages)} searchable pages',flush=True)
    catalogue={'schema_version':1,'retrieved_at':retrieved,'volumes':volumes,'examples':config.get('examples',[]),'search_note':config.get('search_note',''),'source':'Internet Archive digitized books and OCR','total_pages':sum(v['page_count'] for v in volumes)}
    (stage/'catalogue.json').write_text(json.dumps(catalogue,ensure_ascii=False,indent=2)+'\n')
    (stage/'status.json').write_text(json.dumps({'schema_version':1,'checked_at':retrieved,'volumes':len(volumes),'indexed_pages':catalogue['total_pages']})+'\n')
    return catalogue


if __name__=='__main__':
    config=json.loads((ROOT/'config/collections.json').read_text())
    # All sources and indexes validate in staging before the tracked snapshot changes.
    with tempfile.TemporaryDirectory(dir=ROOT/'web',prefix='.refresh-') as temporary:
        stage=Path(temporary)/'data';(stage/'volumes').mkdir(parents=True)
        result=collect(config,stage)
        target=ROOT/'web/data';backup=Path(temporary)/'previous'
        if target.exists():os.replace(target,backup)
        try:
            os.replace(stage,target)
        except OSError:
            if backup.exists():os.replace(backup,target)
            raise
    print(f'Published local index for {len(result["volumes"])} editions and {result["total_pages"]} pages')
