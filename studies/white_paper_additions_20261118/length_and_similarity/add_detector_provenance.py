"""Package unchanged historical scorer provenance without rerunning detectors."""
from pathlib import Path
import json,shutil
import run_topic12 as c

c.frozen()
published=c.ROOT/'outputs/pretrained_detectors_v2'
files={'historical_run_config':c.SOURCE.parent/'RUN_CONFIG.json',
       'historical_environment':c.SOURCE.parent/'ENVIRONMENT.json',
       'scorer_metadata':published/'runs/20261118T013958Z_published_v2/SCORER_METADATA.json',
       'falcon_install':published/'MODEL_INSTALL.json',
       'extension_scoring_lock':c.SOURCE/'SCORING_LOCK.json',
       'extension_scoring_status':c.SOURCE/'SCORING_STATUS.json',
       'extension_scores_complete':c.SOURCE/'SCORES_COMPLETE.json',
       'radar_calibration':c.SOURCE/'RADAR_CALIBRATION.json',
       'thresholds':c.RELEASE/'data/thresholds.json'}
raw={k:c.load(p) for k,p in files.items()}
install=raw['falcon_install']
models={k:{n:v for n,v in m.items() if n!='snapshot_path'} for k,m in install['models'].items()}
radar={k:v for k,v in raw['extension_scoring_lock']['radar_install'].items() if k!='snapshot_path'}
value={'assembled_utc':c.now(),'purpose':'Self contained documentation of reused historical scores. No new detector inference, fitting, precision change, or calibration.',
 'sources':{k:{'file':str(p.relative_to(c.ROOT)),'sha256':c.sha(p)} for k,p in files.items()},
 'original_scores':raw['extension_scores_complete'],'original_scoring_status':raw['extension_scoring_status'],
 'historical_environment':raw['historical_environment'],'historical_package_versions':raw['historical_run_config']['packages'],
 'detector_device':raw['extension_scoring_lock']['device'],'scorer_metadata':raw['scorer_metadata'],
 'metadata_scope':'The reference run records Falcon dtypes and backend; the extension configuration independently records identical package versions and MPS device, and its scoring lock pins the unchanged scorer source.',
 'falcon_models_and_verified_weight_hashes':models,'published_detector_code_pins':install['detector_repositories'],
 'radar_install':radar,'radar_dtype_policy':'Saved loader specifies no torch_dtype override. Its scoring function casts logits to float32 for log softmax before moving the final probability to CPU. No separate forward dtype measurement was recorded.',
 'thresholds':{k:raw['thresholds'][k] for k in c.DET},
 'radar_historical_calibration':{k:raw['radar_calibration'][k] for k in ['n','rank','threshold','calibration_source_sha256']},
 'detector_input':'First 128 whitespace words. Falcon and RADAR tokenizer caps are 512 tokens. The reused score ledger is checked against the exact historical normalized text hash.',
 'threshold_policy':'All operating points remain unchanged. The original 5 percent human calibration target is not a guaranteed false positive rate on this panel.'}
for directory in [c.HERE/'T12-A',c.HERE/'T12-B']:
    if not (directory/'RUN_RECORD.json').exists():continue
    target=directory/'REUSED_DETECTOR_PROVENANCE.json'
    if target.exists():
        prior=c.load(target)
        c.require({k:v for k,v in prior.items() if k!='assembled_utc'}=={k:v for k,v in value.items() if k!='assembled_utc'},'Historical detector provenance changed')
    else:c.write(target,value)
    record=directory/'RUN_RECORD.json';record_copy=directory/'RUN_RECORD_ANALYSIS_ORIGINAL.json'
    if not record_copy.exists():shutil.copyfile(record,record_copy)
    updated=c.load(record)
    updated['reused_detector_provenance']={'file':str(target),'sha256':c.sha(target),
      'original_analysis_record_sha256':c.sha(record_copy),'metadata_enrichment_only':True}
    c.write(record,updated)
    print(target)
