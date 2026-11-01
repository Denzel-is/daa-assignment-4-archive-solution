import java.util.*;

/** Prefix, interval and tree dynamic programming with local state for each request. */
public final class DynamicProgramming {
    private DynamicProgramming() {}

    /** Prefix LCS lengths followed by one optimal backtrack through the table. */
    static Map<String, Object> lcs(Map<String, Object> input) {
        String a = (String) input.get("a");
        String b = (String) input.get("b");
        int n = a.length(), m = b.length();
        int[][] length = new int[n + 1][m + 1];
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                if (a.charAt(i - 1) == b.charAt(j - 1)) {
                    length[i][j] = length[i - 1][j - 1] + 1;
                } else {
                    length[i][j] = Math.max(length[i - 1][j], length[i][j - 1]);
                }
            }
        }
        StringBuilder sequence = new StringBuilder(length[n][m]);
        int i = n, j = m;
        while (i > 0 && j > 0) {
            if (a.charAt(i - 1) == b.charAt(j - 1)) {
                sequence.append(a.charAt(i - 1));
                i--;
                j--;
            } else if (length[i - 1][j] >= length[i][j - 1]) {
                i--;
            } else {
                j--;
            }
        }
        return Map.of("length", length[n][m], "sequence", sequence.reverse().toString());
    }

    /** Last-split interval DP; child intervals are merged before their parent. */
    static Map<String, Object> merge(Map<String, Object> input) {
        List<?> sizes = (List<?>) input.get("sizes");
        int n = sizes.size();
        if (n <= 1) return Map.of("cost", 0L, "plan", new int[0][]);

        long[] prefix = new long[n + 1];
        for (int i = 0; i < n; i++) {
            prefix[i + 1] = prefix[i] + ((Number) sizes.get(i)).longValue();
        }
        long[][] cost = new long[n][n];
        int[][] split = new int[n][n];
        for (int length = 2; length <= n; length++) {
            for (int left = 0; left + length <= n; left++) {
                int right = left + length - 1;
                long sum = prefix[right + 1] - prefix[left];
                long best = Long.MAX_VALUE;
                for (int middle = left; middle < right; middle++) {
                    long candidate = cost[left][middle] + cost[middle + 1][right] + sum;
                    if (candidate < best) {
                        best = candidate;
                        split[left][right] = middle;
                    }
                }
                cost[left][right] = best;
            }
        }

        int[][] plan = new int[n - 1][3];
        int next = 0;
        // Frame: left, right, stage. Stage 1 emits only after both child frames.
        Deque<int[]> stack = new ArrayDeque<>();
        stack.push(new int[]{0, n - 1, 0});
        while (!stack.isEmpty()) {
            int[] frame = stack.pop();
            int left = frame[0], right = frame[1];
            if (left == right) continue;
            int middle = split[left][right];
            if (frame[2] == 1) {
                plan[next++] = new int[]{left, middle, right};
            } else {
                stack.push(new int[]{left, right, 1});
                stack.push(new int[]{middle + 1, right, 0});
                stack.push(new int[]{left, middle, 0});
            }
        }
        return Map.of("cost", cost[0][n - 1], "plan", plan);
    }

    /** Iterative take/skip MWIS, including reconstruction on a 100000-vertex chain. */
    static Map<String, Object> tree(Map<String, Object> input) {
        int n = ((Number) input.get("n")).intValue();
        if (n == 0) return Map.of("weight", 0L, "selected", new int[0]);
        List<?> weights = (List<?>) input.get("weights");
        List<?> edges = (List<?>) input.get("edges");

        int[] offset = new int[n + 1];
        for (Object row : edges) {
            List<?> edge = (List<?>) row;
            offset[((Number) edge.get(0)).intValue() + 1]++;
            offset[((Number) edge.get(1)).intValue() + 1]++;
        }
        for (int vertex = 0; vertex < n; vertex++) offset[vertex + 1] += offset[vertex];
        int[] neighbor = new int[offset[n]];
        int[] next = Arrays.copyOf(offset, n);
        for (Object row : edges) {
            List<?> edge = (List<?>) row;
            int u = ((Number) edge.get(0)).intValue();
            int v = ((Number) edge.get(1)).intValue();
            neighbor[next[u]++] = v;
            neighbor[next[v]++] = u;
        }

        int[] parent = new int[n];
        int[] order = new int[n];
        parent[0] = -1;
        order[0] = 0;
        int count = 1;
        // On a tree, excluding the parent visits each child exactly once.
        for (int index = 0; index < n; index++) {
            int vertex = order[index];
            for (int position = offset[vertex]; position < offset[vertex + 1]; position++) {
                int child = neighbor[position];
                if (child != parent[vertex]) {
                    parent[child] = vertex;
                    order[count++] = child;
                }
            }
        }

        long[] take = new long[n];
        long[] skip = new long[n];
        for (int vertex = 0; vertex < n; vertex++) {
            take[vertex] = ((Number) weights.get(vertex)).longValue();
        }
        // Reverse parent-before-child order is a valid bottom-up tree order.
        for (int index = n - 1; index > 0; index--) {
            int vertex = order[index], ancestor = parent[vertex];
            take[ancestor] += skip[vertex];
            skip[ancestor] += Math.max(take[vertex], skip[vertex]);
        }

        boolean[] chosen = new boolean[n];
        int[] selected = new int[n];
        int selectedCount = 0;
        for (int vertex : order) {
            // Skipping ties also avoids selecting zero-weight vertices unnecessarily.
            if ((parent[vertex] == -1 || !chosen[parent[vertex]]) && take[vertex] > skip[vertex]) {
                chosen[vertex] = true;
                selected[selectedCount++] = vertex;
            }
        }
        return Map.of("weight", Math.max(take[0], skip[0]),
                      "selected", Arrays.copyOf(selected, selectedCount));
    }
}
