# Evaluation Results

Cases evaluated: 22

| Metric | Baseline (single prompt, no tools) | Agent (tools + verification) |
|---|---|---|
| Accuracy | 0.682 | 0.864 |
| Precision | 0.692 | 0.8 |
| Recall | 0.75 | 1.0 |
| F1 | 0.72 | 0.889 |
| False positives (flagged a non-bug) | 4 | 3 |
| False negatives (missed a real bug) | 3 | 0 |
| Total cost (USD) | 0.5925 | 1.6983 |
| Avg latency (ms) | 10096 | 22641 |
| CLI/parse errors | 0 | 0 |
