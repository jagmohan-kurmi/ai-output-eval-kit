# AI Output Eval Kit

Run small, deterministic, fully offline evaluations over JSONL cases. Each case supplies an `actual` value and one or more exact, substring, JSON-path, or schema-subset assertions.

## Install

Requires Python 3.11+ and has no runtime dependencies.

```sh
python -m venv .venv
python -m pip install -e .
```

## Input and run

Each nonblank JSONL line is a separate case:

```json
{"id":"greeting","actual":"Hello Ada","assertions":[{"type":"contains","value":"Ada"}]}
{"id":"shape","actual":{"ok":true},"assertions":[{"type":"json_path","path":"$.ok","expected":true},{"type":"schema","schema":{"type":"object","required":["ok"]}}]}
```

```sh
ai-output-eval-kit fixtures/cases.jsonl
ai-output-eval-kit cases.jsonl --min-pass-rate 0.9 --format json
```

Exit codes: `0` meets the minimum pass rate; `1` falls below it; `2` means invalid input. Schema assertions implement a documented subset (`type`, `required`, `properties`, `items`, `enum`, string lengths, and numeric bounds), not full JSON Schema. `contains` applies to strings, lists, and dicts. Tests: `python -m unittest discover -s tests`.
