# Defence preparation

This study guide is derived from the official public lesson, its eight bounded interactive models and the ungraded practice. It summarizes concepts in original wording; it is not a practice-attempt record or a copy of the answer key. No assessed quiz was opened or attempted.

Read the [bilingual lesson](https://rzhaniya.github.io/daa-assignment-4-archive/) and try the [ungraded practice](https://rzhaniya.github.io/daa-assignment-4-archive/practice.html). Predict a small result before revealing its explanation, then explain one boundary case and one tempting wrong approach aloud.

## Eight mental checks

1. **LCS.** Define `dp[i][j]` for two prefixes. A match extends the diagonal; a mismatch drops one final character. Backtrack through optimal transitions and reverse the collected characters. Can you verify the returned sequence in both inputs without requiring contiguity? Different tie choices can be equally optimal.

2. **Adjacent merges.** Define the cheapest way to collapse original interval `[l,r]`. Every final merge has a split `k`; pay both child costs plus the interval sum. Can each output triple merge two blocks that currently exist? Emit children before their parent and retain original indices. Arbitrary smallest-block greedy choices can violate adjacency.

3. **Tree independent set.** `take[u]` adds the vertex weight and each child's skip state; `skip[u]` adds each child's better state. Process children first. During reconstruction, a chosen parent forces its child to be skipped. Why can the empty set beat every vertex? Zero-weight ties need not produce identical sets; use exact long totals and iterative traversal.

4. **Naive search.** Test starts through `n-m`, inclusive, using literal comparisons. Move by one after a match to retain overlaps. What happens for an empty pattern, empty text or a longer pattern? The empty pattern has `n+1` boundary matches.

5. **KMP.** Define `pi[i]` as the longest proper prefix that is also a suffix. On mismatch, shorten the matched prefix through `pi[j-1]`; never move the text index backward. After a full match, use prefix fallback again. Which already-matched suffix can begin the next overlapping occurrence?

6. **Exact Rabin–Karp.** Use ASCII codes, base 31 and modulus 101, with the highest power on the left. Remove the outgoing contribution, normalize the remainder, shift and add the incoming character. Equal hashes require character verification. Can unequal windows share a hash? Handle empty/oversized patterns before creating a window.

7. **Suffix array and LCP.** Doubling compares pairs of prefix ranks; missing second halves rank below real characters. Kasai reuses the previous common-prefix length, decreasing it by at most one. Check that `sa` contains exactly the original nonempty suffix starts: an internal sentinel must not leak. Why does maximum adjacent LCP reveal a longest repeat, even with overlaps?

8. **Aho–Corasick.** A failure link points to the longest proper suffix that is also a trie prefix. Aggregate state visits in reverse failure-BFS order so suffix patterns count too. Duplicate dictionary entries share a terminal but keep separate output columns. Reset visits and automaton state for each text. Dense matches require aggregation rather than enumerating every occurrence.

## Explain complexity precisely

Separate auxiliary storage from input and output; emitting `z` starts costs at least `O(z)`. Prefix LCS permits quadratic space, merge DP cubic time/quadratic space, and tree DP linear time/space. KMP is `O(n+m+z+1)`. RK uses `O(n+m+c*m)` for nonempty windows, where `c` counts equal-hash candidates; collision verification prevents a deterministic linear worst-case claim. Radix doubling is `O(n log(n+1))`, Kasai linear. With 95 ASCII characters, Aho construction is `O(L+95S+p)` and each text costs `O(|text|+S+p)` using propagation.

The [assessed Moodle defence](https://lms.astanait.edu.kz/mod/quiz/view.php?id=95271) is separate and must be completed independently, without AI or external assistance. Consult Moodle itself for the current rules and availability.
