using System;
using System.Collections.Generic;
using System.Linq;

namespace X2LoadProfiler {

    public static class AssetKeep {

        // Kinds whose loads never request other assets, so keeping one cannot leave a dependent asset behind
        private static readonly HashSet<string> LeafKinds = new HashSet<string> { "Sprite", "AudioClip" };

        public static bool IsLeafKind(string? typeName) {
            return typeName != null && LeafKinds.Contains(typeName);
        }

        // Splits the previous screen's assets into those to keep loaded (requested again by the target and keepable) and the rest (unload)
        public static (List<T> Keep, List<T> Unload) Split<T>(IEnumerable<T> previous, IEnumerable<T> wanted, IEqualityComparer<T> comparer, Func<T, bool>? isKeepable = null) {
            var wantedSet = new HashSet<T>(wanted, comparer);
            var lookup = previous.ToLookup(item => wantedSet.Contains(item) && (isKeepable == null || isKeepable(item)));
            return (lookup[true].ToList(), lookup[false].ToList());
        }
    }

    // Opt-in via transfer_keep.txt in the mod folder; parsing is shared with the profiler switch
    public static class AssetKeepSwitch {

        public static bool Enabled { get; set; }

        public static bool Parse(string? text) {
            return ProfilerSwitch.Parse(text);
        }
    }

}
