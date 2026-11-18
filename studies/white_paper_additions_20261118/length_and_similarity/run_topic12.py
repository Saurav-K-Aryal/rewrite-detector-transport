#!/usr/bin/env python3
"""Frozen, retrospective Topic 12 sensitivity analyses and blinded human review.

No detector is fitted, recalibrated, or called here. Embeddings use an already
installed local Ollama model. Run freeze only after the root decision window.
"""
from __future__ import annotations
import argparse, collections, csv, datetime, hashlib, json, math, os
import platform, random, statistics, sys, time, urllib.request
from pathlib import Path
from scipy.stats import beta

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ADDITIONS = HERE.parent
SOURCE = ROOT / 'outputs/pilot_extensions/runs/20261118T030136Z_full/topic12'
RELEASE = ROOT / 'outputs/github_repos/rewrite-detector-transport'
DECISIONS = ADDITIONS / 'DECISIONS.json'
PROTOCOL = HERE / 'PROTOCOL.json'
DET = ['binoculars', 'fastdetectgpt', 'radar']
NAMES = dict(zip(DET, ['Binoculars', 'Fast DetectGPT', 'RADAR']))
ARMS = ['cross', 'self']
SOURCES = ['wikipedia', 'abstracts', 'recipes']
LABELS = {'human':'Human controls', 'direct':'Gemma direct',
          'cross':'Gemma to Qwen', 'self':'Gemma to Gemma'}
FILES = ['records.jsonl', 'scores.jsonl', 'fullplanned_manifest.jsonl',
         'protocol.json', 'SCORING_LOCK.json', 'SCORES_COMPLETE.json',
         'RADAR_CALIBRATION.json', 'ANALYSIS_PLAN.json']
SEED = 20261118012

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def require(x, message):
    if not x: raise ValueError(message)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def objhash(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text())
def rows(p):
    with Path(p).open() as f: return [json.loads(x) for x in f if x.strip()]
def write(p, x):
    p=Path(p);p.parent.mkdir(parents=True, exist_ok=True)
    t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(x, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    os.replace(t,p)
def append(p,x):
    with Path(p).open('a') as f:
        f.write(json.dumps(x, ensure_ascii=False, allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def csvwrite(p, rs, fields=None):
    require(rs or fields, 'CSV requires a schema')
    with Path(p).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rs[0]));w.writeheader();w.writerows(rs)
def csvread(p):
    with Path(p).open(newline='') as f:return list(csv.DictReader(f))
def text_input(r):return ' '.join(str(r.get('text','')).split()[:128])
def wilson(k,n):
    if not n:return [None,None]
    z=1.959963984540054;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0.,mid-half),min(1.,mid+half)]
def cp(k,n,alpha=.05):
    if not n:return [None,None]
    return [0. if not k else float(beta.ppf(alpha/2,k,n-k+1)),
            1. if k==n else float(beta.ppf(1-alpha/2,k+1,n-k))]
def paired(a,b,family=1):
    require(len(a)==len(b),'Unequal pairs')
    n=len(a);lost=sum(x==1 and y==0 for x,y in zip(a,b));gained=sum(x==0 and y==1 for x,y in zip(a,b))
    # Each discordance interval has failure probability .05/(2*family).
    # The union bound covers their difference without an independence assumption.
    l=cp(lost,n,.05/(2*family));g=cp(gained,n,.05/(2*family))
    return {'n_pairs':n,'parent_flagged':sum(a),'child_flagged':sum(b),
            'retained_flags':sum(x==1 and y==1 for x,y in zip(a,b)),
            'retention_denominator':sum(a),
            'retention_wilson95':wilson(sum(x==1 and y==1 for x,y in zip(a,b)),sum(a)),
            'lost_flags':lost,'gained_flags':gained,
            'parent_minus_child_rate':(lost-gained)/n if n else None,
            'paired_drop_interval95':[max(-1.,l[0]-g[1]),min(1.,l[1]-g[0])] if n else [None,None],
            'interval_family_size':family}
def valid(r):
    if not r or not 100<=len(str(r.get('text','')).split())<=128:return False
    if r.get('condition')=='human':return r.get('status')=='observed_public_human' and r.get('done') is True
    return r.get('status') in ['completed','complete','ok'] and r.get('done') is True and r.get('finish_reason') not in [None,'length','max_tokens','max_token','limit']
def reason(r):
    if not r:return 'record_missing'
    if not 100<=len(str(r.get('text','')).split())<=128:return 'length_outside_100_128'
    return 'eligible' if valid(r) else 'completion_invalid'
def cohort(r):
    if r['condition']=='human':return 'human'
    if r['condition']=='direct' and r.get('model')=='gemma4:12b':return 'direct'
    if r['condition']=='rewrite' and r.get('source_model')=='gemma4:12b':
        if r.get('model')=='qwen3.5:4b':return 'cross'
        if r.get('model')=='gemma4:12b':return 'self'
    return None
