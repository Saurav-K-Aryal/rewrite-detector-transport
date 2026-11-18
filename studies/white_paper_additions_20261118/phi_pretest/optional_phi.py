#!/usr/bin/env python3
"""Optional new-family rewrite panel. Preparation never invokes a model.

Profile and generation require a separately granted local inference slot.
All 450 question IDs are frozen before development, and any budget reduction
uses development timings only. This does not alter mandatory T12-A or T12-B.
"""
import argparse, collections, hashlib, importlib.util, json, math, os, random, sys, time
from pathlib import Path
import run_topic12 as core

HERE=Path(__file__).resolve().parent
OUT=HERE/'optional_phi'
OLD=core.ROOT/'outputs/pilot_extensions/topic12_extension.py'
CLIENT=core.ROOT/'outputs/overnight_multimodel/local_models.py'
SMOKE=core.ROOT/'outputs/pilot_extensions/runs/20261118T025754Z_smoke/topic12/records.jsonl'
DETECTORS=core.ROOT/'outputs/pilot_extensions/detectors.py'
MODEL='phi4:14b'
SEED=202611181412

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def stable_write(p,x):
    if p.exists():core.require(core.load(p)==x,'Immutable optional file changed '+str(p))
    else:core.write(p,x)
def prepare(args):
    core.frozen();core.require(not OUT.exists(),'Optional study already prepared')
    source=module(OLD,'historical_topic12_prompts');rs,bi=core.records()
    parents=sorted([r for r in rs if core.cohort(r)=='direct'],key=lambda r:r['id'])
    core.require(len(parents)==450 and all(core.valid(r) for r in parents),'Expected all 450 valid historical Gemma parents')
    smoke=[r for r in core.rows(SMOKE) if core.cohort(r)=='direct' and core.valid(r)]
    test_qids={r['qid'] for r in parents};core.require(not(test_qids & {r['qid'] for r in smoke}),'Development and test questions overlap')
    rng=random.Random(SEED);queues={s:[] for s in core.SOURCES}
    for r in parents:queues[r['source']].append(r)
    for q in queues.values():rng.shuffle(q)
    ordered=[queues[s][j] for j in range(150) for s in core.SOURCES]
    def item(r,kind,position):
        ident=hashlib.sha256(f'optional-phi-v1:{kind}:{r["id"]}'.encode()).hexdigest()
        seed=int(hashlib.sha256(f'{SEED}:{ident}'.encode()).hexdigest()[:8],16)%2147483647
        return {'id':ident,'qid':r['qid'],'source':r['source'],'source_id':r.get('source_id'),
          'condition':'rewrite','source_model':'gemma4:12b','model':MODEL,'parent_id':r['id'],
          'parent_text_sha256':hashlib.sha256(r['text'].encode()).hexdigest(),
          'seed':seed,'kind':kind,'balanced_order':position,
          'prompt_sha256':hashlib.sha256(source.REWRITE.format(text=r['text']).encode()).hexdigest()}
    test=[item(r,'test',j) for j,r in enumerate(ordered)]
    dev=[]
    for s in core.SOURCES:
        pool=sorted([r for r in smoke if r['source']==s],key=lambda r:r['id'])
        core.require(len(pool)>=1,'One historical smoke parent per source required')
        dev.extend(pool[:1])
    dev=[item(r,'development',j) for j,r in enumerate(dev)]
    OUT.mkdir();core.write(OUT/'TEST_MANIFEST.json',test);core.write(OUT/'DEV_MANIFEST.json',dev)
    deps={str(p):core.sha(p) for p in [OLD,CLIENT,SMOKE,DETECTORS,Path(core.__file__),Path(__file__),core.PROTOCOL,
      core.DECISIONS,core.RELEASE/'data/thresholds.json',core.SOURCE/'RADAR_CALIBRATION.json',core.SOURCE/'SCORING_LOCK.json']}
    plan={'prepared_utc':core.now(),'version':'optional-phi-rewrite-v1','model':MODEL,
      'source_run':str(core.SOURCE),'test_manifest_sha256':core.sha(OUT/'TEST_MANIFEST.json'),
      'dev_manifest_sha256':core.sha(OUT/'DEV_MANIFEST.json'),'input_sha256':deps,
      'test_parent_ids':len(test),'development_parents':3,'seed':SEED,
      'prompts':{'system':source.SYSTEM,'rewrite':source.REWRITE},
      'decoding':{'num_predict':384,'num_ctx':8192,'temperature':.7,'top_p':.9,'repeat_penalty':1.0,'retries':0},
      'generation_budget_seconds':args.generation_hours*3600,'detector_device':'mps',
      'runtime_selection':'Use development maximum wall seconds plus 25 percent. Reserve 60 seconds. Choose the largest source balanced prefix of the frozen 450 IDs fitting the generation budget. Minimum 30 test pairs or drop this optional experiment. Never select by observed test outcomes.',
      'scoring':'Pinned original Binoculars, Fast DetectGPT and RADAR implementations and thresholds. No recalibration. Detector calls use the first 128 whitespace words. Score errors stay unknown and are never retried selectively.',
      'length_filter':'Same 100 to 128 word and valid completion contract for both parent and child as T12-A.',
      'inference':'Serial local inference only after root grants an explicit scheduling slot. Metadata and full model digest frozen before development and rechecked for generation. Development outputs are excluded from test.',
      'status':'Prepared without inference. This optional extension must not delay mandatory experiments.'}
    core.write(OUT/'PROTOCOL.json',plan);print(OUT/'PROTOCOL.json')
