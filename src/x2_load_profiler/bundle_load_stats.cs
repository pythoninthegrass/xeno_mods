namespace X2LoadProfiler {

    public readonly struct BundleLoadSnapshot {

        public readonly int Started;
        public readonly int Completed;
        public readonly int BlockedPolls;
        public readonly int InFlight;
        public readonly double MeanLatencyMs;
        public readonly double MaxLatencyMs;

        public BundleLoadSnapshot(int started, int completed, int blockedPolls, int inFlight, double meanLatencyMs, double maxLatencyMs) {
            Started = started;
            Completed = completed;
            BlockedPolls = blockedPolls;
            InFlight = inFlight;
            MeanLatencyMs = meanLatencyMs;
            MaxLatencyMs = maxLatencyMs;
        }
    }

    // Per-window counters for asset bundle load operations; every method is allocation-free
    public sealed class BundleLoadStats {

        private readonly long _ticksPerSecond;
        private int _started;
        private int _completed;
        private int _blockedPolls;
        private long _latencyTicksSum;
        private long _latencyTicksMax;

        public BundleLoadStats(long ticksPerSecond) {
            _ticksPerSecond = ticksPerSecond;
        }

        public void RecordStart() {
            _started++;
        }

        // A CanStart poll that returned false because the concurrency cap was reached
        public void RecordBlockedPoll() {
            _blockedPolls++;
        }

        public void RecordDone(long latencyTicks) {
            _completed++;
            _latencyTicksSum += latencyTicks;
            if (latencyTicks > _latencyTicksMax) {
                _latencyTicksMax = latencyTicks;
            }
        }

        // Returns the current window and clears the counters
        public BundleLoadSnapshot TakeSnapshot(int inFlight) {
            double msPerTick = 1000.0 / _ticksPerSecond;
            double mean = _completed == 0 ? 0.0 : _latencyTicksSum * msPerTick / _completed;
            var snap = new BundleLoadSnapshot(_started, _completed, _blockedPolls, inFlight, mean, _latencyTicksMax * msPerTick);
            _started = 0;
            _completed = 0;
            _blockedPolls = 0;
            _latencyTicksSum = 0;
            _latencyTicksMax = 0;
            return snap;
        }
    }

}
