#!/usr/bin/env python3
"""CPU analysis for the separately frozen, optional Phi rewrite extension.

This helper does not perform inference or change the original generation plan.
Freeze its addendum before any optional Phi test request.
"""
from __future__ import annotations
import argparse, collections, hashlib, importlib.metadata, json, math, sys, time
from pathlib import Path
import run_topic12 as c
import optional_phi as gen

OUT=gen.OUT
ADDENDUM=OUT/'ANALYSIS_ADDENDUM.json'
CONDITIONS=['direct','cross','self','phi']
LABELS={'direct':'Gemma direct','cross':'Qwen rewrite','self':'Gemma self rewrite','phi':'Phi rewrite'}
COMPARATORS=['direct','cross','self']

def interval_unknown(k,n,unknown):
    c.require(0<=k<=n and 0<=unknown<=n-k,'Invalid unknown count')
    if not n:return [None,None]
    return [c.wilson(k,n)[0],c.wilson(k+unknown,n)[1]]

def cell(flags,condition,detector,panel):
    n=len(flags);unknown=sum(v is None for v in flags);k=sum(v==1 for v in flags)
    c.require(all(v in [0,1,None] for v in flags),'Invalid flag')
    return {'panel':panel,'condition':condition,'detector':detector,'n':n,
      'confirmed_flagged':k,'known_not_flagged':n-unknown-k,'unknown':unknown,
      'confirmed_flag_fraction':k/n if n else None,
      'possible_flag_fraction_range':[k/n,(k+unknown)/n] if n else [None,None],
      'descriptive_wilson95_envelope':interval_unknown(k,n,unknown),
      'interval_note':'Wilson interval when fully observed; otherwise envelope over all allocations of unknown flags. A missing score is not a confirmed negative.'}

def contrast(comparator,phi,family=9):
    c.require(len(comparator)==len(phi),'Unequal paired panel')
    c.require(all(x in [0,1,None] for x in comparator+phi),'Invalid pair flags')
    n=len(phi);unknown=sum(a is None or b is None for a,b in zip(comparator,phi))
    lost=sum(a==1 and b==0 for a,b in zip(comparator,phi))
    gained=sum(a==0 and b==1 for a,b in zip(comparator,phi))
    def bounds(f):
        if not n:return [None,None]
        # Union bound over the two discordance proportions and f comparisons.
        lo_lost=c.cp(lost,n,.05/(2*f))[0]
        hi_lost=c.cp(lost+unknown,n,.05/(2*f))[1]
        lo_gained=c.cp(gained,n,.05/(2*f))[0]
        hi_gained=c.cp(gained+unknown,n,.05/(2*f))[1]
        return [max(-1.,lo_lost-hi_gained),min(1.,hi_lost-lo_gained)]
    return {'n_pairs':n,'both_scored_n':n-unknown,'unknown_pair_outcomes':unknown,
      'comparator_flagged_phi_not_flagged':lost,'comparator_not_flagged_phi_flagged':gained,
      'comparator_minus_phi_point':(lost-gained)/n if n and not unknown else None,
      'identification_range':[(lost-gained-unknown)/n,(lost-gained+unknown)/n] if n else [None,None],
      'paired_drop_individual95':bounds(1),'paired_drop_simultaneous95':bounds(family),
      'simultaneous_family':family,
      'direction':'Positive means lower Phi flag rate. Negative means higher Phi flag rate. Unknown pairs remain in the denominator and widen both bounds.'}

def retention(parent,phi):
    c.require(len(parent)==len(phi),'Unequal retention inputs')
    targets=[b for a,b in zip(parent,phi) if a==1]
    n=len(targets);k=sum(v==1 for v in targets);unknown=sum(v is None for v in targets)
    return {'eligible_pairs':len(parent),'parent_score_unknown':sum(v is None for v in parent),
      'flagged_parent_denominator':n,'retained_flags':k,'unknown_child_scores':unknown,
      'confirmed_retention_fraction':k/n if n else None,
      'possible_retention_range':[k/n,(k+unknown)/n] if n else [None,None],
      'retention_wilson95_envelope':interval_unknown(k,n,unknown),
      'interpretation':'Conditional on a known flagged Gemma parent. Unknown child scores remain explicit; unknown parents cannot be assigned to the flagged-parent stratum.'}

