# Qwen3.5 tau2-bench Evaluation Results

Evaluation of Qwen3.5-397B-A17B, Qwen3.5-122B-A10B, Qwen3.5-27B, and Qwen3.5-35B-A3B on the tau2-bench test split across all 3 domains (airline, retail, telecom). All results use Pass^k from the tau2 paper: C(c,k)/C(n,k).

## Setup

- **Server**: SGLang with `--tp 8 --trust-remote-code --tool-call-parser qwen25 --reasoning-parser qwen3`
- **Radix cache**: Enabled (no speculative decoding)
- **Task split**: test (20 airline / 40 retail / 40 telecom tasks)
- **Trials**: 2 per task
- **Max concurrency**: 16

### Sampling Configs

| Config | Temperature | TopP | TopK | MinP |
|--------|-------------|------|------|------|
| default | server default | — | — | — |
| temp0.6 | 0.6 | 0.95 | 20 | 0 |

## Results (Pass^1)

### Self-play (Qwen3.5 as both agent and user simulator)

| Domain | 27B (default) | 27B (temp0.6) | 397B (default) | 397B (temp0.6) |
|--------|---------------|---------------|----------------|----------------|
| Airline | 62.5% | 65.0% | 65.0% | 67.5% |
| Retail | 51.2% | 56.2% | 60.0% | 65.0% |
| Telecom | 91.0% | 97.5% | 95.0% | 96.3% |

### With gpt-4.1 user simulator (temp0.6)

| Domain | 35B-A3B + gpt-4.1 | 122B-A10B + gpt-4.1 | 27B + gpt-4.1 | 397B + gpt-4.1 | Sonnet 4.5 (leaderboard) |
|--------|---------------------|----------------------|---------------|----------------|--------------------------|
| Airline | 42.5% | **72.5%** | **72.5%** | **72.5%** | 70% |
| Retail | 76.2% | 75.0% | **85.0%** | **85.0%** | 86% |
| Telecom | 95.0% | **100.0%** | **100.0%** | **100.0%** | 98% |

### 122B-A10B with different user simulators (temp0.6)

| Domain | gpt-4.1 | Sonnet 4.6 | Opus 4.6 | Sonnet 4.5 (leaderboard) |
|--------|---------|------------|----------|--------------------------|
| Airline | 72.5% | 70.0% | **77.5%** | 70% |
| Retail | 75.0% | **88.8%** | 83.8% | 86% |
| Telecom | 100.0% | 100.0% | 100.0% | 98% |

### Leaderboard reference (Pass^1, base split, gpt-4.1 user sim)

| Domain | Sonnet 4 | Sonnet 4.5 |
|--------|----------|------------|
| Airline | 60% | 70% |
| Retail | 81% | 86% |
| Telecom | N/A | 98% |

Note: Leaderboard entries use the **base** split (all tasks), not the test split. Our results use the test split only.

## Results (Pass^2)

### Self-play

| Domain | 27B (default) | 27B (temp0.6) | 397B (default) | 397B (temp0.6) |
|--------|---------------|---------------|----------------|----------------|
| Airline | 55.0% | 60.0% | 60.0% | 55.0% |
| Retail | 37.5% | 40.0% | 50.0% | 55.0% |
| Telecom | 48.7% | 92.5% | 90.0% | 92.5% |

## Results (Pass^2) — gpt-4.1 user simulator

| Domain | 35B-A3B + gpt-4.1 | 122B-A10B + gpt-4.1 | 27B + gpt-4.1 | 397B + gpt-4.1 | Sonnet 4.5 |
|--------|---------------------|----------------------|---------------|----------------|------------|
| Airline | 35.0% | 65.0% | 65.0% | 70.0% | — |
| Retail | 60.0% | 60.0% | 75.0% | 72.5% | — |
| Telecom | 92.5% | 100.0% | 100.0% | 100.0% | — |

## Key Findings

1. **Qwen3.5-27B and 397B beat Sonnet 4.5** on airline (72.5% vs 70%) and telecom (100% vs 98%) with gpt-4.1 user sim, and nearly match on retail (85% vs 86%).
2. **27B matches 397B exactly** with gpt-4.1 user sim (72.5%/85.0%/100.0% for both), showing agent capability is not the differentiator at this scale — the user simulator quality is.
3. **122B-A10B (10B active) matches on airline/telecom but dips on retail** (75% vs 85%) with gpt-4.1. The 27B dense outperforms the 122B MoE on retail despite fewer active params.
4. **User sim choice matters as much as model size.** 122B-A10B retail swings from 75% (gpt-4.1) to 88.8% (Sonnet 4.6) — a 13.8pp gap just from user sim. Opus 4.6 gives the best airline (77.5%), Sonnet 4.6 the best retail (88.8%).
5. **35B-A3B (3B active) shows a clear drop**, particularly on airline (42.5% vs 72.5%). With only 3B active parameters it struggles on complex multi-step tasks, though telecom (95%) remains strong.
6. **Self-play user sim is the bottleneck, not agent capability.** Retail jumped from 56-65% to 85% simply by switching from Qwen3.5 self-play to gpt-4.1 user sim. Root cause: Qwen3.5 as user simulator sends `###STOP###` before the agent completes final mutating tool calls (`exchange_delivered_order_items`, `return_delivered_order_items`, `modify_pending_order_items`).
7. **Temperature 0.6 consistently helps** across both model sizes and all domains.
8. **Empty responses**: The model occasionally returns empty responses (no content or tool calls). Patched orchestrator to retry up to 3 times. Some runs have fewer than expected sims due to this (e.g., 27B default telecom: 63/80).

