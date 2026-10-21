#!/usr/bin/env python3
"""File-backed production state. No account publishing, billing or hidden API calls."""
import argparse, contextlib, datetime as dt, hashlib, json, os, pathlib, shutil, subprocess, sys, uuid

TZ = dt.timezone(dt.timedelta(hours=8))
GLOBAL_HISTORY = pathlib.Path(os.environ.get('CODEX_HOME',str(pathlib.Path.home()/'.codex')))/'ai-practical-video/history.json'
ORDER = ['research','demo','script','voice','timeline','preview','final','qa','package']
DEPS = {'research':[], 'demo':['research'], 'script':['demo'], 'voice':['script'],
        'timeline':['voice'], 'preview':['timeline'], 'final':['preview'], 'qa':['final'], 'package':['qa']}

def now(): return dt.datetime.now(TZ).isoformat(timespec='seconds')
def read(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def write(p, data):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); tmp.replace(p)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def digest(data): return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def inside(run, name):
    p=(pathlib.Path(run)/name).resolve()
    if not p.is_relative_to(pathlib.Path(run).resolve()): raise ValueError('artifact outside run: '+str(name))
    return p
def probe(p):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
def duration(p): return float(probe(p)['format']['duration'])

@contextlib.contextmanager
def lock(root):
    import fcntl
    root=pathlib.Path(root); root.mkdir(parents=True,exist_ok=True)
    with open(root/'.production.lock','a+') as f:
        try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('another production command is running; sequential execution only')
        try: yield
        finally: fcntl.flock(f,fcntl.LOCK_UN)

def init(root, topic, mode='specified'):
    root=pathlib.Path(root).resolve(); rid=dt.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    run=root/'runs'/rid; run.mkdir(parents=True)
    for d in ['research','demo','script','voice','film','qa','delivery']: (run/d).mkdir()
    write(run/'manifest.json',{'schema':1,'run_id':rid,'created_at':now(),'topic':topic,'mode':mode,'status':'in_progress','published':False,'stages':{},'events':[]})
    return run

def reconcile(run):
    run=pathlib.Path(run); m=read(run/'manifest.json'); invalid=set()
    for s in ORDER:
        v=m['stages'].get(s,{})
        if any(d in invalid for d in DEPS[s]): invalid.add(s)
        if v.get('state')=='complete' and any(m['stages'].get(d,{}).get('state')!='complete' for d in DEPS[s]): invalid.add(s)
        if v.get('state')=='complete':
            for k,h in {**v.get('inputs',{}),**v.get('outputs',{})}.items():
                p=inside(run,k)
                if not p.is_file() or sha(p)!=h: invalid.add(s)
        if s in invalid and v:
            v['state']='stale'; v['reason']='input, output or prerequisite changed'; v['invalidated_at']=now()
    if invalid:
        m['status']='in_progress'; m['events'].append({'at':now(),'invalidated':sorted(invalid)})
    write(run/'manifest.json',m); return m

def seal(run, stage, inputs, outputs):
    run=pathlib.Path(run); m=reconcile(run)
    for dep in DEPS[stage]:
        if m['stages'].get(dep,{}).get('state')!='complete': raise ValueError('prerequisite not complete: '+dep)
    if not outputs: raise ValueError('at least one output required')
    def hashes(names): return {n:sha(inside(run,n)) for n in names}
    old=m['stages'].get(stage,{})
    m['stages'][stage]={'state':'complete','at':now(),'inputs':hashes(inputs),'outputs':hashes(outputs),'failures':old.get('failures',0)}
    # Explicit reruns invalidate every dependent, even when old paths still exist.
    for s in ORDER[ORDER.index(stage)+1:]:
        if s in m['stages']: m['stages'][s]['state']='stale'
    m['status']='completed_local' if stage=='package' else 'in_progress'
    m['events'].append({'at':now(),'stage':stage,'state':'complete'})
    write(run/'manifest.json',m)

