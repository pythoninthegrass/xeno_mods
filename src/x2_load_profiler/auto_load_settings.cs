using System.Collections.Generic;

namespace X2LoadProfiler {

    // Parsed key=value request to queue a save load at the main menu; an unset save means no auto-load
    public sealed class AutoLoadSettings {

        public string? SavePath { get; private set; }
        public bool Reseed { get; private set; } = true;
        public List<string> Rejected { get; } = new List<string>();

        public static AutoLoadSettings Parse(string text) {
            var s = new AutoLoadSettings();
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

        public string Describe() {
            return SavePath == null ? "none" : $"save={SavePath} reseed={Reseed.ToString().ToLowerInvariant()}";
        }

        private bool Apply(string key, string value) {
            switch (key) {
                case "save":
                    if (value.Length == 0) {
                        return false;
                    }
                    SavePath = value;
                    return true;
                case "reseed":
                    if (!bool.TryParse(value, out bool b)) {
                        return false;
                    }
                    Reseed = b;
                    return true;
                default:
                    return false;
            }
        }
    }

}
