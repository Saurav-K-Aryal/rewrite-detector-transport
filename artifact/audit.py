"""Recompute transport tables from text-free numeric evidence, without inference."""
from __future__ import annotations
import argparse,itertools,math,statistics
from collections import Counter,defaultdict
from pathlib import Path
from .common import ROOT,read_json,read_rows,write_json,write_csv,verify_data,verify_csv,require,safe_output
from .frozen_stats import exact_interval,paired_summary

PANEL=['word_tfidf','char_tfidf','length_style','historical_word','binoculars','fastdetectgpt','radar']
MODELS=['qwen3.5:4b','llama3.1:8b','gemma4:12b'];SOURCES=['wikipedia','abstracts','recipes']
NAMES={'word_tfidf':'Word TF-IDF','char_tfidf':'Character TF-IDF','length_style':'Length/style','historical_word':'Historical word','binoculars':'Binoculars','fastdetectgpt':'Fast-DetectGPT','radar':'RADAR'}

def valid_length(r):return bool(r['done']) and r['status']=='completed' and r['finish_reason'] not in ['length','max_tokens','max_token','limit'] and 100<=r['word_count']<=128

def length_row(rows,source,condition,model):
    words=[r['word_count'] for r in rows];valid=sum(valid_length(r) for r in rows)
    return {'source':source,'condition':condition,'model':model,'source_model':'all','n':len(rows),'length_contract_pass':valid,
        'length_contract_fail':len(rows)-valid,'length_pass_fraction':valid/len(rows),'under100_words':sum(w<100 for w in words),
        'over128_words':sum(w>128 for w in words),'minimum_words':min(words),'median_words':statistics.median(words),'maximum_words':max(words),
        'heuristic_possible_refusal_flags_unadjudicated':sum(bool(r['possible_refusal']) for r in rows)}

