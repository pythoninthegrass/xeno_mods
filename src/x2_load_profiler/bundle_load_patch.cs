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

        // First frame at which AssetBundleRequest.progress was above zero while the load was still running
        public static readonly Dictionary<AssetBundleFileLoadOperation, (long Ticks, float Value)> FirstProgress = new Dictionary<AssetBundleFileLoadOperation, (long, float)>();

        private static readonly FieldInfo FilesLoading = AccessTools.Field(typeof(AssetBundleFileLoadOperation), "_filesLoading");

        // Read once per window, so the boxing cost is negligible
        public static int InFlight => (int)FilesLoading.GetValue(null);
    }

    public static class BundleCanStartPatch {

        [HarmonyPostfix]
        public static void Postfix(bool __result) {
            if (!__result) {
                BundleLoadTracker.Stats.RecordBlockedPoll();
            }
        }
    }

    public static class BundleStartPatch {

        [HarmonyPostfix]
        public static void Postfix(AssetBundleFileLoadOperation __instance) {
            BundleLoadTracker.Stats.RecordStart();
            BundleLoadTracker.StartTimes[__instance] = Stopwatch.GetTimestamp();
        }
    }

    public static class BundleUpdatePatch {

        private static readonly ILog Log = ArtitasLogger.GetLogger(MethodBase.GetCurrentMethod()!.DeclaringType);

        [HarmonyPostfix]
        public static void Postfix(AssetBundleFileLoadOperation __instance, bool __result, Descriptor ____descriptor) {
            if (!__result) {
                if (BundleCapture.Enabled) {
                    float progress = __instance.Progress();
                    if (progress > 0f) {
                        BundleLoadTracker.FirstProgress.TryAdd(__instance, (Stopwatch.GetTimestamp(), progress));
                    }
                }
                return;
            }
            if (!BundleLoadTracker.StartTimes.Remove(__instance, out long startTicks)) {
                return;
            }

            long latencyTicks = Stopwatch.GetTimestamp() - startTicks;
            BundleLoadTracker.Stats.RecordDone(latencyTicks);
            if (BundleCapture.Enabled) {
                RecordCapture(__instance, ____descriptor, startTicks, latencyTicks);
            }
            if (BundleLoadTracker.Stats.IsSlow(latencyTicks)) {
                Log.Warn($"[X2LoadProfiler] SlowBundle ms={latencyTicks * 1000.0 / Stopwatch.Frequency:F0} type={____descriptor.Type?.Name} asset={____descriptor}");
            }
        }

        private static void RecordCapture(AssetBundleFileLoadOperation op, Descriptor descriptor, long startTicks, long latencyTicks) {
            double msPerTick = 1000.0 / Stopwatch.Frequency;
            double queueMs = BundleCapture.RequestTimes.Remove(op, out long requestTicks) ? (startTicks - requestTicks) * msPerTick : 0.0;
            BundleCapture.Parents.Remove(descriptor, out string? parent);
            double? progressMs = null;
            float? progressValue = null;
            if (BundleLoadTracker.FirstProgress.Remove(op, out var first)) {
                progressMs = (Stopwatch.GetTimestamp() - first.Ticks) * msPerTick;
                progressValue = first.Value;
            }
            var handle = descriptor.FileHandle;
            BundleCapture.Add(BundleRecord.LoadLine(BundleCapture.NextSequence(), System.DateTime.Now, queueMs, latencyTicks * msPerTick,
                descriptor.Type?.Name, handle?.RelativePath, handle?.assetBundleName, handle?.contentPackPath, parent, progressMs, progressValue));
        }
    }

}
