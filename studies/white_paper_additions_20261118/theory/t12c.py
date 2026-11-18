#!/usr/bin/env python3
"""Two calibrated synthetic channels identify marking fraction and strength."""
from __future__ import annotations
import csv
import gzip
import time
import numpy as np
from scipy.stats import beta
from common import now, report, setup, write_json

def cp(k, n, alpha=0.05):
    k = np.asarray(k)
    low = np.zeros(k.shape, dtype=float)
    high = np.ones(k.shape, dtype=float)
    positive = k > 0
    below = k < n
    low[positive] = beta.ppf(alpha / 2, k[positive], n - k[positive] + 1)
    high[below] = beta.ppf(1 - alpha / 2, k[below] + 1, n - k[below])
    return low, high

def mc_interval(k, n):
    low, high = cp(np.array([k]), n)
    return [float(low[0]), float(high[0])]

def project_rectangle(a, b, c, d):
    left = np.maximum(a, c)
    right = np.minimum(b, np.sqrt(np.maximum(d, 0)))
    valid = (a <= b) & (c <= d) & (left <= right) & (d >= 0)
    origin = valid & (a == 0) & (c == 0)
    regular = valid & ~origin
    low = np.zeros(len(a))
    high = np.ones(len(a))
    np.divide(left ** 2, np.minimum(d, left), out=low, where=regular)
    np.divide(right ** 2, np.maximum(c, right ** 2), out=high, where=regular)
    # An empty projected set is flagged; conservative [0,1] fallback retains it
    # in every denominator and never counts it as a precise estimate.
    low = np.clip(low, 0, 1)
    high = np.clip(high, 0, 1)
    return low, high, ~valid

def projected_intervals(k1, k2, n, fpr, alpha):
    # Two marginal intervals with alpha/2 each, hence joint coverage >=1-alpha
    # by the union bound even when channel flags for one query are correlated.
    q1l, q1u = cp(k1, n, alpha / 2)
    q2l, q2u = cp(k2, n, alpha / 2)
    scale = 1 - fpr
    a = np.maximum(0, (q1l - fpr) / scale)
    b = np.minimum(1, (q1u - fpr) / scale)
    c = np.maximum(0, (q2l - fpr) / scale)
    d = np.minimum(1, (q2u - fpr) / scale)
    return project_rectangle(a, b, c, d)

def joint_probabilities(rho, theta, fpr):
    s1 = fpr + (1 - fpr) * theta
    s2 = fpr + (1 - fpr) * theta ** 2
    # Categories 00, 10, 01, 11. Both observations share the same latent mark.
    unmarked = np.array([(1-fpr)**2, fpr*(1-fpr), fpr*(1-fpr), fpr**2])
    marked = np.array([(1-s1)*(1-s2), s1*(1-s2), (1-s1)*s2, s1*s2])
    return (1-rho)*unmarked + rho*marked, s1, s2

def simulate(cfg, ir, it, ni, stage, rho, theta, n, reps, writer):
    rng = np.random.default_rng(np.random.SeedSequence([cfg["seed"], ir, it, ni, stage]))
    probs, s1, s2 = joint_probabilities(rho, theta, cfg["fpr"])
    counts = rng.multinomial(n, probs, size=reps)
    k1 = counts[:, 1] + counts[:, 3]
    k2 = counts[:, 2] + counts[:, 3]
    low, high, empty = projected_intervals(k1, k2, n, cfg["fpr"], cfg["confidence_alpha"])
    width = high-low
    covered = (low <= rho) & (rho <= high)
    narrow = width <= cfg["target_width"]
    for r in range(reps):
        writer.writerow({
            "stage": "selection" if stage == 0 else "confirmation", "rho": rho, "theta": theta,
            "queries": n, "replicate": r, "n00": int(counts[r, 0]), "n10": int(counts[r, 1]),
            "n01": int(counts[r, 2]), "n11": int(counts[r, 3]),
            "lower": float(low[r]), "upper": float(high[r]), "midpoint": float((low[r]+high[r])/2),
            "width": float(width[r]), "covered": int(covered[r]), "width_at_most_004": int(narrow[r]),
            "empty_set_fallback": int(empty[r]),
        })
    coverage_hits = int(covered.sum())
    precision_hits = int(narrow.sum())
    return {
        "rho": rho, "theta": theta, "fpr_both": cfg["fpr"], "sensitivity_1": s1, "sensitivity_2": s2,
        "queries": n, "detector_evaluations": 2*n, "replicates": reps,
        "coverage": coverage_hits/reps, "coverage_mc95": mc_interval(coverage_hits, reps),
        "precision_probability": precision_hits/reps, "precision_mc95": mc_interval(precision_hits, reps),
        "mean_interval_width": float(width.mean()), "median_interval_width": float(np.median(width)),
        "p95_interval_width": float(np.quantile(width, .95)), "empty_set_fallbacks": int(empty.sum()),
        "joint_probabilities_00_10_01_11": probs.tolist(),
    }

