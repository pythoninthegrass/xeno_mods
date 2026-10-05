using System.Diagnostics;
using System.Reflection;
using Artitas.Utils;
using Common.Content;
using Common.Content.Managers;
using HarmonyLib;
using log4net;

namespace X2LoadProfiler {

    [HarmonyPatch(typeof(ContentManager), "UpdateTasks")]
    public static class UpdateTasksPatch {

        private static readonly ILog Log = ArtitasLogger.GetLogger(MethodBase.GetCurrentMethod()!.DeclaringType);

        private static readonly UpdateTasksStats Stats = new UpdateTasksStats(Stopwatch.Frequency);

        [HarmonyPrefix]
        public static void Prefix(Bag<IAssetTask> ____processingTasks) {
            Stats.BeginFrame(Stopwatch.GetTimestamp(), ____processingTasks.Count);
        }

        [HarmonyPostfix]
        public static void Postfix(Bag<IAssetTask> ____processingTasks, Bag<IAssetTask> ____pendingTasks) {
            if (!Stats.EndFrame(Stopwatch.GetTimestamp(), ____processingTasks.Count, ____pendingTasks.Count)) {
                return;
            }

            var s = Stats.Last;
            var b = BundleLoadTracker.Stats.TakeSnapshot(BundleLoadTracker.InFlight);
            Log.Warn($"[X2LoadProfiler] frames={s.Frames} updateMs={s.UpdateMs:F1} processing={s.Processing} pending={s.Pending} completed={s.Completed} wallMsPerFrame={s.WallMsPerFrame:F1} bundleStarted={b.Started} bundleDone={b.Completed} bundleInFlight={b.InFlight} bundleBlockedPolls={b.BlockedPolls} bundleMeanMs={b.MeanLatencyMs:F0} bundleMaxMs={b.MaxLatencyMs:F0}");
        }
    }

}
