from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import ReadinessAgent
from .planner import OpenAIPlanner
from .store import RunStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a repository without mutating it.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--model", action="store_true", help="Use the optional OpenAI planner")
    parser.add_argument("--data-dir", type=Path, default=Path(".repo-readiness/runs"))
    args = parser.parse_args()
    planner = OpenAIPlanner() if args.model else None
    run = ReadinessAgent(RunStore(args.data_dir), planner).audit(args.path.resolve())
    print(json.dumps(run.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()