def self_test(args=None):
    x=cell([1,0,None],'phi','test','synthetic')
    c.require(x['n']==3 and x['confirmed_flagged']==1 and x['unknown']==1,'Missingness cell test failed')
    c.require(x['descriptive_wilson95_envelope'][0]<1/3 and x['descriptive_wilson95_envelope'][1]>2/3,'Envelope failed')
    x=contrast([1,1,0,0],[0,1,1,0])
    c.require(x['n_pairs']==4 and x['comparator_minus_phi_point']==0,'Paired difference failed')
    exact=c.paired([1,1,0,0],[0,1,1,0],family=9)
    c.require(x['paired_drop_simultaneous95']==exact['paired_drop_interval95'],'Nine contrast interval differs from known formula')
    y=contrast([1,1,0,0],[0,None,1,0])
    c.require(y['unknown_pair_outcomes']==1 and y['comparator_minus_phi_point'] is None,'Unknown pair treated as zero')
    c.require(y['identification_range']==[-.25,.25],'Unknown identification bounds failed')
    c.require(y['paired_drop_simultaneous95'][0]<=x['paired_drop_simultaneous95'][0] and y['paired_drop_simultaneous95'][1]>=x['paired_drop_simultaneous95'][1],'Unknown interval not conservative')
    z=retention([1,1,0,None],[1,None,1,1])
    c.require(z['flagged_parent_denominator']==2 and z['retained_flags']==1 and z['unknown_child_scores']==1 and z['parent_score_unknown']==1,'Retention missingness failed')
    c.require(cell([],'phi','test','synthetic')['descriptive_wilson95_envelope']==[None,None],'Empty cell failed')
    c.require(contrast([],[])['paired_drop_simultaneous95']==[None,None],'Empty contrast failed')
    c.require(retention([0,0],[1,1])['flagged_parent_denominator']==0,'No flagged parent failed')
    c.require(contrast([1]*100,[0]*100)['paired_drop_simultaneous95'][0]>0,'Known positive direction failed')
    c.require(contrast([0]*100,[1]*100)['paired_drop_simultaneous95'][1]<0,'Known negative direction failed')
    print('Synthetic paired interval, direction, missingness, retention and empty-panel tests passed. No study outcomes read.')
    return {'status':'passed','synthetic_only':True,'checks':['Wilson unknown envelope','paired nine contrast formula parity','unknown pair denominator','unknown identification interval','conservative missing bounds','retention conditional denominator','empty cells','zero flagged parents','positive and negative direction']}

