// Project-scoped LRU. Active tracks own their buffers independently of this cache.
export class BufferCache {
 constructor(maxBytes=256*1024**2){this.maxBytes=maxBytes;this.bytes=0;this.items=new Map();}
 get(key){const value=this.items.get(key);if(value){this.items.delete(key);this.items.set(key,value);}return value;}
 put(key,buffer){if(!buffer)return;const size=buffer.length*buffer.numberOfChannels*4,old=this.items.get(key);if(old){this.bytes-=old.length*old.numberOfChannels*4;this.items.delete(key);}if(size>this.maxBytes)return;this.items.set(key,buffer);this.bytes+=size;while(this.bytes>this.maxBytes){const first=this.items.keys().next().value,value=this.items.get(first);this.bytes-=value.length*value.numberOfChannels*4;this.items.delete(first);}}
 clear(){this.items.clear();this.bytes=0;}
}
export const bufferKey=t=>JSON.stringify([t.id,t.instrument,t.tone?.attack??.5,t.tone?.release??.5]);
