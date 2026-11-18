import argparse
import json
import sys
from pathlib import Path

from .evaluator import InputError, evaluate_jsonl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate offline JSONL output cases.")
    parser.add_argument("cases", type=Path, help="JSONL file with actual values and assertions")
    parser.add_argument("--min-pass-rate", type=float, default=1.0, help="Required aggregate rate, from 0 to 1")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if not 0 <= args.min_pass_rate <= 1:
        parser.error("--min-pass-rate must be between 0 and 1.")
    try:
        report = evaluate_jsonl(args.cases)
    except InputError as exc:
        print(f"ai-output-eval-kit: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        for case in report["cases"]:
            status = "PASS" if case["passed"] else "FAIL"
            print(f"{status} {case['id']}")
            for assertion in case["assertions"]:
                print(f"  {'ok' if assertion['passed'] else 'not ok'} "
                      f"{assertion['type']}: {assertion['detail']}")
        print(f"Pass rate: {report['passed']}/{report['total']} ({report['pass_rate']:.1%})")
    return int(report["pass_rate"] < args.min_pass_rate)


if __name__ == "__main__":
    raise SystemExit(main())
