# Assignment 4 — Dynamic Programming and String Processing

[![Public checks](https://github.com/Denzel-is/daa-assignment-4-archive-solution/actions/workflows/public.yml/badge.svg)](https://github.com/Denzel-is/daa-assignment-4-archive-solution/actions/workflows/public.yml)

Java 17 solution created using the [official GitHub template](https://github.com/RZhaniya/daa-assignment-4-archive). Implements all eight commands, reconstructs optimal witnesses and includes independent semantic tests, full-domain generators and measured search comparisons. The supplied JSON adapter and original learning materials are retained; the solution uses no external Java dependencies.

[English specification](docs/Assignment_4_EN.md) · [Exact contracts](docs/guide/CONTRACTS.md) · [Analysis and measurements](ANALYSIS.md) · [Test evidence](tests/student/README.md) · [Preparation notes](PREPARATION.md)

## Build, run and check

Install JDK 17+ and Python 3.12+ (Python runs the provided launcher). Run from the repository root:

```sh
python tools/run.py --setup
python tools/run.py --check
python tests/student/verify.py
python tools/check_submission.py
python tools/run.py --input tests/student/my_cases.jsonl
```

`submission.json` selects `Java`. The launcher creates `Java/build`, compiles all files under `Java/source` with Java 17 compatibility and runs `Main` with a 384 MiB heap. The program accepts one UTF-8 JSON request per line and returns one JSON result per line; mixed tasks start with fresh state. The setup request `{"task":"ping"}` returns `{"status":"ready"}`.

After building, run the program directly with:

```sh
java -Xmx384m -cp Java/build Main
```

## Implemented algorithms

| Command | Required method | Time after parsing |
| --- | --- | --- |
| `lcs` | Prefix DP and optimal subsequence reconstruction | O((a+1)(b+1)) |
| `merge` | Last-split interval DP and chronological adjacent merges | O(n³) for n≥1; O(1) empty |
| `tree` | Iterative take/skip tree DP and independent-set reconstruction | O(n+1) |
| `naive` | Direct comparisons at every legal start | O(nm+n+1) |
| `kmp` | Prefix function and overlap-preserving fallback | O(n+m+z+1) |
| `rk` | Base 31/mod 101 rolling hash with exact verification | O(n+m+cm) when 1≤m≤n |
| `suffix` | Radix prefix doubling and Kasai LCP | O(n log(n+1)+1) |
| `aho` | Failure automaton and reverse-failure visit aggregation | O(L+95S+p) construction; O(t+S+p) per text |

See [ANALYSIS.md](ANALYSIS.md) for invariants, reconstruction, correctness, auxiliary/output storage and boundary cases. Empty patterns match every boundary; search results include overlaps. Costs, tree totals and dictionary counts use `long`. Deep trees and reconstructions use explicit traversal orders or stacks.

## Reproducible search comparison

The benchmark compares naive, KMP and exact RK on identical random, repetitive near-miss and repetitive dense-match inputs at three sizes within all three domains. It checks correct positions first, warms up the JVM and records five samples per method with the same timing boundary.

```sh
javac --release 17 -encoding UTF-8 -cp Java/build -d Java/build tests/student/SearchBenchmark.java
java -Xmx384m -cp Java/build SearchBenchmark
```

The seed, generator, raw measurements, medians, hardware and limitations are in [ANALYSIS.md](ANALYSIS.md) and [benchmark_results.json](tests/student/benchmark_results.json). An optional output path lets CI save fresh results separately from the recorded local run.

## GitHub Actions

[Public checks](https://github.com/Denzel-is/daa-assignment-4-archive-solution/actions) runs on push, pull request and manual dispatch with Java 17 and 21. It runs the official 44 cases and repeated requests, independent small-oracle and full-domain tests, and submission-file checks. Java 17 also checks startup of all four supplied language adapters and reproduces the search benchmark. Actual evidence is retained as downloadable workflow artifacts for 30 days. Actions are pinned to verified commit SHAs and repository permissions are read-only.

## Preparation and submission

Review the [interactive lesson](https://rzhaniya.github.io/daa-assignment-4-archive/), [public practice](https://rzhaniya.github.io/daa-assignment-4-archive/practice.html) and [preparation notes](PREPARATION.md). The notes summarize the public models and practice concepts; they do not record a practice attempt by the repository owner. The assessed individual defence remains a separate Moodle activity.

For Moodle Online text, submit the **exact commit URL with its full 40-character SHA** and **language: Java**. The successful Actions URL for the same SHA is optional evidence. Click Submit assignment and check the final status. Use the official [submission checklist](docs/guide/SUBMISSION.md); do not submit a ZIP.

OpenAI Codex assisted with implementation, testing, measurements, documentation and CI. The [source and assistance disclosure](ANALYSIS.md#sources-and-ai-assistance) states the contribution and verification. Public checks provide feedback; the instructor's independent rubric checks determine the practical mark.
