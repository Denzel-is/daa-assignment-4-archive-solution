import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/** Exact ASCII string algorithms. Mutable state belongs to one request only. */
final class StringAlgorithms {
    private StringAlgorithms() {}

    private static String string(Map<String, Object> input, String key) {
        return (String) input.get(key);
    }

    /** The empty pattern occurs at every boundary, including after the last character. */
    private static Map<String, Object> boundaries(int length) {
        List<Integer> positions = new ArrayList<>(length + 1);
        for (int start = 0; start <= length; start++) positions.add(start);
        return Map.of("positions", positions);
    }

    /** Literal comparisons, with every possible start tested independently. */
    static Map<String, Object> naive(Map<String, Object> input) {
        String text = string(input, "text"), pattern = string(input, "pattern");
        int n = text.length(), m = pattern.length();
        if (m == 0) return boundaries(n);
        List<Integer> positions = new ArrayList<>();
        for (int start = 0; start <= n - m; start++) {
            int matched = 0;
            while (matched < m && text.charAt(start + matched) == pattern.charAt(matched)) matched++;
            if (matched == m) positions.add(start);
        }
        return Map.of("positions", positions);
    }

    /** Prefix-function KMP; fallback after a match keeps overlapping occurrences. */
    static Map<String, Object> kmp(Map<String, Object> input) {
        String text = string(input, "text"), pattern = string(input, "pattern");
        int n = text.length(), m = pattern.length();
        if (m == 0) return boundaries(n);
        List<Integer> positions = new ArrayList<>();
        if (m > n) return Map.of("positions", positions);
        int[] prefix = new int[m];
        for (int i = 1; i < m; i++) {
            int matched = prefix[i - 1];
            while (matched > 0 && pattern.charAt(i) != pattern.charAt(matched)) {
                matched = prefix[matched - 1];
            }
            if (pattern.charAt(i) == pattern.charAt(matched)) matched++;
            prefix[i] = matched;
        }
        int matched = 0;
        for (int i = 0; i < n; i++) {
            while (matched > 0 && text.charAt(i) != pattern.charAt(matched)) {
                matched = prefix[matched - 1];
            }
            if (text.charAt(i) == pattern.charAt(matched)) matched++;
            if (matched == m) {
                positions.add(i - m + 1);
                matched = prefix[matched - 1];
            }
        }
        return Map.of("positions", positions);
    }

    /** Base-31/mod-101 highest-left rolling hash, followed by exact collision checks. */
    static Map<String, Object> rk(Map<String, Object> input) {
        String text = string(input, "text"), pattern = string(input, "pattern");
        int n = text.length(), m = pattern.length();
        if (m == 0) return boundaries(n);
        List<Integer> positions = new ArrayList<>();
        if (m > n) return Map.of("positions", positions);
        final long base = 31, modulus = 101;
        long highestPower = 1, patternHash = 0, windowHash = 0;
        for (int i = 0; i < m; i++) {
            if (i > 0) highestPower = highestPower * base % modulus;
            patternHash = (patternHash * base + pattern.charAt(i)) % modulus;
            windowHash = (windowHash * base + text.charAt(i)) % modulus;
        }
        for (int start = 0; start <= n - m; start++) {
            if (windowHash == patternHash) {
                int matched = 0;
                while (matched < m && text.charAt(start + matched) == pattern.charAt(matched)) matched++;
                if (matched == m) positions.add(start);
            }
            if (start < n - m) {
                windowHash = (windowHash - text.charAt(start) * highestPower) % modulus;
                if (windowHash < 0) windowHash += modulus;
                windowHash = (windowHash * base + text.charAt(start + m)) % modulus;
            }
        }
        return Map.of("positions", positions);
    }

    /** Stable counting sort on one member of a suffix rank pair; rank 0 is end-of-text. */
    private static void countingSort(int[] source, int[] destination, int[] rank,
                                     int shift, int classes, int[] counts) {
        Arrays.fill(counts, 0, classes + 1, 0);
        for (int suffix : source) {
            int key = suffix + shift < rank.length ? rank[suffix + shift] : 0;
            counts[key]++;
        }
        for (int key = 1; key <= classes; key++) counts[key] += counts[key - 1];
        for (int i = source.length - 1; i >= 0; i--) {
            int suffix = source[i];
            int key = suffix + shift < rank.length ? rank[suffix + shift] : 0;
            destination[--counts[key]] = suffix;
        }
    }

