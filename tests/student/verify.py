"""Independent A4 semantic tests, generated full-limit inputs and actual evidence.

Run: python tests/student/verify.py
Only small inputs use exhaustive oracles. Large structured cases have proved
closed-form optima; large suffix results are checked without storing suffixes.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import random
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEED = 40431026
SEARCHES = ("naive", "kmp", "rk")


def compact(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def integer(value):
    return type(value) is int and -(1 << 63) <= value < (1 << 63)


def integer_list(value):
    return type(value) is list and all(integer(v) for v in value)


def subsequence(sequence, text):
    position = 0
    for character in text:
        if position < len(sequence) and sequence[position] == character:
            position += 1
    return position == len(sequence)


def direct_positions(text, pattern):
    """Independent C-library substring lookup, preserving overlapping starts."""
    if not pattern:
        return list(range(len(text) + 1))
    result = []
    start = text.find(pattern)
    while start >= 0:
        result.append(start)
        start = text.find(pattern, start + 1)
    return result


@lru_cache(maxsize=None)
def adjacent_merge_cost(sizes):
    """Enumerate the possible next adjacent operations, rather than interval DP."""
    if len(sizes) < 2:
        return 0
    return min(sizes[i] + sizes[i + 1] + adjacent_merge_cost(
        sizes[:i] + (sizes[i] + sizes[i + 1],) + sizes[i + 2:])
        for i in range(len(sizes) - 1))


def direct_suffix(text):
    """Small inputs only: explicitly sort suffix strings and compare characters."""
    sa = sorted(range(len(text)), key=lambda start: text[start:])
    lcp = [0] * len(text)
    for i in range(1, len(sa)):
        a, b = sa[i - 1], sa[i]
        length = 0
        while a + length < len(text) and b + length < len(text) and text[a + length] == text[b + length]:
            length += 1
        lcp[i] = length
    return {"sa": sa, "lcp": lcp, "repeated_length": max(lcp, default=0)}


def oracle(request):
    """Create small expected values without calling the submitted Java code."""
    task = request["task"]
    if task == "ping":
        return {"status": "ready"}
    if task == "lcs":
        a, b = request["a"], request["b"]
        if len(a) > len(b):
            a, b = b, a
        optimum = 0
        for mask in range(1 << len(a)):
            if mask.bit_count() <= optimum:
                continue
            candidate = "".join(a[i] for i in range(len(a)) if mask & (1 << i))
            if subsequence(candidate, b):
                optimum = len(candidate)
        return {"length": optimum}
    if task == "merge":
        return {"cost": adjacent_merge_cost(tuple(request["sizes"]))}
    if task == "tree":
        n, edges, weights = request["n"], request["edges"], request["weights"]
        optimum = 0
        for mask in range(1 << n):
            if all(not ((mask >> a) & 1 and (mask >> b) & 1) for a, b in edges):
                optimum = max(optimum, sum(weights[i] for i in range(n) if (mask >> i) & 1))
        return {"weight": optimum}
    if task in SEARCHES:
        return {"positions": direct_positions(request["text"], request["pattern"])}
    if task == "suffix":
        return direct_suffix(request["text"])
    return {"counts": [[len(direct_positions(text, pattern)) for pattern in request["patterns"]]
                       for text in request["texts"]]}


def validate_suffix_large(text, answer, expected):
    """Exact suffix order from inverse-tail ranks, then independent direct LCP.

    For unary/periodic fixtures expected SA/LCP is closed form. On the fixed
    high-alphabet random fixture, direct adjacent comparisons have small total
    work; no suffix substrings are materialized by this checker.
    """
    sa, lcp = answer["sa"], answer["lcp"]
    n = len(text)
    assert len(sa) == len(lcp) == n
    assert len(set(sa)) == n and all(0 <= start < n for start in sa)
    if "sa" in expected:
        assert sa == expected["sa"] and lcp == expected["lcp"]
    else:
        rank = [0] * (n + 1)
        rank[n] = -1
        for position, start in enumerate(sa):
            rank[start] = position
        previous = None
        for start in sa:
            key = (text[start], rank[start + 1])
            assert previous is None or previous < key
            previous = key
        # Ranking shorter tails before/after each other correctly certifies
        # whole suffix order by induction on suffix length.
        assert not n or lcp[0] == 0
        for i in range(1, n):
            a, b = sa[i - 1], sa[i]
            length = 0
            while a + length < n and b + length < n and text[a + length] == text[b + length]:
                length += 1
            assert lcp[i] == length
    return max(lcp, default=0)


def validate(request, answer, expected):
    """Validate optimum values and witnesses, accepting non-unique optima."""
    try:
        assert type(answer) is dict
        task = request["task"]
        if task == "ping":
            return answer.get("status") == "ready"
        if task == "lcs":
            length, sequence = answer["length"], answer["sequence"]
            return (integer(length) and type(sequence) is str and
                    length == expected["length"] == len(sequence) and
                    subsequence(sequence, request["a"]) and subsequence(sequence, request["b"]))
        if task == "merge":
            cost, plan = answer["cost"], answer["plan"]
            assert integer(cost) and type(plan) is list and cost == expected["cost"]
            sizes = request["sizes"]
            blocks = [(i, i) for i in range(len(sizes))]
            prefix = [0]
            for size in sizes:
                prefix.append(prefix[-1] + size)
            paid = 0
            assert len(plan) == max(0, len(sizes) - 1)
            for merge in plan:
                assert integer_list(merge) and len(merge) == 3
                left, split, right = merge
                assert 0 <= left <= split < right < len(sizes)
                index = blocks.index((left, split))
                assert index + 1 < len(blocks) and blocks[index + 1] == (split + 1, right)
                blocks[index:index + 2] = [(left, right)]
                paid += prefix[right + 1] - prefix[left]
            return paid == cost and len(blocks) <= 1
        if task == "tree":
            weight, selected = answer["weight"], answer["selected"]
            assert integer(weight) and integer_list(selected)
            chosen = set(selected)
            return (len(chosen) == len(selected) and all(0 <= v < request["n"] for v in chosen)
                    and not any(a in chosen and b in chosen for a, b in request["edges"])
                    and sum(request["weights"][v] for v in chosen) == weight == expected["weight"])
        if task in SEARCHES:
            return integer_list(answer["positions"]) and answer["positions"] == expected["positions"]
        if task == "suffix":
            assert integer_list(answer["sa"]) and integer_list(answer["lcp"])
            assert type(answer["repeated"]) is str
            text = request["text"]
            if expected.get("large"):
                length = validate_suffix_large(text, answer, expected)
            else:
                assert answer["sa"] == expected["sa"] and answer["lcp"] == expected["lcp"]
                length = expected["repeated_length"]
            repeated = answer["repeated"]
            return len(repeated) == length and (not repeated or len(direct_positions(text, repeated)) >= 2)
        counts = answer["counts"]
        return (type(counts) is list and len(counts) == len(request["texts"])
                and all(integer_list(row) and len(row) == len(request["patterns"])
                        and all(v >= 0 for v in row) for row in counts)
                and counts == expected["counts"])
    except (AssertionError, KeyError, IndexError, TypeError, ValueError):
        return False


def named_cases():
    cases = []
    def add(name, request, reason):
        cases.append({"name": name, "input": request, "expected": oracle(request), "reason": reason})
    add("ping", {"task": "ping"}, "Supplied JSONL transport answers ready.")
    for name, a, b, reason in [
        ("both_empty", "", "", "Empty sequences have no common character."),
        ("left_empty", "", "abc", "An empty input permits only the empty subsequence."),
        ("right_empty", "abc", "", "The other empty-input direction also has optimum zero."),
        ("subsequence_not_substring", "tea_time", "team", "team appears in order, although its m is separated."),
        ("alternative_optima", "ab", "ba", "Both a and b are optimal length-one sequences."),
        ("repeated_characters", "aabaac", "abaca", "Exhaustive subsets of the shorter input establish the optimum."),
        ("spaces_case_punctuation", "A !a?", "!A a?", "Spaces, punctuation and case participate as ordinary characters.")]:
        add("lcs_" + name, {"task": "lcs", "a": a, "b": b}, reason)
    for name, sizes, reason in [
        ("empty", [], "No merges and zero cost."),
        ("single", [1000000000], "One block is already complete, so no cost is paid."),
        ("zero_ties", [0, 0, 0, 0], "Every chronological adjacent plan has cost zero."),
        ("two", [2, 3], "The only merge costs 5."),
        ("alternatives", [1, 1, 1], "Either adjacent pair costs 2 first, then 3, total 5."),
        ("adjacency_matters", [1, 100, 1], "Only adjacent pairs may be merged: 101 then 102 gives 203."),
        ("64bit", [1000000000] * 4, "Two balanced pair merges cost 2e9 each, then 4e9: 8e9 total."),
        ("asymmetric", [7, 0, 2, 9, 1], "Enumerating every possible next adjacent merge supplies an independent optimum.")]:
        add("merge_" + name, {"task": "merge", "sizes": sizes}, reason)
    for name, weights, edges, reason in [
        ("empty", [], [], "The empty tree permits the empty selected set."),
        ("one_negative", [-1], [], "The empty set beats a negative singleton."),
        ("one_positive", [1000000000], [], "The singleton itself has optimum 1e9."),
        ("one_zero", [0], [], "Either selecting or skipping the zero vertex is optimal."),
        ("all_negative", [-4, -1, -7, -2], [[0,1],[1,2],[1,3]], "The empty set has value zero and beats every nonempty set."),
        ("tie", [1, 1], [[0,1]], "Either endpoint alone is an optimum of weight one."),
        ("chain", [4,9,6], [[0,1],[1,2]], "Endpoints contribute 10, beating the middle vertex's 9."),
        ("64bit_star", [1000000000] * 5, [[0,1],[0,2],[0,3],[0,4]], "All four leaves are compatible and total 4e9.")]:
        add("tree_" + name, {"task": "tree", "n": len(weights), "weights": weights, "edges": edges}, reason)
    search_pairs = [
        ("both_empty", "", "", "An empty pattern matches the sole empty-text boundary 0."),
        ("empty_pattern", "A !", "", "Empty pattern matches all four boundaries 0..3."),
        ("empty_text", "", "a", "A nonempty pattern cannot occur in an empty text."),
        ("longer", "ab", "abc", "Pattern length exceeds text length."),
        ("overlap", "aaaaa", "aaa", "All three overlapping starts 0,1,2 count."),
        ("fallback", "ababababa", "ababa", "The overlapping starts are 0,2,4."),
        ("case_spaces_punctuation", "A!? a!? A!? ", "A!? ", "Case-sensitive matches begin at 0 and 8."),
        ("collision", "abdj", "ab", "ab and dj share hash 75 modulo 101, but only start 0 matches."),
        ("negative_rolling_remainder", "~       ab~ab", "ab", "High outgoing ASCII values exercise normalized rolling subtraction; starts are 8 and 11.")]
    for name, text, pattern, reason in search_pairs:
        for task in SEARCHES:
            add(task + "_" + name, {"task": task, "text": text, "pattern": pattern}, reason)
    for name, text, reason in [
        ("empty", "", "No nonempty suffixes or repeats exist."),
        ("one", "?", "Only suffix 0, with LCP zero and no repeat."),
        ("distinct", "A!z~", "Distinct first characters determine every suffix order; every LCP is zero."),
        ("unary", "aaaaaa", "Shortest suffix first; adjacent LCPs are 0,1,2,3,4,5 and overlap is allowed."),
        ("banana", "banana", "Direct suffix strings give SA 5,3,1,0,4,2 and maximum LCP 3."),
        ("tied_repeats", "ababcdcd", "ab and cd are both longest repeated substrings of length two."),
        ("spaces_case", " A! A? A!", "Printable ASCII order includes spaces and punctuation.")]:
        add("suffix_" + name, {"task":"suffix","text":text}, reason)
    for name, patterns, texts, reason in [
        ("no_dictionary", [], ["abc", "", "abc"], "Retain an empty count row for each independent text."),
        ("no_texts", ["a", "ab"], [], "With no queries the result is an empty outer array."),
        ("empty_both", [], [], "Both dictionary and texts are empty."),
        ("suffix_duplicates_reset", ["he", "she", "he", "e"], ["sheshe", "sheshe", ""], "Each entry occurs twice in each repeated text, then zero in the empty text."),
        ("dense_overlap", ["a", "aa", "aaa", "aa"], ["aaaaa", "aa", "a"], "At length five the counts are 5,4,3,4; overlap and duplicate terminals both count."),
        ("no_cross_text_match", ["ab", "a", "b"], ["a", "b", "ab", ""], "State must reset: independent a and b texts cannot create an ab match."),
        ("case_punctuation", ["A!", "a!", "!", " "], ["A! a!A!", " A! "], "Direct exact substring searches count each case-sensitive dictionary entry.")]:
        add("aho_" + name, {"task":"aho","patterns":patterns,"texts":texts}, reason)
    return cases


def random_cases():
    rng = random.Random(SEED)
    alphabet = "abA !?"
    def word(maximum):
        return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, maximum)))
    cases = []
    for trial in range(40):
        n = rng.randint(0, 11)
        requests = [
            {"task":"lcs","a":word(10),"b":word(10)},
            {"task":"merge","sizes":[rng.randint(0, 12) for _ in range(rng.randint(0, 7))]},
            {"task":"tree","n":n,"weights":[rng.randint(-7, 9) for _ in range(n)],
             "edges":[[v, rng.randrange(v)] for v in range(1, n)]}]
        text, pattern = word(35), word(8)
        requests += [{"task":task,"text":text,"pattern":pattern} for task in SEARCHES]
        requests.append({"task":"suffix","text":word(40)})
        patterns = [word(4) or "!" for _ in range(rng.randint(0, 9))]
        requests.append({"task":"aho","patterns":patterns,
                         "texts":[word(25) for _ in range(rng.randint(0, 5))]})
        for request in requests:
            cases.append({"name":f"seed_{SEED}_trial_{trial}_{request['task']}",
                          "input":request,"expected":oracle(request)})
    return cases


def witness_regressions():
    results = []
    def exercise(task, request, valid, invalid):
        expected = oracle(request)
        assert all(validate(request, answer, expected) for answer in valid), task + " valid rejected"
        assert all(not validate(request, answer, expected) for answer in invalid), task + " false witness accepted"
        results.append({"task":task,"alternative_valid_accepted":len(valid),"invalid_rejected":len(invalid)})
    exercise("lcs", {"task":"lcs","a":"ab","b":"ba"},
        [{"length":1,"sequence":"a"},{"length":1,"sequence":"b"},
         {"length":1,"sequence":"a","error":"optional extra fields are ignored"}],
        [{"length":2,"sequence":"ab"},{"length":1,"sequence":"c"},{"length":True,"sequence":"a"}])
    exercise("merge", {"task":"merge","sizes":[1,1,1]},
        [{"cost":5,"plan":[[0,0,1],[0,1,2]]},{"cost":5,"plan":[[1,1,2],[0,0,2]]}],
        [{"cost":5,"plan":[[0,1,2],[0,0,1]]},{"cost":5,"plan":[[0,0,2],[1,1,2]]},
         {"cost":4,"plan":[[0,0,1],[0,1,2]]},{"cost":5,"plan":[[0,0,1]]}])
    exercise("tree", {"task":"tree","n":2,"weights":[1,1],"edges":[[0,1]]},
        [{"weight":1,"selected":[0]},{"weight":1,"selected":[1]}],
        [{"weight":2,"selected":[0,1]},{"weight":1,"selected":[0,0]},
         {"weight":1,"selected":[2]},{"weight":0,"selected":[]}])
    request = {"task":"suffix","text":"ababcdcd"}
    exact = oracle(request)
    common = {"sa":exact["sa"],"lcp":exact["lcp"]}
    exercise("suffix", request,
        [{**common,"repeated":"ab"},{**common,"repeated":"cd"}],
        [{**common,"repeated":"ef"},{**common,"repeated":"aba"},
         {**common,"sa":list(reversed(exact["sa"])),"repeated":"ab"},
         {**common,"lcp":[0] * 8,"repeated":"ab"}])
    for task in SEARCHES:
        exercise(task, {"task":task,"text":"aaaa","pattern":"aa"},
            [{"positions":[0,1,2]}],
            [{"positions":[0,2]},{"positions":[0,1,1,2]},{"positions":[2,1,0]}])
    exercise("aho", {"task":"aho","patterns":["a","aa","a"],"texts":["aaa",""]},
        [{"counts":[[3,2,3],[0,0,0]]}],
        [{"counts":[[3,1,3],[0,0,0]]},{"counts":[[3,2],[0,0]]},
         {"counts":[[3,2,3],[3,2,3]]}])
    return results


def full_limit_cases():
    yield "lcs_1000x1000_tied", {"task":"lcs","a":"ab" * 500,"b":"ba" * 500}, {"length":999}
    yield "lcs_1000x1000_disjoint", {"task":"lcs","a":"a" * 1000,"b":"b" * 1000}, {"length":0}
    yield "lcs_empty_by_1000", {"task":"lcs","a":"","b":"a" * 1000}, {"length":0}
    # A complete ordered binary merge tree has 56 leaves at depth 7 and 144 at 8.
    yield "merge_200_billion_blocks", {"task":"merge","sizes":[1000000000] * 200}, {"cost":1544000000000}
    yield "merge_200_zero_blocks", {"task":"merge","sizes":[0] * 200}, {"cost":0}
    n = 100000
    chain = [[v - 1, v] for v in range(1, n)]
    yield "tree_100000_deep_chain", {"task":"tree","n":n,"weights":[1000000000] * n,"edges":chain}, {"weight":50000000000000}
    yield "tree_100000_negative_chain", {"task":"tree","n":n,"weights":[-1000000000] * n,"edges":chain}, {"weight":0}
    yield "tree_100000_zero_ties", {"task":"tree","n":n,"weights":[0] * n,"edges":chain}, {"weight":0}
    yield "tree_100000_star", {"task":"tree","n":n,"weights":[1000000000] * n,
                                "edges":[[0,v] for v in range(1,n)]}, {"weight":99999000000000}
    search_cases = [
        ("naive_3000_equal", "naive", "a" * 3000, "a" * 3000),
        ("naive_3000_near_mismatch", "naive", "a" * 3000, "a" * 1499 + "b"),
        ("naive_3000_empty", "naive", "a" * 3000, ""),
        ("kmp_200000_by_100000", "kmp", "ab" * 100000, "ab" * 50000),
        ("kmp_200000_empty", "kmp", "a" * 200000, ""),
        ("kmp_200000_near_mismatch", "kmp", "a" * 200000, "a" * 99999 + "b"),
        ("rk_10000_by_2000_dense", "rk", "a" * 10000, "a" * 2000),
        ("rk_10000_by_2000_collision", "rk", "a" * 9998 + "dj", "a" * 1998 + "ab"),
        ("rk_pattern_length_10000", "rk", "a" * 2000, "a" * 10000),
        ("rk_10000_empty", "rk", "a" * 10000, "")]
    for name, task, text, pattern in search_cases:
        # The full alternating KMP fixture has a closed-form answer. Repeated
        # built-in search of its 100000-character pattern would waste billions
        # of character comparisons in the checker, outside the Java timer.
        positions = (list(range(0,100001,2)) if name == "kmp_200000_by_100000"
                     else direct_positions(text,pattern))
        yield name, {"task":task,"text":text,"pattern":pattern}, {"positions":positions}
    n = 50000
    unary = {"task":"suffix","text":"a" * n}
    yield "suffix_50000_unary", unary, {"large":True,"sa":list(range(n - 1,-1,-1)),"lcp":list(range(n))}
    periodic = {"task":"suffix","text":"ab" * (n // 2)}
    sa = list(range(n - 2,-1,-2)) + list(range(n - 1,0,-2))
    lcp = [0] + list(range(2,n,2)) + [0] + list(range(1,n - 1,2))
    yield "suffix_50000_periodic", periodic, {"large":True,"sa":sa,"lcp":lcp}
    rng = random.Random(SEED + 1)
    text = "".join(chr(rng.randrange(32,127)) for _ in range(n))
    yield "suffix_50000_printable_random", {"task":"suffix","text":text}, {"large":True}
    # p=10000, L=100000 exactly, q=100, total text length=200000, output=1m counts.
    patterns = ["a" * (1 + (i % 19)) for i in range(10000)]
    patterns[-1] += "a" * (100000 - sum(map(len,patterns)))
    texts = ["a" * 2000 if i % 2 == 0 else "a" * 1999 + "b" for i in range(100)]
    counts = [[max(0,(2000 if i % 2 == 0 else 1999) - len(pattern) + 1)
               for pattern in patterns] for i in range(100)]
    assert len(patterns) == 10000 and sum(map(len,patterns)) == 100000
    yield "aho_dense_duplicates_suffixes_1m_counts", {"task":"aho","patterns":patterns,"texts":texts}, {"counts":counts}
    # Combine a deep trie with thousands of duplicate shallow terminal IDs.
    # Copying inherited output lists at every state would require roughly
    # 90000*9999 entries; terminal sharing plus failure propagation stays linear.
    patterns = ["a"] * 9999 + ["a" * 90001]
    yield "aho_deep_trie_duplicate_shallow_terminals", {"task":"aho","patterns":patterns,
        "texts":["a" * 200000]}, {"counts":[[200000] * 9999 + [110000]]}
    # One length-100000 pattern creates 100001 trie states. Each of 100 texts
    # is shorter than it, so all 100 answers are independently known to be zero.
    pattern = "a" * 99999 + "b"
    yield "aho_100001_states_100_texts", {"task":"aho","patterns":[pattern],
        "texts":["a" * 2000 for _ in range(100)]}, {"counts":[[0] for _ in range(100)]}
    yield "aho_100_empty_dictionary_rows", {"task":"aho","patterns":[],
        "texts":["a" * 2000 for _ in range(100)]}, {"counts":[[] for _ in range(100)]}


def dimensions(request):
    task = request["task"]
    if task == "lcs":
        return {"a_length":len(request["a"]),"b_length":len(request["b"])}
    if task == "merge":
        return {"blocks":len(request["sizes"]),"max_block":max(request["sizes"],default=0)}
    if task == "tree":
        return {"vertices":request["n"],"edges":len(request["edges"])}
    if task in SEARCHES:
        return {"text_length":len(request["text"]),"pattern_length":len(request["pattern"]),
                "length_product":len(request["text"]) * len(request["pattern"])}
    if task == "suffix":
        return {"text_length":len(request["text"])}
    return {"patterns":len(request["patterns"]),"total_pattern_length":sum(map(len,request["patterns"])),
            "texts":len(request["texts"]),"total_text_length":sum(map(len,request["texts"])),
            "output_count_entries":len(request["patterns"]) * len(request["texts"])}


def run(command, requests):
    data = "".join(compact(request) + "\n" for request in requests)
    start = time.perf_counter()
    result = subprocess.run(command, input=data, text=True, encoding="utf-8", capture_output=True,
                            timeout=20, check=True)
    elapsed = time.perf_counter() - start
    lines = result.stdout.splitlines()
    assert len(lines) == len(requests), f"expected {len(requests)} output lines, received {len(lines)}"
    assert len(result.stdout.encode()) <= 8 * 1024 * 1024, "batch output exceeds official 8 MiB bound"
    answers = [json.loads(line) for line in lines]
    return answers, {"seconds_including_JVM_JSON_IO":round(elapsed,6),
                     "input_sha256":hashlib.sha256(data.encode()).hexdigest(),
                     "output_sha256":hashlib.sha256(result.stdout.encode()).hexdigest(),
                     "stdout_bytes":len(result.stdout.encode())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--small-only", action="store_true", help="skip generated full-limit cases")
    args = parser.parse_args()
    build = ROOT / "Java" / "build"
    build.mkdir(exist_ok=True)
    sources = sorted((ROOT / "Java" / "source").glob("*.java"))
    subprocess.run(["javac","--release","17","-encoding","UTF-8","-d",str(build),
                    *map(str,sources)], check=True, timeout=60)
    command = ["java","-Xmx384m","-cp",str(build),"Main"]
    named, seeded = named_cases(), random_cases()
    (HERE / "my_cases.jsonl").write_text("".join(compact(c["input"]) + "\n" for c in named),encoding="utf-8")
    save(HERE / "expected.json",named)
    mixed = (named + seeded) * 2
    answers, mixed_evidence = run(command,[c["input"] for c in mixed])
    for case, answer in zip(mixed,answers):
        assert validate(case["input"],answer,case["expected"]), (case["name"],case["input"],answer,case["expected"])
    (HERE / "actual.jsonl").write_text("".join(compact(a) + "\n" for a in answers[:len(named)]),encoding="utf-8")
    regressions = witness_regressions()
    print(f"PASS {len(named)} named + {len(seeded)} seeded independent-oracle cases, repeated twice ({len(mixed)} requests)",flush=True)
    print("PASS checker alternatives and false-witness regressions",flush=True)
    scale = []
    if not args.small_only:
        reset = {"task":"aho","patterns":["a","aa","a"],"texts":["aa",""]}
        reset_expected = {"counts":[[2,1,2],[0,0,0]]}
        for name, request, expected in full_limit_cases():
            answers, evidence = run(command,[request,{"task":"ping"},reset])
            assert validate(request,answers[0],expected), name
            assert answers[1] == {"status":"ready"} and answers[2] == reset_expected, name + " state reset"
            scale.append({"name":name,"task":request["task"],"dimensions":dimensions(request),
                          "result":"PASS",**evidence})
            print("PASS " + name,flush=True)
    evidence = {"status":"PASS","seed":SEED,"named_cases":len(named),"seeded_oracle_cases":len(seeded),
                "mixed_requests":len(mixed),"mixed_batch":mixed_evidence,
                "witness_regressions":regressions,"full_limit_cases":scale,
                "java_heap":"384 MiB","batch_timeout_seconds":20,"stdout_limit_bytes":8 * 1024 * 1024,
                "compile_command":"javac --release 17 -encoding UTF-8 -d Java/build Java/source/*.java",
                "command":"python tests/student/verify.py"}
    save(HERE / ("verification_small.json" if args.small_only else "verification.json"),evidence)
    print("PASS own A4 verification complete",flush=True)


if __name__ == "__main__":
    main()
