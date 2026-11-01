# Student tests and evidence

Run from the repository root with Python 3.12+ and JDK 17+:

```sh
python tools/run.py --setup
python tools/run.py --check
python tools/run.py --input tests/student/my_cases.jsonl
python tests/student/verify.py
```

`verify.py` compiles all production Java sources using `javac --release 17`,
then runs the original JSONL entry point with a **384 MiB Java heap**, a
**20-second timeout per batch**, and an **8 MiB stdout limit**. This is the
default complete suite used in CI. `--small-only` skips the generated maximum
size cases for a quicker local check.

## Saved fixtures and actual evidence

- [my_cases.jsonl](my_cases.jsonl): 65 named requests, including all eight
  commands and the supplied ping setup request.
- [expected.json](expected.json): those inputs, independently calculated
  expected values, and a reason for every test. A non-unique optimum is recorded
  by its value rather than requiring one arbitrary reconstruction.
- [actual.jsonl](actual.jsonl): actual Java responses for the same 65 requests.
  The script obtains these by launching the compiled program; they are not
  copied from the oracle.
- [verification.json](verification.json): the actual pass results, scale
  dimensions, timing boundaries, stdout byte counts, and SHA-256 digests of
  generated input batches and their actual stdout.

The suite additionally generates **320 small random cases** from
`random.Random(40431026)`: 40 cases per command. It concatenates the 65 named and
320 random cases twice in a single process, giving **770 mixed requests**. This
checks reset across different tasks and repeated requests. Search requests use
the same text/pattern within each trial, so naive, KMP and Rabin-Karp must all
agree with an independently obtained answer in their common domain.

## Independent expected answers

The Python oracles never call the submitted Java algorithms:

| Command | Small-input oracle |
|---|---|
| `lcs` | Enumerate every subsequence of the shorter input and test it against the other input; take the longest length. |
| `merge` | Enumerate every possible next adjacent operation, memoizing the resulting tuple of current block sizes. This follows chronological operations rather than reusing interval DP. |
| `tree` | Enumerate all vertex subsets, reject those containing an edge, and take the greatest weight, including the empty subset. |
| `naive`, `kmp`, `rk` | Use Python's independently implemented substring lookup repeatedly from the next start, retaining overlaps. Empty patterns use the boundary range directly. |
| `suffix` | Explicitly sort the suffix strings on small inputs, then compare adjacent suffix characters directly to obtain each LCP. |
| `aho` | Run the independent exact substring oracle separately for every dictionary position and text; duplicate dictionary entries remain separate columns. |

The semantic checker validates reconstructions as well as optimum values:

- An LCS sequence must have the declared optimum length and be a subsequence of
  both inputs.
- A merge plan must operate on two adjacent blocks that actually exist at that
  moment, contain exactly `n-1` operations, finish in one block, and sum to the
  declared optimum cost. Prefix sums recalculate each paid cost independently.
- A selected tree set must contain no duplicates, no adjacent vertices, valid
  vertex IDs, and a weight sum equal to the independent optimum.
- Search starts and Aho counts must match the independent exact answers with
  their required integer types and array dimensions.
- A suffix result must have the exact suffix order and adjacent LCPs. A longest
  repeat may differ from the oracle's chosen text, but must have the optimum
  length and occur at two distinct starts, allowing overlap.

## Tests of the semantic checker

`witness_regressions()` checks the validators themselves. It accepts **13 valid
witnesses**, including alternative LCS characters for `ab`/`ba`, both optimal
three-block merge chronologies, either endpoint of a tied two-vertex tree, and
both `ab` and `cd` for the tied longest-repeat example `ababcdcd`. Another valid
result includes an arbitrary extra field named `error`: extra fields are
ignored by the contract, regardless of their name.

It rejects **27 false witnesses**: a non-common or non-optimal LCS, Boolean
integer fields, parent-before-child/nonadjacent/unfinished merge plans, wrong
merge costs, adjacent/duplicate/out-of-range or suboptimal tree selections,
wrong suffix order/LCP/repeated strings, omitted/duplicated/reversed search
starts, and wrong Aho overlap counts, column counts or reset results. Acceptance
therefore does not depend on matching one chosen reconstruction.

## Named edge cases

Every named fixture has a reason in `expected.json`. These include:

- Empty LCS inputs in both directions, repeated characters, printable
  punctuation and case, alternative optima, and a subsequence that is not a
  substring (`tea_time` versus `team`). The actual result is length 4, `team`.
- No blocks, one block, zeros and tied merge plans. `[1,100,1]` has optimum
  203 because the two outer size-one blocks are not adjacent. Four blocks of
  size one billion have optimum `8000000000`; the actual plan merges each pair
  before their parent interval.
- Empty/singleton trees, all-negative weights, zero/tied optima, a non-greedy
  chain whose endpoints beat its middle vertex, and a star with a 64-bit sum.
- All empty-pattern boundary positions, an empty text, a longer pattern,
  overlapping matches, KMP fallback, case, spaces and punctuation. `abdj` versus
  `ab` exercises the prescribed collision: both `ab` and `dj` hash to 75 with
  base 31/modulus 101, but only start 0 is returned. A tilde followed by spaces
  exercises negative intermediate rolling remainders.
