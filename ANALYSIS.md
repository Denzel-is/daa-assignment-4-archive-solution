# Assignment 4 — implementation and evidence

## Environment and commands

Selected language: **Java**, as recorded in submission.json. The implementation is compatible with Java 17 and requires no external libraries; the supplied Main.java and Json.java are unchanged. Local execution used Oracle Java 21.0.10+8-LTS-217 (HotSpot 64-bit Server VM), Python 3.13.14, Windows 11 Pro 10.0.26200 amd64, an Intel Core i5-1235U (10 cores, 12 logical processors) and approximately 16 GiB RAM. The launcher and own checks cap the Java heap at 384 MiB. CI checks Temurin Java 17 and 21 with Python 3.12 on Ubuntu 24.04.

Run from the repository root:

    python tools/run.py --setup
    python tools/run.py --check
    python tests/student/verify.py
    python tools/run.py --input tests/student/my_cases.jsonl
    python tools/check_submission.py
    javac --release 17 -encoding UTF-8 -cp Java/build -d Java/build tests/student/SearchBenchmark.java
    java -Xmx384m -cp Java/build SearchBenchmark

The launcher creates Java/build, compiles all Java/source/*.java with javac --release 17 -encoding UTF-8, and executes java -Xmx384m -cp Java/build Main. Only JSON results go to stdout, one per request line; compilation diagnostics go to stderr. Ping is preserved. Every command creates all mutable state locally: no DP table, automaton, matched prefix, counter or traversal state survives a request. Aho also resets visits and current state between texts within one request.

## Algorithm explanations

### LCS — prefix dynamic programming

length[i][j] is the optimum common-subsequence length of prefixes a[0..i) and b[0..j). Row and column zero are zero; matching final characters extend length[i-1][j-1] by one, while a mismatch takes the maximum of removing either final character. Increasing i and j makes dependencies ready. An optimum either uses the matching final character or, for a mismatch, must omit at least one of them, proving the recurrence by prefix induction. Backtracking appends matching characters, otherwise follows an optimal predecessor (dropping from a on ties), then reverses the sequence. It returns an optimal subsequence of both inputs; ties can produce different accepted sequences, and tea_time/team detects confusing subsequences with contiguous substrings.

Time and auxiliary DP storage are O((|a|+1)(|b|+1)); backtracking takes O(|a|+|b|) time and O(length+1) reconstruction storage. Input is O(|a|+|b|+1) and output is O(length+1). Either empty input returns length zero and the empty sequence.

### Merge — adjacent interval dynamic programming

cost[l][r] is the minimum cost of collapsing original closed interval [l,r], and split[l][r] records its chosen last split k. A singleton costs zero; prefix sums provide the interval sum, and the recurrence minimizes cost[l][k]+cost[k+1][r]+sum(l..r) over l<=k<r. Increasing interval lengths ensures both children are ready. Every valid final operation combines two adjacent child intervals for some k, so all splits cover every possible optimum; interval-length induction also constructs a plan attaining the recurrence. Explicit postorder frames emit both child plans before [l,k,r], producing chronological original-index operations rather than positions in a shortened array. Ties use the first split; zero/single blocks need no merges. For [1,100,1], the optimum is 203, while arbitrarily combining the separated ones is invalid.

For n>=1 time is O(n³), auxiliary tables use O(n²), prefix sums and reconstruction stack use O(n), input is O(n), and output is O(n). The empty case takes O(1) time/space. All sums/costs are long; any plan costs at most (n-1)*sum(sizes)<=3.98*10^13. Four billion-sized blocks have optimum 8,000,000,000, exposing 32-bit overflow.

### Tree — take/skip dynamic programming

Root the tree at zero, build primitive adjacency arrays, and fill a parent-before-child order iteratively. Initialize take[u]=weight[u] and skip[u]=0; process that order backward, adding skip[v] to its parent's take and max(take[v],skip[v]) to its parent's skip. Take requires u and therefore forbids its children; skip allows each child subtree its better choice. Child subtrees have no conflict edges between them, so their values add, proving optimality by induction from leaves; root choice cannot change the undirected optimum. Reconstruction scans parent-before-child, forces a child skipped when its parent is selected, and otherwise takes only when strictly better than skip. Skipping ties preserves value, all-negative/empty trees select nothing, and deep chains never use recursive calls.

Time and auxiliary arrays are O(n+1), input is O(n+1), and selected-output space is O(n+1). Long values safely accommodate a positive sum up to 10^14. The chain [4,9,6] selects endpoints of value 10 rather than the tempting middle vertex of value 9; zero-weight ties and negative singletons check reconstruction boundaries.

### Naive exact search

For each legal start zero through n-m inclusive, compare actual characters and report only a complete match. The matched prefix consists entirely of equal character pairs, so completing m comparisons is necessary and sufficient. Testing every start preserves overlaps and the last window. An empty pattern is handled first with all n+1 boundaries, including after the text; a longer pattern has no legal start. Case, spaces and punctuation are literal ASCII. aaaaa/aaa returns [0,1,2], exposing skipped overlaps.

Time after parsing is O(n*m+n+1), auxiliary storage O(1), input O(n+m+1), and output O(z+1), including the returned ArrayList and boxed starts. The empty-pattern output work is included.

### KMP — prefix reuse

prefix[i] is the longest proper prefix of pattern[0..i] that is also its suffix. Prefix construction and scanning follow prefix[matched-1] on a mismatch until the next character can extend a viable border; the text position never moves backward. This preserves all remaining candidates because excluded longer borders cannot match the suffix already examined. After a full match, report its start and fall back through the same table, retaining overlaps. Empty patterns return boundaries before indexing and longer patterns return no matches. abababa/aba gives starts 0,2,4; repetitive near-misses test reuse of long matched prefixes.

Successful increments and fallbacks are charged to forward progress, giving O(n+m+z+1) time. Auxiliary prefix space is O(m+1), input O(n+m+1), and output O(z+1).

### Exact Rabin–Karp — specified collision laboratory

The fingerprint is a polynomial in ASCII codes using base 31, modulus 101 and the highest power at the left. Compute the first window, pattern hash and 31^(m-1) modulo 101; remove the outgoing weighted character, normalize a negative remainder, multiply by 31 and add the incoming character. Induction on window starts proves this equals a fresh polynomial evaluation. Unequal hashes exclude equality, but equal hashes trigger literal comparison before reporting, so collisions never create false matches. Empty and oversized patterns are handled before creating a window. ab and dj both hash to 75, yet text abdj/pattern ab reports only zero; separate fixtures exercise normalized subtraction.

For 1<=m<=n time is O(n+m+c*m), where c is the number of equal-hash windows; O(n*m+n+m+1) covers all boundary cases. Auxiliary hash space is O(1), input O(n+m+1), and output O(z+1). Verification can be quadratic for many true matches or collisions; deterministic linear worst-case time is not claimed. Long arithmetic is used throughout the rolling calculation.

### Suffix array — prefix doubling and Kasai

Initial positive ranks encode printable ASCII, reserving zero for beyond the text without adding a sentinel character or suffix. For widths 1,2,4,..., stable counting sort by second rank and then first rank orders pairs; equal pairs receive equal new ranks. Correct width-character prefix ranks therefore produce correct doubled-prefix ranks, proving correctness by induction. Distinct ranks or a width covering the text determine full suffix order; arrays contain exactly starts 0..n-1 and no suffix strings are materialized. Each round is O(n) over at most max(95,n) classes, giving O(n log(n+1)) doubling time and O(n+1) auxiliary space rather than comparison sorting's O(n log²(n+1)).

Kasai builds inverse ranks and scans starts in text order, comparing with each suffix's lexicographic predecessor. Removing a leading character reduces the reusable common-prefix lower bound by at most one, so common is decremented after a nonzero comparison and reset for the first suffix. Successful extensions total O(n), giving linear Kasai time and lcp[0]=0. Any two suffixes' common prefix is bounded by the adjacent LCPs between them, so a maximum adjacent LCP gives a longest repeat, even with overlaps. The code keeps the first strict maximum encountered in text-order scanning; tied longest repeats are valid. Empty text returns empty arrays/string; banana gives SA [5,3,1,0,4,2], LCP [0,1,3,0,0,2] and ana.

Combined auxiliary and output storage are each O(n+1), with O(n+1) input. The one returned substring is the only materialized suffix-related string. Empty input takes O(1); unary and periodic tests catch missing overlaps, poor scaling and leaked sentinels.

### Aho–Corasick — aggregated dictionary matching

Insert patterns into one trie and record a terminal for every original dictionary position; duplicate patterns share terminals but keep separate output columns. Dense 95-character rows grow geometrically with actual states rather than duplicate input length. BFS creates failure links to longest proper suffixes that are trie prefixes and completes missing transitions from shallower failure states. Each independent text starts at root with fresh visit counts; scanning counts the current state, and reverse BFS propagates visits to failure parents. Thus every suffix-pattern terminal receives exactly the text prefixes ending with that pattern, counting overlaps without enumerating individual dictionary-entry matches. Read counts in original dictionary order. An empty dictionary retains an empty row for every text; no texts gives no rows.

Let L include duplicate pattern lengths, p be dictionary size, S trie states including root, and q texts. Construction is O(L+95*S+p) time and O(95*S+p) auxiliary memory, including geometric allocation/copying. Each text is O(|text|+S+p) time and O(S+1) visits space with the automaton retained. Output is O(q*(p+1)+1), input O(L+total_text_length+p+q+1), and counts use long. Dense duplicate/suffix patterns, a million-count output and deep tries expose lost suffix matches, inherited-output copying, per-match traversal and stale counts.

## Own tests and actual executions

The saved [inputs](tests/student/my_cases.jsonl), [independent expectations and reasons](tests/student/expected.json), and [actual Java results](tests/student/actual.jsonl) align by case/line order. [Test notes](tests/student/README.md) explain generators and proofs. The [verifier](tests/student/verify.py) independently enumerates shorter-string subsequences, choices of the next adjacent merge and vertex subsets; it uses Python's separate exact substring finder, direct small suffix sorting/LCP and direct per-pattern counting. It never calls production methods to generate expectations. Semantic checks validate chronological plans and paid cost, independent sets and weight, subsequences, exact starts, suffix/LCP order and any optimal repeat; extra output fields are ignored.

| Fixture | Independent expected value | Actual Java result | Defect exposed |
| --- | --- | --- | --- |
| lcs_subsequence_not_substring | {"length":4} | {"length":4,"sequence":"team"} | team appears in order, although its m is separated. |
| merge_adjacency_matters | {"cost":203} | {"plan":[[1,1,2],[0,0,2]],"cost":203} | Only adjacent pairs may be merged: 101 then 102 gives 203. |
| tree_chain | {"weight":10} | {"selected":[0,2],"weight":10} | Endpoints contribute 10, beating the middle vertex's 9. |
| naive_overlap | {"positions":[0,1,2]} | {"positions":[0,1,2]} | All three overlapping starts 0,1,2 count. |
| kmp_fallback | {"positions":[0,2,4]} | {"positions":[0,2,4]} | The overlapping starts are 0,2,4. |
| rk_collision | {"positions":[0]} | {"positions":[0]} | ab and dj share hash 75 modulo 101, but only start 0 matches. |
| suffix_banana | {"sa":[5,3,1,0,4,2],"lcp":[0,1,3,0,0,2],"repeated_length":3} | {"repeated":"ana","lcp":[0,1,3,0,0,2],"sa":[5,3,1,0,4,2]} | Direct suffix strings give SA 5,3,1,0,4,2 and maximum LCP 3. |
| aho_suffix_duplicates_reset | {"counts":[[2,2,2,2],[2,2,2,2],[0,0,0,0]]} | {"counts":[[2,2,2,2],[2,2,2,2],[0,0,0,0]]} | Each entry occurs twice in each repeated text, then zero in the empty text. |


Actual local results: **44 official cases** and their repeated batch passed. Own checks passed **65 named + 320 seeded oracle cases**, repeated twice in one JVM (**770 requests**, seed 40431026). Checker regressions accepted 13 valid variants and rejected 27 false results.

**26 full-domain cases passed**: LCS 1000x1000, merge n=200, four 100000-vertex chain/star trees, naive n=3000, KMP n=200000/m=100000 and empty patterns, RK n=10000/m=2000 (product 20000000) and m=10000 on shorter text, three length-50000 suffix inputs, and Aho at L=100000/p=10000/q=100/total text length 200000 with one million counts. A separate request has 100001 trie states and 100 texts; combined deep-trie/shallow-duplicate stress detects inherited-output copying. Each scale request is followed by ping and small Aho in the same JVM. Every batch uses a 20-second timeout, 384 MiB heap and 8 MiB stdout cap; largest recorded stdout was 5,000,261 bytes. These validate correctness and completion, not benchmark rankings.

Large expected values have separate justifications: shifted alternating LCS is 999 because equal-length distinct strings cannot share length 1000; 200 uniform blocks have 56 leaves at depth 7 and 144 at depth 8, total 1544*10^9. A positive even chain chooses 50000 independent vertices, a star chooses 99999 leaves, and negative/zero cases have value zero. Unary suffixes sort by remaining length with LCP 0..49999; alternating suffixes have a closed-form parity grouping. The fixed printable-random suffix case is certified by its permutation and increasing (first character, inverse rank of tail) pairs, with empty-tail rank -1, then direct adjacent LCP comparisons without materialized suffix strings. Dense Aho expectations follow run lengths. Generated large inputs/outputs have dimensions and SHA-256 digests in verification.json; the source reconstructs them rather than committing repetitive megabytes.

## Search comparison

[SearchBenchmark.java](tests/student/SearchBenchmark.java) compares identical immutable inputs at n/m=(500/50,1500/150,3000/300), within all three domains. Random inputs use java.util.Random(20261031L+n), independent uniform a..z text/pattern, then plant the pattern at n/4 and 3n/4. Repetitive near-misses use a^n versus a^(m-1)b, and dense matches use a^n versus a^m; report these families separately. An independent exhaustive character oracle checks all three outputs before timing, every warm-up, and every retained timed result after stopping the timer. The known ab/dj collision is a separate correctness check. Fresh polynomial evaluation computes hash-candidate counts outside timing.

The local measured environment is specified above; [benchmark_results.json](tests/student/benchmark_results.json) includes UTC timestamp, JVM details and actual raw data. Timer: System.nanoTime. Each input has 20 warm-up calls per method, then five samples per method, each with 30 complete calls; first method rotates per round/sample. The interval includes algorithm execution, output allocation, volatile consumption of occurrence count and saving result references in a preallocated list. It excludes compilation, JVM startup, input generation, JSON parsing, correctness/candidate checks and I/O equally for all methods. Normal JIT/GC remains; no explicit GC or fresh JVM per sample is used. Raw totals below are milliseconds for 30 calls; median per-call time is median total divided by 30. JSON also stores all per-call averages.

| Family | n | m | Method | Five raw totals (ms; 30 calls each) | Median per call (ms) | Matches / hash candidates |
| --- | ---: | ---: | --- | --- | ---: | --- |
| random | 500 | 50 | naive | 2.2471, 3.1900, 2.1907, 2.0797, 7.7293 | 0.074903 | 2 / 4 |
| random | 500 | 50 | kmp | 2.4135, 2.6199, 2.6184, 2.7946, 2.1419 | 0.087280 | 2 / 4 |
| random | 500 | 50 | rk | 4.1080, 4.0226, 3.7486, 3.4002, 9.4869 | 0.134087 | 2 / 4 |
| random | 1500 | 150 | naive | 1.7978, 2.2176, 2.2251, 1.8714, 1.8181 | 0.062380 | 2 / 15 |
| random | 1500 | 150 | kmp | 7.2552, 3.8472, 3.2075, 3.3646, 3.3018 | 0.112153 | 2 / 15 |
| random | 1500 | 150 | rk | 5.4456, 3.5256, 7.4924, 7.4396, 3.3093 | 0.181520 | 2 / 15 |
| random | 3000 | 300 | naive | 4.3656, 4.5614, 5.1321, 4.7245, 5.9073 | 0.157483 | 2 / 22 |
| random | 3000 | 300 | kmp | 5.4011, 5.2421, 6.8383, 5.2863, 5.3754 | 0.179180 | 2 / 22 |
| random | 3000 | 300 | rk | 5.7078, 1.9958, 2.3831, 2.0749, 2.0208 | 0.069163 | 2 / 22 |
| repetitive_mismatch | 500 | 50 | naive | 3.8338, 3.7916, 2.3895, 2.3636, 2.3636 | 0.079650 | 0 / 0 |
| repetitive_mismatch | 500 | 50 | kmp | 2.2272, 2.2428, 6.2322, 2.1379, 1.9363 | 0.074240 | 0 / 0 |
| repetitive_mismatch | 500 | 50 | rk | 0.3245, 0.3775, 0.3261, 0.3202, 0.3872 | 0.010870 | 0 / 0 |
| repetitive_mismatch | 1500 | 150 | naive | 28.0726, 26.0990, 30.4737, 26.9395, 31.3334 | 0.935753 | 0 / 0 |
| repetitive_mismatch | 1500 | 150 | kmp | 9.2895, 7.2276, 0.8570, 0.7717, 0.8032 | 0.028567 | 0 / 0 |
| repetitive_mismatch | 1500 | 150 | rk | 0.9689, 0.9303, 1.0956, 0.9367, 0.9424 | 0.031413 | 0 / 0 |
| repetitive_mismatch | 3000 | 300 | naive | 130.6019, 121.8245, 101.4570, 120.9164, 114.9215 | 4.030547 | 0 / 0 |
| repetitive_mismatch | 3000 | 300 | kmp | 1.5078, 3.5532, 3.2984, 1.7056, 1.5329 | 0.056853 | 0 / 0 |
| repetitive_mismatch | 3000 | 300 | rk | 2.4415, 3.0106, 2.0100, 1.9080, 1.9492 | 0.067000 | 0 / 0 |
| repetitive_matches | 500 | 50 | naive | 23.0017, 15.4220, 15.7403, 26.8808, 9.3761 | 0.524677 | 451 / 451 |
| repetitive_matches | 500 | 50 | kmp | 9.5970, 2.9973, 2.2386, 3.2248, 2.1321 | 0.099910 | 451 / 451 |
| repetitive_matches | 500 | 50 | rk | 5.1312, 4.9303, 6.7553, 9.0971, 5.0162 | 0.171040 | 451 / 451 |
| repetitive_matches | 1500 | 150 | naive | 43.2789, 25.6252, 38.6008, 36.9697, 48.6947 | 1.286693 | 1351 / 1351 |
| repetitive_matches | 1500 | 150 | kmp | 2.2494, 1.9636, 2.1165, 1.4639, 1.6509 | 0.065453 | 1351 / 1351 |
| repetitive_matches | 1500 | 150 | rk | 47.4465, 60.2778, 66.6207, 74.6123, 52.4479 | 2.009260 | 1351 / 1351 |
| repetitive_matches | 3000 | 300 | naive | 131.0232, 116.6780, 148.3939, 140.5259, 160.9864 | 4.684197 | 2701 / 2701 |
| repetitive_matches | 3000 | 300 | kmp | 1.7995, 1.9036, 3.3385, 4.1391, 7.8454 | 0.111283 | 2701 / 2701 |
| repetitive_matches | 3000 | 300 | rk | 252.9670, 195.8955, 256.6831, 219.7152, 289.6381 | 8.432233 | 2701 / 2701 |


Repetitive near-misses penalize naive's repeated long-prefix comparisons; KMP reuses borders while RK excludes every window by hash in that family. Dense true matches force exact RK to verify full candidate windows, demonstrating c*m without false collisions; KMP retains linear scan progress and pays for output. Random windows usually mismatch early and have few hash candidates, so overhead/JIT thresholds dominate short runs; observed random timings are not monotone and do not establish a universal winner. Nine inputs, one laptop, five samples per method/input and one evolving JVM limit the experiment. Background scheduling, power management, allocation, JIT and GC add noise; separate forks and more warm-up would improve confidence. No confidence interval or cross-machine claim is made.

Modulus 101 deliberately creates many more random candidate collisions than typical larger production fingerprints; it is a teaching laboratory, not a general comparison of all production RK implementations. Exact verification remains necessary for exact correctness, and dense true matches can be expensive with no collision at all. Asymptotic bounds come from algorithm operations rather than medians.

## Automation and submission

[Public checks](https://github.com/Denzel-is/daa-assignment-4-archive-solution/actions/workflows/public.yml) runs on pushes, pull requests and manual dispatch under Java 17 and 21. Java 17 preserves startup checks for all four supplied adapters, with .NET 8 installed; both run Java setup, official cases, independent full-domain tests and submission checks. Java 17 reproduces the benchmark into benchmark_ci.json, keeping committed local measurements separate. Evidence artifacts last 30 days, action commits are pinned, repository permissions are read-only and stale runs are cancelled. Logs identify the exact tested SHA/runtime.

Submit the exact commit URL containing the full 40-character SHA and language Java in Moodle Online text. A successful Actions URL for the same SHA is optional; follow the [submission checklist](docs/guide/SUBMISSION.md), click Submit assignment and verify final status. Public checks provide feedback rather than the official practical grade. The assessed individual defence is separate; [preparation notes](PREPARATION.md) summarize public material and do not claim a quiz attempt.

## Sources and AI assistance

The [official template](https://github.com/RZhaniya/daa-assignment-4-archive), [specification](docs/Assignment_4_EN.md), [contracts](docs/guide/CONTRACTS.md), [rubric](docs/guide/RUBRIC.md), [testing notes](docs/guide/TESTING.md) and [lecture clarifications](docs/LECTURE_CLARIFICATIONS_EN_RU.md) define methods, limits and submission. The supplied transport, launcher, validator and public cases are retained. The [interactive lesson](https://rzhaniya.github.io/daa-assignment-4-archive/) and [ungraded practice](https://rzhaniya.github.io/daa-assignment-4-archive/practice.html) were reviewed through their checked-in public sources docs/content.js, docs/app.js and docs/practice-content.js. Preparation notes summarize concepts without copying the answer key or claiming an owner practice attempt. No assessed quiz was accessed.

OpenAI Codex generated implementation, independent tests, benchmark, documentation, preparation notes and CI, then executed the reported runs/measurements. Separate Codex agents cross-reviewed implementation modules, tests and benchmark using independent exhaustive small oracles and closed-form scale cases; these are AI-assisted checks rather than human review. Recorded outputs came from actual Java execution and timings from actual timer measurements. No claim is made that the owner personally authored or independently verified AI-generated work. Assistance is disclosed for assessment under the syllabus; no external algorithm library replaced a required method.
