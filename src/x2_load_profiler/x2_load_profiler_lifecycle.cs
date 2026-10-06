using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Artitas;
using Artitas.Utils;
using Common.Content;
using Common.Modding;
using HarmonyLib;
using log4net;
using UnityEngine;

namespace X2LoadProfiler {

    public class X2LoadProfilerLifecycle : IModLifecycle {

        private static readonly ILog Log = ArtitasLogger.GetLogger(MethodBase.GetCurrentMethod()!.DeclaringType);

        private const string ExperimentFileName = "unity_experiment.txt";

        private const string AutoLoadFileName = "auto_load.txt";

        private const string BundleCaptureFlagFileName = "bundle_log.txt";

        private const string BundleCaptureOutputFileName = "bundle_loads.tsv";

        private const string BundleCapFileName = "bundle_cap.txt";

        private const string ProfilerFileName = "profiler.txt";

        private const string ProfileOutputFileName = "profile.txt";

        public void Create(Mod mod, Harmony patcher) {
            Log.Warn("[X2LoadProfiler] Loaded");
            AutoLoad.ConfigPath = Path.Combine(mod.ContentPack, AutoLoadFileName);
            ApplyBundleCap(mod);
            ApplyProfiler(mod, patcher);
            if (File.Exists(AutoLoad.ConfigPath)) {
                InstrumentationPatches.ApplyAutoLoad(patcher);
            }
            try {
                ApplyExperiment(mod);
            } catch (Exception e) {
                Log.Warn($"[X2LoadProfiler] Experiment failed: {e}");
            }
            Log.Warn($"[X2LoadProfiler] UnitySettings backgroundLoadingPriority={Application.backgroundLoadingPriority} asyncUploadTimeSlice={QualitySettings.asyncUploadTimeSlice} asyncUploadBufferSize={QualitySettings.asyncUploadBufferSize} asyncUploadPersistentBuffer={QualitySettings.asyncUploadPersistentBuffer} targetFrameRate={Application.targetFrameRate} vSyncCount={QualitySettings.vSyncCount}");
        }

        private static void ApplyBundleCap(Mod mod) {
            string path = Path.Combine(mod.ContentPack, BundleCapFileName);
            string? text = File.Exists(path) ? File.ReadAllText(path) : null;
            BundleConcurrencyConfig.ModCap = BundleConcurrency.ParseCap(text, BundleConcurrency.DefaultCap);
            Log.Warn($"[X2LoadProfiler] BundleCap={BundleConcurrencyConfig.ModCap} source={(text == null ? "default" : path)}");
        }

        private static void ApplyProfiler(Mod mod, Harmony patcher) {
            string path = Path.Combine(mod.ContentPack, ProfilerFileName);
            ProfilerSwitch.Enabled = ProfilerSwitch.Parse(File.Exists(path) ? File.ReadAllText(path) : null);
            Log.Warn($"[X2LoadProfiler] Profiler={ProfilerSwitch.Enabled} source={(File.Exists(path) ? path : "default")}");
            if (!ProfilerSwitch.Enabled) {
                return;
            }
            InstrumentationPatches.ApplyProfiler(patcher);
            UpdateTasksPatch.ProfilePath = Path.Combine(mod.ContentPack, ProfileOutputFileName);
            File.WriteAllText(UpdateTasksPatch.ProfilePath, "");
            if (File.Exists(Path.Combine(mod.ContentPack, BundleCaptureFlagFileName))) {
                BundleCapture.Enable(Path.Combine(mod.ContentPack, BundleCaptureOutputFileName));
            }
        }

        private static void ApplyExperiment(Mod mod) {
            string path = Path.Combine(mod.ContentPack, ExperimentFileName);
            if (!File.Exists(path)) {
                Log.Warn($"[X2LoadProfiler] Experiment file not found: {path}");
                return;
            }

            var settings = UnityExperimentSettings.Parse(File.ReadAllText(path));
            foreach (string line in settings.Rejected) {
                Log.Warn($"[X2LoadProfiler] Experiment line rejected: {line}");
            }
            if (settings.BackgroundLoadingPriority != null) {
                if (Enum.TryParse(settings.BackgroundLoadingPriority, out ThreadPriority priority)) {
                    Application.backgroundLoadingPriority = priority;
                } else {
                    Log.Warn($"[X2LoadProfiler] Unknown ThreadPriority: {settings.BackgroundLoadingPriority}");
                }
            }
            if (settings.AsyncUploadTimeSlice != null) {
                QualitySettings.asyncUploadTimeSlice = settings.AsyncUploadTimeSlice.Value;
            }
            if (settings.AsyncUploadBufferSize != null) {
                QualitySettings.asyncUploadBufferSize = settings.AsyncUploadBufferSize.Value;
            }
            if (settings.AsyncUploadPersistentBuffer != null) {
                QualitySettings.asyncUploadPersistentBuffer = settings.AsyncUploadPersistentBuffer.Value;
            }
            Log.Warn($"[X2LoadProfiler] Experiment applied from {path}: {settings.Describe()}");
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
