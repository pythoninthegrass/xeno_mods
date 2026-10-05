using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Artitas;
using Common.Content;
using Common.Modding;
using HarmonyLib;

namespace X2LoadTiming {

    public class X2LoadTimingLifecycle : IModLifecycle {

        private const string MarkersFileName = "markers.txt";

        public void Create(Mod mod, Harmony patcher) {
            Markers.Path = Path.Combine(mod.ContentPack, MarkersFileName);
        }

        public void Destroy() { }

        public void OnWorldCreate(IModLifecycle.Section section, WeakReference<World> world) { }

        public IEnumerable<Descriptor> GetRequiredAssets(IModLifecycle.Section section) {
            return Enumerable.Empty<Descriptor>();
        }

        public void OnWorldDispose(IModLifecycle.Section section, WeakReference<World> world) { }
    }

    public static class Markers {

        public static string? Path;

        public static void Mark(string message) {
            MarkerLog.Append(Path, DateTime.Now, message);
        }
    }

}