def freeze(args):
    gen.verify();c.require(not ADDENDUM.exists(),'Analysis addendum already frozen')
    c.require(not (OUT/'records.jsonl').exists(),'Cannot freeze after any Phi test output')
    c.require(not (OUT/'test_client/REQUESTS.jsonl').exists() and not (OUT/'test_client/REQUEST_FAILURES.jsonl').exists(),'Cannot freeze after any Phi test request')
    deps=[Path(__file__),Path(c.__file__),Path(gen.__file__),OUT/'PROTOCOL.json',OUT/'MODEL_LOCK.json',
          OUT/'TEST_MANIFEST.json',OUT/'SELECTED_TEST_MANIFEST.json',OUT/'TEST_LOCK.json',OUT/'DEVELOPMENT.json',
          c.PROTOCOL,c.SOURCE/'records.jsonl',c.SOURCE/'scores.jsonl',c.SOURCE/'SCORES_COMPLETE.json',
          c.RELEASE/'data/thresholds.json',c.HERE/'T12-A/REUSED_DETECTOR_PROVENANCE.json']
    tests=self_test()
    c.write(ADDENDUM,{'version':'optional-phi-analysis-v1','frozen_utc':c.now(),
      'freeze_timing':'Before every Phi test request. Three disjoint development outputs already exist and are excluded.',
      'historical_exposure':'Historical Gemma, Qwen and self rewrite detector aggregates and T12-A/B sensitivity results are already known. Phi test outputs and scores do not yet exist.',
      'input_sha256':{str(p):c.sha(p) for p in deps},'synthetic_self_test':tests,
      'planned_parent_groups':450,'selected_test_groups':len(c.load(OUT/'SELECTED_TEST_MANIFEST.json')),
      'primary_panel':'Intersection by exact parent_id and qid where historical Gemma direct, historical Qwen rewrite, historical Gemma self rewrite and new Phi rewrite each satisfy the frozen 100 to 128 whitespace word and valid completion contract. Inclusion never depends on detector scores.',
      'primary_table_rows':['Gemma direct','Qwen rewrite','Gemma self rewrite','Phi rewrite'],
      'detectors':c.DET,'thresholds':'Original frozen detector cutoffs unchanged. No fitting, recalibration or threshold selection.',
      'primary_cells':'Flag fractions on the common eligible panel. Every cell reports confirmed flags, n, unknown count, and a descriptive 95 percent Wilson interval. Unknown scores remain in n and widen the interval to the union over every unknown flag assignment.',
      'paired_comparisons':['Gemma direct minus Phi','Qwen rewrite minus Phi','Gemma self rewrite minus Phi'],
      'paired_family':'Nine simultaneous contrasts, three comparisons for each of three detectors. Also show conservative individual 95 percent intervals. Differences use union bounds on two Clopper Pearson discordance proportions. Unknown paired outcomes widen both discordance bounds and stay in n; no point estimate is imputed.',
      'retention':'Fraction of common-panel Phi rewrites still flagged among known flagged direct Gemma parents, separately for each detector. Child score outages remain unknown in this denominator; unavailable parent scores are counted separately.',
      'diagnostics':'All 450 planned parent groups remain in accounting, including runtime omissions, generation errors, length violations, unavailable detector scores and common-panel exclusions. Separate own-Phi eligible parent and Phi rates are diagnostic, not replacements for the common panel. Completion and eligibility fractions have explicit n and Wilson intervals.',
      'human_reference':'The unchanged T12-A human control false positive rates are provided outside the four-row table as reference rates, with n and 95 percent intervals.',
      'meaning_preservation':'Phi outputs have no human fidelity evidence. No Phi embedding proxy is used in this primary extension. This analysis does not unlock or replace the historical 900 pair dual-human endpoint.',
      'inference':'Descriptive comparisons on a fixed source and detector panel. A positive, negative or inconclusive contrast will be reported without an expected favorable direction.',
      'limits':['Phi is approximately 14.7 billion parameters and Gemma approximately 12.38 billion. Model size, training and serving backend are confounded.',
                'Comparator texts are reused and questions do not establish author independence.',
                'The common-panel restriction is conditional on valid outputs from every model and may select easier groups.',
                'Results do not establish human fidelity, factual correctness or a universal detection limit.'],
      'outputs':['RESULT.txt','PHI_ANALYSIS.json','ANALYSIS_COMPLETE.json','common_panel_cells.csv','paired_contrasts.csv','parent_flag_retention.csv','planned_diagnostics.csv','planned_accounting.csv'],
      'public_release':'Only validated scripts, protocols with local paths redacted, aggregate outputs and run metadata. No source prose, individual records or private human material.'})
    print(ADDENDUM)

def verified():
    gen.verify();a=c.load(ADDENDUM)
    for path,h in a['input_sha256'].items():c.require(c.sha(path)==h,'Frozen analysis dependency changed '+path)
    return a

