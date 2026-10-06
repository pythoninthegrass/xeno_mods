using System;
using System.Globalization;

namespace X2LoadProfiler {

    // Tab-separated records for the per-bundle-load capture; L lines are loads (last two columns: time from the first nonzero progress reading to done and that first reading, - if progress stayed 0 until done), U lines are unloads
    public static class BundleRecord {

        private const string TimeFormat = "yyyy-MM-dd HH:mm:ss.fff";

        public static string LoadLine(int sequence, DateTime doneAt, double requestToStartMs, double startToDoneMs, string? type, string? path, string? bundle, string? pack, string? parent, double? progressToDoneMs, float? firstProgress) {
            return string.Join("\t", "L", sequence.ToString(CultureInfo.InvariantCulture), doneAt.ToString(TimeFormat, CultureInfo.InvariantCulture),
                requestToStartMs.ToString("F1", CultureInfo.InvariantCulture), startToDoneMs.ToString("F1", CultureInfo.InvariantCulture),
                Field(type), Field(path), Field(bundle), Field(pack), Field(parent),
                progressToDoneMs.HasValue ? progressToDoneMs.Value.ToString("F1", CultureInfo.InvariantCulture) : "-",
                firstProgress.HasValue ? firstProgress.Value.ToString("F2", CultureInfo.InvariantCulture) : "-");
        }

        public static string UnloadLine(DateTime at, string? type, string? path) {
            return string.Join("\t", "U", at.ToString(TimeFormat, CultureInfo.InvariantCulture), Field(type), Field(path));
        }

        private static string Field(string? value) {
            if (string.IsNullOrEmpty(value)) {
                return "-";
            }
            return value!.Replace('\t', ' ').Replace('\r', ' ').Replace('\n', ' ');
        }
    }

}