## Run Scripts

| Script | Description |
|--------|-------------|
| `scripts/run_qwen397b_test.sh` | 397B self-play sweep (temp0.6, all 3 domains) |
| `scripts/run_qwen397b_gpt41user.sh` | 397B agent + gpt-4.1 user sim (temp0.6, all 3 domains) |
| `scripts/run_qwen27b_gpt41user.sh` | 27B agent + gpt-4.1 user sim (temp0.6, all 3 domains) |
| `scripts/run_qwen35b_test.sh` | 35B-A3B self-play sweep (temp0.6, all 3 domains) |
| `scripts/run_qwen35b_gpt41user.sh` | 35B-A3B agent + gpt-4.1 user sim (temp0.6, all 3 domains) |
| `scripts/run_qwen122b_gpt41user.sh` | 122B-A10B agent + gpt-4.1 user sim (temp0.6, all 3 domains) |
| `scripts/run_qwen122b_sonnet46user.sh` | 122B-A10B agent + Sonnet 4.6 user sim (temp0.6, all 3 domains) |
| `scripts/run_qwen122b_opus46user.sh` | 122B-A10B agent + Opus 4.6 user sim (temp0.6, all 3 domains) |

## Trajectory Files

All saved in `data/simulations/`:

| File | Model | Agent Temp | User Sim | Sims |
|------|-------|-----------|----------|------|
| `qwen3.5-27B-temp0_airline_test.json` | 27B | default | self | 40 |
| `qwen3.5-27B-temp0_retail_test.json` | 27B | default | self | 80 |
| `qwen3.5-27B-temp0_telecom_test.json` | 27B | default | self | 63 |
| `qwen3.5-27B-temp06_airline_test.json` | 27B | 0.6 | self | 40 |
| `qwen3.5-27B-temp06_retail_test.json` | 27B | 0.6 | self | 80 |
| `qwen3.5-27B-temp06_telecom_test.json` | 27B | 0.6 | self | 79 |
| `qwen3.5-397B-temp0_airline_test.json` | 397B | default | self | 39 |
| `qwen3.5-397B-temp0_retail_test.json` | 397B | default | self | 79 |
| `qwen3.5-397B-temp0_telecom_test.json` | 397B | default | self | 80 |
| `qwen3.5-397B-temp06_airline_test.json` | 397B | 0.6 | self | 39 |
| `qwen3.5-397B-temp06_retail_test.json` | 397B | 0.6 | self | 80 |
| `qwen3.5-397B-temp06_telecom_test.json` | 397B | 0.6 | self | 80 |
| `qwen3.5-397B-temp06-gpt41user_airline_test.json` | 397B | 0.6 | gpt-4.1 | 40 |
| `qwen3.5-397B-temp06-gpt41user_retail_test.json` | 397B | 0.6 | gpt-4.1 | 80 |
| `qwen3.5-397B-temp06-gpt41user_telecom_test.json` | 397B | 0.6 | gpt-4.1 | 80 |
| `qwen3.5-27B-temp06-gpt41user_airline_test.json` | 27B | 0.6 | gpt-4.1 | 40 |
| `qwen3.5-27B-temp06-gpt41user_retail_test.json` | 27B | 0.6 | gpt-4.1 | 80 |
| `qwen3.5-27B-temp06-gpt41user_telecom_test.json` | 27B | 0.6 | gpt-4.1 | 80 |
| `qwen3.5-35B-temp06-gpt41user_airline_test.json` | 35B-A3B | 0.6 | gpt-4.1 | 40 |
| `qwen3.5-35B-temp06-gpt41user_retail_test.json` | 35B-A3B | 0.6 | gpt-4.1 | 80 |
| `qwen3.5-35B-temp06-gpt41user_telecom_test.json` | 35B-A3B | 0.6 | gpt-4.1 | 80 |
| `qwen3.5-122B-temp06-gpt41user_airline_test.json` | 122B-A10B | 0.6 | gpt-4.1 | 40 |
| `qwen3.5-122B-temp06-gpt41user_retail_test.json` | 122B-A10B | 0.6 | gpt-4.1 | 80 |
| `qwen3.5-122B-temp06-gpt41user_telecom_test.json` | 122B-A10B | 0.6 | gpt-4.1 | 80 |
| `qwen3.5-122B-temp06-sonnet46user_airline_test.json` | 122B-A10B | 0.6 | Sonnet 4.6 | 40 |
| `qwen3.5-122B-temp06-sonnet46user_retail_test.json` | 122B-A10B | 0.6 | Sonnet 4.6 | 80 |
| `qwen3.5-122B-temp06-sonnet46user_telecom_test.json` | 122B-A10B | 0.6 | Sonnet 4.6 | 80 |
| `qwen3.5-122B-temp06-opus46user_airline_test.json` | 122B-A10B | 0.6 | Opus 4.6 | 40 |
| `qwen3.5-122B-temp06-opus46user_retail_test.json` | 122B-A10B | 0.6 | Opus 4.6 | 80 |
| `qwen3.5-122B-temp06-opus46user_telecom_test.json` | 122B-A10B | 0.6 | Opus 4.6 | 80 |
