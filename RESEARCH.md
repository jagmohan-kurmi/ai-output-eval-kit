# Scope, evidence, and limits

This package evaluates saved expected-output cases locally. It deliberately does not call an AI model, make network requests, judge semantic quality, or handle prompts/secrets. JSONL gives a simple line-oriented format suitable for test fixtures and batch output capture.

Evidence:
- [JSON Lines format](https://jsonlines.org/)
- [JSON Schema specification](https://json-schema.org/specification)
- [Google Cloud DORA 2024 report: AI adoption and software delivery performance](https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report)

The 2024 DORA research highlights the importance of trust and delivery-system context when interpreting AI adoption and output. This tool's pass rate is only the proportion of supplied assertions/cases that pass; it is not a measure of model quality, safety, trustworthiness, or organizational performance. Its schema checks are an intentionally limited subset and JSON-path syntax supports only basic object keys and array indices.
