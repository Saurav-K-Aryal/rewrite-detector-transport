Topic 12 sensitivity analyses from November 18, 2026

This package contains the frozen analysis implementation, a publication copy of
the protocol, aggregate detector results and local model run metadata.

T12-A applies a shared 100 to 128 word and valid completion contract to historical
records. It retains each rewrite only when its direct parent also qualifies.
It reports Wilson intervals descriptively and conservative paired discordance
intervals for six detector comparisons. This is a retrospective sensitivity
analysis on reused records, not an independent confirmatory replication.

T12-B adds a fixed BGE-M3 cosine threshold of 0.90 with 0.85 and 0.95 sensitivity
analyses. These thresholds are assumptions, not independently calibrated human
fidelity criteria. Human ratings remain pending until actual files are imported.

The reusable runner requires Python and SciPy, the historical private source run
and original provenance files, and the original project folder layout. It does
not download models or train detectors. Public release of aggregate results does
not provide the private raw text required to repeat embeddings and human review.
Run `python run_topic12.py self-test` for synthetic statistical and eligibility
checks. See the command line help for the frozen analysis stages.

Absolute local project paths in protocol and run metadata are replaced with
PROJECT_ROOT. PUBLICATION_MANIFEST.json records original and public hashes, so
the redacted publication copy is not misrepresented as byte identical to the
original frozen record. Numerical values and analysis choices are unchanged.

Raw source prose, human rating sheets, reviewer identities, assignment keys,
individual similarity scores and embedding vectors are excluded deliberately.
The optional Phi rewrite implementation is included as prepared code only.
Its presence does not imply that generation or detector scoring was completed.