def run(output,verify=False,plots=True):
    output=safe_output(output);output.mkdir(parents=True,exist_ok=True);files=verify_data()
    records=read_rows('data/records.jsonl.gz');scores=read_rows('data/scores.jsonl.gz');thresholds=read_json('data/thresholds.json')
    byid={r['id']:r for r in records};lookup={(r['id'],r['detector']):r for r in scores}
    require(len(byid)==len(records)==8700,'Duplicate or missing record')
    require(len(lookup)==len(scores)==60900 and set(lookup)=={(r['id'],d) for r in records for d in PANEL},'Incomplete detector panel')
    expected={'human':1500,'human_reference':450,'direct':1350,'rewrite':4050,'human_rewrite':1350}
    require(dict(Counter(r['condition'] for r in records))==expected,'Condition counts differ')
    forbidden={'text','question','human_answer','parent_text','rewrite_text','reviewer_id','meaning_preserved'}
    require(all(not forbidden.intersection(r) for r in records+scores),'Unexpected text/reviewer field in derived evidence')
    for s in scores:
        require(s['status']=='scored' and math.isfinite(s['score']),'Failed/nonfinite score')
        cutoff=thresholds[s['detector']]
        flag=int(s['score']<cutoff['cutoff']) if cutoff['direction']=='less' else int(s['score']>cutoff['cutoff'])
        require(flag==s['flag'],'Frozen threshold decision differs')
    for r in records:
        if r['condition'] in ['rewrite','human_rewrite']:
            parent=byid[r['parent_id']];require(parent['qid']==r['qid'] and parent['source']==r['source'],'Cross-question parent link')
            require(parent['condition']==('direct' if r['condition']=='rewrite' else 'human_reference'),'Wrong parent category')
            require(parent['model']==r['source_model'] if r['condition']=='rewrite' else r['source_model']=='public_human','Wrong origin model')
    for q in {r['qid'] for r in records if r['condition']=='direct'}:
        matrix=[r for r in records if r['qid']==q and r['condition']=='rewrite']
        require(len(matrix)==9 and {(r['source_model'],r['model']) for r in matrix}==set(itertools.product(MODELS,MODELS)),'Incomplete3×3matrix')
    cal=read_json('data/radar_calibration_scores.json');require(cal['n']==500 and cal['rank']==476 and len(cal['values'])==500 and sorted(cal['values'])[475]==cal['threshold']==thresholds['radar']['cutoff'],'RADAR calibration mismatch')
    grouped=defaultdict(list)
    for r in records:grouped[r['source'],r['condition'],r['source_model'],r['model']].append(r)
    require(len(grouped)*len(PANEL)==357,'Interval family changed');cells=[]
    for (source,condition,origin,model),rr in sorted(grouped.items(),key=lambda x:str(x[0])):
        for detector in PANEL:
            k=sum(lookup[r['id'],detector]['flag'] for r in rr);lo,hi=exact_interval(k,len(rr))
            cells.append({'source':source,'condition':condition,'source_model':origin,'model':model,'detector':detector,'flagged':k,'n':len(rr),'rate':k/len(rr),'simultaneous95_lower':lo,'simultaneous95_upper':hi,'interval_family':357})
    direct=[];paired=[];lengths=[]
    for source in ['all']+SOURCES:
        source_rows=[r for r in records if source=='all' or r['source']==source]
        for model in MODELS:
            rr=[r for r in source_rows if r['condition']=='direct' and r['model']==model]
            for detector in PANEL:
                k=sum(lookup[r['id'],detector]['flag'] for r in rr)
                direct.append({'source':source,'model':model,'detector':detector,'flagged':k,'n':len(rr),'rate':k/len(rr),'interval_note':'Source-specific cells use frozen 357-family intervals in cell_metrics.csv; pooled values are descriptive.'})
            for condition in ['direct','rewrite','human_rewrite']:lengths.append(length_row([r for r in source_rows if r['condition']==condition and r['model']==model],source,condition,model))
        for condition,origins in [('rewrite',MODELS),('human_rewrite',['public_human'])]:
            for origin,model in itertools.product(origins,MODELS):
                rr=sorted([r for r in source_rows if r['condition']==condition and r['source_model']==origin and r['model']==model],key=lambda r:r['qid']);parents=[byid[r['parent_id']] for r in rr]
                for detector in PANEL:
                    values=paired_summary(parents,rr,[lookup[r['id'],detector] for r in parents],[lookup[r['id'],detector] for r in rr])
                    paired.append(dict(source=source,condition=condition,source_model=origin,model=model,detector=detector,score_direction='lower means more AI evidence' if detector=='binoculars' else 'higher means more AI evidence',**values))
    human=[c for c in cells if c['condition']=='human'];totals=[]
    for detector in PANEL:
        hh=[c for c in human if c['detector']==detector];dd=[c for c in direct if c['source']=='all' and c['detector']==detector]
        totals.append({'detector':detector,'human_false_positives':sum(c['flagged'] for c in hh),'human_n':sum(c['n'] for c in hh),
            'human_fpr':sum(c['flagged'] for c in hh)/sum(c['n'] for c in hh),'direct_flagged':sum(c['flagged'] for c in dd),'direct_n':sum(c['n'] for c in dd),
            'direct_detection_rate':sum(c['flagged'] for c in dd)/sum(c['n'] for c in dd),'interpretation':'Descriptive equal-source/equal-model totals; repeated model outputs share question blocks.'})
    unreviewed=[]
    for detector in ['binoculars','fastdetectgpt']:
        for model in ['qwen3.5:4b','gemma4:12b']:
            rr=[r for r in records if r['condition']=='rewrite' and r['source_model']=='gemma4:12b' and r['model']==model]
            event=lambda r:lookup[r['parent_id'],detector]['flag']==1 and lookup[r['id'],detector]['flag']==0
            unreviewed.append({'detector':detector,'rewriter':model,'n_planned':len(rr),'parent_flagged_to_rewrite_unflagged':sum(event(r) for r in rr),
                'with_mechanical_length_contract_only':sum(valid_length(r) and event(r) for r in rr),'quality_status':'Not meaning-qualified; not the primary J endpoint.'})
    generated=[r for r in records if r['condition'] not in ['human','human_reference']]
    for r in generated:require(valid_length(r)==bool(r['length_contract_pass']),'Recorded word-count validity mismatch')
    summary={'records':len(records),'generated':len(generated),'scores':len(scores),'detectors':7,'matrix_questions':len({r['qid'] for r in generated}),
        'human_controls':1500,'human_references':450,'interval_family':357,'primary_status':'pending_independent_review_and_adjudication',
        'length_contract_fail':sum(not valid_length(r) for r in generated),'length_contract_pass':sum(valid_length(r) for r in generated)}
    tables={'cell_metrics':cells,'human_fpr_by_source':human,'direct_by_model_source':direct,'paired_history_changes':paired,
        'length_diagnostics':lengths,'all_comparators':totals,'unreviewed_primary_arm_diagnostics':unreviewed}
    for name,table in tables.items():write_csv(output/(name+'.csv'),table)
    write_json(output/'summary.json',summary)
    if verify:
        require(summary==read_json('results/reference/summary.json'),'Reference summary mismatch')
        keys={'cell_metrics':['source','condition','source_model','model','detector'],'human_fpr_by_source':['source','detector'],
            'direct_by_model_source':['source','model','detector'],'paired_history_changes':['source','condition','source_model','model','detector'],
            'length_diagnostics':['source','condition','model','source_model'],'all_comparators':['detector'],'unreviewed_primary_arm_diagnostics':['detector','rewriter']}
        for name,key in keys.items():verify_csv(output/(name+'.csv'),ROOT/f'results/reference/{name}.csv',key)
    if plots:_plots(output,human,paired)
    write_json(output/'AUDIT_STATUS.json',{'status':'passed','evidence_checksums':files,'threshold_flags_recomputed':len(scores),'simultaneous_intervals_recomputed':357,
        'reference_tables_checked':verify,'model_scoring_repeated':False,'primary_status':summary['primary_status'],
        'scope':'Numeric transport audit only. Original texts/weights/private judgments are not distributed. Semantic fidelity and score recomputation are outside this artifact.'})
    return summary

