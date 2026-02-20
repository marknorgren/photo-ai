"""Eval command: run model against golden evaluation dataset."""

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

from tqdm import tqdm

from .scanner import extract_gps, resize_and_encode, analyze_image, validate_analysis

log = logging.getLogger(__name__)


def run_eval(eval_path: Path, *, analyze_fn: Callable[[str, str], dict], model: str, max_dimension: int, max_retries: int = 3) -> None:
    """Run model against golden evaluation dataset and report accuracy."""
    with open(eval_path) as f:
        golden = json.load(f)

    photos = golden["photos"]
    print(f"Eval: {len(photos)} photos from {eval_path.name}")
    print(f"Model: {model}")
    print()

    results = []
    for entry in tqdm(photos, desc="Evaluating", unit="img"):
        image_path = Path(entry["path"])
        if not image_path.exists():
            log.warning("Missing: %s — skipping", image_path)
            results.append({"filename": entry["filename"], "human": entry["human_score"], "model": None, "error": "file not found"})
            continue

        gps = extract_gps(image_path)
        model_score = None
        error_msg = None

        for attempt in range(1, max_retries + 1):
            try:
                b64, _, _ = resize_and_encode(image_path, max_dimension)
                result = analyze_image(analyze_fn, b64, gps=gps)
                analysis = validate_analysis(result)
                model_score = analysis["composition_score"]
                break
            except Exception as e:
                log.warning("Error on %s (attempt %d/%d): %s", entry["filename"], attempt, max_retries, e)
                if attempt == max_retries:
                    error_msg = str(e)
                else:
                    time.sleep(2 ** attempt)

        results.append({
            "filename": entry["filename"],
            "human": entry["human_score"],
            "model": model_score,
            "error": error_msg,
        })

    # Report
    print()
    print(f"{'Photo':<20} {'Human':>5} {'Model':>5} {'Delta':>5}  Notes")
    print("-" * 70)

    scored = []
    for r in results:
        if r["model"] is None:
            print(f"{r['filename']:<20} {r['human']:>5} {'ERR':>5} {'':>5}  {r['error']}")
            continue
        delta = r["model"] - r["human"]
        scored.append(r)
        flag = ""
        if abs(delta) >= 2:
            flag = " <<<" if delta > 0 else " >>>"
        print(f"{r['filename']:<20} {r['human']:>5} {r['model']:>5.0f} {delta:>+5.0f}{flag}")

    if not scored:
        print("\nNo photos scored — cannot compute stats.")
        return

    # Stats
    human_scores = [r["human"] for r in scored]
    model_scores = [r["model"] for r in scored]
    deltas = [r["model"] - r["human"] for r in scored]
    abs_deltas = [abs(d) for d in deltas]

    n = len(scored)
    mean_human = sum(human_scores) / n
    mean_model = sum(model_scores) / n
    mae = sum(abs_deltas) / n
    bias = sum(deltas) / n

    # Pearson correlation (no numpy dependency)
    if n > 1:
        sum_xy = sum(h * m for h, m in zip(human_scores, model_scores))
        sum_x = sum(human_scores)
        sum_y = sum(model_scores)
        sum_x2 = sum(h ** 2 for h in human_scores)
        sum_y2 = sum(m ** 2 for m in model_scores)
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
        correlation = numerator / denominator if denominator > 0 else 0.0
    else:
        correlation = 0.0

    # Score distribution
    model_dist: dict[int, int] = {}
    for s in model_scores:
        k = int(s)
        model_dist[k] = model_dist.get(k, 0) + 1

    overscored = sum(1 for d in deltas if d > 0)
    matched = sum(1 for d in deltas if d == 0)
    underscored = sum(1 for d in deltas if d < 0)

    print()
    print("Summary")
    print("=" * 40)
    print(f"  Photos scored:     {n}/{len(results)}")
    print(f"  Mean human score:  {mean_human:.2f}")
    print(f"  Mean model score:  {mean_model:.2f}")
    print(f"  Mean bias:         {bias:+.2f} ({'model overscores' if bias > 0 else 'model underscores'})")
    print(f"  MAE:               {mae:.2f}")
    print(f"  Pearson r:         {correlation:.3f}")
    print(f"  Overscored:        {overscored}")
    print(f"  Matched:           {matched}")
    print(f"  Underscored:       {underscored}")
    print()
    print("Model score distribution:")
    for score in sorted(model_dist):
        bar = "#" * model_dist[score]
        print(f"  {score}: {bar} ({model_dist[score]})")

    # Write results JSON
    results_path = eval_path.with_name(f"eval_results_{model.replace('/', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.json")
    eval_output = {
        "model": model,
        "eval_file": str(eval_path),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stats": {
            "n": n,
            "mean_human": round(mean_human, 2),
            "mean_model": round(mean_model, 2),
            "bias": round(bias, 2),
            "mae": round(mae, 2),
            "pearson_r": round(correlation, 3),
            "overscored": overscored,
            "matched": matched,
            "underscored": underscored,
        },
        "results": results,
    }
    with open(results_path, "w") as f:
        json.dump(eval_output, f, indent=2)
    print(f"\nResults saved: {results_path}")
