"""
Ganji Protocol - Pipeline Entrypoint
Runs daily data collection, feature engineering, detection, signal output, and delivery.
"""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.data_layer import run_data_collection
from engine.detection import compute_cips
from engine.features import compute_all_features
from engine.output import build_signal_output, save_signal
from engine.deliver import deliver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run_pipeline(historical: bool = False) -> dict:
    log.info("%s", "=" * 60)
    log.info("Ganji Protocol Pipeline Starting")
    log.info(f"Mode: {'HISTORICAL BACKFILL' if historical else 'DAILY UPDATE'}")
    log.info("%s", "=" * 60)

    summary = {
        "pipeline_date": date.today().isoformat(),
        "mode": "historical" if historical else "daily",
        "data_collection": {},
        "signal_id": None,
        "confidence": None,
        "delivery": {},
        "errors": [],
    }

    data_summary = run_data_collection(historical=historical)
    summary["data_collection"] = data_summary

    features = compute_all_features()
    if not features:
        msg = "No features computed. Ensure rate data exists and data collection completed successfully."
        log.error(msg)
        summary["errors"].append("no_features")
        return summary

    detection_result = compute_cips(features)
    signal = build_signal_output(
        features=features,
        result=detection_result,
        signal_date=date.today(),
        sequence=1,
        data_quality={"data_collection": data_summary},
    )

    save_signal(signal)
    summary["signal_id"] = signal["signal_id"]
    summary["confidence"] = signal["detection"]["confidence"]

    delivery_results = deliver(signal)
    summary["delivery"] = delivery_results

    if not delivery_results.get("file"):
        summary["errors"].append("file_delivery_failed")
    if not delivery_results.get("console"):
        summary["errors"].append("console_delivery_failed")

    log.info("Pipeline complete | signal=%s | confidence=%s", summary["signal_id"], summary["confidence"])
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ganji Protocol pipeline entry point")
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Run historical backfill from Yahoo Finance before daily update.",
    )
    args = parser.parse_args()

    result = run_pipeline(historical=args.historical)
    print(json.dumps(result, indent=2))