def _plots(out,human,paired):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(10,4),sharex=True)
    for ax,source in zip(axes,SOURCES):
        rr=[next(r for r in human if r['source']==source and r['detector']==d) for d in PANEL];values=[100*r['rate'] for r in rr]
        ax.errorbar(values,range(7),xerr=[[100*r['rate']-100*r['simultaneous95_lower'] for r in rr],[100*r['simultaneous95_upper']-100*r['rate'] for r in rr]],fmt='ko',capsize=2)
        ax.set_yticks(range(7),[NAMES[d] for d in PANEL],fontsize=8);ax.set_title(source.capitalize());ax.set_xlabel('Human-control flag rate (%)');ax.set_xlim(-2,102)
    fig.suptitle('500 human controls/source; 357-cell family simultaneous intervals');fig.tight_layout();fig.savefig(out/'human_false_positives.pdf');plt.close(fig)
    for source in ['all']+SOURCES:
        fig,axes=plt.subplots(2,4,figsize=(10,5.8));im=None
        for ax,detector in zip(axes.flat,PANEL):
            matrix=np.array([[100*next(r['rewrite_minus_parent_flag_rate'] for r in paired if r['source']==source and r['condition']=='rewrite' and r['source_model']==origin and r['model']==model and r['detector']==detector) for model in MODELS] for origin in MODELS])
            im=ax.imshow(matrix,cmap='Greys',vmin=-100,vmax=100);ax.set_xticks(range(3),['Qwen','Llama','Gemma'],fontsize=8);ax.set_yticks(range(3),['Qwen','Llama','Gemma'],fontsize=8);ax.set_title(NAMES[detector],fontsize=10)
            for i,j in itertools.product(range(3),repeat=2):ax.text(j,i,f'{matrix[i,j]:+.1f}',ha='center',va='center',color='white' if matrix[i,j]>15 else 'black',fontsize=8)
        axes.flat[-1].axis('off');fig.suptitle(f'{source.capitalize()}: rewrite minus parent flags (percentage points)\nRows = parent model; columns = final writer; descriptive, no fidelity judgment',fontsize=11)
        fig.subplots_adjust(top=.84,hspace=.42,wspace=.45);fig.savefig(out/f'rewrite_matrix_{source}.pdf');plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'results/recomputed');p.add_argument('--verify',action='store_true');p.add_argument('--no-plots',action='store_true');a=p.parse_args()
    print(run(a.output,a.verify,not a.no_plots))
