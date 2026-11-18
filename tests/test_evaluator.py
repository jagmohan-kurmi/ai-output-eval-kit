import json
import os
import shutil
import subprocess
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai_output_eval_kit.evaluator import InputError, evaluate_jsonl  # noqa: E402


@contextmanager
def scratch():
    path = ROOT / "tests" / ".work"
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class EvalTests(unittest.TestCase):
    def test_exact_contains_path_and_schema_assertions(self):
        cases = [
            {"id": "answer", "actual": {"answer": "42", "tags": ["ok"]},
             "assertions": [
                 {"type": "json_path", "path": "$.answer", "expected": "42"},
                 {"type": "contains", "path": "$.tags", "value": "ok"},
                 {"type": "schema", "schema": {"type": "object", "required": ["answer"],
                                               "properties": {"answer": {"type": "string"}}}},
             ]},
        ]
        with scratch() as directory:
            path = directory / "cases.jsonl"
            path.write_text("\n".join(json.dumps(case) for case in cases), encoding="utf-8")
            report = evaluate_jsonl(path)
            self.assertEqual(1.0, report["pass_rate"])
            self.assertEqual(3, len(report["cases"][0]["assertions"]))

    def test_failed_case_in_aggregate_and_cli_gate(self):
        case = {"id": "bad", "actual": "wrong", "expected": "right",
                "assertions": [{"type": "exact"}]}
        with scratch() as directory:
            path = directory / "cases.jsonl"
            path.write_text(json.dumps(case), encoding="utf-8")
            report = evaluate_jsonl(path)
            self.assertEqual(0, report["pass_rate"])
            run = subprocess.run([sys.executable, "-m", "ai_output_eval_kit.cli",
                                  str(path), "--format", "json"], cwd=ROOT, capture_output=True, text=True,
                                 env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
            self.assertEqual(1, run.returncode)
            self.assertEqual(1, json.loads(run.stdout)["failed"])

    def test_malformed_jsonl_returns_domain_error(self):
        with scratch() as directory:
            path = directory / "broken.jsonl"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(InputError):
                evaluate_jsonl(path)


if __name__ == "__main__":
    unittest.main()
