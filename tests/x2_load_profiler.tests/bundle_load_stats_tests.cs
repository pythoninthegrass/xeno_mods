using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

// One tick is one millisecond
public class BundleLoadStatsTests {

    private static BundleLoadStats NewStats() => new(1000);

    [Fact]
    public void Snapshot_counts_starts_completions_and_blocked_polls() {
        var s = NewStats();
        s.RecordStart();
        s.RecordStart();
        s.RecordBlockedPoll();
        s.RecordBlockedPoll();
        s.RecordBlockedPoll();
        s.RecordDone(10);
        var snap = s.TakeSnapshot(1);
        Assert.Equal(2, snap.Started);
        Assert.Equal(1, snap.Completed);
        Assert.Equal(3, snap.BlockedPolls);
    }

    [Fact]
    public void Snapshot_reports_in_flight_as_given() {
        var s = NewStats();
        Assert.Equal(25, s.TakeSnapshot(25).InFlight);
    }

    [Fact]
    public void Snapshot_latency_mean_and_max_in_ms() {
        var s = NewStats();
        s.RecordDone(100);
        s.RecordDone(300);
        s.RecordDone(200);
        var snap = s.TakeSnapshot(0);
        Assert.Equal(200.0, snap.MeanLatencyMs);
        Assert.Equal(300.0, snap.MaxLatencyMs);
    }

    [Fact]
    public void Snapshot_with_no_completions_has_zero_latency() {
        var snap = NewStats().TakeSnapshot(0);
        Assert.Equal(0.0, snap.MeanLatencyMs);
        Assert.Equal(0.0, snap.MaxLatencyMs);
    }

    [Fact]
    public void Snapshot_resets_counters_for_the_next_window() {
        var s = NewStats();
        s.RecordStart();
        s.RecordBlockedPoll();
        s.RecordDone(500);
        s.TakeSnapshot(0);
        var next = s.TakeSnapshot(0);
        Assert.Equal(0, next.Started);
        Assert.Equal(0, next.Completed);
        Assert.Equal(0, next.BlockedPolls);
        Assert.Equal(0.0, next.MaxLatencyMs);
    }

    [Fact]
    public void Latency_converts_with_ticks_per_second() {
        var s = new BundleLoadStats(10_000_000);
        s.RecordDone(5_000_000);
        Assert.Equal(500.0, s.TakeSnapshot(0).MeanLatencyMs);
    }

    [Fact]
    public void IsSlow_is_true_at_or_above_the_threshold() {
        var s = NewStats();
        Assert.False(s.IsSlow(499));
        Assert.True(s.IsSlow(500));
        Assert.True(s.IsSlow(1500));
    }

    [Fact]
    public void IsSlow_converts_with_ticks_per_second() {
        var s = new BundleLoadStats(10_000_000);
        Assert.False(s.IsSlow(4_999_999));
        Assert.True(s.IsSlow(5_000_000));
    }
}
