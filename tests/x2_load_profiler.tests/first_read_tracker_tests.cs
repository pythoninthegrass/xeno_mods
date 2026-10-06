using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

public class FirstReadTrackerTests {

    [Fact]
    public void First_read_of_an_item_is_reported_and_repeats_are_not() {
        var tracker = new FirstReadTracker<string>();
        Assert.True(tracker.Read("a"));
        Assert.False(tracker.Read("a"));
        Assert.True(tracker.Read("b"));
    }

    [Fact]
    public void Release_makes_the_next_read_count_again() {
        var tracker = new FirstReadTracker<string>();
        tracker.Read("a");
        tracker.Release("a");
        Assert.True(tracker.Read("a"));
    }

    [Fact]
    public void Releasing_an_item_that_was_never_read_is_harmless() {
        var tracker = new FirstReadTracker<string>();
        tracker.Release("a");
        Assert.True(tracker.Read("a"));
    }
}

public class ReadLineTests {

    [Fact]
    public void Read_line_is_tab_separated_with_time_type_and_path() {
        string line = BundleRecord.ReadLine(new DateTime(2026, 10, 6, 15, 0, 1, 250), "Template", "a/b.json");
        Assert.Equal("R\t2026-10-06 15:00:01.250\tTemplate\ta/b.json", line);
    }
}