- Empty, one-character, all-distinct and all-equal suffix inputs, overlapping
  repeats, tied longest repeats and ordinary ASCII spaces/punctuation. No
  sentinel or empty suffix belongs in the result.
- Empty Aho dictionary, empty texts array, empty individual text, duplicate and
  suffix patterns, dense overlaps, repeated independent texts and a query split
  that must not create a match across text boundaries.

## Generated published-limit cases

The default script runs **26 maximum-size or boundary scale cases**. It creates
large inputs in memory rather than committing multi-megabyte fixtures. The
generator, seed, dimensions and input/output hashes make every batch repeatable.
Every scale request shares a process with a following ping and a small Aho
request with duplicate patterns and an empty text, checking reset again.

| Area | Inputs and independent expected result |
|---|---|
| LCS | `1000 x 1000` alternating `ab`/`ba` has optimum 999; two disjoint unary strings have optimum 0; an empty versus length-1000 input also has optimum 0. Returned subsequences are checked. |
| Merge | 200 equal blocks of size `1000000000` have optimum `1544000000000`; 200 zero blocks cost 0. Both chronological plans are simulated. |
| Tree | 100,000-vertex positive chain has optimum `50000000000000`; all-negative and all-zero chains have optimum 0; a positive star has optimum `99999000000000`. Every selected set is validated. |
| Naive | Text length 3000, pattern length 3000, a long near-match failure pattern, and an empty pattern returning all 3001 boundaries. |
| KMP | Text length 200000 and pattern length 100000, dense alternating overlaps, long near-match failures, and an empty pattern returning all 200001 boundaries. |
| Rabin-Karp | `10000 x 2000` reaches the product bound 20,000,000 for both dense matches and a deliberate equal-hash nonmatch; a length-10000 pattern on a length-2000 text returns no starts; an empty pattern returns 10001 boundaries. |
| Suffix | 50,000-character unary, periodic and seeded full-printable-ASCII strings. The unary and periodic suffix orders/LCPs have closed forms; the random case uses exact tail-rank order certification and direct adjacent LCP comparisons. |
| Aho | 10,000 duplicate/suffix patterns with total length exactly 100000, 100 texts with total length 200000, and one million returned counts; a 90002-state trie with 9999 duplicate shallow terminals; a length-100000 pattern creating 100001 states queried against 100 independent texts; and 100 empty-dictionary rows. |

For 200 equal merge leaves, an optimal ordered binary merge tree can have 56
leaves at depth 7 and 144 at depth 8, so its total cost is
`(56*7 + 144*8)*1000000000 = 1544000000000`. Equal positive leaves cannot improve
this balanced depth distribution; an ordered tree with it exists. This gives a
closed-form optimum independently of the interval-DP implementation.

For the maximum alternating KMP case, exactly the even starts from 0 through
100000 match: a start must begin with `a`, and the length-100000 pattern must
fit inside the length-200000 text. This closed-form list avoids expensive
repeated long-pattern searches in the test generator; small search cases still
use the independent built-in substring oracle.

For `a*50000`, the suffix array is descending starts and LCPs are `0..49999`.
For `ab*25000`, the even starts appear descending, followed by the descending
odd starts. Within the first group LCPs grow `2,4,...,49998`; the group boundary
has LCP 0 and the second group's LCPs grow `1,3,...,49997`. The checker compares
every array entry to these formulas, without character-scanning their quadratic
sum of LCP lengths.

For the fixed printable-random suffix fixture, the checker first certifies that
the suffix array is a permutation. It builds the inverse ranks and checks that
`(text[start], rank[start+1])`, using rank `-1` for the empty tail, strictly
increase in the proposed order. Repeatedly reducing equal first characters to
their shorter tails proves the full suffix order. Independent direct adjacent
character comparisons then check all LCP entries; this high-alphabet fixture
has short shared prefixes. This check stores no suffix strings and does not
reuse the production suffix algorithm.

In the dense Aho fixture, pattern lengths cycle from 1 through 19, with one
final adjustment so total dictionary length is exactly 100000. Texts alternate
between 2000 `a` characters and 1999 `a` characters followed by `b`; each count
is therefore `max(0, a_run_length-pattern_length+1)`. Duplicate patterns must
receive the same count. The large-state fixture's only pattern is longer than
every text, independently proving all its counts zero while still exercising
construction and approximately ten million reverse-failure state visits.

The combined deep-trie/duplicate-terminal fixture uses 9999 copies of `a` and
one pattern consisting of 90001 `a` characters. Its total pattern length is
exactly 100000, with 10000 dictionary entries and 90002 trie states. A text of
200000 `a` characters gives each shallow duplicate count 200000 and the deep
pattern count `200000-90001+1 = 110000`. Copying 9999 inherited terminal IDs into
every deep state's output list would create roughly 900 million entries. This
case therefore exercises the large-trie and duplicate-terminal dimensions
together, with only 10000 output counts required by the contract.

## Timing and benchmark distinction

Verification durations in `verification.json` include JVM startup, JSON
parsing, algorithm execution and I/O; Python fixture generation and semantic
validation occur outside that timer. They show completion within the tested
batch limit and are not an algorithm benchmark. The separate
`SearchBenchmark.java` and `benchmark_results.json` use the controlled timing
boundary and methodology recorded in root `ANALYSIS.md`.
