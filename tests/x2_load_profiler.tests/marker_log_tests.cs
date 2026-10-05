using X2LoadTiming;

namespace X2LoadProfiler.Tests;

public class MarkerLogTests {

    private static readonly DateTime Stamp = new DateTime(2026, 10, 5, 22, 30, 1, 123);

    [Fact]
    public void Line_is_timestamp_then_message() {
        Assert.Equal("2026-10-05 22:30:01,123 Handling Setup for GroundCombat", MarkerLog.FormatLine(Stamp, "Handling Setup for GroundCombat"));
    }

    [Fact]
    public void Line_breaks_in_the_message_collapse_to_spaces() {
        Assert.Equal("2026-10-05 22:30:01,123 a b c", MarkerLog.FormatLine(Stamp, "a\r\nb\nc"));
    }

    [Fact]
    public void Append_writes_one_line_per_call_in_order() {
        string path = Path.Combine(Path.GetTempPath(), $"markers-{Guid.NewGuid():N}.txt");
        try {
            MarkerLog.Append(path, Stamp, "first");
            MarkerLog.Append(path, Stamp.AddSeconds(2), "second");
            Assert.Equal(new[] { "2026-10-05 22:30:01,123 first", "2026-10-05 22:30:03,123 second" }, File.ReadAllLines(path));
        } finally {
            File.Delete(path);
        }
    }

    [Fact]
    public void Append_with_a_null_path_does_nothing() {
        MarkerLog.Append(null, Stamp, "ignored");
    }
}
