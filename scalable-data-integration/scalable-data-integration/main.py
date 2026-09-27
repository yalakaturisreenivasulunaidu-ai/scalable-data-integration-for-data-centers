#!/usr/bin/env python3
"""
Entry point for the Scalable Data Integration base project.

Usage:
    python main.py --config config.yaml
"""

import argparse
import json
import sys

from data_integration.config import load_config
from data_integration.pipeline import Pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the scalable data-integration pipeline for a data center."
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to the pipeline YAML config."
    )
    args = parser.parse_args()

    config = load_config(args.config)
    pipeline = Pipeline(config)
    stats = pipeline.run()

    print(json.dumps(stats, indent=2))
    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
