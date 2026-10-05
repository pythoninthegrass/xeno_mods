using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using Common.Content.AsyncOperations;
using Artitas.Utils;
using Common.Content;
using HarmonyLib;
using log4net;

namespace X2LoadProfiler {

    public static class BundleLoadTracker {

        public static readonly BundleLoadStats Stats = new BundleLoadStats(Stopwatch.Frequency);

        public static readonly Dictionary<AssetBundleFileLoadOperation, long> StartTimes = new Dictionary<AssetBundleFileLoadOperation, long>();

        private static readonly FieldInfo FilesLoading = AccessTools.Field(typeof(AssetBundleFileLoadOperation), "_filesLoading");

        // Read once per window, so the boxing cost is negligible
        public static int InFlight => (int)FilesLoading.GetValue(null);
    }

    [HarmonyPatch(typeof(AssetBundleFileLoadOperation), nameof(AssetBundleFileLoadOperation.CanStart))]
    public static class BundleCanStartPatch {

        [HarmonyPostfix]
        public static void Postfix(bool __result) {
            if (!__result) {
                BundleLoadTracker.Stats.RecordBlockedPoll();
            }
        }
    }

    [HarmonyPatch(typeof(AssetBundleFileLoadOperation), nameof(AssetBundleFileLoadOperation.Start))]
    public static class BundleStartPatch {

        [HarmonyPostfix]
        public static void Postfix(AssetBundleFileLoadOperation __instance) {
            BundleLoadTracker.Stats.RecordStart();
            BundleLoadTracker.StartTimes[__instance] = Stopwatch.GetTimestamp();
        }
    }

    [HarmonyPatch(typeof(AssetBundleFileLoadOperation), nameof(AssetBundleFileLoadOperation.Update))]
    public static class BundleUpdatePatch {

        private static readonly ILog Log = ArtitasLogger.GetLogger(MethodBase.GetCurrentMethod()!.DeclaringType);

        [HarmonyPostfix]
        public static void Postfix(AssetBundleFileLoadOperation __instance, bool __result, Descriptor ____descriptor) {
            if (!__result || !BundleLoadTracker.StartTimes.Remove(__instance, out long startTicks)) {
                return;
            }

            long latencyTicks = Stopwatch.GetTimestamp() - startTicks;
            BundleLoadTracker.Stats.RecordDone(latencyTicks);
            if (BundleLoadTracker.Stats.IsSlow(latencyTicks)) {
                Log.Warn($"[X2LoadProfiler] SlowBundle ms={latencyTicks * 1000.0 / Stopwatch.Frequency:F0} type={____descriptor.Type?.Name} asset={____descriptor}");
            }
        }
    }

}
