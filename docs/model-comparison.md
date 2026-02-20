# Model Comparison: LM Studio vs OpenAI (GPT-4o, GPT-5)

Ran the same 85 SF street photos through three vision models to compare
composition scoring, category assignment, and practical trade-offs.

**Date:** 2026-02-20
**Dataset:** 85 HEIC photos from SF Feb 2026 (architecture, street, urban, landscape, food)
**Prompt:** Identical across all models (composition analysis with issues/suggestions)

## Models Tested

| Model | Provider | Type | Default in CLI |
|---|---|---|---|
| qwen/qwen3-vl-30b | LM Studio (local) | Standard VLM | Yes |
| gpt-4o | OpenAI API | Standard VLM | No (deprecated) |
| gpt-5 | OpenAI API | Reasoning VLM | Yes (new default) |

## Score Comparison

| Metric | LM Studio | GPT-4o | GPT-5 |
|---|---|---|---|
| Mean score | 5.13 | 4.64 | 4.58 |
| Score range | 3–6 | 4–5 | 3–6 |
| Score 6 count | 20 | 0 | 1 |
| Score 5 count | 57 | 54 | 48 |
| Score 4 count | 7 | 31 | 35 |
| Score 3 count | 1 | 0 | 1 |

GPT-4o compresses everything into 4–5. GPT-5 is similar but slightly more
willing to use the extremes (one 6, one 3). LM Studio uses the full range
more naturally.

## Agreement With LM Studio

| Metric | GPT-4o | GPT-5 |
|---|---|---|
| Bias (LM − model) | +0.49 | +0.55 |
| MAE | 0.56 | 0.58 |
| Exact match | 37/85 (44%) | 38/85 (45%) |
| Within ±1 | 85/85 (100%) | 83/85 (98%) |
| Model higher by 2+ | 0 | 0 |
| LM higher by 2+ | 0 | 2 |
| Category mismatches | 37/85 (44%) | 37/85 (44%) |

All three models broadly agree — scores never differ by more than 2, and
98–100% are within ±1. The OpenAI models are systematically ~0.5 points more
conservative.

## Category Assignment

Category agreement is noisy across all models (~44% mismatch rate). Common
disagreements:

- LM Studio `street` ↔ GPT `urban` (most frequent)
- LM Studio `landscape` ↔ GPT `architecture` or `travel`
- LM Studio `night`/`concert`/`abstract` ↔ GPT `urban` (GPT collapses niche categories)

GPT-4o was worst here — it labeled 48/85 photos as `urban`. GPT-5 is more
balanced (25 architecture, 23 urban, 18 street, 10 travel).

## Practical Comparison

| Factor | LM Studio | GPT-4o | GPT-5 |
|---|---|---|---|
| Time (85 photos) | ~12 min | ~12 min | ~93 min |
| Per-image speed | ~8s | ~8s | ~66s |
| Cost | $0 (local GPU) | ~$2.50 | ~$2.50 |
| JSON errors | 1/85 | 0/85 | 0/85 |
| Score range used | Broad (3–6) | Narrow (4–5) | Moderate (3–6) |
| Category variety | 9 categories | 6 categories | 7 categories |

### GPT-5 API Quirks

GPT-5 is a reasoning model (like o-series) with these API differences:
- Uses `max_completion_tokens` instead of `max_tokens`
- Does not support custom `temperature` (only default 1)
- Needs higher token budget (8192+) because reasoning tokens consume the allowance
- ~2,400 reasoning tokens per image on top of ~270 visible output tokens

## Recommendation

**LM Studio (qwen/qwen3-vl-30b) is the best default** for this use case:
- Free (runs locally)
- Fast (8s/image)
- Uses the full 1–7 score range more naturally
- More granular category assignment
- Occasional JSON errors (1/85) are handled by retry logic

Use OpenAI providers for:
- Cross-validation of scores on important batches
- Environments without a local GPU
- When JSON reliability matters (0% error rate)

**Anthropic** was not tested — the API key hit its monthly spend limit. To be
tested after 2026-03-01.

## Per-Photo Scores

