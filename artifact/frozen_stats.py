"""Verbatim statistical function extracts from the validated final audit.
No inference, fitting, or threshold selection.
"""
import statistics
from scipy.stats import beta
FAMILY=357
def require(condition,message):
    if not condition: raise ValueError(message)

def exact_interval(k,n,family=FAMILY):
    require(0<=k<=n and n>0,'Invalid binomial count')
    tail=.05/(2*family)
    return [0. if k==0 else float(beta.ppf(tail,k,n-k+1)),
            1. if k==n else float(beta.ppf(1-tail,k+1,n-k))]


def paired_summary(parents,children,parent_scores,child_scores):
    """Descriptive paired changes, one observation per question. No p-values."""
    require(len(parents)==len(children)==len(parent_scores)==len(child_scores)>0,'Invalid paired inputs')
    require(all(a['qid']==b['qid'] and b['parent_id']==a['id'] for a,b in zip(parents,children)), 'Wrong parent link')
    p=[s['flag'] for s in parent_scores];c=[s['flag'] for s in child_scores];n=len(p)
    differences=[b['score']-a['score'] for a,b in zip(parent_scores,child_scores)]
    lost=sum(a==1 and b==0 for a,b in zip(p,c));gained=sum(a==0 and b==1 for a,b in zip(p,c))
    return {'n_pairs':n,'parent_flagged':sum(p),'rewrite_flagged':sum(c),
            'parent_flag_rate':sum(p)/n,'rewrite_flag_rate':sum(c)/n,
            'rewrite_minus_parent_flag_rate':(sum(c)-sum(p))/n,
            'lost_flags':lost,'gained_flags':gained,'unchanged_flags':n-lost-gained,
            'parent_mean_raw_score':statistics.mean(s['score'] for s in parent_scores),
            'rewrite_mean_raw_score':statistics.mean(s['score'] for s in child_scores),
            'mean_paired_raw_score_change':statistics.mean(differences),
            'median_paired_raw_score_change':statistics.median(differences)}
