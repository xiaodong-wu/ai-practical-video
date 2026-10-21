// Adapted from wallstreet-explainer at 920ed1d; MIT. See ../references/upstream/wallstreet/LICENSE.
// 逐帧渲染：页面暴露 window.ready（Promise）和 window.seek(t)（画出 t 秒那一帧），Playwright 截图，ffmpeg 编码。
// 放在片子目录外也行：--dir 指向含 index.html + timeline.json 的目录（默认当前目录）。
//   node render.mjs --dir film --stills 0.5,3.2,10       # 看帧（out/still_*.png）
//   node render.mjs --dir film --video --h 720            # 预览整片（out/visual_720.mp4，无声）
//   node render.mjs --dir film --video --h 720 --range 0:18   # 只渲一段（out/visual_720_range.mp4）
//   node render.mjs --dir film --video --h 1080           # 成片画面
// 页面要求：seek 是确定的（同一个 t 永远画出同一帧，不依赖播放时间、不用 CSS 动画），并且 await 图片解码与字体。
import fs from 'node:fs/promises'; import path from 'node:path'; import http from 'node:http';
import {handler} from './serve.mjs';
import {spawn} from 'node:child_process'; import {once} from 'node:events';
import {createRequire} from 'node:module'; import fsSync from 'node:fs'; import {fileURLToPath} from 'node:url';

const arg = k => { const i = process.argv.indexOf(k); return i >= 0 ? process.argv[i + 1] : null; };
const has = k => process.argv.includes(k);
function loadPlaywright() {
  const here = path.dirname(fileURLToPath(import.meta.url)); let local = {};
  try { local = JSON.parse(fsSync.readFileSync(path.join(here, 'local.json'), 'utf8')); } catch {}
  for (const t of [process.env.PLAYWRIGHT_FROM, local.playwright_from, path.join(process.cwd(), 'package.json'), fileURLToPath(import.meta.url)].filter(Boolean)) {
    try { return createRequire(t)('playwright'); } catch {}
  }
  throw new Error('找不到 playwright：npm i playwright，或在 scripts/local.json 写 playwright_from 指向装了它的 package.json');
}
const {chromium} = loadPlaywright();
const here = path.resolve(arg('--dir') ?? '.');
const H = Number(arg('--h') ?? 960), Wd = 2 * Math.round(H * 9 / 32), out = path.join(here, 'out');
await fs.mkdir(out, {recursive: true});
const T = JSON.parse(await fs.readFile(path.join(here, 'timeline.json'), 'utf8'));
const mime = {'.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.TTF': 'font/ttf', '.otf': 'font/otf', '.woff2': 'font/woff2', '.webm':'video/webm', '.mp4':'video/mp4'};
const worker = arg('--worker');
let server, port = Number(arg('--port'));
if (!worker) {
  server = http.createServer(handler(here));
  await new Promise(r => server.listen(0, '127.0.0.1', r)); port = server.address().port;
}
async function page() {
  const b = await chromium.launch({args: ['--force-color-profile=srgb', '--disable-lcd-text']});
  const p = await b.newPage({viewport: {width: Wd, height: H}}); const errs = [];
  p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  p.on('requestfailed', q => { const reason=q.failure()?.errorText; if(q.resourceType()==='media' && reason==='net::ERR_ABORTED')return; errs.push('请求失败 '+reason+' '+q.url()); }); p.on('response', s => { if (s.status() >= 400) errs.push(s.status() + ' ' + s.url()); });
  await p.goto(`http://127.0.0.1:${port}/index.html`); await p.evaluate(() => window.ready);
  return {b, p, errs};
}
if (arg('--stills')) {
  const {b, p, errs} = await page(); const ts = arg('--stills').split(',').map(Number);
  for (const t of ts) { await p.evaluate(t => window.seek(t), t); await p.screenshot({path: path.join(out, `still_${t.toFixed(2)}.png`)}); }
  await b.close(); server.close(); if (errs.length) {console.error([...new Set(errs)].slice(0,8));process.exit(2);} console.log('stills', ts.length); process.exit(0);
}
const fps = T.fps ?? 30, N = Math.ceil(T.duration * fps);
if (worker) {
  const [a, z] = worker.split(':').map(Number); const {b, p, errs} = await page();
  const enc = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-framerate', String(fps), '-i', 'pipe:0', '-c:v', 'libx264', '-preset', 'medium',
    '-crf', H >= 1080 ? '14' : '18', '-pix_fmt', 'yuv420p', '-r', String(fps), path.join(out, `seg_${H}_${a}.mp4`)], {stdio: ['pipe', 'ignore', 'inherit']});
  for (let f = a; f < z; f++) { await p.evaluate(t => window.seek(t), f / fps); const buf = await p.screenshot({type: 'jpeg', quality: H >= 1080 ? 96 : 92}); if (!enc.stdin.write(buf)) await once(enc.stdin, 'drain'); }
  enc.stdin.end(); const [code]=await once(enc, 'exit'); await b.close(); if(code!==0)throw Error('encoder failed '+code); if (errs.length) { console.error([...new Set(errs)].slice(0, 5)); process.exit(2); } process.exit(0);
}
if (!has('--video')) { console.log('用 --stills 或 --video'); server.close(); process.exit(1); }
const RG = arg('--range'), F0 = RG ? Math.round(Number(RG.split(':')[0]) * fps) : 0, F1 = RG ? Math.min(N, Math.round(Number(RG.split(':')[1]) * fps)) : N;
const K = Number(arg('--workers') ?? 2), size = Math.ceil((F1 - F0) / K), starts = []; const t0 = Date.now();
await Promise.all(Array.from({length: K}, (_, i) => { const a = F0 + i * size, z = Math.min(F1, a + size); if (a >= z) return null; starts.push(a);
  return new Promise((res, rej) => { const c = spawn(process.execPath, [fileURLToPath(import.meta.url), '--dir', here, '--worker', `${a}:${z}`, '--port', String(port), '--h', String(H)], {stdio: 'inherit'}); c.on('exit', x => x === 0 ? res() : rej(new Error('worker ' + a))); }); }));
starts.sort((a, b) => a - b);
await fs.writeFile(path.join(out, `list_${H}.txt`), starts.map((s,i) => `file 'seg_${H}_${s}.mp4'\nduration ${(((starts[i+1]??F1)-s)/fps).toFixed(9)}`).join('\n'));
const vout = path.join(out, RG ? `visual_${H}_range.mp4` : `visual_${H}.mp4`);
await new Promise((res, rej) => { const c = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', path.join(out, `list_${H}.txt`), '-c', 'copy', vout], {stdio: 'inherit'}); c.on('exit', x => x === 0 ? res() : rej()); });
server.close(); console.log('rendered', F1 - F0, 'frames in', ((Date.now() - t0) / 1000).toFixed(1), 's ->', vout);

