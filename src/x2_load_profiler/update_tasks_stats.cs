namespace X2LoadProfiler {

    public readonly struct UpdateTasksSnapshot {

        public readonly int Frames;
        public readonly double UpdateMs;
        public readonly int Processing;
        public readonly int Pending;
        public readonly int Completed;
        public readonly double WallMsPerFrame;

        public UpdateTasksSnapshot(int frames, double updateMs, int processing, int pending, int completed, double wallMsPerFrame) {
            Frames = frames;
            UpdateMs = updateMs;
            Processing = processing;
            Pending = pending;
            Completed = completed;
            WallMsPerFrame = wallMsPerFrame;
        }
    }

    // Per-second rollup of UpdateTasks calls; every method is allocation-free
    public sealed class UpdateTasksStats {

        public UpdateTasksSnapshot Last { get; private set; }

        private readonly long _ticksPerSecond;
        private long _windowStartTicks;
        private long _frameStartTicks;
        private int _processingBefore;
        private int _frames;
        private long _updateTicks;
        private int _completed;

        public UpdateTasksStats(long ticksPerSecond) {
            _ticksPerSecond = ticksPerSecond;
        }

        public void BeginFrame(long nowTicks, int processingCount) {
            if (_frames == 0) {
                _windowStartTicks = nowTicks;
            }
            _frameStartTicks = nowTicks;
            _processingBefore = processingCount;
        }

        // Returns true when the one-second window closed and Last was filled
        public bool EndFrame(long nowTicks, int processingCount, int pendingCount) {
            _frames++;
            _updateTicks += nowTicks - _frameStartTicks;
            if (processingCount < _processingBefore) {
                _completed += _processingBefore - processingCount;
            }

            long windowTicks = nowTicks - _windowStartTicks;
            if (windowTicks < _ticksPerSecond) {
                return false;
            }

            double msPerTick = 1000.0 / _ticksPerSecond;
            Last = new UpdateTasksSnapshot(
                _frames,
                _updateTicks * msPerTick,
                processingCount,
                pendingCount,
                _completed,
                windowTicks * msPerTick / _frames);
            _frames = 0;
            _updateTicks = 0;
            _completed = 0;
            return true;
        }
    }

}
