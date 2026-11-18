# Rewrite detector transport

A portable, text-free numerical audit of a frozen three-model rewriting matrix and seven text detectors across three source-domain bundles.

The artifact recomputes the published tables from included numeric scores and record metadata. It makes no generation or detector-scoring calls and requires no model weights or external dataset downloads after dependency installation.

## Run the audit

Use Python 3.12 from this directory:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
make test
make verify
```

The command writes tables, figures and `AUDIT_STATUS.json` to `results/recomputed/`, comparing every reference-table entry with the recomputation. Reference outputs are under `results/reference/`. `make audit` recomputes without that comparison.

## Study and result boundaries

The study used 450 question/source blocks across three source-domain bundles, a complete 3×3 parent/rewriter matrix, human-origin rewrite controls and 1,500 separate public-human control excerpts. It completed 6,750 model calls, producing 8,700 records and 60,900 scores across seven detectors. All 357 simultaneous interval cells are retained.

The existing thresholds remain frozen. RADAR received its separately specified 500-human calibration pass. The audit checks score direction, every threshold flag, the full rewriting matrix, parent-child links, paired lost/gained detections, word-count validity, and the original family of simultaneous intervals.

Raw detection loss is not a meaning-preserving evasion outcome. Independent semantic review and adjudication remain pending, so this release does not calculate or assert the quality-qualified primary result. The same-model rewrite is a substantive comparator. Detector agreement is not independent replication when methods share scoring models, and multiple outputs from one question are not independent samples.

## Contents

- `artifact/`: portable audit and extracted statistical functions.
- `data/`: text-free record metadata, numeric detector scores, frozen thresholds and numeric RADAR calibration scores.
- `provenance/`: source and model identifiers, original evidence hashes and export boundaries.
- `results/reference/`: checked source-specific, matrix, paired and quality-diagnostic tables.
- `docs/`: data dictionary, scoring protocol and limitations.
- `paper/`: ACM `sigconf` sources and the compiled preprint. `make paper` requires `latexmk` and a TeX installation containing `acmart`. `make figures` rebuilds the publication figures from the bundled audited summaries.

This is a portable numerical audit, not a full rerun of model scoring. Source texts, prompts, generated prose, model weights, private review keys and completed human ratings are not distributed. Consequently the release cannot independently recount words from text, recompute detector scores, assess factual truth or supply missing semantic judgments. Recorded word counts and heuristic flags are audited as metadata. See [the reproduction limits](docs/original_execution.md).

Human controls, human-reference excerpts and model rewrites of human-origin text remain separate categories. Only the first category supplies the main false-positive denominators. See [the rights note](LICENSE_NOTE.md) before redistribution.
