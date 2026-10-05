using System;
using System.Globalization;

namespace X2LoadProfiler {

    // Cap on concurrent asset bundle file loads; 0 means unlimited, matching the game's own convention
    public static class BundleConcurrency {

        public const int DefaultCap = 200;

        public static int ParseCap(string? text, int defaultCap) {
            if (text != null && int.TryParse(text.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out int cap) && cap >= 0) {
                return cap;
            }
            return defaultCap;
        }

        // The mod only raises the game's cap, never lowers it
        public static int EffectiveCap(int gameCap, int modCap) {
            if (gameCap == 0 || modCap == 0) {
                return 0;
            }
            return Math.Max(gameCap, modCap);
        }

        public static bool CanStart(int filesLoading, int cap) {
            return cap == 0 || filesLoading < cap;
        }
    }

}
