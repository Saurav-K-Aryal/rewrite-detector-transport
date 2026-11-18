# Two channel calibrated audit

This CPU simulation studies when two calibrated detector channels can identify a creator's marking fraction and strength. It requires Python 3.12, NumPy and SciPy. No model weights, GPU, text dataset or external service is needed. Run from this folder.

```sh
python -m pip install -r requirements.txt
python validate.py --out local_validation.json
python t12c.py --out local_runs/T12-C
```

Each new run freezes its protocol and source before simulation and refuses to overwrite an existing run. Use `--prepare-only` to freeze without execution, then `--execute-frozen` with the same output folder. A custom protocol can be supplied with `--protocol` during preparation.

The archived study assumes known synthetic response curves and retains dependence between channels through a shared latent mark. At marked fraction 0.5, accepted query-grid counts ranged from 100,000 to 50,000,000 across four strengths. These are hypothetical counts under conservative confidence intervals, not measured performance on actual 50-token text or lower bounds for every estimator.

`results/T12-C/` contains the original frozen protocol, compact results and aggregate selection and confirmation CSVs. `DESIGN.txt` gives the identification argument and interval construction. Fixed seeds reproduce the omitted raw replicates. `provenance/` records hashes, validation and public execution adaptations. The scientific entrypoint is unchanged.

The archived default waiting-window timestamp was overridden by an explicit start instruction before the original runs. Historical protocols and timestamps are preserved. The scheduling note in `provenance/PORTABLE_ADAPTATIONS.json` explains this without including private authorization records.
