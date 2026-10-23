import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "research" / "tools"))

import analyze_evidence


class EvidenceAnalyzerTests(unittest.TestCase):
    def test_detects_use_after_free(self):
        text = "ERROR: AddressSanitizer: heap-use-after-free"
        self.assertRegex(
            text,
            analyze_evidence.PATTERNS["heap_use_after_free"],
        )

    def test_detects_memory_limit(self):
        text = "Allowed memory size of 8388608 bytes exhausted"
        self.assertRegex(text, analyze_evidence.PATTERNS["memory_limit"])

    def test_detects_http_500(self):
        self.assertRegex(
            "HTTP/1.1 500 Internal Server Error",
            analyze_evidence.PATTERNS["http_500"],
        )

    def test_command_output_is_unverified(self):
        self.assertEqual(
            analyze_evidence.CATEGORIES["command_output_pattern"],
            "unverified_claim",
        )

    def test_report_has_limitations(self):
        report = analyze_evidence.build_report(context=0)
        self.assertIn("files_analyzed", report)
        self.assertIn("results", report)
        self.assertTrue(report["limitations"])


if __name__ == "__main__":
    unittest.main()
