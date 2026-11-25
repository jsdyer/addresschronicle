import {searchPages} from './model.mjs';
const volumes=new Map();
self.onmessage=event=>{const d=event.data;try{if(d.type==='volume'){volumes.set(d.volume.id,d.volume);return;}if(d.type==='search'){const selected=d.ids.map(id=>volumes.get(id));if(selected.some(x=>!x))throw new Error('A selected edition is not loaded.');self.postMessage({type:'result',request:d.request,...searchPages(selected,d.query,d.options)});}}catch(error){self.postMessage({type:'error',request:d.request,message:error.message});}};
