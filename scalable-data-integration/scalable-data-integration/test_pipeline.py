"""
Smoke test: runs the pipeline end-to-end using mock connectors/sinks
(no external infra needed) and asserts records flow all the way through.
"""

import json
import os
import shutil

from data_integration.config import load_config
from data_integration.pipeline import Pipeline


def test_pipeline_runs_end_to_end(tmp_path=None):
    output_dir = "output_test"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    config = load_config("config.yaml")
    config.sinks[0].options["path"] = os.path.join(output_dir, "integrated_data.jsonl")

    pipeline = Pipeline(config)
    stats = pipeline.run()

    assert stats["extracted"] > 0, "Expected mock connectors to yield records"
    assert stats["loaded"] > 0, "Expected records to reach the sink"
    assert stats["error_count"] == 0, f"Unexpected errors: {stats['errors']}"

    out_file = config.sinks[0].options["path"]
    assert os.path.exists(out_file)
    with open(out_file) as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == stats["loaded"]
    assert all("_ingested_at" in r and "_tag" in r for r in lines)

    shutil.rmtree(output_dir)
    print("OK -", stats)


if __name__ == "__main__":
    test_pipeline_runs_end_to_end()
