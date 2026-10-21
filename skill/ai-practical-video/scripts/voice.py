#!/usr/bin/env python3
"""Free local Kokoro adapter. Cache keys include text, model, voice file and synthesis settings."""
import argparse, pathlib, re, shutil, subprocess
from pipeline import read,write,sha,digest,validate_script,seal,reconcile,lock

def verify_models(config):
    """Refuse model changes; legacy configs use the bundled fixed model lock."""
    pinned = read(pathlib.Path(__file__).resolve().parents[1] / 'references/model-lock.json')
    identity = {}
    for key in ('model', 'voices'):
        path = pathlib.Path(config[key])
        expected = config.get(key + '_sha256') or pinned.get(path.name, {}).get('sha256')
        if not expected:
            raise ValueError('Missing expected SHA256 for '+key+'; explicitly configure '+key+'_sha256')
        actual = sha(path)
        if actual != expected:
            raise ValueError('Model checksum mismatch for '+key+'; inspect the changed file before resuming')
        identity[key + '_sha'] = actual
    return identity

def spoken_text(text, pronunciations):
    """Chinese G2P has no English reader; reject names it would silently drop."""
    for key in sorted(pronunciations, key=len, reverse=True):
        text = text.replace(key, pronunciations[key])
    missing = sorted(set(re.findall(r'[A-Za-z]+(?:[-_][A-Za-z]+)*', text)))
    if missing:
        raise ValueError('Add Chinese readings to script.pronunciations for: ' + ', '.join(missing))
    return text

def chunks(text):
    # Synthesize short clauses individually: every subtitle gets a measured audio span.
    parts=re.findall(r'[^，。！？；：、,.!?;:]+[，。！？；：、,.!?;:]?',text)
    out=[]
    for p in parts:
        p=p.strip()
        if not p: continue
        while len(p)>25: out.append(p[:20]);p=p[20:]
        if p:out.append(p)
    return out

def generate(run, config):
    import numpy as np, soundfile as sf
    from misaki import zh
    from kokoro_onnx import Kokoro
    run=pathlib.Path(run);conf=read(config);validate_script(run)
    if conf.get('provider')!='kokoro-local' or conf.get('cost_per_generation')!=0: raise ValueError('this adapter only supports free local Kokoro; paid providers require a separate explicit quote and approval')
    if not conf.get('voice_id'): raise ValueError('voice is not configured')
    if reconcile(run)['stages'].get('script',{}).get('state')!='complete':raise ValueError('seal the verified script before voice generation')
    write(run/'voice/config.json',conf)
    model=pathlib.Path(conf['model']); voices=pathlib.Path(conf['voices'])
    identity={k:conf[k] for k in ['provider','voice_id','speed','engine_version']}; identity.update(verify_models(conf))
    cache=pathlib.Path(conf['cache']);cache.mkdir(parents=True,exist_ok=True)
    sc=read(run/'script/script.json');records=[];scenes=[];whole=[];cursor=0;sr=24000
    for scene in sc['scenes']:
        spoken_text(scene['narration'], sc.get('pronunciations', {}))
    engine=Kokoro(str(model),str(voices)); g2p=zh.ZHG2P(version='1.1')
    for scene in sc['scenes']:
        begin=cursor
        for i,part in enumerate(chunks(scene['narration'])):
            spoken=spoken_text(part,sc.get('pronunciations',{}))
            key=digest({'text':spoken,'display':part,'voice':identity});cached=cache/(key+'.wav')
            reused=cached.exists()
            if reused:
                audio,sr=sf.read(cached,dtype='float32')
            else:
                phones,_=g2p(spoken)
                if not phones.strip():raise ValueError('empty phonemes: '+spoken)
                if '❓' in phones:raise ValueError('Unknown pronunciation in: '+spoken+'; revise script.pronunciations')
                audio,sr=engine.create(phones,voice=conf['voice_id'],speed=conf['speed'],is_phonemes=True)
                sf.write(cached,audio,sr,subtype='PCM_16')
                audio,sr=sf.read(cached,dtype='float32')
            name=f"{scene['id']}-{i:02d}.wav";shutil.copyfile(cached,run/'voice'/name)
            d=len(audio)/sr;records.append({'scene_id':scene['id'],'text':part,'spoken':spoken,'start':cursor,'end':cursor+d,'file':'voice/'+name,'cache_key':key,'cache_hit':reused,'sha256':sha(cached)})
            whole.append(audio);gap=np.zeros(round(sr*0.12),dtype='float32');whole.append(gap);cursor+=d+len(gap)/sr
        scenes.append({**scene,'start':begin,'end':cursor})
    whole.append(np.zeros(round(sr*.6),dtype='float32'));cursor+=.6;scenes[-1]['end']=cursor
    sf.write(run/'voice/narration.wav',np.concatenate(whole),sr,subtype='PCM_16')
    write(run/'voice/manifest.json',{'script_hash':sha(run/'script/script.json'),'voice':identity,'segments':records,'duration':cursor,'cost':0,'license':conf['license'],'range_ok':60<=cursor<=90})
    write(run/'voice/measured-scenes.json',scenes)
    seal(run,'voice',['script/script.json','voice/config.json'],['voice/manifest.json','voice/narration.wav','voice/measured-scenes.json']+[r['file'] for r in records])
    print(f'VOICE: {cursor:.2f}s; cache {sum(r["cache_hit"] for r in records)}/{len(records)}; cost 0')
    if not 60<=cursor<=90: raise ValueError('measured narration outside 60–90s: revise script, never speed up or truncate to fit')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--config',required=True);a=p.parse_args()
    with lock(pathlib.Path(a.run).parent.parent): generate(a.run,a.config)
