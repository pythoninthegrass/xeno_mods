using System;
using System.Diagnostics;
using System.Reflection;
using Artitas.Utils;
using Common.Content;
using Common.Content.Managers;
using HarmonyLib;
using log4net;
using X2LoadTiming;

namespace X2LoadProfiler {

    public static class UpdateTasksPatch {

        private static readonly ILog Log = ArtitasLogger.GetLogger(MethodBase.GetCurrentMethod()!.DeclaringType);

        // Set when the profiler is on; keeps the per-second lines available at log levels that drop WARN
        public static string? ProfilePath;

        private static readonly UpdateTasksStats Stats = new UpdateTasksStats(Stopwatch.Frequency);

        [HarmonyPrefix]
        public static void Prefix(Bag<IAssetTask> ____processingTasks) {
            Stats.BeginFrame(Stopwatch.GetTimestamp(), ____processingTasks.Count);
        }

        [HarmonyPostfix]
        public static void Postfix(Bag<IAssetTask> ____processingTasks, Bag<IAssetTask> ____pendingTasks) {
            BundleCapture.Flush();
            if (!Stats.EndFrame(Stopwatch.GetTimestamp(), ____processingTasks.Count, ____pendingTasks.Count)) {
                return;
            }

            var s = Stats.Last;
            var b = BundleLoadTracker.Stats.TakeSnapshot(BundleLoadTracker.InFlight);
            string line = ProfileLine.Format(s, b);
            Log.Warn(line);
            MarkerLog.Append(ProfilePath, DateTime.Now, line);
        }
    }

}
