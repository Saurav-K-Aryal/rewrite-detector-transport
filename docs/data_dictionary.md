# Text-free sufficient evidence

`data/records.jsonl.gz` has 8,700 rows:1,500 human-control excerpts,450 human-reference excerpts,1,350 direct outputs,4,050 model-to-model rewrites and 1,350 rewrites of human-origin excerpts. Fields include stable record/question IDs, source, condition, origin/final model, parent ID, completion state, word count, stored mechanical-validity/refusal flags and available costs. It contains no source text, prompt, title, answer, reviewer identity or semantic label.

`data/scores.jsonl.gz` contains exactly seven score rows per record: detector, raw score, frozen flag, status, an input hash and available tokenizer-cap fields. The hash identifies the original normalized 128-word scoring input but does not reveal it. It permits correspondence to the original archive; the numeric release cannot recompute that hash from text it does not contain.

`data/thresholds.json` gives each score direction and strict cutoff. A score exactly at the cutoff is unflagged. `radar_calibration_scores.json` retains 500 numeric calibration scores, rank 476 and the resulting cutoff; human calibration text is excluded.

The main false-positive cohort is condition `human`. Condition `human_reference` links the source excerpt to its question and human-origin rewrites. Condition `human_rewrite` denotes machine-transformed human-origin content and is not assigned a human-negative label.

One question produces multiple model outputs, which are paired through its stable ID. Aggregated model counts are descriptive. The audit never treats all 60,900 detector rows as independent samples.

All data/provenance files present at export are hashed in `data/SHA256SUMS.json`. Original evidence-file hashes are recorded separately because sanitized metadata exports differ from the original full-text files.