def fail(run, stage, reason, waiting=False):
    run=pathlib.Path(run); m=reconcile(run); v=m['stages'].setdefault(stage,{})
    n=v.get('failures',0)+(0 if waiting else 1)
    v.update(state='waiting' if waiting else 'failed',reason=reason,failures=n,at=now())
    # Initial failure plus two repair attempts; demos get one repair then a new candidate.
    v['repair_allowed']=not waiting and n < (2 if stage=='demo' else 3)
    m['status']='waiting' if waiting else 'in_progress'; m['events'].append({'at':now(),'stage':stage,'reason':reason})
    for s in ORDER[ORDER.index(stage)+1:]:
        if s in m['stages']: m['stages'][s]['state']='stale'
    write(run/'manifest.json',m)

def stamp(s):
    if not s: return None
    t=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('timestamps require timezone')
    return t.astimezone(TZ)

def event_bounds(candidate):
    """Retain date-only evidence without inventing an event timestamp or timezone."""
    exact=stamp(candidate.get('event_at'))
    if exact: return exact,exact,'timestamp'
    raw=candidate.get('event_date')
    if not raw: return None,None,'unknown'
    day=dt.date.fromisoformat(raw)
    if day.isoformat()!=raw: raise ValueError('event_date requires YYYY-MM-DD')
    # Unknown source timezone: cover UTC-14 through UTC+14 conservatively.
    # Only an interval wholly inside a freshness window can earn its points.
    midnight=dt.datetime.combine(day,dt.time.min,tzinfo=dt.timezone.utc)
    return ((midnight-dt.timedelta(hours=14)).astimezone(TZ),
            (midnight+dt.timedelta(days=1,hours=14)).astimezone(TZ),'date')

def rank(candidates, history, at=None):
    at=stamp(at) if at else dt.datetime.now(TZ)
    if len(candidates)>10: raise ValueError('maximum 10 candidates')
    results=[]
    for original in candidates:
        c=dict(original); reasons=[]; sources=c.get('sources',[])
        earliest,latest,precision=event_bounds(c)
        age=(at-earliest).total_seconds()/86400 if earliest else None
        recent=age is not None and latest<=at and age<=7
        if earliest and earliest>at: reasons.append('event is in the future')
        c['event_time_bounds']={'precision':precision,'earliest':earliest.isoformat() if earliest else None,
                               'latest':latest.isoformat() if latest else None,
                               'timezone_known':precision=='timestamp'}
        independent={s.get('origin_id') for s in sources if s.get('origin_id')}
        primary=any(s.get('kind')=='official' and s.get('url') and s.get('verified') for s in sources)
        signals=[]
        for sig in c.get('heat_signals',[]):
            observed=stamp(sig.get('observed_at'))
            # A copied headline or a cumulative count without a time window is not current heat.
            if sig.get('verified') and sig.get('url') and sig.get('metric') and isinstance(sig.get('value'),(int,float)) and sig['value']>0 and sig.get('window') and observed and 0<=(at-observed).total_seconds()<=7*86400:
                signals.append(sig)
        label='有热度证据' if recent and signals else ('近期更新' if recent and primary else '常青选题')
        for k in ['business_use','feature_verified','demo_feasible']:
            if not c.get(k): reasons.append('missing '+k)
        if not primary: reasons.append('no verified official feature source')
        key='|'.join(str(c.get(k,'')).strip().casefold() for k in ['tool','feature','scenario'])
        for h in history:
            hdate=stamp(h.get('completed_at'))
            if h.get('key')==key and hdate and 0<=(at-hdate).total_seconds()<30*86400:
                if not (c.get('material_change') and c.get('change_source')): reasons.append('duplicate within 30 days')
        scores=c.get('scores',{})
        for k in ['fit','reproducibility','service_demand']:
            if not isinstance(scores.get(k), (int,float)) or not 0<=scores[k]<=5: raise ValueError('score must be 0..5: '+k)
        fresh=5 if recent and age<=3 else (3 if recent else 0)
        total=scores['fit']*6+scores['reproducibility']*6+scores['service_demand']*3+fresh*3+(10 if signals and recent else 0)
        c.update(key=key,classification=label,independent_origins=len(independent),eligible=not reasons,rejection_reasons=reasons,score=total)
        results.append(c)
    pool=[c for c in results if c['eligible'] and c['classification']!='常青选题'] or [c for c in results if c['eligible']]
    pool.sort(key=lambda c:(c['score'],c['id']),reverse=True)
    selected=pool[0] if pool else None
    return {'searched_at':at.isoformat(),'timezone':'Asia/Shanghai','candidates':results,'selected':selected,'fallback_reason':'没有可核验且能完成演示的近期选题，采用未重复常青案例' if selected and selected['classification']=='常青选题' else None}

