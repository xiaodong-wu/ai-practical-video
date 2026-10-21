#!/usr/bin/env python3
"""Measured timeline, real-capture rendering, QA and version-coherent delivery."""
import argparse, math, pathlib, shutil, subprocess, sys, zipfile, re
from pipeline import read,write,sha,digest,probe,duration,seal,reconcile,lock,now,inside,GLOBAL_HISTORY
HERE=pathlib.Path(__file__).resolve().parent

def srt_time(t):
    ms=round(t*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
def timeline(run):
    m=reconcile(run)
    if m['stages'].get('voice',{}).get('state')!='complete':raise ValueError('voice is missing or stale')
    v=read(run/'voice/manifest.json');sc=read(run/'voice/measured-scenes.json');cap=read(run/'demo/capture/log.json')
    if not 60<=v['duration']<=90: raise ValueError('revise narration to fit 60–90 seconds')
    for s in sc:
        a=cap['actions'][s['capture_index']];s.update(video='../demo/capture/recording.webm',clip_start=a['start'],clip_end=a['end']-.15)
    t={'fps':30,'width':1080,'height':1920,'duration':math.ceil(v['duration']*30)/30,'scenes':sc,'captions':v['segments'],'script_hash':v['script_hash']}
    write(run/'film/timeline.json',t);shutil.copyfile(HERE.parent/'assets/film.html',run/'film/index.html')
    # Render root contains demo and film so capture paths remain local and editable.
    shutil.copyfile(run/'film/index.html',run/'index.html');shutil.copyfile(run/'film/timeline.json',run/'timeline.json')
    troot=read(run/'timeline.json')
    for s in troot['scenes']:s['video']='demo/capture/recording.webm'
    write(run/'timeline.json',troot)
    srt='\n\n'.join(f'{i+1}\n{srt_time(c["start"])} --> {srt_time(c["end"])}\n{c["text"]}' for i,c in enumerate(v['segments']))+'\n'
    (run/'film/subtitles.srt').write_text(srt,encoding='utf-8')
    seal(run,'timeline',['voice/manifest.json','voice/measured-scenes.json','demo/capture/log.json','demo/capture/recording.webm'],['film/timeline.json','film/index.html','film/subtitles.srt','index.html','timeline.json'])

def command(args): subprocess.run([str(x) for x in args],check=True)
def render(run, final=False):
    m=reconcile(run);needed='preview' if final else 'timeline'
    if m['stages'].get(needed,{}).get('state')!='complete':raise ValueError('required stage incomplete: '+needed)
    if final:
        q=read(run/'qa/preview-review.json')
        if not all(q.get(k) is True for k in ['visual_checked','phone_readable','claims_match','audio_checked','no_clipping']):raise ValueError('preview review not passed')
        if q.get('preview_sha256')!=sha(run/'preview.mp4'):raise ValueError('preview review is stale')
    h=1920 if final else 960
    command(['node',HERE/'render.mjs','--dir',run,'--video','--h',h,'--workers','2'])
    out=run/('final.mp4' if final else 'preview.mp4')
    # No atempo, no fixed -t, no shortest: preserve the complete narration.
    command(['ffmpeg','-v','error','-y','-i',run/f'out/visual_{h}.mp4','-i',run/'voice/narration.wav','-map','0:v','-map','1:a','-c:v','copy','-af','loudnorm=I=-16:TP=-1.5:LRA=9','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',out])
    seal(run,'final' if final else 'preview',['timeline.json','index.html','voice/narration.wav']+(['qa/preview-review.json'] if final else []),[out.name])

def covers(run):
    from PIL import Image,ImageDraw,ImageFont
    data=read(run/'script/platforms.json')
    local=read(HERE/'local.json') if (HERE/'local.json').exists() else {}
    candidates=[local.get('cover_font'),'/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/Hiragino Sans GB.ttc','/System/Library/Fonts/STHeiti Medium.ttc']
    fontpath=next((p for p in candidates if p and pathlib.Path(p).is_file()),None)
    if not fontpath:raise ValueError('configure scripts/local.json cover_font with a CJK font path')
    for platform in ['wechat','douyin']:
        im=Image.new('RGB',(1080,1920),'#0d1729');d=ImageDraw.Draw(im)
        f=lambda n:ImageFont.truetype(fontpath,n)
        d.text((78,230),'AI · 做给你看',font=f(42),fill='#68e0b2')
        for i,line in enumerate(data[platform]['cover_lines']):d.text((78,350+i*112),line,font=f(86),fill='#f6f4ec')
        d.rounded_rectangle((78,690,960,1540),radius=28,fill='#edf4f3')
        shot=Image.open(run/'demo/capture/step-0.png').convert('RGB');shot.thumbnail((830,790));im.paste(shot,(100,715))
        d.text((78,1640),data[platform]['cover_subtitle'],font=f(36),fill='#adc5ce')
        d.text((78,1710),'结果与规则 · 完整拆解' if platform=='wechat' else '看操作 · 学一招',font=f(34),fill='#68e0b2' if platform=='wechat' else '#67d6ef')
        im.save(run/f'delivery/{platform}-cover.png')

def qa(run):
    from PIL import Image,ImageDraw
    m=reconcile(run)
    if m['stages'].get('final',{}).get('state')!='complete':raise ValueError('final not complete')
    t=read(run/'timeline.json');p=probe(run/'final.mp4');vs=next(x for x in p['streams'] if x['codec_type']=='video');au=next(x for x in p['streams'] if x['codec_type']=='audio')
    checks={'h264':vs['codec_name']=='h264','aac':au['codec_name']=='aac','size':(vs['width'],vs['height'])==(1080,1920),'fps':vs['avg_frame_rate']=='30/1','duration':60<=float(p['format']['duration'])<=90,'complete_audio':float(au['duration'])>=duration(run/'voice/narration.wav')-.05,'sync_end':abs(float(vs['duration'])-float(au['duration']))<.15,'script_current':t['script_hash']==sha(run/'script/script.json')}
    decoded=subprocess.run(['ffmpeg','-v','error','-i',str(run/'final.mp4'),'-f','null','-'],capture_output=True,text=True)
    checks['full_decode']=decoded.returncode==0 and not decoded.stderr.strip()
    # Examine the content area on every final frame, excluding the persistent source header.
    sig=subprocess.run(['ffmpeg','-v','error','-i',str(run/'final.mp4'),'-vf','crop=800:650:100:670,signalstats,metadata=mode=print:file=-','-an','-f','null','-'],capture_output=True,text=True,check=True).stdout
    mins=[int(x) for x in re.findall(r'lavfi.signalstats.YMIN=(\d+)',sig)];maxs=[int(x) for x in re.findall(r'lavfi.signalstats.YMAX=(\d+)',sig)]
    ranges=[b-a for a,b in zip(mins,maxs)]
    checks['content_each_frame']=len(ranges)==int(vs.get('nb_frames',len(ranges))) and bool(ranges) and min(ranges)>30
    write(run/'qa/content-check.json',{'frames_checked':len(ranges),'minimum_luma_range':min(ranges) if ranges else None,'threshold':30,'region':[100,670,800,650]})
    audit=read(run/'qa/layout.json');checks['layout']=all(x['captionFits'] and x['headingFits'] and x['videoReady'] and x.get('screenNonBlank') for x in audit)
    review=read(run/'qa/preview-review.json');checks['review_current']=review['preview_sha256']==sha(run/'preview.mp4') and all(review[k] for k in ['visual_checked','phone_readable','claims_match','audio_checked','no_clipping'])
    sheet=Image.new('RGB',(360*4,640*2),'#152135');draw=ImageDraw.Draw(sheet)
    for i,s in enumerate(t['scenes'][:8]):
        output=run/f'qa/phone-{i}.jpg';command(['ffmpeg','-v','error','-y','-ss',s['start']+.5,'-i',run/'final.mp4','-frames:v','1','-vf','scale=360:640',output]);sheet.paste(Image.open(output),((i%4)*360,(i//4)*640))
    sheet.save(run/'qa/contact-sheet.jpg');covers(run)
    report={'at':now(),'status':'passed' if all(checks.values()) else 'failed','checks':checks,'media':p,'final_sha256':sha(run/'final.mp4'),'notes':['local finished video only; not published','AI disclosure suggestion must be checked against the current upload form'],'manual_review':review}
    write(run/'qa/report.json',report)
    if not all(checks.values()):raise ValueError('QA failed: '+str(checks))
    seal(run,'qa',['final.mp4','qa/layout.json','qa/preview-review.json','script/platforms.json'],['qa/report.json','qa/content-check.json','qa/contact-sheet.jpg','delivery/wechat-cover.png','delivery/douyin-cover.png'])

def package(run):
    m=reconcile(run)
    if m['stages'].get('qa',{}).get('state')!='complete':raise ValueError('QA must pass before packaging')
    delivery=run/'delivery';shutil.copyfile(run/'final.mp4',delivery/'video.mp4');shutil.copyfile(run/'film/subtitles.srt',delivery/'subtitles.srt')
    for name,p in [('platforms.json','script/platforms.json'),('storyboard.json','script/script.json'),('quality-report.json','qa/report.json'),('contact-sheet.jpg','qa/contact-sheet.jpg'),('sources.json','research/selection.json')]:shutil.copyfile(run/p,delivery/name)
    (delivery/'narration.txt').write_text('\n\n'.join(s['narration'] for s in read(run/'script/script.json')['scenes']),encoding='utf-8')
    platforms=read(run/'script/platforms.json')
    for name,label in [('wechat','微信视频号'),('douyin','抖音')]:
        p=platforms[name]
        (delivery/(label+'-发布文案.txt')).write_text('标题：'+p['title']+'\n\n简介：'+p['description']+'\n\n话题：'+' '.join('#'+h for h in p['hashtags'])+'\n\nAI声明：'+p['ai_disclosure']+'\n\n相关服务方向：'+p['monetization']+'\n',encoding='utf-8')
    write(delivery/'delivery-manifest.json',{'run_id':m['run_id'],'status':'completed_local','published':False,'final_sha256':sha(run/'final.mp4'),'script_sha256':sha(run/'script/script.json'),'duration':duration(run/'final.mp4'),'resolution':[1080,1920],'voice':read(run/'voice/manifest.json')['voice']})
    shutil.copytree(run/'demo/files',delivery/'example-files',dirs_exist_ok=True)
    shutil.copytree(HERE.parent/'references/upstream',delivery/'source-licenses',dirs_exist_ok=True)
    write(delivery/'asset-usage.json',read(run/'demo/usage.json'))
    (delivery/'AI声明建议.txt').write_text('建议按平台当前发布页面选择 AI 生成或 AI 辅助创作标识。可填写：本视频使用模拟业务数据；操作经过实测；旁白由 AI 合成，脚本及剪辑由 AI 辅助完成。录屏为真实文件预览。请勿将模拟结果描述为真实客户业绩。\n',encoding='utf-8')
    write(delivery/'checksums.json',{str(p.relative_to(delivery)):sha(p) for p in sorted(delivery.rglob('*')) if p.is_file() and p.name!='checksums.json'})
    bundle=run/'发布素材与可编辑源码.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for folder in ['delivery','research','demo','script','voice','film','qa']:
            for p in sorted((run/folder).rglob('*')):
                if p.is_file():z.write(p,str(p.relative_to(run)))
        for name in ['index.html','timeline.json','preview.mp4','final.mp4']:z.write(run/name,name)
        snapshot=read(run/'manifest.json');snapshot['status']='completed_local';snapshot['archive_snapshot']=True
        snapshot['stages']['package']={'state':'complete','at':now(),'inputs':{'qa/report.json':sha(run/'qa/report.json')},'outputs':{str(p.relative_to(run)):sha(p) for p in delivery.rglob('*') if p.is_file()},'note':'Archive excludes its own hash; included delivery files are sealed.'}
        z.writestr('manifest.json',__import__('json').dumps(snapshot,ensure_ascii=False,indent=2))
        for p in sorted(HERE.parent.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.name!='local.json':z.write(p,'editable-toolkit/'+str(p.relative_to(HERE.parent)))
    outputs=[str(p.relative_to(run)) for p in delivery.rglob('*') if p.is_file()]+[bundle.name]
    seal(run,'package',['qa/report.json','script/script.json','script/platforms.json','demo/usage.json'],outputs)
    historyfile=run.parent.parent/'history.json';history=read(historyfile) if historyfile.exists() else []
    selected=read(run/'research/selection.json')['selected'];history=[h for h in history if h.get('run_id')!=m['run_id']]
    history.append({'key':selected['key'],'run_id':m['run_id'],'completed_at':now(),'status':'completed_local','title':selected['title']});write(historyfile,history)
    with lock(GLOBAL_HISTORY.parent):
        global_history=read(GLOBAL_HISTORY) if GLOBAL_HISTORY.exists() else []
        global_history=[h for h in global_history if h.get('run_id')!=m['run_id']]
        global_history.append(history[-1]);write(GLOBAL_HISTORY,global_history)
    print(bundle)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['timeline','preview','final','qa','package']);p.add_argument('--run',required=True);a=p.parse_args();r=pathlib.Path(a.run).resolve()
    with lock(r.parent.parent):
        if a.command in ['preview','final']:render(r,a.command=='final')
        else:globals()[a.command](r)
