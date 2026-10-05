using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Common.Content;
using Common.Content.AsyncOperations;
using Common.Content.Managers;
using Common.Content.Tasks;
using HarmonyLib;

namespace X2LoadProfiler {

    // Opt-in per-load capture: enabled only when bundle_log.txt exists in the mod folder, so the shipped mod pays nothing
    public static class BundleCapture {

        public static string? OutputPath;

        public static readonly Dictionary<Descriptor, string> Parents = new Dictionary<Descriptor, string>();

        public static readonly Dictionary<AssetBundleFileLoadOperation, long> RequestTimes = new Dictionary<AssetBundleFileLoadOperation, long>();

        private static readonly StringBuilder Pending = new StringBuilder();
        private static int _sequence;

        public static bool Enabled => OutputPath != null;

        public static void Enable(string path) {
            OutputPath = path;
            File.WriteAllText(path, "");
        }

        public static void Add(string line) {
            lock (Pending) {
                Pending.Append(line).Append('\n');
            }
        }

        public static int NextSequence() {
            return ++_sequence;
        }

        public static void Flush() {
            if (OutputPath == null) {
                return;
            }
            lock (Pending) {
                if (Pending.Length == 0) {
                    return;
                }
                File.AppendAllText(OutputPath, Pending.ToString());
                Pending.Clear();
            }
        }
    }

    public static class CaptureLoadTaskPatch {

        [HarmonyPostfix]
        public static void Postfix(Descriptor descriptor, Descriptor parent) {
            if (BundleCapture.Enabled && parent != null) {
                BundleCapture.Parents[descriptor] = parent.ToString();
            }
        }
    }

    public static class CaptureRequestPatch {

        [HarmonyPostfix]
        public static void Postfix(AssetBundleFileLoadOperation __instance) {
            if (BundleCapture.Enabled) {
                BundleCapture.RequestTimes[__instance] = System.Diagnostics.Stopwatch.GetTimestamp();
            }
        }
    }

    public static class CaptureUnloadPatch {

        [HarmonyPrefix]
        public static void Prefix(Descriptor descriptor) {
            if (BundleCapture.Enabled && descriptor != null) {
                BundleCapture.Add(BundleRecord.UnloadLine(DateTime.Now, descriptor.Type?.Name, descriptor.FileHandle?.RelativePath));
            }
        }
    }

}