def hostinfo():
    return {'platform':platform.platform(),'machine':platform.machine(),'python':sys.version,
            'logical_cpus':os.cpu_count()}

def freeze(args):
    require(DECISIONS.exists(),'DECISIONS.json must exist before freezing or analysis')
    require(not PROTOCOL.exists(),'Protocol already frozen; do not overwrite')
    expected=load(SOURCE/'SCORING_LOCK.json')['input_sha256']
    for n,h in expected.items():require(sha(SOURCE/n)==h,'Historical scoring input changed '+n)
    require(sha(SOURCE/'scores.jsonl')==load(SOURCE/'SCORES_COMPLETE.json')['scores_sha256'], 'Historical scores changed')
    snapshots={str(SOURCE/n):sha(SOURCE/n) for n in FILES}
    snapshots[str(RELEASE/'data/thresholds.json')]=sha(RELEASE/'data/thresholds.json')
    snapshots[str(DECISIONS)]=sha(DECISIONS)
    if (ADDITIONS/'INPUT_PROVENANCE.json').exists():
        snapshots[str(ADDITIONS/'INPUT_PROVENANCE.json')]=sha(ADDITIONS/'INPUT_PROVENANCE.json')
    write(PROTOCOL,{'version':'topic12-additions-1','frozen_utc':now(), 'seed':SEED,
      'study_type':'Retrospective sensitivity analyses of reused historical detector scores. Aggregate historical outcomes were already known. This is not an independent confirmatory replication.',
      'source_run':str(SOURCE),'input_sha256':snapshots,'code_sha256':sha(__file__),
      'A':{'length_words':[100,128],'unit':'whitespace separated words',
           'completion':'Generated parent and child must both be completed, done true, and not truncated. Public human controls use their observed public human status.',
           'detectors':DET,'thresholds':'Original locked thresholds, no recalibration',
           'table':'Four rows with descriptive Wilson intervals conditional on length and valid completion. Missing scores remain explicit unknowns in the denominator.',
           'paired':'Each rewrite is paired to its own direct Gemma parent. Retention denominator is eligible scored pairs whose parent was flagged. Drop is parent minus child rate on the same eligible paired panel.',
           'drop_interval':'Difference of two Clopper Pearson discordance intervals with union bound. Six contrast simultaneous intervals also reported. No new confirmatory claims.'},
      'B':{'model':'bge-m3:latest','backend':'Ollama /api/embed local only',
           'cosine_primary':.90,'cosine_sensitivity':[.85,.95],
           'similarity_label':'Unvalidated embedding proxy for fidelity to the parent, not human validated semantic preservation or factual correctness',
           'text':'Whole eligible text, at most 128 words. No detector outcomes used for embedding selection or threshold selection.',
           'eligibility':'A eligibility plus available embedding similarity at or above the fixed threshold for each rewrite pair. Human and direct reference rows remain A reference rows, with paired comparisons restricted separately to each selected rewrite arm.',
           'missing':'Embedding errors remain in the attempted ledger and all planned accounting. Conditional proxy rates are not all planned success rates.',
           'batch_size':8,'timeout_seconds':120,'max_retries':0,
           'development_profile':'Two batches of eight synthetic paragraphs, lengths 100 and 128 words. No evaluation text or detector outcomes used. First batch includes model startup.',
           'embedding_wall_budget_seconds':14400,
           'human_unique_pairs':80,'human_cross_pairs':40,'human_self_pairs':40,
           'human_distinct_qids':80,'human_shared_pairs':20,'ratings_per_rater':50,
           'primary_per_rater':40,'secondary_per_rater':10,
           'sampling':'Source stratified seeded sampling of length and completion eligible pairs, independent of similarity and detector outcomes. At most one selected pair per qid across arms. Primary rater assignments frozen before ratings.',
           'rating_scale':{'0':'Material meaning changed','1':'Uncertain or partly preserved','2':'All material meaning preserved'},
           'preserved':'Rating 2 only on preassigned primary ratings. No adjudication or cherry picking.',
           'agreement':'Exact agreement, Wilson interval, and unweighted Cohen kappa on 20 double coded pairs. Seeded percentile bootstrap for kappa is descriptive; undefined kappa reported as unavailable.',
           'human_status':'No human observations exist until two actual completed files are imported. This small retrospective sample does not unlock the historical 900 pair confirmatory endpoint.'},
      'known_limits':['Sources and questions are reused; question separation does not prove author independence.',
                      'Three fixed detector implementations do not establish a universal impossibility result.',
                      'The similarity cutoffs are frozen assumptions without independent fidelity calibration.'],
      'host':hostinfo()})
    print(str(PROTOCOL))

