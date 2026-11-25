export function normalize(text){return String(text).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,' ');}
export function searchPages(volumes, query, {mode='words',limit=200,includeSurrounding=false}={}){
  const q=normalize(query),tokens=q.split(' ').filter(Boolean);
  if(q.length<2||q.length>140||tokens.length>12)throw new Error('Enter 2–140 characters and no more than 12 words.');
  const hits=[];let total=0;
  for(const volume of volumes){
    for(const page of volume.pages){
      if(!includeSurrounding && volume.directory_leaf_ranges?.length && !volume.directory_leaf_ranges.some(([first,last])=>page.leaf>=first&&page.leaf<=last))continue;
      const lines=page.text.split('\n');let lastHit=-4;
      for(let start=0;start<lines.length;start++){
        if(start-lastHit<3)continue;
        const snippet=lines.slice(start,start+3).join('\n').slice(0,650),n=normalize(snippet);
        const match=mode==='phrase'?n.includes(q):tokens.every(t=>new RegExp(`(?:^| )${t}(?: |$)`).test(n));
        if(!match)continue;
        lastHit=start;total++;
        if(hits.length<limit)hits.push({id:`${volume.id}:${page.leaf}:${start}`,volume_id:volume.id,year:volume.year,city:volume.city,title:volume.title,scope:volume.scope,leaf:page.leaf,reader_index:page.reader_index,printed_page:page.printed_page??null,line:start+1,snippet,query});
      }
    }
  }
  return {hits,total,truncated:total>hits.length};
}
export function scanURL(hit){
  if(!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$/.test(hit.volume_id)||!Number.isSafeInteger(hit.reader_index)||hit.reader_index<0)throw new Error('Invalid source reference');
  return `https://archive.org/details/${hit.volume_id}/page/n${hit.reader_index}/mode/1up`;
}
export function citation(hit){return `${hit.title} (${hit.year}), ${hit.printed_page?`printed page ${hit.printed_page}, `:''}scan ${hit.reader_index+1}; OCR leaf ${hit.leaf}. Internet Archive. ${scanURL(hit)}\nOCR excerpt (verify against scan): ${hit.snippet}`;}
export function exportCSV(hits){const quote=v=>'"'+(typeof v==='string'&&/^[=+@\-\t\r]/.test(v)?"'"+v:String(v??'')).replaceAll('"','""')+'"';return [['City','Edition','Title','Printed page','Reader scan','Source leaf','OCR excerpt','Source URL'],...hits.map(h=>[h.city,h.year,h.title,h.printed_page,h.reader_index+1,h.leaf,h.snippet,scanURL(h)])].map(r=>r.map(quote).join(',')).join('\r\n');}
export function validPart(raw,id){if(raw?.schema_version!==1||raw.id!==id||!Array.isArray(raw.pages)||raw.pages.length>1000)throw new Error('Unexpected search-index format');for(const p of raw.pages)if(!Number.isSafeInteger(p.leaf)||p.leaf<0||!Number.isSafeInteger(p.reader_index)||p.reader_index<0||typeof p.text!=='string'||p.text.length>250000)throw new Error('Invalid page in search index');return raw.pages;}
