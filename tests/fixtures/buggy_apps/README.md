# Evaluation fixture ground truth

These tiny, locally authored fixtures are unexecuted until an evaluator constructs a controlled event and pins a Git commit. `divide(1, 0)` raises ZeroDivisionError; `parse_age('unknown')` raises ValueError; `load_url({})` raises KeyError. The remaining scenarios in `investigation_cases.json` describe incomplete, conflicting or adversarial evidence, not known diagnoses. Human adjudication and a separate held-out set are required before claiming diagnosis accuracy. The automated scenarios inject mocked model output and test workflow behavior only.