def frozen():
    require(PROTOCOL.exists(),'Run freeze after root decisions before any analysis')
    p=load(PROTOCOL);require(sha(__file__)==p['code_sha256'],'Implementation changed after freeze')
    for name,h in p['input_sha256'].items():require(sha(name)==h,'Frozen input changed '+name)
    return p
def records():
    rs=rows(SOURCE/'records.jsonl');byid={r['id']:r for r in rs}
    require(len(byid)==len(rs),'Duplicate record IDs')
    plans=rows(SOURCE/'fullplanned_manifest.jsonl')
    require(set(byid)=={r['id'] for r in plans},'Planned and observed record IDs differ')
    for q in plans:
        r=byid[q['id']]
        for k in ['qid','source','source_id','condition','source_model','model','parent_id']:
            require(r.get(k)==q.get(k),'Record and planned metadata differ '+k)
        if r.get('parent_id'):
            require(r['parent_id'] in byid,'Missing parent record')
            require(byid[r['parent_id']]['qid']==r['qid'],'Parent question mismatch')
    return rs,byid
def eligible_groups(rs,byid):
    gs={k:[] for k in ['human','direct']+ARMS};account=[]
    for r in rs:
        c=cohort(r)
        if not c:continue
        why=reason(r)
        if c in ARMS and why=='eligible':
            p=byid[r['parent_id']];why='eligible' if valid(p) else 'parent_'+reason(p)
        account.append({'id':r['id'],'qid':r['qid'],'source':r['source'],'cohort':c,'eligibility':why})
        if why=='eligible':gs[c].append(r)
    return gs,account
def scores(byid):
    ss=rows(SOURCE/'scores.jsonl');idx={};cuts=load(RELEASE/'data/thresholds.json')
    require(len(ss)==load(SOURCE/'SCORES_COMPLETE.json')['score_rows'],'Score count differs')
    for s in ss:
        if s['detector'] not in DET:continue
        key=(s['id'],s['detector']);require(key not in idx,'Duplicate detector score')
        require(s['id'] in byid,'Unknown score record')
        require(s['input_hash']==objhash(text_input(byid[s['id']])),'Detector text hash differs')
        if s['status']=='scored':
            require(s['flag'] in [0,1] and math.isfinite(s['score']),'Invalid scored value')
            cut=cuts[s['detector']]
            flag=int(s['score']<cut['cutoff']) if cut['direction']=='less' else int(s['score']>cut['cutoff'])
            require(flag==s['flag'],'Historical flag and frozen cutoff disagree')
        idx[key]=s
    return idx
def scored(ss,r,d):return ss.get((r['id'],d),{}).get('status')=='scored'
def pct(v):return 'NA' if v is None else f'{100*v:.1f}'
def interval(v):return '['+pct(v[0])+', '+pct(v[1])+']'
def display_cell(m):
    if not m['n']:return 'NA, n = 0'
    ans=f"{100*m['flagged']/m['n']:.1f}% ({m['flagged']}/{m['n']}) {interval(m['wilson95'])}"
    if m['unknown']:ans+=f"; {m['unknown']} unknown"
    return ans
def summarize(gs,byid,ss):
    cells=[];pairs=[]
    for c,rs in gs.items():
        for d in DET:
            flags=[ss[r['id'],d]['flag'] for r in rs if scored(ss,r,d)]
            k=sum(flags);n=len(rs);unknown=n-len(flags)
            cells.append({'cohort':c,'detector':d,'flagged':k,'n':n,'scored_n':len(flags),
                          'unknown':unknown,'wilson95':wilson(k,n),
                          'rate_bounds_due_to_missing':[k/n,(k+unknown)/n] if n else [None,None],
                          'denominator_note':'Missing scores counted in n as unknown; displayed flag fraction is confirmed flags only if any unknown exists.'})
    for c in ARMS:
        for d in DET:
            eligible=[r for r in gs[c] if scored(ss,r,d) and scored(ss,byid[r['parent_id']],d)]
            a=[ss[r['parent_id'],d]['flag'] for r in eligible];b=[ss[r['id'],d]['flag'] for r in eligible]
            z=paired(a,b);sim=paired(a,b,family=6)
            flagged_parents=[r for r in gs[c] if scored(ss,byid[r['parent_id']],d) and ss[r['parent_id'],d]['flag']==1]
            retained=sum(scored(ss,r,d) and ss[r['id'],d]['flag']==1 for r in flagged_parents)
            unknown_children=sum(not scored(ss,r,d) for r in flagged_parents)
            z.update(retained_flags=retained,retention_denominator=len(flagged_parents),
                     retention_unknown_children=unknown_children,
                     retention_wilson95=wilson(retained,len(flagged_parents)),
                     retention_missingness_bounds=[retained/len(flagged_parents),(retained+unknown_children)/len(flagged_parents)] if flagged_parents else [None,None])
            z.update(cohort=c,detector=d,eligible_n=len(gs[c]),missing_paired_scores=len(gs[c])-len(eligible),
                     simultaneous_six95=sim['paired_drop_interval95'],
                     paired_drop_basis='Eligible pairs with both scores available. Missing score counts remain explicit. Retention includes every eligible pair with a known flagged parent, and unknown children are counted as unknown rather than confirmed negatives.')
            pairs.append(z)
    return cells,pairs
