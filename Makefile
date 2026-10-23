.PHONY: check test analyze clean-report

check:
	python3 -m py_compile research/tools/analyze_evidence.py tests/test_evidence_analyzer.py
	python3 -m unittest discover -s tests -v

test:
	python3 -m unittest discover -s tests -v

analyze:
	python3 research/tools/analyze_evidence.py --json

clean-report:
	rm -f research/evidence-analysis-v2.json
