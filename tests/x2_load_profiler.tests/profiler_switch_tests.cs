using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

public class ProfilerSwitchTests {

    [Fact]
    public void Missing_file_leaves_the_profiler_off() {
        Assert.False(ProfilerSwitch.Parse(null));
    }

    [Fact]
    public void True_turns_the_profiler_on_ignoring_case_and_whitespace() {
        Assert.True(ProfilerSwitch.Parse(" True \r\n"));
        Assert.True(ProfilerSwitch.Parse("true"));
    }

    [Fact]
    public void False_keeps_the_profiler_off() {
        Assert.False(ProfilerSwitch.Parse("false"));
    }

    [Fact]
    public void Garbage_or_empty_falls_back_to_off() {
        Assert.False(ProfilerSwitch.Parse("yes"));
        Assert.False(ProfilerSwitch.Parse(""));
    }

    [Fact]
    public void Switch_defaults_to_off_until_the_lifecycle_sets_it() {
        Assert.False(ProfilerSwitch.Enabled);
    }
}
