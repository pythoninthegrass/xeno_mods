using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Artitas;
using Artitas.Utils;
using Common.Content;
using Common.Modding;
using HarmonyLib;
using log4net;

namespace X2LoadProfiler {

    public class X2LoadProfilerLifecycle : IModLifecycle {

        private static readonly ILog Log = ArtitasLogger.GetLogger(MethodBase.GetCurrentMethod()!.DeclaringType);

        public void Create(Mod mod, Harmony patcher) {
            Log.Warn("[X2LoadProfiler] Loaded");
        }

        public void Destroy() {
            Log.Warn("[X2LoadProfiler] Destroyed");
        }

        public void OnWorldCreate(IModLifecycle.Section section, WeakReference<World> world) { }

        public IEnumerable<Descriptor> GetRequiredAssets(IModLifecycle.Section section) {
            return Enumerable.Empty<Descriptor>();
        }

        public void OnWorldDispose(IModLifecycle.Section section, WeakReference<World> world) { }
    }

}
