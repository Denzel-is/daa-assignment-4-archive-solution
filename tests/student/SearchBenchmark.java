import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.*;

/** Same-input comparison; all correctness checking lies outside measured intervals. */
public final class SearchBenchmark {
    private static final long SEED = 20261031L;
    private static final int WARMUPS = 20;
    private static final int SAMPLES = 5;
    private static final int CALLS_PER_SAMPLE = 30;
    private static volatile long consumed;

    private static Map<String,Object> input(String family, int n, int m) {
        if (family.equals("random")) {
            Random random = new Random(SEED + n);
            char[] text = new char[n], pattern = new char[m];
            for (int i = 0; i < n; i++) text[i] = (char) ('a' + random.nextInt(26));
            for (int i = 0; i < m; i++) pattern[i] = (char) ('a' + random.nextInt(26));
            // Two planted occurrences; independent exhaustive checking finds ALL starts.
            System.arraycopy(pattern, 0, text, n / 4, m);
            System.arraycopy(pattern, 0, text, 3 * n / 4, m);
            return Map.of("text", new String(text), "pattern", new String(pattern));
        }
        String pattern = family.equals("repetitive_mismatch")
                ? "a".repeat(m - 1) + "b" : "a".repeat(m);
        return Map.of("text", "a".repeat(n), "pattern", pattern);
    }

    private static List<Integer> oracle(Map<String,Object> input) {
        String text = (String) input.get("text"), pattern = (String) input.get("pattern");
        List<Integer> expected = new ArrayList<>();
        for (int i = 0; i <= text.length() - pattern.length(); i++) {
            boolean match = true;
            for (int j = 0; j < pattern.length(); j++) {
                if (text.charAt(i+j) != pattern.charAt(j)) { match = false; break; }
            }
            if (match) expected.add(i);
        }
        return expected;
    }

    private static Map<String,Object> call(int method, Map<String,Object> input) {
        return switch (method) {
            case 0 -> Algorithms.naive(input);
            case 1 -> Algorithms.kmp(input);
            default -> Algorithms.rk(input);
        };
    }

    private static void verify(Map<String,Object> result, List<Integer> expected) {
        Object value = result.get("positions");
        int size = value instanceof List<?> list ? list.size() : java.lang.reflect.Array.getLength(value);
        if (size != expected.size()) throw new AssertionError("Wrong occurrence count");
        for (int i = 0; i < size; i++) {
            Object item = value instanceof List<?> list ? list.get(i) : java.lang.reflect.Array.get(value,i);
            if (((Number) item).intValue() != expected.get(i)) throw new AssertionError("Wrong start");
        }
    }

    private static void consume(Map<String,Object> result) {
        Object value = result.get("positions");
        consumed += value instanceof List<?> list ? list.size() : java.lang.reflect.Array.getLength(value);
    }

    /** Independently recompute candidate count to interpret the deliberately small hash. */
    private static int equalHashCandidates(Map<String,Object> input) {
        String text = (String) input.get("text"), pattern = (String) input.get("pattern");
        int wanted = 0;
        for (int j = 0; j < pattern.length(); j++) wanted = (wanted * 31 + pattern.charAt(j)) % 101;
        int candidates = 0;
        for (int i = 0; i <= text.length() - pattern.length(); i++) {
            int hash = 0;
            for (int j = 0; j < pattern.length(); j++) hash = (hash * 31 + text.charAt(i+j)) % 101;
            if (hash == wanted) candidates++;
        }
        return candidates;
    }

