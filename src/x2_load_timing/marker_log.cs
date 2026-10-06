using System;
using System.IO;

namespace X2LoadTiming {

    public static class MarkerLog {

        private static readonly object Gate = new object();

        public static string FormatLine(DateTime timestamp, string message) {
            string oneLine = message.Replace("\r\n", " ").Replace('\n', ' ').Replace('\r', ' ');
            return $"{timestamp:yyyy-MM-dd HH:mm:ss,fff} {oneLine}";
        }

        public static void Append(string? path, DateTime timestamp, string message) {
            if (path == null) {
                return;
            }
            lock (Gate) {
                File.AppendAllText(path, FormatLine(timestamp, message) + "\n");
            }
        }
    }

}
