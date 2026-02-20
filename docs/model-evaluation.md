# Vision Model Evaluation for Photo Composition Scoring

Research findings on vision LLM performance for structured photo composition analysis, with recommendations for alternative models on macOS Apple Silicon (MLX backend).

## Current Model Issues

**Current setup:** Qwen3-VL-30B via LM Studio (MLX backend on macOS Apple Silicon)

### Score Compression

85 photos scored, only 3 distinct values used (4.0, 5.0, 6.0) out of a 1-7 scale:

| Score | Count | Percentage |
|-------|-------|------------|
| 6.0   | 43    | 50.6%      |
| 5.0   | 41    | 48.2%      |
| 4.0   | 1     | 1.2%       |

The prompt explicitly instructs "be critical, most photos should score 3-5" but the model ignores this guidance entirely.

### Systematic Biases

- **Famous landmark bias:** Anything containing the Golden Gate Bridge receives 6.0 regardless of actual composition quality (framing, exposure, orientation).
- **Rotation/orientation not penalized:** Sideways or incorrectly oriented photos still receive high scores.
- **Food snapshot overscoring:** Casual meal photos rated the same as intentional photographic compositions.
- **Hallucinated composition elements:** Model claims "rule of thirds" on rotated food snapshots where no such compositional technique is present.

### Root Cause

Qwen3-VL-30B is a Mixture-of-Experts (MoE) model with only ~3B active parameters per token despite the "30B" label. This small effective model size likely explains the poor rubric adherence, score compression, and inability to follow nuanced scoring instructions.

## Golden Evaluation Dataset

**File:** `golden_eval.json`

14 photos from the SF February 2026 photo set, independently reviewed and scored by Claude Opus 4.6.

### Summary Statistics

| Metric | Value |
|--------|-------|
| Human score range | 2-6 |
| Model score range | 4-6 |
| Mean human score | 3.93 |
| Mean model score | 5.50 |
| Mean absolute delta | 1.43 points |
| Photos overscored | 12 of 14 |
| Photos underscored | 0 of 14 |
| Photos matched | 2 of 14 |

### Key Finding

The model has a strong and consistent upward bias. Worst disagreements occur on food photos (delta of -3 points), confirming the food snapshot overscoring pattern identified above.

## Recommended Alternative Models (MLX-native for macOS)

### Tier 1: Primary Recommendations

#### 1. Gemma 3 27B QAT 4-bit (recommended first try)

- **HuggingFace:** `mlx-community/gemma-3-27b-it-qat-4bit`
- **RAM:** ~14GB at 4-bit
- Google's Quantization Aware Training (QAT) preserves quality better than post-training quantization.
- Strong instruction following and structured output adherence.
- Vision-native architecture.
- Different training lineage than Qwen, which may break the generosity/compression pattern.
- Runs in LM Studio (unified MLX engine) or via mlx-vlm.

#### 2. Qwen2.5-VL-32B 4-bit

- **HuggingFace:** `mlx-community/Qwen2.5-VL-32B-Instruct-4bit`
- **RAM:** ~17GB at 4-bit
- Newer architecture than Qwen3-VL with better instruction following.
- Strong at structured tasks and document parsing.

#### 3. Qwen2.5-VL-72B 4-bit (if RAM allows)

- **HuggingFace:** `mlx-community/Qwen2.5-VL-72B-Instruct-4bit`
- **RAM:** ~38GB at 4-bit, needs 64GB+ Mac
- Larger model size correlates with better rubric adherence and more nuanced scoring.
- Most downloaded 72B variant on HuggingFace.

### Tier 2: Worth Testing

| Model | Notes |
|-------|-------|
| Qwen2.5-VL-7B 8-bit | Speed baseline (~7GB, very fast, may still compress scores) |
| Pixtral 12B | Good instruction following benchmarks |
| MiniCPM-o 2.6 | Highest throughput in Clarifai benchmarks (1075 tok/s) |

## Serving Options

| Method | Command | Pros | Cons |
|--------|---------|------|------|
| LM Studio (current) | GUI + API at localhost:1234 | Easy model switching, already set up | Vision support varies by model |
| mlx-vlm | `pip install mlx-vlm` | Direct Python API, full control | Need to wire into analyze.py |
| vllm-mlx | OpenAI-compatible server | Drop-in replacement, continuous batching | Newer project, less mature |

## How to Test a New Model

1. Download the model in LM Studio (or via `huggingface-cli download`).
2. Load it in LM Studio.
3. Run eval mode: `uv run analyze.py --eval golden_eval.json --model <model-name>`
4. Compare correlation and score distribution against the golden dataset.

## Key Benchmarks (from Clarifai)

At 32 concurrent requests on NVIDIA L40S:

| Model | Throughput | TTFT | Per-token latency |
|-------|-----------|------|-------------------|
| MiniCPM-o 2.6 | 1075 tok/s | 0.120s | 0.024s |
| Qwen2.5-VL-7B | 1017 tok/s | 0.121s | 0.025s |
| Gemma-3-4B | 943 tok/s | 0.236s | 0.027s |

These benchmarks are GPU-based (NVIDIA L40S). MLX performance on Apple Silicon will differ, but relative rankings between models are informative for comparison purposes.

## Sources

- [MLX-VLM](https://github.com/Blaizzy/mlx-vlm)
- [mlx-community Qwen2.5-VL collection](https://huggingface.co/collections/mlx-community/qwen25-vl)
- [mlx-community Gemma 3 QAT collection](https://huggingface.co/collections/mlx-community/gemma-3-qat-68002674cd5afc6f9022a0ae)
- [LM Studio Unified MLX Engine](https://lmstudio.ai/blog/unified-mlx-engine)
- [vllm-mlx](https://github.com/waybarrios/vllm-mlx)
- [Clarifai VLM Benchmarks](https://www.clarifai.com/blog/benchmarking-best-open-source-vision-language-models)
- [Gemma 3 QAT Blog](https://developers.googleblog.com/en/gemma-3-quantized-aware-trained-state-of-the-art-ai-to-consumer-gpus/)