def export_analysis(out,gs,account,byid,ss,label,extra=None):
    out.mkdir(parents=True,exist_ok=True);cells,ps=summarize(gs,byid,ss)
    write(out/'metrics.json',{'cells':cells,'paired':ps,'extra':extra or {}})
    csvwrite(out/'cell_metrics.csv',cells);csvwrite(out/'paired_metrics.csv',ps)
    csvwrite(out/'eligibility.csv',account)
    lookup={(r['cohort'],r['detector']):r for r in cells}
    table=['| Cohort | Binoculars | Fast DetectGPT | RADAR |','|---|---|---|---|']
    for c in ['human','direct']+ARMS:table.append('| '+LABELS[c]+' | '+' | '.join(display_cell(lookup[c,d]) for d in DET)+' |')
    drops=sum(not p['missing_paired_scores'] and p['simultaneous_six95'][0] is not None and p['simultaneous_six95'][0]>0 for p in ps)
    if label=='T12-A':
        prose=f'Length and completion matched analyses retained lower rewrite flag rates in {drops} of six detector comparisons under conservative simultaneous paired intervals. The estimates reuse the historical panel and describe detector sensitivity after rewriting. They do not establish meaning preservation or a universal failure of detection.'
    else:
        prose=f'Among pairs passing the fixed embedding similarity proxy, {drops} of six detector comparisons retained lower rewrite flag rates under conservative simultaneous paired intervals. Embedding similarity is an unvalidated proxy for fidelity to the parent. Human fidelity estimates remain pending actual independent ratings.'
    require(len(prose.split())<=60,'Paste text exceeds 60 words')
    lines=[label,'','Frozen protocol','',str(PROTOCOL),'','Paste ready text','',prose,'','Four row table','',
           *table,'','Each cell gives confirmed flags, denominator and a descriptive 95% Wilson interval. Percentages inside brackets are percentages. Human and direct rows are reference cohorts. Each rewrite comparison uses its own eligible parent pairs.','',
           'Paired retention and drop','']
    for p in ps:
        n=p['retention_denominator'];r=p['retained_flags']
        lines.append(f"{LABELS[p['cohort']]} with {NAMES[p['detector']]} retained {pct(r/n if n else None)}% ({r}/{n}) {interval(p['retention_wilson95'])}. Parent minus rewrite flag rate was {pct(p['parent_minus_child_rate'])} percentage points over {p['n_pairs']} pairs, with a conservative 95% interval {interval(p['paired_drop_interval95'])} and simultaneous six comparison interval {interval(p['simultaneous_six95'])}.")
    counts=collections.Counter((a['cohort'],a['eligibility']) for a in account)
    lines+=['','Exclusions and missing outcomes','',json.dumps({f'{c} / {e}':n for (c,e),n in sorted(counts.items())},indent=2),'',
      'Limits and what is not established','',
      'This is a retrospective sensitivity analysis on reused questions and known historical aggregate results. Wilson intervals are descriptive. Length exclusions and unavailable outcomes remain in the accounting file. Fixed detector thresholds do not guarantee the original calibration rate on these sources. This does not establish factual correctness, human authorship, universal nonidentifiability, or independence by author.','',
      'Run record','',str(out/'RUN_RECORD.json')]
    if extra:lines+=['','Additional evidence','',json.dumps(extra,indent=2)]
    (out/'RESULT.txt').write_text('\n'.join(lines)+'\n')
    return cells,ps
def analyze_a(args):
    t=time.monotonic();frozen();rs,bi=records();gs,account=eligible_groups(rs,bi);ss=scores(bi)
    out=HERE/'T12-A';export_analysis(out,gs,account,bi,ss,'T12-A')
    write(out/'RUN_RECORD.json',{'completed_utc':now(),'elapsed_seconds':time.monotonic()-t,
           'protocol_sha256':sha(PROTOCOL),'historical_scores_sha256':sha(SOURCE/'scores.jsonl'),
           'new_model_calls':0,'host':hostinfo(),'status':'complete'})
    print(str(out/'RESULT.txt'))

