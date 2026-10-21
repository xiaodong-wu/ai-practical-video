import fs from 'node:fs/promises';import path from 'node:path';
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript','.json':'application/json','.webm':'video/webm','.mp4':'video/mp4','.png':'image/png','.jpg':'image/jpeg','.css':'text/css'};
export function handler(root){return async(q,r)=>{try{
 const p=path.resolve(root,'.'+decodeURIComponent(new URL(q.url,'http://local').pathname));if(!p.startsWith(root+path.sep))throw Error('outside root');
 const b=await fs.readFile(p);const headers={'Content-Type':types[path.extname(p)]||'application/octet-stream','Accept-Ranges':'bytes','Cache-Control':'no-store'};
 const range=q.headers.range?.match(/^bytes=(\d+)-(\d*)$/);
 if(range){const start=Number(range[1]),end=Math.min(range[2]?Number(range[2]):b.length-1,b.length-1);if(start>=b.length||end<start){r.writeHead(416,{'Content-Range':`bytes */${b.length}`}).end();return;}r.writeHead(206,{...headers,'Content-Length':end-start+1,'Content-Range':`bytes ${start}-${end}/${b.length}`}).end(b.subarray(start,end+1));}
 else r.writeHead(200,{...headers,'Content-Length':b.length}).end(b);
}catch{r.writeHead(404).end();}};}