def main():
    cfg, out = setup(__file__, "t12c_protocol.json")
    if cfg is None:
        return
    started = time.monotonic()
    selection = []
    confirmation = []
    failures = []
    fields = ["stage", "rho", "theta", "queries", "replicate", "n00", "n10", "n01", "n11", "lower", "upper", "midpoint", "width", "covered", "width_at_most_004", "empty_set_fallback"]
    with gzip.open(out / "replicates.csv.gz", "wt", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for ir, rho in enumerate(cfg["rho_grid"]):
            for it, theta in enumerate(cfg["theta_grid"]):
                eligible = []
                for ni, n in enumerate(cfg["query_grid"]):
                    try:
                        row = simulate(cfg, ir, it, ni, 0, rho, theta, n, cfg["selection_replicates"], writer)
                        selection.append(row)
                        if row["precision_probability"] >= cfg["selection_precision_rate"]:
                            eligible.append((ni, n))
                    except Exception as error:
                        failures.append({"stage": "selection", "rho": rho, "theta": theta, "queries": n,
                                         "attempted_replicates": cfg["selection_replicates"], "error": repr(error)})
                ni, n = eligible[0] if eligible else (len(cfg["query_grid"])-1, cfg["query_grid"][-1])
                try:
                    row = simulate(cfg, ir, it, ni, 1, rho, theta, n, cfg["confirmation_replicates"], writer)
                    row["selection_passed"] = bool(eligible)
                    row["precision_criterion_met"] = bool(eligible) and row["precision_mc95"][0] >= cfg["target_precision_probability"]
                    row["query_count_interpretation"] = "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
                    confirmation.append(row)
                except Exception as error:
                    failures.append({"stage": "confirmation", "rho": rho, "theta": theta, "queries": n,
                                     "attempted_replicates": cfg["confirmation_replicates"], "error": repr(error)})
    one_channel = {
        "q1": .01+.99*.25, "rho_times_theta": .25, "compatible_rho_interval": [.25, 1],
        "examples_rho_theta": [[.25, 1], [.5, .5], [1, .25]],
        "interpretation": "Even infinitely many first-channel queries cannot distinguish these parameter pairs",
    }
    if cfg["fpr"] != .01:
        one_channel["q1"] = cfg["fpr"] + (1-cfg["fpr"])*.25
    summary = {
        "label": "Synthetic oracle-calibrated channels, not observed watermark performance on 50-token text",
        "one_channel_nonidentification": one_channel,
        "two_channel_inverse": {"a": "(q1-f)/(1-f)", "b": "(q2-f)/(1-f)", "theta": "b/a", "rho": "a*a/b",
                                "jacobian_determinant": "(1-f)^2*rho*theta^2", "singularities": "rho=0 or theta=0"},
        "selection": selection, "confirmation": confirmation, "failures": failures,
        "planned_selection_cells": len(cfg["rho_grid"])*len(cfg["theta_grid"])*len(cfg["query_grid"]),
        "planned_confirmation_cells": len(cfg["rho_grid"])*len(cfg["theta_grid"]),
        "wall_seconds": time.monotonic()-started, "finished_utc": now(),
    }
    write_json(out / "summary.json", summary)
    write_json(out / "FAILURES.json", failures)
    primary = [r for r in confirmation if r["rho"] == cfg["primary_table_rho"]]
    primary.sort(key=lambda r: r["theta"], reverse=True)
    def interval(rate, ci):
        return f"{100*rate:.2f}% [{100*ci[0]:.2f}, {100*ci[1]:.2f}]"
    table = "| Strength | TPR channel 1 and 2 | Queries | Coverage with MC 95% CI | Width at most .04 with MC 95% CI |\n|---:|---:|---:|---:|---:|\n"
    for row in primary:
        count = f"{row['queries']:,}" + ("" if row["precision_criterion_met"] else " criterion unmet")
        table += f"| {row['theta']} | {100*row['sensitivity_1']:.2f}%, {100*row['sensitivity_2']:.2f}% | {count} | {interval(row['coverage'], row['coverage_mc95'])} | {interval(row['precision_probability'], row['precision_mc95'])} |\n"
    passed = [r for r in primary if r["precision_criterion_met"]]
    if len(passed) == len(cfg["theta_grid"]) and not failures:
        nmin = min(r["queries"] for r in passed)
        nmax = max(r["queries"] for r in passed)
        prose = (f"With known synthetic calibration and one percent false positives, two channels estimated a marked fraction of 0.5 with 95 percent interval width at most 0.04 in at least 95 percent of replicates using {nmin:,} to {nmax:,} queries across four strengths, while one channel left fraction unidentified.")
    else:
        prose = (f"With known synthetic calibration and one percent false positives, two channels met the prespecified precision criterion in {len(passed)} of {len(cfg['theta_grid'])} strength settings at marked fraction 0.5, while one channel left fraction unidentified and weaker signals required wider intervals or more queries.")
    limits = (f"Each table row uses {cfg['confirmation_replicates']} independent confirmation replicates at marked fraction {cfg['primary_table_rho']}. Sensitivities are stipulated response curves, not measurements on real 50 token outputs. Calibration is known exactly and query outputs are independent. Both channels observe each query and share its latent mark, requiring two detector evaluations per query. Marginal exact intervals with a union bound remain valid under this within query dependence. Width at most 0.04 gives half width at most 0.02 around the reported interval midpoint. No precision guarantee is uniform near zero marking fraction or zero strength. Monte Carlo intervals describe simulation uncertainty. Empty projected confidence sets receive a flagged conservative [0,1] fallback. The candidate query grid does not identify the exact minimum sample size. Execution failures remain recorded rather than becoming simulated successes. No provider or actual watermark implementation was audited.")
    compact_record = {k: v for k, v in summary.items() if k not in ["selection", "confirmation"]}
    compact_record["confirmation"] = confirmation
    report(out, "T12 C synthetic two channel audit", prose, table, limits, compact_record)
    write_json(out / "RUN_COMPLETE.json", {"status": "completed_with_failures" if failures else "completed", "wall_seconds": summary["wall_seconds"], "finished_utc": summary["finished_utc"], "failed_cells": len(failures)})
    print(f"T12-C completed {len(confirmation)} confirmation settings; {out}")

if __name__ == "__main__":
    main()
