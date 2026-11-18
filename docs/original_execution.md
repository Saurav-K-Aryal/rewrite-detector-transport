# Scoring and reproduction limits

The audit command reads only numeric evidence in this repository and makes no network calls. It reproduces all 357 cell intervals and the seven exported count, paired-change and length-diagnostic tables. It does not regenerate text, fit classifiers, change thresholds, run detectors or create semantic labels.

For the two published scoring methods, the original run used pinned Falcon 7B base/instruct models, native MPS bfloat 16 forwards and float 32 CPU reductions. Production invoked unchanged published functions. Binoculars uses shifted hard-label NLL divided by all-position cross-entropy; lower scores are stronger evidence. Fast-DetectGPT uses aligned shifted distributions and labels; higher scores are stronger evidence. Both share the same scoring-model pair.

RADAR used the official class 0 probability with a pinned local checkpoint, evaluation mode, maximum 512 tokens and separate human-only calibration. Its model-card conditions differ from its source-repository license. Exact model/source revisions and the retained license note are in `provenance/scoring_models.json`. No third-party detector implementation or weights are vendored here.

Every detector received the first 128 whitespace-separated words, subject to a 512-token cap for neural scorers. The recorded extra token caps did not bind in this run. The numeric export cannot independently validate tokenization, original word counts, inherited human labels, actual semantic fidelity or pretraining contamination. Reproducing those aspects requires the retained original inputs, licensed source retrieval and exact scoring environment. Numeric checksums and raw-score recomputation serve different purposes.

The data source was the pinned RAID human-text material identified in `provenance/run.json`; no raw source corpus is redistributed. Distinct source/question groups do not establish distinct authors. Dependency licenses and upstream model/dataset terms remain independent of this artifact.
