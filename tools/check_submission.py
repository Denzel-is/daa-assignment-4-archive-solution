"""Check that the requested implementation, documentation and evidence are present."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "submission.json").read_text(encoding="utf-8"))
    assert manifest["language"] == "Java", "This solution selects Java"
    for name in ["Algorithms.java", "DynamicProgramming.java", "StringAlgorithms.java"]:
        text = (ROOT / "Java/source" / name).read_text(encoding="utf-8")
        assert "UnsupportedOperationException" not in text and "TODO" not in text, name
    analysis = (ROOT / "ANALYSIS.md").read_text(encoding="utf-8")
    assert len(analysis) > 4000 and "REPLACE_WITH" not in analysis, "Complete the analysis"
    assert "Codex" in analysis, "Disclose AI assistance"
    student = ROOT / "tests/student"
    for name in ["verify.py", "my_cases.jsonl", "expected.json", "actual.jsonl",
                 "verification.json", "SearchBenchmark.java", "benchmark_results.json"]:
        assert (student / name).is_file() and (student / name).stat().st_size, name
    assert json.loads((student / "verification.json").read_text())["status"] == "PASS"
    measured = json.loads((student / "benchmark_results.json").read_text())["measurements"]
    assert len(measured) == 9 and all(row["all_outputs_checked"] for row in measured)
    print("PASS preparation: Java source, English analysis, tests and actual measurements present")


if __name__ == "__main__":
    main()