    /** Radix-sorted prefix doubling and linear Kasai LCP; no suffix strings or sentinel. */
    static Map<String, Object> suffix(Map<String, Object> input) {
        String text = string(input, "text");
        int n = text.length();
        int[] sa = new int[n], lcp = new int[n];
        if (n == 0) return Map.of("sa", sa, "lcp", lcp, "repeated", "");
        int[] rank = new int[n], nextRank = new int[n], temporary = new int[n];
        int[] counts = new int[Math.max(n + 1, 96)];
        for (int i = 0; i < n; i++) {
            sa[i] = i;
            rank[i] = text.charAt(i) - 31; // Printable ASCII gives positive ranks 1..95.
        }
        int classes = 95;
        for (int width = 1; width < n; width *= 2) {
            countingSort(sa, temporary, rank, width, classes, counts);
            countingSort(temporary, sa, rank, 0, classes, counts);
            int newClasses = 1;
            nextRank[sa[0]] = newClasses;
            for (int i = 1; i < n; i++) {
                int previous = sa[i - 1], current = sa[i];
                int previousSecond = previous + width < n ? rank[previous + width] : 0;
                int currentSecond = current + width < n ? rank[current + width] : 0;
                if (rank[previous] != rank[current] || previousSecond != currentSecond) newClasses++;
                nextRank[current] = newClasses;
            }
            int[] swap = rank;
            rank = nextRank;
            nextRank = swap;
            classes = newClasses;
            if (classes == n) break;
        }
        // Reuse the rank storage as the inverse suffix array for Kasai.
        for (int i = 0; i < n; i++) rank[sa[i]] = i;
        int common = 0, longest = 0, repeatedStart = 0;
        for (int start = 0; start < n; start++) {
            int position = rank[start];
            if (position == 0) {
                common = 0;
                continue;
            }
            int previous = sa[position - 1];
            while (start + common < n && previous + common < n
                    && text.charAt(start + common) == text.charAt(previous + common)) common++;
            lcp[position] = common;
            if (common > longest) {
                longest = common;
                repeatedStart = start;
            }
            if (common > 0) common--;
        }
        return Map.of("sa", sa, "lcp", lcp,
                "repeated", text.substring(repeatedStart, repeatedStart + longest));
    }

    /** Dense rows grow with actual trie states, rather than duplicate pattern length. */
    private static final class Trie {
        static final int ALPHABET = 95;
        int[] next = new int[16 * ALPHABET];
        int states = 1;

        int extend(int state, int character) {
            int position = state * ALPHABET + character;
            int child = next[position];
            if (child == 0) {
                if (states == next.length / ALPHABET) next = Arrays.copyOf(next, next.length * 2);
                child = states++;
                next[position] = child;
            }
            return child;
        }
    }

    /** Failure automaton with reverse-BFS visit propagation, including duplicate terminals. */
    static Map<String, Object> aho(Map<String, Object> input) {
        List<?> patterns = (List<?>) input.get("patterns"), texts = (List<?>) input.get("texts");
        int p = patterns.size(), q = texts.size();
        long[][] counts = new long[q][p];
        if (p == 0 || q == 0) return Map.of("counts", counts);
        Trie trie = new Trie();
        int[] terminal = new int[p];
        for (int index = 0; index < p; index++) {
            String pattern = (String) patterns.get(index);
            int state = 0;
            for (int i = 0; i < pattern.length(); i++) state = trie.extend(state, pattern.charAt(i) - 32);
            terminal[index] = state;
        }
        int[] failure = new int[trie.states], queue = new int[trie.states];
        int head = 0, tail = 0;
        for (int character = 0; character < Trie.ALPHABET; character++) {
            int child = trie.next[character];
            if (child != 0) queue[tail++] = child;
        }
        while (head < tail) {
            int state = queue[head++];
            int row = state * Trie.ALPHABET, fallbackRow = failure[state] * Trie.ALPHABET;
            for (int character = 0; character < Trie.ALPHABET; character++) {
                int child = trie.next[row + character];
                if (child != 0) {
                    failure[child] = trie.next[fallbackRow + character];
                    queue[tail++] = child;
                } else {
                    trie.next[row + character] = trie.next[fallbackRow + character];
                }
            }
        }
        for (int index = 0; index < q; index++) {
            String text = (String) texts.get(index);
            long[] visits = new long[trie.states];
            int state = 0;
            for (int i = 0; i < text.length(); i++) {
                state = trie.next[state * Trie.ALPHABET + text.charAt(i) - 32];
                visits[state]++;
            }
            for (int i = tail - 1; i >= 0; i--) {
                int vertex = queue[i];
                visits[failure[vertex]] += visits[vertex];
            }
            for (int pattern = 0; pattern < p; pattern++) counts[index][pattern] = visits[terminal[pattern]];
        }
        return Map.of("counts", counts);
    }
}
