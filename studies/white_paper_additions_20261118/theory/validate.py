"""Numerical checks of the public calibrated-audit implementation."""
import argparse
from pathlib import Path
import numpy as np
from common import digest, now, write_json
from t12c import cp, joint_probabilities, project_rectangle

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='local_validation.json')
    args=parser.parse_args()
    cases=[((0,0,0,0),(0,1,False)),((.25,.25,.125,.125),(.5,.5,False)),
           ((.5,.6,.1,.2),(0,1,True)),((0,-.1,0,.2),(0,1,True)),
           ((.2,.3,.08,.1),(.4,1,False)),((.1,.4,.2,.3),(.2,.8,False)),
           ((1,1,1,1),(1,1,False))]
    for values,expected in cases:
        lo,hi,empty=project_rectangle(*(np.array([x]) for x in values))
        assert np.allclose([lo[0],hi[0]],expected[:2],atol=1e-12)
        assert bool(empty[0])==expected[2]
    rho,theta=np.meshgrid(np.linspace(0,1,501),np.linspace(0,1,501),indexing='ij')
    aa,bb=rho*theta,rho*theta**2
    rng=np.random.default_rng(2026111809)
    for _ in range(25):
        a,b=np.sort(rng.uniform(size=2));c,d=np.sort(rng.uniform(size=2))
        lo,hi,empty=project_rectangle(*(np.array([x]) for x in [a,b,c,d]))
        feasible=(a<=aa)&(aa<=b)&(c<=bb)&(bb<=d)
        if feasible.any():
            assert not empty[0]
            assert lo[0]<=rho[feasible].min()+1e-12
            assert hi[0]>=rho[feasible].max()-1e-12
    probabilities,s1,s2=joint_probabilities(.5,.5,.01)
    assert np.isclose(probabilities.sum(),1)
    assert np.isclose(probabilities[1]+probabilities[3],.2575)
    assert np.isclose(probabilities[2]+probabilities[3],.13375)
    assert probabilities[3]>.2575*.13375
    lo,hi=cp(np.array([0,1000]),1000)
    assert lo[0]==0 and hi[1]==1
    here=Path(__file__).resolve().parent
    record={'status':'passed','validated_utc':now(),'scope':'Post-result software checks, no Monte Carlo scientific rerun',
            'analytic_boundary_cases':7,'independent_parameter_grid_points':int(rho.size),
            'rectangle_checks':25,'joint_distribution_and_dependence':'passed','binomial_endpoints':'passed',
            'source_sha256':{name:digest(here/name) for name in ['t12c.py','common.py','validate.py']}}
    write_json(args.out,record)
    print('Passed projection, dependence and binomial checks')

if __name__=='__main__': main()
