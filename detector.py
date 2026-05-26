"""
Ganji Protocol - Detector (Engine Kernel)
Single entry point for the full pipeline.
Runs all five layers in sequence.

Usage:
  Daily update (cron):   python detector.py
  Historical backfill:   python detector.py --historical
  Tests:                 python -m pytest tests/

Reference: SYSTEM.md Section 4.7
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def setup_logging():
    log_path = _ROOT / "data" / "pipeline.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path),
        ],
    )


def run(historical: bool = False) -> dict:
    """
    Runs the full Ganji Protocol detection pipeline.

    Layer 1: Data ingestion
    Layer 2: Feature engineering
    Layer 3: Detection engine
    Layer 4: Signal output
    Layer 5: Signal delivery

    Returns the pipeline result dict.
    """
    log = logging.getLogger(__name__)

    log.info("=" * 60)
    log.info("GANJI PROTOCOL PIPELINE STARTING")
    log.info(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    log.info("=" * 60)

    pipeline_result = {
        "status":    "OK",
        "signal":    None,
        "errors":    [],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # Layer 1: Data ingestion
    try:
        log.info("--- Layer 1: Data Ingestion ---")
        from engine.data_layer import run_data_collection
        data_summary = run_data_collection(historical=historical)
        if data_summary.get("errors"):
            pipeline_result["errors"].extend(data_summary["errors"])
            log.warning(f"Data layer errors: {data_summary['errors']}")
    except Exception as e:
        log.error(f"Layer 1 failed: {e}")
        pipeline_result["status"] = "DEGRADED"
        pipeline_result["errors"].append(f"data_layer: {e}")

    # Layer 2: Feature engineering
    try:
        log.info("--- Layer 2: Feature Engineering ---")
        from engine.features import compute_all_features
        features = compute_all_features()
        if not features:
            raise RuntimeError("No features computed. Check data layer.")
    except Exception as e:
        log.error(f"Layer 2 failed: {e}")
        pipeline_result["status"] = "ERROR"
        pipeline_result["errors"].append(f"features: {e}")
        return pipeline_result

    # Layer 3: Detection engine
    try:
        log.info("--- Layer 3: Detection Engine ---")
        from engine.detection import compute_cips
        result = compute_cips(features)
    except Exception as e:
        log.error(f"Layer 3 failed: {e}")
        pipeline_result["status"] = "ERROR"
        pipeline_result["errors"].append(f"detection: {e}")
        return pipeline_result

    # Layer 4: Signal output
    try:
        log.info("--- Layer 4: Signal Output ---")
        from engine.output import build_signal_output, save_signal
        signal = build_signal_output(features, result)
        save_signal(signal)
        pipeline_result["signal"] = signal
    except Exception as e:
        log.error(f"Layer 4 failed: {e}")
        pipeline_result["status"] = "ERROR"
        pipeline_result["errors"].append(f"output: {e}")
        return pipeline_result

    # Layer 5: Signal delivery
    try:
        log.info("--- Layer 5: Signal Delivery ---")
        from engine.deliver import deliver
        delivery_results = deliver(signal)
        pipeline_result["delivery"] = delivery_results
    except Exception as e:
        log.error(f"Layer 5 failed: {e}")
        pipeline_result["errors"].append(f"deliver: {e}")

    log.info("=" * 60)
    log.info(f"PIPELINE COMPLETE | status={pipeline_result['status']}")
    log.info(f"Signal: {signal['signal_id']} | {signal['detection']['confidence']}")
    if pipeline_result["errors"]:
        log.warning(f"Errors: {pipeline_result['errors']}")
    log.info("=" * 60)

    return pipeline_result


if __name__ == "__main__":
    setup_logging()

    parser = argparse.ArgumentParser(description="Ganji Protocol Detection Engine")
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Run historical backfill from Yahoo Finance (run once on first setup)",
    )
    args = parser.parse_args()

    result = run(historical=args.historical)
    print(json.dumps(
        {k: v for k, v in result.items() if k != "signal"},
        indent=2
    ))
