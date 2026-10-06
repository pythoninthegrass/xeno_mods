using System;
using System.Diagnostics;
using System.Linq;
using HarmonyLib;
using UnityEngine;

namespace X2LoadProfiler {

    // Holds experiment values against the game's own writes and traces every write with its caller
    public static class UnitySettingsGuard {

        public static UnityExperimentSettings Forced = new UnityExperimentSettings();

        public static Action<string>? Trace;

        public static void Apply(Harmony patcher, UnityExperimentSettings forced, Action<string>? trace) {
            Forced = forced;
            Trace = trace;
            Hook(patcher, AccessTools.PropertySetter(typeof(Application), nameof(Application.backgroundLoadingPriority)), nameof(BackgroundLoadingPriority));
            Hook(patcher, AccessTools.PropertySetter(typeof(Application), nameof(Application.targetFrameRate)), nameof(TargetFrameRate));
            Hook(patcher, AccessTools.PropertySetter(typeof(QualitySettings), nameof(QualitySettings.asyncUploadTimeSlice)), nameof(AsyncUploadTimeSlice));
            Hook(patcher, AccessTools.PropertySetter(typeof(QualitySettings), nameof(QualitySettings.asyncUploadBufferSize)), nameof(AsyncUploadBufferSize));
            Hook(patcher, AccessTools.PropertySetter(typeof(QualitySettings), nameof(QualitySettings.asyncUploadPersistentBuffer)), nameof(AsyncUploadPersistentBuffer));
            Hook(patcher, AccessTools.PropertySetter(typeof(QualitySettings), nameof(QualitySettings.vSyncCount)), nameof(VSyncCount));
        }

        public static void BackgroundLoadingPriority(ref ThreadPriority value) {
            ThreadPriority forced = Enum.TryParse(Forced.BackgroundLoadingPriority, out ThreadPriority p) ? p : value;
            Record("backgroundLoadingPriority", value, ref value, forced);
        }

        public static void TargetFrameRate(ref int value) {
            Record("targetFrameRate", value, ref value, UnityExperimentSettings.Resolve(value, Forced.TargetFrameRate));
        }

        public static void AsyncUploadTimeSlice(ref int value) {
            Record("asyncUploadTimeSlice", value, ref value, UnityExperimentSettings.Resolve(value, Forced.AsyncUploadTimeSlice));
        }

        public static void AsyncUploadBufferSize(ref int value) {
            Record("asyncUploadBufferSize", value, ref value, UnityExperimentSettings.Resolve(value, Forced.AsyncUploadBufferSize));
        }

        public static void AsyncUploadPersistentBuffer(ref bool value) {
            Record("asyncUploadPersistentBuffer", value, ref value, UnityExperimentSettings.Resolve(value, Forced.AsyncUploadPersistentBuffer));
        }

        public static void VSyncCount(ref int value) {
            Record("vSyncCount", value, ref value, UnityExperimentSettings.Resolve(value, Forced.VSyncCount));
        }

        private static void Record<T>(string key, T requested, ref T value, T resolved) {
            value = resolved;
            if (Trace == null) {
                return;
            }
            string callers = string.Join(" < ", new StackTrace(2, false).GetFrames().Take(4).Select(f => $"{f.GetMethod()?.DeclaringType?.Name}.{f.GetMethod()?.Name}"));
            Trace($"Set {key} requested={requested} stored={resolved} by {callers}");
        }

        private static void Hook(Harmony patcher, System.Reflection.MethodBase? setter, string prefix) {
            if (setter == null) {
                return;
            }
            patcher.Patch(setter, new HarmonyMethod(AccessTools.Method(typeof(UnitySettingsGuard), prefix)));
        }
    }

}
