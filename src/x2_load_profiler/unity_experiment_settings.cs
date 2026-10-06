using System.Collections.Generic;
using System.Globalization;

namespace X2LoadProfiler {

    // Parsed key=value overrides for Unity async loading settings; unset keys stay null
    public sealed class UnityExperimentSettings {

        public string? BackgroundLoadingPriority { get; private set; }
        public int? AsyncUploadTimeSlice { get; private set; }
        public int? AsyncUploadBufferSize { get; private set; }
        public bool? AsyncUploadPersistentBuffer { get; private set; }
        public int? VSyncCount { get; private set; }
        public int? TargetFrameRate { get; private set; }
        public List<string> Rejected { get; } = new List<string>();

        public static UnityExperimentSettings Parse(string text) {
            var s = new UnityExperimentSettings();
            foreach (string raw in text.Split('\n')) {
                string line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("#")) {
                    continue;
                }
                int eq = line.IndexOf('=');
                if (eq < 0 || !s.Apply(line.Substring(0, eq).Trim(), line.Substring(eq + 1).Trim())) {
                    s.Rejected.Add(line);
                }
            }
            return s;
        }

        // The value a setter should store: the experiment's when one is set, otherwise what the game asked for
        public static T Resolve<T>(T requested, T? forced) where T : struct {
            return forced ?? requested;
        }

        public string Describe() {
            var parts = new List<string>();
            if (BackgroundLoadingPriority != null) {
                parts.Add($"backgroundLoadingPriority={BackgroundLoadingPriority}");
            }
            if (AsyncUploadTimeSlice != null) {
                parts.Add($"asyncUploadTimeSlice={AsyncUploadTimeSlice}");
            }
            if (AsyncUploadBufferSize != null) {
                parts.Add($"asyncUploadBufferSize={AsyncUploadBufferSize}");
            }
            if (AsyncUploadPersistentBuffer != null) {
                parts.Add($"asyncUploadPersistentBuffer={AsyncUploadPersistentBuffer.ToString().ToLowerInvariant()}");
            }
            if (VSyncCount != null) {
                parts.Add($"vSyncCount={VSyncCount}");
            }
            if (TargetFrameRate != null) {
                parts.Add($"targetFrameRate={TargetFrameRate}");
            }
            return parts.Count == 0 ? "none" : string.Join(" ", parts);
        }

        private bool Apply(string key, string value) {
            switch (key) {
                case "backgroundLoadingPriority":
                    BackgroundLoadingPriority = value;
                    return value.Length > 0;
                case "asyncUploadTimeSlice":
                    return TryInt(value, v => AsyncUploadTimeSlice = v);
                case "asyncUploadBufferSize":
                    return TryInt(value, v => AsyncUploadBufferSize = v);
                case "vSyncCount":
                    return TryInt(value, v => VSyncCount = v);
                case "targetFrameRate":
                    return TryInt(value, v => TargetFrameRate = v);
                case "asyncUploadPersistentBuffer":
                    if (!bool.TryParse(value, out bool b)) {
                        return false;
                    }
                    AsyncUploadPersistentBuffer = b;
                    return true;
                default:
                    return false;
            }
        }

        private static bool TryInt(string value, System.Action<int> set) {
            if (!int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int v)) {
                return false;
            }
            set(v);
            return true;
        }
    }

}