    public static void main(String[] args) throws Exception {
        String[] methods = {"naive", "kmp", "rk"};
        List<Object> rows = new ArrayList<>();
        for (String family : new String[]{"random", "repetitive_mismatch", "repetitive_matches"}) {
            for (int[] shape : new int[][]{{500,50},{1500,150},{3000,300}}) {
                Map<String,Object> input = input(family, shape[0], shape[1]);
                List<Integer> expected = oracle(input);
                for (int method = 0; method < methods.length; method++) verify(call(method,input),expected);
                for (int round = 0; round < WARMUPS; round++) {
                    for (int offset = 0; offset < 3; offset++) {
                        int method = (round + offset) % 3;
                        Map<String,Object> result = call(method,input);
                        consume(result);
                        verify(result,expected);
                    }
                }
                double[][] times = new double[3][SAMPLES];
                double[][] sampleTotals = new double[3][SAMPLES];
                for (int sample = 0; sample < SAMPLES; sample++) {
                    for (int offset = 0; offset < 3; offset++) {
                        int method = (sample + offset) % 3;
                        List<Map<String,Object>> results = new ArrayList<>(CALLS_PER_SAMPLE);
                        long start = System.nanoTime();
                        for (int invocation = 0; invocation < CALLS_PER_SAMPLE; invocation++) {
                            Map<String,Object> result = call(method,input);
                            consume(result);
                            results.add(result);
                        }
                        long elapsed = System.nanoTime() - start;
                        sampleTotals[method][sample] = elapsed / 1_000_000.0;
                        times[method][sample] = elapsed / 1_000_000.0 / CALLS_PER_SAMPLE;
                        for (Map<String,Object> result : results) verify(result,expected);
                    }
                }
                Map<String,Object> row = new LinkedHashMap<>();
                row.put("family",family); row.put("n",shape[0]); row.put("m",shape[1]);
                row.put("seed",SEED+shape[0]); row.put("occurrences",expected.size());
                row.put("equal_hash_candidates",equalHashCandidates(input));
                row.put("all_outputs_checked",true);
                for (int method = 0; method < 3; method++) {
                    row.put(methods[method]+"_sample_totals_ms",sampleTotals[method]);
                    row.put(methods[method]+"_ms",times[method]);
                    double[] ordered = times[method].clone(); Arrays.sort(ordered);
                    row.put(methods[method]+"_median_ms",ordered[SAMPLES/2]);
                }
                rows.add(row);
            }
        }
        // A collision is a correctness laboratory, independent of timing medians.
        Map<String,Object> collision = Map.of("text","abdj","pattern","ab");
        for (int method = 0; method < 3; method++) verify(call(method,collision),List.of(0));
        Map<String,Object> environment = new LinkedHashMap<>();
        environment.put("java_runtime",System.getProperty("java.runtime.version"));
        environment.put("java_vm",System.getProperty("java.vm.name"));
        environment.put("java_vendor",System.getProperty("java.vendor"));
        environment.put("os",System.getProperty("os.name")+" "+System.getProperty("os.version"));
        environment.put("architecture",System.getProperty("os.arch"));
        environment.put("processor",System.getenv("PROCESSOR_IDENTIFIER"));
        environment.put("logical_processors",Runtime.getRuntime().availableProcessors());
        environment.put("max_heap_bytes",Runtime.getRuntime().maxMemory());
        Map<String,Object> report = new LinkedHashMap<>();
        report.put("measured_at_utc",Instant.now().toString()); report.put("environment",environment);
        report.put("base_seed",SEED); report.put("warmup_calls_per_method_per_input",WARMUPS);
        report.put("samples_per_method_per_input",SAMPLES); report.put("calls_per_sample",CALLS_PER_SAMPLE);
        report.put("timer","System.nanoTime; ms per call = sample duration / 30");
        report.put("timing_boundary","30 complete Algorithms calls on the same immutable Map, each including result allocation, volatile occurrence-count consumption and saving its result reference in a preallocated list. Excludes compilation, JVM startup, generation, parsing, correctness/candidate checks and I/O. Normal JIT/GC remains; no explicit GC. Methods rotate first position each round/sample.");
        report.put("random_generator","java.util.Random(base_seed+n), independent uniform a..z text/pattern, then plant pattern at n/4 and 3n/4; n/m=(500/50,1500/150,3000/300)");
        report.put("repetitive_generator","text=a^n; mismatch pattern=a^(m-1)b; dense-match pattern=a^m");
        report.put("correctness","Independent exhaustive character oracle before timing and every warm-up; all 30 retained results from every timing sample verified after stopping the timer. Three methods agree. RK collision ab/dj both hash75 but only ab reports.");
        report.put("measurements",rows); report.put("consumed",consumed);
        Path output = Path.of(args.length==0 ? "tests/student/benchmark_results.json" : args[0]);
        Files.writeString(output,Json.write(report)+System.lineSeparator(),StandardCharsets.UTF_8);
        System.out.println("PASS search comparison; wrote "+output);
    }
}
