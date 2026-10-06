using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;

namespace X2LoadProfiler {

    // Parsed NAME=value overrides for the Constants.Optimizing tunables that are swept from the mod
    public sealed class OptimizingExperiment {

        public const string CmFrameLoadBudget = "CM_FRAME_LOAD_BUDGET";
        public const string PromiseHandlingBudget = "PROMISE_HANDLING_BUDGET";
        public const string StrategyInitializeFrameBudget = "STRATEGY_INITIALIZE_FRAME_BUDGET";

        private static readonly string[] KnownNames = { CmFrameLoadBudget, PromiseHandlingBudget, StrategyInitializeFrameBudget };

        public Dictionary<string, long> Values { get; } = new Dictionary<string, long>();
        public List<string> Rejected { get; } = new List<string>();

        // Set by the lifecycle; read by the UpdateTasks prefix
        public static long? ForcedCmFrameLoadBudget;

        public static OptimizingExperiment Parse(string text) {
            var e = new OptimizingExperiment();
            foreach (string raw in text.Split('\n')) {
                string line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("#")) {
                    continue;
                }
                int eq = line.IndexOf('=');
                string name = eq < 0 ? "" : line.Substring(0, eq).Trim();
                string value = eq < 0 ? "" : line.Substring(eq + 1).Trim();
                if (Array.IndexOf(KnownNames, name) < 0
                    || !long.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out long parsed)
                    || parsed < 0) {
                    e.Rejected.Add(line);
                    continue;
                }
                e.Values[name] = parsed;
            }
            return e;
        }

        public long? Get(string name) {
            return Values.TryGetValue(name, out long v) ? v : (long?)null;
        }

        public string Describe() {
            return Values.Count == 0 ? "none" : string.Join(" ", Values.OrderBy(kv => kv.Key).Select(kv => $"{kv.Key}={kv.Value}"));
        }
    }

}
