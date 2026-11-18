# Phi rewrite pretest registry

This registry specifies new Phi rewrites and their analysis before Phi test
generation. The experiment uses 450 existing source questions and previously
observed Gemma direct responses, Qwen rewrites and Gemma self rewrites. Historical
comparator results were already known. The new Phi test is prospective on reused
sources. It is not an independent replication on new source questions. The
earlier T12-A and T12-B analyses remain retrospective sensitivity analyses.

Three disjoint historical smoke parents were used for a development timing
profile. Their generated responses are excluded from this registry and from
the test panel. The timing rule selected all 450 previously frozen test groups.
Only aggregate development timing and technical status metadata are included.

The frozen generation protocol uses the original rewrite prompt and decoding
settings. The separately frozen analysis addendum compares four conditions on
the same parent groups where every text is complete and contains 100 to 128
words. Three fixed detectors retain their original thresholds. Nine paired
contrasts have conservative simultaneous intervals, with separate individual
intervals and flagged-parent retention. Missing observations remain explicit.
No favorable direction is assumed. Phi fidelity to its parent is unreviewed.

Phi has about 14.7 billion parameters and the Gemma comparator about 12.38
billion. Model size, training and serving backend are confounded. Eligibility
under every model can select easier groups. This experiment does not replace
the historical human-qualified endpoint or establish a universal detection limit.

## Contents and provenance

The three Python source files are unchanged scientific implementations. Run
`python analyze_phi.py self-test` for synthetic statistical checks. Execution
requires Python with SciPy and the original private project inputs and layout.
No new inference is performed by the self-test.

The generation protocol, analysis addendum, model lock, selection lock and
metadata-only manifests are included. Manifests contain question and parent
identifiers, prompt and parent text hashes, seeds and source categories. They
contain no source prose, generated responses or detector outcomes. Raw data,
rating sheets, assignment keys, reviewer identities and model weights are absent.

Absolute local project paths in protocol documents are replaced by PROJECT_ROOT.
PRIVACY_HASH_MANIFEST.json bridges original local hashes and public file hashes.
Scientific choices, numeric settings, IDs, hashes and seeds are unchanged. A
public protocol copy is not represented as byte-identical to its private source
when its paths have been redacted. Redaction changes no analysis implementation.

PRETEST_STATUS.json records the local check that no Phi test record or request
ledger existed when this registry was staged. The repository commit timestamp
provides the external publication time once this staging folder is published.
This registry reports no Phi test results.