def validate_script(run):
    run=pathlib.Path(run); d=read(run/'script/script.json'); evidence=read(run/'demo/evidence.json')
    ids={x['id'] for x in evidence['items']}
    assert len(d['hooks'])==3 and d['selected_hook'] in range(3), 'three hooks and selected index required'
    assert d['hook_reason'] and d['business_use'] and d['access_conditions']
    seen=set()
    for scene in d['scenes']:
        assert scene['id'] not in seen; seen.add(scene['id'])
        assert scene['evidence_id'] in ids and scene['narration'] and scene['heading']
        assert scene['visual_kind'] in ['real_capture','local_file_preview','illustration']
        if scene['visual_kind']=='illustration': assert scene['disclosure']=='示意画面'
        assert all(inside(run,p).is_file() for p in scene.get('proof_files',[]))
        assert scene.get('claim_checked') is True, 'verify claim against actual output first'
    phases=[s['phase'] for s in d['scenes']]
    assert phases[0] in ['result','hook'] and 'problem' in phases and 'steps' in phases and 'verify' in phases and phases[-1] in ['service','takeaway']
    assert any(s['visual_kind']!='illustration' for s in d['scenes']), 'a practical video needs real operation evidence'
    return {'ok':True,'scenes':len(seen),'script_hash':sha(run/'script/script.json'),'at':now()}

def main():
    a=argparse.ArgumentParser(); sub=a.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('init'); p.add_argument('--root',required=True); p.add_argument('--topic',required=True); p.add_argument('--mode',choices=['auto','specified'],default='specified')
    for cmd in ['status','seal','fail','wait','check-script','select']:
        p=sub.add_parser(cmd); p.add_argument('--run',required=True)
        if cmd in ['seal','fail','wait']: p.add_argument('--stage',choices=ORDER,required=True)
        if cmd=='seal': p.add_argument('--inputs',nargs='*',default=[]); p.add_argument('--outputs',nargs='+',required=True)
        if cmd in ['fail','wait']: p.add_argument('--reason',required=True)
        if cmd=='select': p.add_argument('--candidates',required=True); p.add_argument('--history'); p.add_argument('--at')
    args=a.parse_args()
    root=pathlib.Path(args.root) if args.cmd=='init' else pathlib.Path(args.run).parent.parent
    with lock(root):
        if args.cmd=='init': print(init(root,args.topic,args.mode)); return
        run=pathlib.Path(args.run)
        if args.cmd=='status':
            m=reconcile(run); print(json.dumps(m,ensure_ascii=False,indent=2))
        elif args.cmd=='seal': seal(run,args.stage,args.inputs,args.outputs)
        elif args.cmd in ['fail','wait']: fail(run,args.stage,args.reason,args.cmd=='wait')
        elif args.cmd=='check-script': write(run/'script/check.json',validate_script(run))
        elif args.cmd=='select':
            history=read(GLOBAL_HISTORY) if GLOBAL_HISTORY.exists() else []
            if args.history and pathlib.Path(args.history).exists(): history+=read(args.history)
            result=rank(read(args.candidates),history,args.at)
            write(run/'research/selection.json',result)
            if not result['selected']: raise SystemExit('no eligible candidate')
            print(result['selected']['title'])

if __name__=='__main__': main()
