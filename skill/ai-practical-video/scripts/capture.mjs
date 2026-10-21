// Record actual browser interactions; never reconstruct a third-party application's UI.
import fs from 'node:fs/promises'; import path from 'node:path'; import http from 'node:http';
import {createRequire} from 'node:module'; import {fileURLToPath} from 'node:url';
const arg=k=>process.argv[process.argv.indexOf(k)+1];
let local={};try{local=JSON.parse(await fs.readFile(new URL('local.json',import.meta.url),'utf8'));}catch{}
const {chromium}=createRequire(process.env.PLAYWRIGHT_FROM||local.playwright_from||import.meta.url)('playwright');
const run=path.resolve(arg('--run')), plan=JSON.parse(await fs.readFile(path.join(run,'demo/capture-plan.json'),'utf8'));
const out=path.join(run,'demo/capture');await fs.mkdir(out,{recursive:true});
const mime={'.html':'text/html; charset=utf-8','.json':'application/json','.csv':'text/csv; charset=utf-8','.png':'image/png','.webm':'video/webm','.js':'text/javascript','.css':'text/css'};
const server=http.createServer(async(q,r)=>{try{const p=path.resolve(run,'.'+decodeURIComponent(new URL(q.url,'http://local').pathname));if(!p.startsWith(run+path.sep))throw Error('outside root');r.setHeader('Content-Type',mime[path.extname(p)]||'application/octet-stream');r.end(await fs.readFile(p));}catch{r.writeHead(404).end();}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser,ctx; const log=[];
try{
 browser=await chromium.launch();ctx=await browser.newContext({viewport:{width:630,height:840},recordVideo:{dir:out,size:{width:630,height:840}}});
 const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const t0=Date.now();await page.goto(plan.url||`http://127.0.0.1:${server.address().port}/demo/viewer.html`);await page.waitForLoadState('networkidle');
 for(const [i,a] of plan.actions.entries()){
   const start=(Date.now()-t0)/1000;await page.waitForTimeout(200);
   const actionStart=(Date.now()-t0)/1000;
   if(a.kind==='click')await page.locator(a.selector).click();
   else if(a.kind==='fill')await page.locator(a.selector).fill(a.value);
   else if(a.kind==='press')await page.locator(a.selector).press(a.value);
   else if(a.kind!=='observe')throw Error('unsupported action');
   if(a.expect)await page.getByText(a.expect,{exact:false}).first().waitFor({state:'visible'});
   await page.waitForTimeout(600);const settled=(Date.now()-t0)/1000;
   await page.screenshot({path:path.join(out,`step-${i}.png`)});
   await fs.writeFile(path.join(out,`step-${i}.txt`),await page.locator('body').innerText());
   await page.waitForTimeout(a.hold_ms||3200);
   log.push({index:i,action:a,start,action_start:actionStart,settled_at:settled,end:(Date.now()-t0)/1000,url:page.url(),screenshot:`demo/capture/step-${i}.png`});
 }
 const video=page.video();await ctx.close();ctx=null;await video.saveAs(path.join(out,'recording.webm'));await video.delete();
 if(errors.length)throw Error(errors.join('; '));
 await fs.writeFile(path.join(out,'log.json'),JSON.stringify({captured_at:new Date().toISOString(),viewport:{width:630,height:840},actions:log},null,2));
 console.log('Recorded',log.length,'real browser actions');
}finally{if(ctx)await ctx.close();if(browser)await browser.close();server.close();}
