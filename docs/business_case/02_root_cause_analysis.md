# Root-Cause Analysis

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.

Rate vs group average, by dimension (inbound: deviation rate; outbound: late dispatch rate).

| case_type | dimension | value | cases | deviation_rate | rework_rate | rate_vs_group_avg |
|---|---|---|---|---|---|---|
| INBOUND | uom_valid | invalid | 50 | 0.240 | 0.040 | 3.707 |
| INBOUND | supplier_id | SUP007 | 45 | 0.133 | 0.022 | 2.060 |
| INBOUND | supplier_id | SUP009 | 54 | 0.111 | 0.074 | 1.716 |
| INBOUND | supplier_id | SUP006 | 271 | 0.100 | 0.089 | 1.539 |
| INBOUND | supplier_id | SUP018 | 257 | 0.089 | 0.058 | 1.382 |
| INBOUND | supplier_id | SUP014 | 148 | 0.088 | 0.020 | 1.357 |
| INBOUND | supplier_id | SUP022 | 38 | 0.079 | 0.053 | 1.219 |
| INBOUND | zone | COLD | 382 | 0.079 | 0.047 | 1.213 |
| OUTBOUND | backorder | backorder | 376 | 0.566 | 0.077 | 6.810 |
| OUTBOUND | priority | High | 433 | 0.185 | 0.083 | 2.221 |
| OUTBOUND | zone | AMB | 1521 | 0.088 | 0.048 | 1.059 |
| OUTBOUND | zone | COLD | 1090 | 0.085 | 0.135 | 1.026 |
| OUTBOUND | priority | Standard | 2020 | 0.071 | 0.079 | 0.857 |
| OUTBOUND | zone | CTRL | 250 | 0.044 | 0.028 | 0.529 |
| OUTBOUND | priority | Low | 408 | 0.034 | 0.076 | 0.412 |
| OUTBOUND | backorder | no backorder | 2485 | 0.010 | 0.080 | 0.121 |

Association, not proof of causation; confirm through process walk-throughs.