def api(route,payload=None,timeout=120):
    body=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request('http://127.0.0.1:11434/api/'+route,data=body,
                               headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
def model_metadata():
    tags=api('tags');matches=[m for m in tags['models'] if m['name']=='bge-m3:latest']
    require(len(matches)==1,'Required local bge-m3 model not installed; no automatic downloads')
    return {'model':matches[0],'ollama':api('version')}
def profile_embed(args):
    p=frozen();require(args.ollama_slot,'Root must grant the Ollama scheduling slot explicitly')
    out=HERE/'T12-B';out.mkdir(parents=True,exist_ok=True);require(not (out/'EMBEDDING_PROFILE.json').exists(),'Development profile already recorded')
    metadata=model_metadata();measurements=[]
    base='A researcher recorded changes in a small public library during the spring season and checked each observation against the original notes before preparing a concise account for colleagues.'
    for n in [100,128]:
        texts=[' '.join((f'Development example {j} '+base+' ').split()*8) for j in range(8)]
        texts=[' '.join(x.split()[:n]) for x in texts];beg=time.monotonic()
        result=api('embed',{'model':'bge-m3:latest','input':texts,'truncate':False,'keep_alive':'10m'})
        vectors=result['embeddings'];require(len(vectors)==8 and all(v for v in vectors),'Development embedding failed')
        measurements.append({'words':n,'n':8,'seconds':time.monotonic()-beg,'dimensions':[len(v) for v in vectors]})
    rs,bi=records();gs,_=eligible_groups(rs,bi)
    ids={r['id'] for arm in ARMS for r in gs[arm]};ids|={bi[i]['parent_id'] for i in list(ids)}
    estimate=max(m['seconds']/m['n'] for m in measurements)*len(ids)
    write(out/'EMBEDDING_PROFILE.json',{'created_utc':now(),'model_metadata':metadata,
      'protocol_sha256':sha(PROTOCOL),'development_only':True,'measurements':measurements,
      'eligible_unique_texts':len(ids),'conservative_estimated_seconds':estimate,
      'budget_seconds':p['B']['embedding_wall_budget_seconds'],
      'fits_budget':estimate<=p['B']['embedding_wall_budget_seconds'],'host':hostinfo()})
    print(str(out/'EMBEDDING_PROFILE.json'))
def embed(args):
    p=frozen();require(args.ollama_slot,'Root must grant the Ollama scheduling slot explicitly')
    t=time.monotonic();rs,bi=records();gs,_=eligible_groups(rs,bi)
    selected={r['id'] for arm in ARMS for r in gs[arm]}
    selected|={bi[i]['parent_id'] for i in list(selected)}
    ids=sorted(selected);out=HERE/'T12-B';out.mkdir(parents=True,exist_ok=True)
    metadata=model_metadata();profile=load(out/'EMBEDDING_PROFILE.json')
    require(profile['protocol_sha256']==sha(PROTOCOL) and profile['model_metadata']==metadata,'Development profile differs')
    require(profile['fits_budget'],'Development estimate exceeds frozen budget; revise the plan explicitly before proceeding')
    lock=out/'EMBEDDING_LOCK.json'
    entry={'model_metadata':metadata,'protocol_sha256':sha(PROTOCOL),'ids':ids,
           'text_hashes':{i:objhash(bi[i]['text']) for i in ids},'batch_size':8}
    if lock.exists():require(load(lock)==entry,'Embedding lock changed')
    else:write(lock,entry)
    ledger=out/'embeddings.jsonl';old=rows(ledger) if ledger.exists() else []
    done={r['id']:r for r in old};require(len(done)==len(old),'Duplicate embedding ledger IDs')
    require(set(done)<=set(ids),'Unknown ledger IDs')
    for i,r in done.items():require(r['text_hash']==entry['text_hashes'][i] and r['model_digest']==metadata['model']['digest'],'Changed cached embedding input')
    pending=[i for i in ids if i not in done]
    for start in range(0,len(pending),8):
        require(time.monotonic()-t<p['B']['embedding_wall_budget_seconds'],'Frozen wall budget reached; partial ledger preserved')
        batch=pending[start:start+8];beg=time.monotonic();error=None;vectors=None
        try:
            result=api('embed',{'model':'bge-m3:latest','input':[bi[i]['text'] for i in batch],
                                'truncate':False,'keep_alive':'10m'},timeout=120)
            vectors=result['embeddings'];require(len(vectors)==len(batch),'Embedding batch length mismatch')
            require(all(v and all(isinstance(x,(int,float)) and math.isfinite(x) for x in v) and sum(x*x for x in v)>0 for v in vectors),'Invalid embedding vector')
        except Exception as exc:error=f'{type(exc).__name__}: {exc}'
        elapsed=time.monotonic()-beg
        for j,i in enumerate(batch):
            append(ledger,{'id':i,'text_hash':entry['text_hashes'][i],
              'model_digest':metadata['model']['digest'],'created_utc':now(),
              'status':'error' if error else 'embedded','error':error,
              'vector':None if error else vectors[j],'batch_seconds':elapsed,'batch_n':len(batch)})
        print(f'Embedded attempts {start+len(batch)}/{len(pending)}',flush=True)
    require(model_metadata()==metadata,'Ollama model metadata changed during run')
    write(out/'EMBEDDING_RUN.json',{'finished_utc':now(),'elapsed_seconds':time.monotonic()-t,
       'attempted_this_run':len(pending),'model_metadata':metadata,'host':hostinfo(),
       'ledger_sha256':sha(ledger),'failures':sum(r['status']!='embedded' for r in rows(ledger))})
def similarities(byid):
    out=HERE/'T12-B';lock=load(out/'EMBEDDING_LOCK.json')
    require(lock['protocol_sha256']==sha(PROTOCOL),'Embedding protocol differs')
    require(sha(out/'embeddings.jsonl')==load(out/'EMBEDDING_RUN.json')['ledger_sha256'],'Embedding ledger changed')
    emb={r['id']:r for r in rows(out/'embeddings.jsonl')}
    require(set(emb)==set(lock['ids']),'Incomplete embedding ledger')
    for i,r in emb.items():require(r['text_hash']==objhash(byid[i]['text']) and r['model_digest']==lock['model_metadata']['model']['digest'],'Embedding provenance mismatch')
    ans={}
    for i,r in byid.items():
        if cohort(r) not in ARMS:continue
        a=emb.get(i,{});b=emb.get(r['parent_id'],{})
        if a.get('status')==b.get('status')=='embedded':
            x=a['vector'];y=b['vector'];require(len(x)==len(y),'Embedding dimensions differ')
            ans[i]=max(-1.,min(1.,sum(u*v for u,v in zip(x,y))/math.sqrt(sum(u*u for u in x)*sum(v*v for v in y))))
    return ans
def analyze_b(args):
    t=time.monotonic();p=frozen();rs,bi=records();gs,account=eligible_groups(rs,bi)
    sims=similarities(bi);ss=scores(bi);out=HERE/'T12-B'
    allmetrics={}
    for threshold in [p['B']['cosine_primary']]+p['B']['cosine_sensitivity']:
        subset={c:[r for r in rr if c not in ARMS or sims.get(r['id'],-2)>=threshold] for c,rr in gs.items()}
        acc=[dict(a) for a in account]
        for a in acc:
            if a['cohort'] in ARMS and a['eligibility']=='eligible':
                a['eligibility']='embedding_unavailable' if a['id'] not in sims else ('eligible' if sims[a['id']]>=threshold else 'below_similarity_threshold')
        extra={'cosine_threshold':threshold,'proxy_only':True,
               'human_ratings':'Pending actual completed independent rating files',
               'model_metadata':load(out/'EMBEDDING_LOCK.json')['model_metadata']}
        target=out if threshold==p['B']['cosine_primary'] else out/f'sensitivity_{threshold:.2f}'
        cells,pairs=export_analysis(target,subset,acc,bi,ss,'T12-B',extra)
        allmetrics[str(threshold)]={'cells':cells,'paired':pairs}
        write(target/'RUN_RECORD.json',{'completed_utc':now(),'elapsed_seconds':time.monotonic()-t,
              'protocol_sha256':sha(PROTOCOL),'scores_sha256':sha(SOURCE/'scores.jsonl'),
              'embedding_ledger_sha256':sha(out/'embeddings.jsonl'),'status':'complete',
              'host':hostinfo(),'human_status':'pending'})
    write(out/'threshold_sensitivity.json',allmetrics)
    csvwrite(out/'pair_similarity.csv',[{'id':i,'cosine_similarity':v} for i,v in sorted(sims.items())])
    print(str(out/'RESULT.txt'))

HUMAN_FIELDS=['review_id','parent_text','rewrite_text','rating','notes','possible_unblinding']
def human_pack(args):
    frozen();rs,bi=records();gs,_=eligible_groups(rs,bi);out=HERE/'T12-B'/'human_review'
    require(not out.exists(),'Human pack exists; never regenerate assignments after ratings')
    rng=random.Random(SEED);selected=[];used=set()
    for arm in ARMS:
        quotas=[14,13,13] if arm=='cross' else [13,14,13]
        for source,n in zip(SOURCES,quotas):
            pool=sorted([r for r in gs[arm] if r['source']==source and r['qid'] not in used],key=lambda r:r['id'])
            rng.shuffle(pool);require(len(pool)>=n,'Insufficient distinct source groups for human plan')
            for r in pool[:n]:selected.append((arm,r));used.add(r['qid'])
    require(len(selected)==len(used)==80,'Human sample not 80 distinct groups')
    rng.shuffle(selected);key=[]
    # Randomized primary assignment balanced within each arm, exactly 40 each.
    primary={}
    for arm in ARMS:
        ids=[r['id'] for a,r in selected if a==arm];rng.shuffle(ids)
        primary.update({i:('A' if j<20 else 'B') for j,i in enumerate(ids)})
    shared=set()
    for reviewer in ['A','B']:
        for arm in ARMS:
            ids=[r['id'] for a,r in selected if a==arm and primary[r['id']]==reviewer]
            rng.shuffle(ids);shared.update(ids[:5])
    assignments={'A':[],'B':[]};out.mkdir(parents=True)
    for j,(arm,r) in enumerate(selected):
        rid='R'+hashlib.sha256(f'{SEED}:{j}:{r["id"]}'.encode()).hexdigest()[:10].upper()
        pr=primary[r['id']];raters=['A','B'] if r['id'] in shared else [pr]
        row={'review_id':rid,'parent_text':bi[r['parent_id']]['text'],'rewrite_text':r['text'],
             'rating':'','notes':'','possible_unblinding':''}
        for reviewer in raters:assignments[reviewer].append(row.copy())
        key.append({'review_id':rid,'record_id':r['id'],'parent_id':r['parent_id'],'qid':r['qid'],
                    'source':r['source'],'arm':arm,'primary_rater':pr,'assigned_raters':raters,
                    'text_hash':objhash([row['parent_text'],row['rewrite_text']])})
    for reviewer in ['A','B']:
        rng.shuffle(assignments[reviewer]);require(len(assignments[reviewer])==50,'Wrong assignment count')
        csvwrite(out/f'reviewer_{reviewer}_blank.csv',assignments[reviewer],HUMAN_FIELDS)
    write(out/'PRIVATE_ASSIGNMENTS.json',key)
    manifest={'created_utc':now(),'protocol_sha256':sha(PROTOCOL),'unique_pairs':80,'total_ratings':100,
              'double_coded_pairs':20,'rating_scale':load(PROTOCOL)['B']['rating_scale'],
              'files':{n:sha(out/n) for n in ['reviewer_A_blank.csv','reviewer_B_blank.csv','PRIVATE_ASSIGNMENTS.json']},
              'status':'awaiting genuine independent human ratings'}
    write(out/'PACK_LOCK.json',manifest)
    (out/'INSTRUCTIONS.txt').write_text('Rate independently without discussing items. Do not inspect private assignments or analysis outputs.\n\nCompare the rewrite with its parent. Judge preservation of meaning, including entities, quantities, causal claims, certainty, additions and omissions. The parent may be factually wrong. This task does not rate factual accuracy.\n\nEnter exactly one integer rating per pair.\n0  Material meaning changed\n1  Uncertain or partly preserved\n2  All material meaning preserved\n\nComplete all 50 assigned rows. Do not alter review IDs or either text column. Record concerns in notes and suspected source or model clues in possible_unblinding. Incidental clues may weaken blinding. Save as a new UTF-8 CSV. Do not fill in another person\'s file. Primary assignments were fixed in advance.\n')
    print(str(out))
def kappa(a,b):
    n=len(a)
    if not n:return None
    observed=sum(x==y for x,y in zip(a,b))/n
    expected=sum(a.count(c)*b.count(c) for c in [0,1,2])/(n*n)
    return None if expected==1 else (observed-expected)/(1-expected)
def import_human(args):
    t=time.monotonic();frozen();out=HERE/'T12-B'/'human_review';lock=load(out/'PACK_LOCK.json')
    require(lock['protocol_sha256']==sha(PROTOCOL),'Human protocol differs')
    for n,h in lock['files'].items():require(sha(out/n)==h,'Original human pack changed')
    require(args.name_a.strip() and args.name_b.strip() and args.name_a.strip().casefold()!=args.name_b.strip().casefold(),'Two distinct actual reviewer identities required')
    key=load(out/'PRIVATE_ASSIGNMENTS.json');lookup={x['review_id']:x for x in key};ratings={}
    paths={'A':Path(args.rater_a).resolve(),'B':Path(args.rater_b).resolve()}
    require(paths['A']!=paths['B'],'Reviewer files must be distinct')
    for who in ['A','B']:
        got=csvread(paths[who]);blank=csvread(out/f'reviewer_{who}_blank.csv');expected={x['review_id']:x for x in blank}
        require(len(got)==len({x.get('review_id') for x in got})==50,'Exactly 50 unique assigned rows required')
        require({x.get('review_id') for x in got}==set(expected),'Assigned reviewer IDs differ')
        for r in got:
            rid=r['review_id'];require(set(r)==set(HUMAN_FIELDS),'Unexpected rating file columns')
            require(all(r[f]==expected[rid][f] for f in ['parent_text','rewrite_text']),'Review text changed')
            require(r['rating'].strip() in ['0','1','2'],'Missing or invalid human rating; no imputation')
            require(objhash([r['parent_text'],r['rewrite_text']])==lookup[rid]['text_hash'],'Human text hash differs')
            ratings[who,rid]=int(r['rating'].strip())
    primary=[ratings[k['primary_rater'],k['review_id']] for k in key]
    shared=[k for k in key if len(k['assigned_raters'])==2];a=[ratings['A',k['review_id']] for k in shared];b=[ratings['B',k['review_id']] for k in shared]
    require(len(primary)==80 and len(shared)==20,'Wrong human denominators')
    rng=random.Random(SEED+1);boot=[]
    for _ in range(5000):
        ix=[rng.randrange(20) for _ in range(20)];z=kappa([a[i] for i in ix],[b[i] for i in ix])
        if z is not None:boot.append(z)
    boot.sort();kci=[boot[int(.025*(len(boot)-1))],boot[int(.975*(len(boot)-1))]] if boot else [None,None]
    kept=sum(v==2 for v in primary);agree=sum(x==y for x,y in zip(a,b));summary={
      'preserved':kept,'primary_n':80,'preserved_wilson95':wilson(kept,80),
      'shared_exact_agreement':agree,'shared_n':20,'agreement_wilson95':wilson(agree,20),
      'cohen_kappa':kappa(a,b),'kappa_bootstrap95_descriptive':kci,'valid_bootstrap_replicates':len(boot),
      'rating_counts':dict(collections.Counter(primary)),
      'status':'observed human ratings imported','imported_utc':now(),
      'limitations':'Small retrospective source stratified sample with preassigned primary ratings. Human labels measure fidelity to the parent, not factual correctness or the prior 900 pair confirmatory endpoint.'}
    target=out/'imported';require(not target.exists(),'Human import exists; corrections require an explicit versioned audit')
    target.mkdir();write(target/'human_metrics.json',summary)
    write(target/'PRIVATE_IMPORT_RECORD.json',{'reviewers':{'A':args.name_a,'B':args.name_b},
        'input_files':{str(v):sha(v) for v in paths.values()},'protocol_sha256':sha(PROTOCOL),
        'elapsed_seconds':time.monotonic()-t,'imported_utc':now(),'host':hostinfo()})
    text=f'Independent human review found preserved meaning in {kept} of 80 preassigned primary ratings, {100*kept/80:.1f}% with a 95% interval {interval(wilson(kept,80))}. Exact agreement was {agree} of 20 shared pairs. These ratings assess fidelity to the parent and do not establish factual correctness.'
    require(len(text.split())<=60,'Human paste text too long')
    (target/'HUMAN_RESULT.txt').write_text(text+'\n\n'+json.dumps(summary,indent=2)+'\n')
    print(str(target/'HUMAN_RESULT.txt'))
def self_test(args):
    require(wilson(0,0)==[None,None],'Empty Wilson failed')
    require(abs(wilson(50,100)[0]-.4038315303659956)<1e-12,'Wilson check failed')
    require(cp(0,10)[0]==0 and cp(10,10)[1]==1,'CP boundaries failed')
    z=paired([1,1,0,0],[0,1,1,0]);require(z['retained_flags']==1 and z['retention_denominator']==2 and z['parent_minus_child_rate']==0,'Paired counts failed')
    require(z['paired_drop_interval95'][0]<=0<=z['paired_drop_interval95'][1],'Paired interval failed')
    base={'text':' '.join(['x']*110),'status':'completed','done':True,'finish_reason':'stop','condition':'direct'}
    require(valid(base),'Valid generation rejected')
    require(not valid(dict(base,finish_reason='length')),'Truncation accepted')
    require(not valid(dict(base,text='short')),'Short response accepted')
    require(valid(dict(base,condition='human',status='observed_public_human',finish_reason='public_source')),'Human status rejected')
    require(kappa([0,1,2],[0,1,2])==1 and kappa([2,2],[2,2]) is None,'Kappa failed')
    print('Synthetic statistical and eligibility checks passed. No historical outcomes read.')
def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True)
    for name in ['freeze','analyze-a','analyze-b','human-pack','self-test']:sub.add_parser(name)
    for name in ['embed','profile-embed']:
        e=sub.add_parser(name);e.add_argument('--ollama-slot',action='store_true',help='Root explicitly allocated the local inference slot')
    h=sub.add_parser('import-human');h.add_argument('--rater-a',required=True);h.add_argument('--rater-b',required=True);h.add_argument('--name-a',required=True);h.add_argument('--name-b',required=True)
    a=parser.parse_args();globals()[a.cmd.replace('-','_')](a)
if __name__=='__main__':main()
