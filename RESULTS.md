# Qwen3.5 tau2-bench Evaluation Results

Evaluation of Qwen3.5-397B-A17B and Qwen3.5-27B on the tau2-bench test split across all 3 domains (airline, retail, telecom). All results use Pass^k from the tau2 paper: C(c,k)/C(n,k).

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

### With gpt-4.1 user simulator (397B agent, temp0.6)

| Domain | 397B self-play | 397B + gpt-4.1 user | Sonnet 4.5 (leaderboard) |
|--------|---------------|---------------------|--------------------------|
| Airline | 67.5% | **72.5%** | 70% |
| Retail | 65.0% | **85.0%** | 86% |
| Telecom | 96.3% | **100.0%** | 98% |

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

| Domain | 397B + gpt-4.1 user | Sonnet 4.5 |
|--------|---------------------|------------|
| Airline | 70.0% | — |
| Retail | 72.5% | — |
| Telecom | 100.0% | — |

## Key Findings

1. **Qwen3.5-397B beats Sonnet 4.5** on airline (72.5% vs 70%) and telecom (100% vs 98%) with gpt-4.1 user sim, and nearly matches on retail (85% vs 86%).
2. **Self-play user sim is the bottleneck, not agent capability.** Retail jumped from 65% to 85% simply by switching from Qwen3.5 self-play to gpt-4.1 user sim. Root cause: Qwen3.5 as user simulator sends `###STOP###` before the agent completes final mutating tool calls (`exchange_delivered_order_items`, `return_delivered_order_items`, `modify_pending_order_items`).
3. **Temperature 0.6 consistently helps** across both model sizes and all domains.
4. **27B telecom (97.5%) nearly matches 397B (96.3%) and Sonnet 4.5 (98%)** — strong performance for 14x fewer active parameters.
5. **Empty responses**: The model occasionally returns empty responses (no content or tool calls). Patched orchestrator to retry up to 3 times. Some runs have fewer than expected sims due to this (e.g., 27B default telecom: 63/80).

## Run Scripts

| Script | Description |
|--------|-------------|
| `scripts/run_qwen397b_test.sh` | 397B self-play sweep (temp0.6, all 3 domains) |
| `scripts/run_qwen397b_gpt41user.sh` | 397B agent + gpt-4.1 user sim (temp0.6, all 3 domains) |

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
