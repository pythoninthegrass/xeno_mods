using System;

namespace X2LoadProfiler {

    // One line per profiler window; the same text goes to the game log and to profile.txt
    public static class ProfileLine {

        public static string Format(UpdateTasksSnapshot s, BundleLoadSnapshot b) {
            return FormattableString.Invariant($"[X2LoadProfiler] frames={s.Frames} updateMs={s.UpdateMs:F1} processing={s.Processing} pending={s.Pending} completed={s.Completed} wallMsPerFrame={s.WallMsPerFrame:F1} bundleStarted={b.Started} bundleDone={b.Completed} bundleInFlight={b.InFlight} bundleBlockedPolls={b.BlockedPolls} bundleMeanMs={b.MeanLatencyMs:F0} bundleMaxMs={b.MaxLatencyMs:F0}");
        }
    }

}
