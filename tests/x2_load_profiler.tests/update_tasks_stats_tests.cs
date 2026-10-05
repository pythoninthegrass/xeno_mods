using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

// One tick is one millisecond, so a one-second window is 1000 ticks
public class UpdateTasksStatsTests {

    private const long TicksPerSecond = 1000;

    private static UpdateTasksStats NewStats() => new(TicksPerSecond);

    private static bool Frame(UpdateTasksStats s, long start, long durationTicks, int processingBefore = 0, int processingAfter = 0, int pending = 0) {
        s.BeginFrame(start, processingBefore);
        return s.EndFrame(start + durationTicks, processingAfter, pending);
    }

    [Fact]
    public void EndFrame_before_one_second_does_not_roll_over() {
        var s = NewStats();
        Assert.False(Frame(s, 0, 5));
        Assert.False(Frame(s, 100, 5));
        Assert.False(Frame(s, 900, 5));
    }

    [Fact]
    public void EndFrame_at_one_second_rolls_over() {
        var s = NewStats();
        Frame(s, 0, 5);
        Assert.True(Frame(s, 995, 5));
    }

    [Fact]
    public void Last_is_empty_before_first_rollover() {
        var s = NewStats();
        Frame(s, 0, 5);
        Assert.Equal(0, s.Last.Frames);
    }

    [Fact]
    public void Snapshot_counts_frames_in_window() {
        var s = NewStats();
        Frame(s, 0, 1);
        Frame(s, 500, 1);
        Frame(s, 999, 1);
        Assert.Equal(3, s.Last.Frames);
    }

    [Fact]
    public void Snapshot_sums_time_inside_update_tasks() {
        var s = NewStats();
        Frame(s, 0, 10);
        Frame(s, 500, 20);
        Frame(s, 980, 20);
        Assert.Equal(50.0, s.Last.UpdateMs);
    }

    [Fact]
    public void Snapshot_wall_ms_per_frame_is_window_length_over_frames() {
        var s = NewStats();
        Frame(s, 0, 1);
        Frame(s, 500, 1);
        Frame(s, 999, 1);
        Assert.Equal(1000.0 / 3, s.Last.WallMsPerFrame, 6);
    }

    [Fact]
    public void Snapshot_reports_collection_sizes_from_last_frame() {
        var s = NewStats();
        Frame(s, 0, 1, processingAfter: 40, pending: 200);
        Frame(s, 999, 1, processingAfter: 25, pending: 150);
        Assert.Equal(25, s.Last.Processing);
        Assert.Equal(150, s.Last.Pending);
    }

    [Fact]
    public void Snapshot_completed_sums_processing_count_drops() {
        var s = NewStats();
        Frame(s, 0, 1, processingBefore: 25, processingAfter: 20);
        Frame(s, 500, 1, processingBefore: 20, processingAfter: 25);
        Frame(s, 999, 1, processingBefore: 25, processingAfter: 22);
        Assert.Equal(8, s.Last.Completed);
    }

    [Fact]
    public void Counters_reset_after_rollover() {
        var s = NewStats();
        Frame(s, 0, 10, processingBefore: 5, processingAfter: 0);
        Frame(s, 999, 10, processingBefore: 5, processingAfter: 0);
        Frame(s, 1010, 4, processingBefore: 3, processingAfter: 2);
        Assert.True(Frame(s, 2010, 4, processingBefore: 3, processingAfter: 1));
        Assert.Equal(2, s.Last.Frames);
        Assert.Equal(8.0, s.Last.UpdateMs);
        Assert.Equal(3, s.Last.Completed);
    }

    [Fact]
    public void Next_window_starts_at_the_next_frame_begin() {
        var s = NewStats();
        Frame(s, 0, 1);
        Frame(s, 999, 1);
        Frame(s, 5000, 1);
        Assert.False(Frame(s, 5500, 1));
        Assert.True(Frame(s, 5999, 1));
        Assert.Equal(3, s.Last.Frames);
    }

    [Fact]
    public void Frame_path_does_not_allocate() {
        var s = NewStats();
        Frame(s, 0, 1);
        long before = GC.GetAllocatedBytesForCurrentThread();
        for (int i = 1; i < 500; i++) {
            Frame(s, i * 10L, 2, 5, 4, 100);
        }
        long after = GC.GetAllocatedBytesForCurrentThread();
        Assert.Equal(0, after - before);
    }
}
