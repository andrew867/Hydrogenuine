"""CLI entry point: python -m hg_runtime.demos.governed_research_soak"""

from __future__ import annotations

import argparse
import json
import sys

from hg_runtime.demos.governed_research_soak.config import load_config
from hg_runtime.demos.governed_research_soak.orchestrator import run, run_operator_ui


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Governed Research Soak — demo harness",
    )
    parser.add_argument(
        "--question",
        default="Summarize recent advances in local LLM inference optimization",
        help="Research question for the demo",
    )
    parser.add_argument(
        "--output",
        default="docs/proofs/governed_research_soak/latest",
        help="Output directory for proof bundle",
    )
    parser.add_argument(
        "--demo-mode",
        action="store_true",
        default=True,
        help="Run in demo mode (default: true)",
    )
    parser.add_argument(
        "--live-model",
        action="store_true",
        default=False,
        help="Use live model instead of fixture",
    )
    parser.add_argument(
        "--live-sources",
        action="store_true",
        default=False,
        help="Use live sources instead of fixture",
    )
    parser.add_argument(
        "--playwright-capture",
        action="store_true",
        default=False,
        help="Attempt Playwright screenshot capture",
    )
    parser.add_argument(
        "--model-base-url",
        default="",
        help="Base URL for OpenAI-compatible model endpoint (default: http://127.0.0.1:1234/v1)",
    )
    parser.add_argument(
        "--model-name",
        default="",
        help="Model name for live model calls (auto-detected if empty)",
    )
    parser.add_argument(
        "--require-live-model",
        action="store_true",
        default=False,
        help="Fail with RED if live model endpoint is unavailable",
    )
    parser.add_argument(
        "--operator-ui",
        action="store_true",
        default=False,
        help="Run operator UI flow with real browser approve/deny clicks",
    )

    args = parser.parse_args()

    config = load_config(
        question=args.question,
        output_dir=args.output,
        demo_mode=args.demo_mode,
        live_model=args.live_model or args.operator_ui,
        live_sources=args.live_sources or args.operator_ui,
        playwright_capture=args.playwright_capture or args.operator_ui,
        model_base_url=args.model_base_url,
        model_name=args.model_name,
        require_live_model=args.require_live_model or args.operator_ui,
    )

    if args.operator_ui:
        result = run_operator_ui(config)
    else:
        result = run(config)

    print(json.dumps(result, indent=2))

    verdict = result.get("verdict", "")
    if verdict.startswith("GREEN_") or verdict.startswith("YELLOW_"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
