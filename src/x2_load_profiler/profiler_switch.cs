namespace X2LoadProfiler {

    // Opt-in switch for the profiling patches; the load fix does not consult it
    public static class ProfilerSwitch {

        public static bool Enabled { get; set; }

        public static bool Parse(string? text) {
            return text != null && bool.TryParse(text.Trim(), out bool on) && on;
        }
    }

}