def optional_data():
    complete=c.load(OUT/'GENERATION_COMPLETE.json');sc=c.load(OUT/'SCORES_COMPLETE.json')
    c.require(c.sha(OUT/'records.jsonl')==complete['records_sha256'],'Phi generation hash mismatch')
    c.require(c.sha(OUT/'scores.jsonl')==sc['scores_sha256'],'Phi score hash mismatch')
    selected=c.load(OUT/'SELECTED_TEST_MANIFEST.json');tasks={r['id']:r for r in selected}
    rr=c.rows(OUT/'records.jsonl');byid={r['id']:r for r in rr}
    c.require(len(byid)==len(rr)==len(selected) and set(byid)==set(tasks),'Phi generation panel incomplete or duplicated')
    c.require(complete['model_lock_sha256']==c.sha(OUT/'MODEL_LOCK.json'),'Phi model lock changed')
    for ident,r in byid.items():
        for key in ['qid','source','source_id','parent_id','seed','source_model','model','prompt_sha256','parent_text_sha256','kind']:
            c.require(r.get(key)==tasks[ident].get(key),'Phi planned metadata changed '+key)
        c.require(r['kind']=='test','Development output entered test panel')
    ss=c.rows(OUT/'scores.jsonl');idx={};cuts=c.load(c.RELEASE/'data/thresholds.json')
    c.require(len(ss)==sc['score_rows']==3*len(selected),'Phi score panel must contain exactly three statuses per selected record')
    for s in ss:
        key=(s['id'],s['detector']);c.require(s['id'] in byid and s['detector'] in c.DET and key not in idx,'Unexpected or duplicate Phi score')
        c.require(s['input_hash']==c.objhash(c.text_input(byid[s['id']])),'Phi detector input differs')
        if s['status']=='scored':
            c.require(s['flag'] in [0,1] and math.isfinite(s['score']),'Invalid Phi score')
            cut=cuts[s['detector']];expected=int(s['score']<cut['cutoff']) if cut['direction']=='less' else int(s['score']>cut['cutoff'])
            c.require(s['flag']==expected,'Phi cutoff mismatch')
        idx[key]=s
    model=c.load(OUT/'MODEL_LOCK.json')
    c.require(c.load(OUT/'test_client/SERVER_VERSION.json')==model['server_version'],'Phi serving version differs')
    mm=c.load(OUT/'test_client/MODEL_MANIFEST.json')
    c.require(mm[gen.MODEL]['digest']==model['model']['digest'],'Phi model digest differs')
    return byid,idx,complete,sc

def flag(scores,record,detector):
    if not record:return None
    s=scores.get((record['id'],detector),{})
    return s['flag'] if s.get('status')=='scored' else None