def verify():
    core.frozen();p=core.load(OUT/'PROTOCOL.json')
    for path,h in p['input_sha256'].items():core.require(core.sha(path)==h,'Optional dependency changed '+path)
    core.require(core.sha(OUT/'TEST_MANIFEST.json')==p['test_manifest_sha256'],'Test manifest changed')
    core.require(core.sha(OUT/'DEV_MANIFEST.json')==p['dev_manifest_sha256'],'Development manifest changed')
    return p
def metadata(client):return {'model':client.model_metadata(MODEL),'server_version':client.version}
def create_client(p,folder,hours):
    m=module(CLIENT,'preserved_ollama_client')
    return m.Client(folder,models=[MODEL],max_hours=hours,request_timeout=300,context=p['decoding']['num_ctx'])
def generate_one(client,p,task,parent):
    prompt=p['prompts']['rewrite'].format(text=parent['text'])
    core.require(hashlib.sha256(prompt.encode()).hexdigest()==task['prompt_sha256'],'Prompt changed')
    core.require(hashlib.sha256(parent['text'].encode()).hexdigest()==task['parent_text_sha256'],'Parent changed')
    r=dict(task,created_utc=core.now());start=time.monotonic()
    try:
        response=client.generate(MODEL,prompt,seed=task['seed'],max_tokens=384,
                                  system=p['prompts']['system'],temperature=.7)
        text=response.get('text','').strip();done=response.get('done') is True;finish=response.get('finish_reason','unknown')
        truncated=finish in ['length','max_tokens','max_token','limit']
        r.update(response,text=text,word_count=len(text.split()),done=done,finish_reason=finish,
          status='empty' if not text else 'incomplete' if not done else 'completed_truncated' if truncated else 'completed',
          length_contract_pass=100<=len(text.split())<=128 and done and not truncated)
    except Exception as exc:
        if type(exc).__name__=='BudgetExceeded':raise
        r.update(status='error',text='',done=False,finish_reason='exception',word_count=0,error=repr(exc))
    r['wall_seconds']=time.monotonic()-start;return r