```
Photo                  LM Studio  GPT-4o  GPT-5
IMG_8825.HEIC                  5       5      5
IMG_8835.HEIC                  5       5      5
IMG_8837.HEIC                  5       5      5
IMG_8846.HEIC                  5       5      5
IMG_8849.HEIC                  4       4      4
IMG_8850.HEIC                  3       4      3
IMG_8852.HEIC                  5       5      5
IMG_8856.HEIC                  5       5      5
IMG_8859.HEIC                  5       5      5
IMG_8860.HEIC                  6       5      5
IMG_8862.HEIC                  4       4      4
IMG_8870.HEIC                  5       5      5
IMG_8878.HEIC                  5       5      5
IMG_8881.HEIC                  5       5      5
IMG_8890.HEIC                  5       4      4
IMG_8893.HEIC                  5       4      5
IMG_8897.HEIC                  4       5      5
IMG_8902.HEIC                  5       4      5
IMG_8905.HEIC                  6       5      5
IMG_8909.HEIC                  5       5      5
IMG_8913.HEIC                  5       5      5
IMG_8916.HEIC                  6       5      5
IMG_8926.HEIC                  5       5      5
IMG_8927.HEIC                  5       5      5
IMG_8928.HEIC                  6       5      5
IMG_8931.HEIC                  4       4      4
IMG_8933.HEIC                  5       4      4
IMG_8935.HEIC                  5       5      4
IMG_8953.HEIC                  5       5      4
IMG_8963.HEIC                  5       4      4
IMG_8973.HEIC                  5       4      4
IMG_8974.HEIC                  5       4      4
IMG_8979.HEIC                  5       4      4
IMG_8981.HEIC                  5       5      4
IMG_8991.HEIC                  4       4      4
IMG_9002.HEIC                  5       4      5
IMG_9008.HEIC                  5       4      4
IMG_9009.HEIC                  4       5      4
IMG_9018.HEIC                  4       4      4
IMG_9019.HEIC                  5       4      4
IMG_9026.HEIC                  5       5      5
IMG_9039.HEIC                  6       5      5
IMG_9043.HEIC                  5       5      5
IMG_9046.HEIC                  5       5      5
IMG_9059.HEIC                  6       5      6
IMG_9061.HEIC                  5       4      4
IMG_9062.HEIC                  5       4      4
IMG_9084.HEIC                  5       5      4
IMG_9085.HEIC                  6       5      5
IMG_9114.HEIC                  5       5      5
IMG_9124.HEIC                  5       5      5
IMG_9145.HEIC                  5       4      4
IMG_9147.HEIC                  5       5      5
IMG_9155.HEIC                  5       5      5
IMG_9159.HEIC                  5       4      5
IMG_9167.HEIC                  5       4      4
IMG_9175.HEIC                  5       5      5
IMG_9179.HEIC                  5       4      4
IMG_9184.HEIC                  6       5      5
IMG_9187.HEIC                  6       5      5
IMG_9192.HEIC                  6       5      5
IMG_9213.HEIC                  5       4      4
IMG_9222.HEIC                  5       4      4
IMG_9229.HEIC                  5       4      4
IMG_9236.HEIC                  6       5      5
IMG_9242.HEIC                  5       4      4
IMG_9245.HEIC                  6       5      5
IMG_9259.HEIC                  5       5      5
IMG_9263.HEIC                  5       5      4
IMG_9270.HEIC                  6       5      5
IMG_9284.HEIC                  6       5      5
IMG_9285.HEIC                  5       4      4
IMG_9286.HEIC                  5       4      4
IMG_9292.HEIC                  6       5      5
IMG_9304.HEIC                  5       5      4
IMG_9306.HEIC                  5       4      4
IMG_9309.HEIC                  6       5      4
IMG_9334.HEIC                  6       5      5
IMG_9343.HEIC                  5       5      5
IMG_9353.HEIC                  6       5      4
IMG_9355.HEIC                  5       4      4
IMG_9365.HEIC                  6       5      5
IMG_9371.HEIC                  5       5      5
IMG_9402.HEIC                  6       5      5
IMG_9405.HEIC                  5       5      5
```
