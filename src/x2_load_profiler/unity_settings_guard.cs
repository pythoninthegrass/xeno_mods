using System;
using HarmonyLib;
using Common.Content.Managers;
using UnityEngine;

namespace X2LoadProfiler {

    // Holds experiment values against the game's own writes. Patching the Unity setters themselves does not work (the original
    // setter never runs, so no value is stored), so the values are compared and re-applied once per UpdateTasks frame instead.
    public static class UnitySettingsGuard {

        public static UnityExperimentSettings Forced = new UnityExperimentSettings();

        public static Action<string>? Trace;

        private static string last = "";

        public static void Apply(Harmony patcher, UnityExperimentSettings forced, Action<string>? trace) {
            Forced = forced;
            Trace = trace;
            patcher.Patch(AccessTools.Method(typeof(ContentManager), "UpdateTasks"), postfix: new HarmonyMethod(AccessTools.Method(typeof(UnitySettingsGuard), nameof(Tick))));
        }

        public static void Tick() {
            ThreadPriority priority = Enum.TryParse(Forced.BackgroundLoadingPriority, out ThreadPriority p) ? p : Application.backgroundLoadingPriority;
            Hold(Application.backgroundLoadingPriority, priority, v => Application.backgroundLoadingPriority = v);
            Hold(Application.targetFrameRate, UnityExperimentSettings.Resolve(Application.targetFrameRate, Forced.TargetFrameRate), v => Application.targetFrameRate = v);
            Hold(QualitySettings.asyncUploadTimeSlice, UnityExperimentSettings.Resolve(QualitySettings.asyncUploadTimeSlice, Forced.AsyncUploadTimeSlice), v => QualitySettings.asyncUploadTimeSlice = v);
            Hold(QualitySettings.asyncUploadBufferSize, UnityExperimentSettings.Resolve(QualitySettings.asyncUploadBufferSize, Forced.AsyncUploadBufferSize), v => QualitySettings.asyncUploadBufferSize = v);
            Hold(QualitySettings.asyncUploadPersistentBuffer, UnityExperimentSettings.Resolve(QualitySettings.asyncUploadPersistentBuffer, Forced.AsyncUploadPersistentBuffer), v => QualitySettings.asyncUploadPersistentBuffer = v);
            Hold(QualitySettings.vSyncCount, UnityExperimentSettings.Resolve(QualitySettings.vSyncCount, Forced.VSyncCount), v => QualitySettings.vSyncCount = v);
            if (Trace != null) {
                string now = Describe();
                if (now != last) {
                    last = now;
                    Trace($"UnitySettings frame {now}");
                }
            }
        }

        public static string Describe() {
            return $"backgroundLoadingPriority={Application.backgroundLoadingPriority} asyncUploadTimeSlice={QualitySettings.asyncUploadTimeSlice} asyncUploadBufferSize={QualitySettings.asyncUploadBufferSize} asyncUploadPersistentBuffer={QualitySettings.asyncUploadPersistentBuffer} targetFrameRate={Application.targetFrameRate} vSyncCount={QualitySettings.vSyncCount}";
        }

        private static void Hold<T>(T current, T wanted, Action<T> set) where T : struct {
            if (!current.Equals(wanted)) {
                set(wanted);
            }
        }
    }

}