def profile(args):
    p=verify();core.require(args.ollama_slot,'Root must explicitly grant local inference slot')
    core.require(not (OUT/'DEVELOPMENT.json').exists(),'Development already completed')
    client=create_client(p,OUT/'development_client',1)
    stable_write(OUT/'MODEL_LOCK.json',metadata(client))
    prelock={'protocol_sha256':core.sha(OUT/'PROTOCOL.json'),'model_lock_sha256':core.sha(OUT/'MODEL_LOCK.json')}
    if (OUT/'PRE_INFERENCE_LOCK.json').exists():
        recorded=core.load(OUT/'PRE_INFERENCE_LOCK.json')
        core.require(all(recorded.get(k)==v for k,v in prelock.items()),'Pre inference lock changed')
    else:core.write(OUT/'PRE_INFERENCE_LOCK.json',dict(prelock,frozen_utc=core.now()))
    bi={r['id']:r for r in core.rows(SMOKE)};tasks=core.load(OUT/'DEV_MANIFEST.json')
    ledger=OUT/'development_records.jsonl';old=core.rows(ledger) if ledger.exists() else []
    seen={r['id'] for r in old};core.require(len(seen)==len(old),'Duplicate development records')
    for task in tasks:
        if task['id'] not in seen:core.append(ledger,generate_one(client,p,task,bi[task['parent_id']]))
    records=core.rows(ledger);core.require(len(records)==3,'Development is incomplete')
    seconds=max(r['wall_seconds'] for r in records)*1.25
    n=min(450,max(0,int((p['generation_budget_seconds']-60)/max(seconds,.001))//3*3))
    status='ready' if n>=30 and all(r['status']=='completed' for r in records) else 'drop_optional'
    core.write(OUT/'DEVELOPMENT.json',{'completed_utc':core.now(),'n':3,'max_seconds_with_margin':seconds,
      'selected_n':n if status=='ready' else 0,'status':status,'generation_only_estimated_seconds':n*seconds,
      'records_sha256':core.sha(ledger),'errors':sum(r['status']!='completed' for r in records),
      'runtime_only_selection':True,'semantic_or_detector_outcomes_not_used':True})
    selected=core.load(OUT/'TEST_MANIFEST.json')[:n] if status=='ready' else []
    core.write(OUT/'SELECTED_TEST_MANIFEST.json',selected)
    core.write(OUT/'TEST_LOCK.json',{'frozen_utc':core.now(),'selected_manifest_sha256':core.sha(OUT/'SELECTED_TEST_MANIFEST.json'),
      'development_sha256':core.sha(OUT/'DEVELOPMENT.json'),'selection_uses_test_outcomes':False})
    print(OUT/'DEVELOPMENT.json')
def generate(args):
    p=verify();core.require(args.ollama_slot,'Root must explicitly grant local inference slot')
    dev=core.load(OUT/'DEVELOPMENT.json');core.require(dev['status']=='ready','Optional experiment dropped by development gate')
    lock=core.load(OUT/'TEST_LOCK.json');core.require(core.sha(OUT/'SELECTED_TEST_MANIFEST.json')==lock['selected_manifest_sha256'],'Selected IDs changed')
    core.require(core.sha(OUT/'DEVELOPMENT.json')==lock['development_sha256'],'Development decision changed')
    client=create_client(p,OUT/'test_client',p['generation_budget_seconds']/3600)
    core.require(metadata(client)==core.load(OUT/'MODEL_LOCK.json'),'Model or backend changed after development')
    _,bi=core.records();tasks=core.load(OUT/'SELECTED_TEST_MANIFEST.json');ledger=OUT/'records.jsonl'
    old=core.rows(ledger) if ledger.exists() else [];seen={r['id'] for r in old}
    core.require(len(seen)==len(old) and seen<={t['id'] for t in tasks},'Invalid existing generation ledger')
    for j,task in enumerate(tasks):
        if task['id'] in seen:continue
        core.append(ledger,generate_one(client,p,task,bi[task['parent_id']]))
        if (j+1)%10==0:print(f'Optional Phi rewrites {j+1}/{len(tasks)}',flush=True)
    actual=core.rows(ledger);core.require(len(actual)==len(tasks),'Incomplete optional panel')
    core.write(OUT/'GENERATION_COMPLETE.json',{'finished_utc':core.now(),'records_sha256':core.sha(ledger),
      'selected_n':len(tasks),'full_planned_n':450,'not_selected_runtime':450-len(tasks),
      'status_counts':dict(collections.Counter(r['status'] for r in actual)),
      'model_lock_sha256':core.sha(OUT/'MODEL_LOCK.json'),'client_statistics':client.stats()})
def score(args):
    p=verify();core.require(args.ollama_slot,'Root must grant the shared local accelerator slot, including detector inference')
    complete=core.load(OUT/'GENERATION_COMPLETE.json');core.require(core.sha(OUT/'records.jsonl')==complete['records_sha256'],'Optional generation changed')
    dependencies=core.load(core.SOURCE/'SCORING_LOCK.json')['source_sha256']
    for relative,h in dependencies.items():
        path=core.ROOT/relative
        if path.exists():core.require(core.sha(path)==h,'Historical scoring dependency changed '+relative)
    d=module(DETECTORS,'preserved_detectors');cuts=core.load(core.RELEASE/'data/thresholds.json')
    rs=core.rows(OUT/'records.jsonl');ledger=OUT/'scores.jsonl';old=core.rows(ledger) if ledger.exists() else []
    seen={(s['id'],s['detector']) for s in old};core.require(len(seen)==len(old),'Duplicate optional scores')
    pub=None;official=False
    for r in rs:
        pending=[name for name in ['binoculars','fastdetectgpt'] if (r['id'],name) not in seen]
        if not pending:continue
        text=core.text_input(r);raw=None;error=None
        if text and str(r['status']).startswith('completed'):
            if pub is None:pub=d.published_scorer(p['detector_device'])
            try:raw=pub.score(text,verify_official=not official);official=True
            except Exception as exc:error=repr(exc)
        for name in pending:
            row={'id':r['id'],'detector':name,'input_hash':core.objhash(text),'score':None,'flag':None,'status':'generation_unavailable'}
            if raw is not None:
                z=raw[name+'_score'];core.require(math.isfinite(z),'Nonfinite detector score')
                row.update(score=z,flag=int(z<cuts[name]['cutoff']) if name=='binoculars' else int(z>cuts[name]['cutoff']),status='scored',
                  original_token_count=raw['original_token_count'],scored_token_count=raw['scored_token_count'],token_cap_truncated=raw['token_cap_truncated'])
            elif error:row.update(status='score_error',error=error)
            core.append(ledger,row)
    if pub is not None:
        del pub
        import gc,torch
        gc.collect();torch.mps.empty_cache()
    radar=d.RadarScorer(core.load(core.SOURCE/'RADAR_CALIBRATION.json')['install'],p['detector_device'])
    for r in rs:
        if (r['id'],'radar') in seen:continue
        text=core.text_input(r);row={'id':r['id'],'detector':'radar','input_hash':core.objhash(text),'score':None,'flag':None,'status':'generation_unavailable'}
        if text and str(r['status']).startswith('completed'):
            try:
                z,audit=radar.score(text);row.update(score=z,flag=int(z>cuts['radar']['cutoff']),status='scored',**audit)
            except Exception as exc:row.update(status='score_error',error=repr(exc))
        core.append(ledger,row)
    core.write(OUT/'SCORES_COMPLETE.json',{'finished_utc':core.now(),'scores_sha256':core.sha(ledger),
      'score_rows':len(core.rows(ledger)),'thresholds_sha256':core.sha(core.RELEASE/'data/thresholds.json')})
def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--generation-hours',type=float,default=2)
    for name in ['profile','generate','score']:
        x=sub.add_parser(name);x.add_argument('--ollama-slot',action='store_true')
    args=parser.parse_args();globals()[args.cmd](args)
if __name__=='__main__':main()