def analyze(args):
    start=time.monotonic();add=verified();phi,phi_scores,genc,scorec=optional_data()
    old,old_byid=c.records();old_scores=c.scores(old_byid)
    old_rewrites={}
    for r in old:
        kind=c.cohort(r)
        if kind in ['cross','self']:
            key=(r['parent_id'],kind);c.require(key not in old_rewrites,'Duplicated historical comparator');old_rewrites[key]=r
    plans=c.load(OUT/'TEST_MANIFEST.json');selected={r['id'] for r in c.load(OUT/'SELECTED_TEST_MANIFEST.json')}
    units=[];account=[]
    for task in plans:
        parent=old_byid[task['parent_id']]
        c.require(parent['qid']==task['qid'],'Parent question differs')
        rr={'direct':parent,'cross':old_rewrites.get((parent['id'],'cross')),
            'self':old_rewrites.get((parent['id'],'self')),'phi':phi.get(task['id'])}
        for condition,r in rr.items():
            if r:c.require(r['qid']==task['qid'] and (condition=='direct' or r['parent_id']==parent['id']),'Comparator parent link differs')
        eligible={k:c.valid(r) for k,r in rr.items()}
        common=all(eligible.values());own=eligible['direct'] and eligible['phi']
        unit={'task':task,'records':rr,'common':common,'own_phi':own};units.append(unit)
        acc={'qid':task['qid'],'parent_id':parent['id'],'source':task['source'],
          'phi_id':task['id'],'selected_for_generation':task['id'] in selected,'common_eligible':common,'own_phi_eligible':own}
        for condition,r in rr.items():
            acc[condition+'_eligibility']=c.reason(r)
            acc[condition+'_status']=r.get('status') if r else 'not_selected_runtime' if condition=='phi' and task['id'] not in selected else 'record_missing'
            for d in c.DET:
                ss=phi_scores if condition=='phi' else old_scores
                acc[condition+'_'+d+'_score_status']=ss.get((r['id'],d),{}).get('status','unavailable') if r else 'generation_unavailable'
        account.append(acc)
    c.require(len(units)==450 and len({u['task']['qid'] for u in units})==450,'Expected 450 distinct planned parent groups')
    common=[u for u in units if u['common']];own=[u for u in units if u['own_phi']]
    def flags(us,condition,d):return [flag(phi_scores if condition=='phi' else old_scores,u['records'][condition],d) for u in us]
    cells=[cell(flags(common,k,d),k,d,'common_eligible') for k in CONDITIONS for d in c.DET]
    pairs=[];ret=[]
    for d in c.DET:
        ph=flags(common,'phi',d)
        for comparator in COMPARATORS:
            pairs.append(dict(contrast(flags(common,comparator,d),ph),comparator=comparator,detector=d))
        ret.append(dict(retention(flags(common,'direct',d),ph),detector=d))
    diagnostics=[]
    for name,us,kinds in [('all_planned',units,CONDITIONS),('own_phi_eligible',own,['direct','phi'])]:
        diagnostics.extend(cell(flags(us,k,d),k,d,name) for k in kinds for d in c.DET)
    completion=[]
    for k in CONDITIONS:
        complete_n=sum(bool(u['records'][k]) and u['records'][k].get('status') in ['completed','complete','ok'] and u['records'][k].get('done') is True and u['records'][k].get('finish_reason') not in [None,'length','max_tokens','max_token','limit'] for u in units)
        eligible_n=sum(c.valid(u['records'][k]) for u in units)
        completion.append({'condition':k,'planned_n':450,'completed_nontruncated_n':complete_n,
          'completion_wilson95':c.wilson(complete_n,450),'own_text_length_completion_eligible_n':eligible_n,
          'eligibility_wilson95':c.wilson(eligible_n,450)})
    human=[r for r in old if c.cohort(r)=='human' and c.valid(r)]
    human_ref=[cell([flag(old_scores,r,d) for r in human],'human',d,'historical_reference') for d in c.DET]
    run={'completed_utc':c.now(),'elapsed_seconds':time.monotonic()-start,'analysis_code_sha256':c.sha(__file__),
      'analysis_addendum_sha256':c.sha(ADDENDUM),'host':c.hostinfo(),
      'analysis_environment_package_versions':{p:importlib.metadata.version(p) for p in ['numpy','scipy','torch','transformers']},
      'package_version_scope':'Measured during CPU analysis, not a separate observation of the earlier detector process.',
      'generation_complete':genc,'score_complete':scorec,
      'model_and_backend':c.load(OUT/'MODEL_LOCK.json'),
      'generation_error_counts':dict(collections.Counter(r['status'] for r in phi.values())),
      'score_status_counts':dict(collections.Counter(s['status'] for s in phi_scores.values())),
      'new_model_calls_in_analysis':0}
    result={'study':'optional Phi common parent panel','common_parent_n':len(common),'own_phi_eligible_n':len(own),
      'all_planned_n':450,'runtime_selected_n':len(selected),'cells':cells,'paired_contrasts':pairs,
      'parent_flag_retention':ret,'human_fpr_reference':human_ref,'completion_and_eligibility':completion,
      'diagnostic_cells':diagnostics,'run_record':run,'human_fidelity':'Phi unreviewed'}
    c.write(OUT/'PHI_ANALYSIS.json',result)
    for name,rs in [('common_panel_cells.csv',cells),('paired_contrasts.csv',pairs),('parent_flag_retention.csv',ret),
                    ('planned_diagnostics.csv',diagnostics),('completion_diagnostics.csv',completion),('planned_accounting.csv',account)]:c.csvwrite(OUT/name,rs)
    c.write(OUT/'ANALYSIS_RUN_RECORD.json',run)
    lo=sum(r['paired_drop_simultaneous95'][0] is not None and r['paired_drop_simultaneous95'][0]>0 for r in pairs)
    hi=sum(r['paired_drop_simultaneous95'][1] is not None and r['paired_drop_simultaneous95'][1]<0 for r in pairs)
    available=sum(r['n_pairs']>0 for r in pairs)
    prose=f'Comparisons used {len(common)} source groups with complete texts of 100 to 128 words under every condition. Simultaneous paired intervals placed Phi flag rates lower in {lo} and higher in {hi} of nine comparisons. The remaining comparisons were inconclusive or unavailable. Comparator texts are reused. Phi meaning preservation remains unreviewed.'
    c.require(len(prose.split())<=60,'Paste text exceeds 60 words')
    lookup={(m['condition'],m['detector']):m for m in cells}
    def cell_text(m):
        if not m['n']:return 'NA, n = 0'
        s=f"{c.pct(m['confirmed_flag_fraction'])}% ({m['confirmed_flagged']}/{m['n']}) {c.interval(m['descriptive_wilson95_envelope'])}"
        return s+(f"; {m['unknown']} unknown" if m['unknown'] else '')
    table=['| Condition | Binoculars | Fast DetectGPT | RADAR |','|---|---|---|---|']
    table.extend('| '+LABELS[k]+' | '+' | '.join(cell_text(lookup[k,d]) for d in c.DET)+' |' for k in CONDITIONS)
    lines=['Optional Phi rewrite extension','','Paste ready text','',prose,'','Four row common panel table','',*table,'',
      'Each cell gives a percentage, confirmed flag count and common denominator, followed by a descriptive 95% interval in percent. Unknown scores remain in the denominator and widen the interval. All four rows use the same source groups.','',
      'Human false positive reference','']
    for h in human_ref:lines.append(c.NAMES[h['detector']]+' '+cell_text(h)+'.')
    lines+=['','Paired comparisons and flagged parent retention','']
    for r in pairs:
        lines.append(f"{LABELS[r['comparator']]} minus Phi with {c.NAMES[r['detector']]} over {r['n_pairs']} pairs gives {c.pct(r['comparator_minus_phi_point'])} percentage points, individual 95% interval {c.interval(r['paired_drop_individual95'])}, nine comparison simultaneous interval {c.interval(r['paired_drop_simultaneous95'])}, and {r['unknown_pair_outcomes']} unknown paired outcomes.")
    for r in ret:lines.append(f"Phi retained {r['retained_flags']}/{r['flagged_parent_denominator']} flagged Gemma parents under {c.NAMES[r['detector']]}, {c.pct(r['confirmed_retention_fraction'])}% with descriptive 95% interval {c.interval(r['retention_wilson95_envelope'])}, {r['unknown_child_scores']} unknown children and {r['parent_score_unknown']} unavailable parent scores.")
    lines+=['','All planned outcomes and exclusions','',f"All 450 planned groups remain in planned_accounting.csv. Runtime selected {len(selected)}, common eligible {len(common)}, own Phi eligible {len(own)}. Completion and eligibility proportions with 95% intervals are in completion_diagnostics.csv. All planned and own Phi rates are in planned_diagnostics.csv. Generation and scoring failures remain explicit in the run record.",'',
      'Limits and what is not established','',
      'Phi has approximately 14.7 billion parameters and Gemma approximately 12.38 billion. Size, training and serving backend are confounded. Common eligibility can select easier groups. Comparators and source questions are reused, and question separation does not establish author independence. No Phi human fidelity or embedding qualification is available. This extension does not replace the historical 900 pair human endpoint or establish factual correctness or a universal detection limit.','',
      'Full frozen generation protocol','',json.dumps(c.load(OUT/'PROTOCOL.json'),indent=2),
      'Full frozen analysis addendum','',json.dumps(add,indent=2),
      'Model backend runtime and errors','',json.dumps(run,indent=2),
      'Historical detector provenance','',(c.HERE/'T12-A/REUSED_DETECTOR_PROVENANCE.json').read_text()]
    (OUT/'RESULT.txt').write_text('\n'.join(lines)+'\n')
    c.write(OUT/'ANALYSIS_COMPLETE.json',{'completed_utc':c.now(),'result_sha256':c.sha(OUT/'RESULT.txt'),
      'analysis_sha256':c.sha(OUT/'PHI_ANALYSIS.json'),'analysis_addendum_sha256':c.sha(ADDENDUM),
      'status':'complete','common_parent_n':len(common),'new_model_calls':0})
    print(OUT/'RESULT.txt')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['self-test','freeze','analyze']);a=p.parse_args()
    {'self-test':self_test,'freeze':freeze,'analyze':analyze}[a.command](a)
if __name__=='__main__':main()
