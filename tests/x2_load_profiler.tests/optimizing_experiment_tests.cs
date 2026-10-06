using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

public class OptimizingExperimentTests {

    [Fact]
    public void Empty_text_sets_nothing() {
        var e = OptimizingExperiment.Parse("");
        Assert.Empty(e.Values);
        Assert.Empty(e.Rejected);
        Assert.Null(e.Get("PROMISE_HANDLING_BUDGET"));
    }

    [Fact]
    public void Parses_the_three_known_constants() {
        var e = OptimizingExperiment.Parse("CM_FRAME_LOAD_BUDGET=0\nPROMISE_HANDLING_BUDGET=30\nSTRATEGY_INITIALIZE_FRAME_BUDGET=50\n");
        Assert.Equal(0, e.Get("CM_FRAME_LOAD_BUDGET"));
        Assert.Equal(30, e.Get("PROMISE_HANDLING_BUDGET"));
        Assert.Equal(50, e.Get("STRATEGY_INITIALIZE_FRAME_BUDGET"));
        Assert.Empty(e.Rejected);
    }

    [Fact]
    public void Ignores_comments_blank_lines_and_whitespace() {
        var e = OptimizingExperiment.Parse("# note\n\n  PROMISE_HANDLING_BUDGET = 7  \r\n");
        Assert.Equal(7, e.Get("PROMISE_HANDLING_BUDGET"));
        Assert.Empty(e.Rejected);
    }

    [Fact]
    public void Rejects_unknown_names_and_bad_values() {
        var e = OptimizingExperiment.Parse("CM_MAX_CONCURRENT_ASSET_BUNDLE_FILES_LOADING=5\nPROMISE_HANDLING_BUDGET=fast\nnoequals\nPROMISE_HANDLING_BUDGET=-1\n");
        Assert.Empty(e.Values);
        Assert.Equal(4, e.Rejected.Count);
    }

    [Fact]
    public void Describe_lists_only_the_values_that_were_set() {
        Assert.Equal("none", OptimizingExperiment.Parse("").Describe());
        Assert.Equal("PROMISE_HANDLING_BUDGET=30", OptimizingExperiment.Parse("PROMISE_HANDLING_BUDGET=30").Describe());
    }

    [Fact]
    public void Defaults_set_the_measured_best_promise_budget() {
        var e = OptimizingExperiment.WithDefaults(OptimizingExperiment.Parse(""));
        Assert.Equal(100, e.Get("PROMISE_HANDLING_BUDGET"));
        Assert.Null(e.Get("CM_FRAME_LOAD_BUDGET"));
    }

    [Fact]
    public void A_file_value_wins_over_the_default() {
        var e = OptimizingExperiment.WithDefaults(OptimizingExperiment.Parse("PROMISE_HANDLING_BUDGET=10"));
        Assert.Equal(10, e.Get("PROMISE_HANDLING_BUDGET"));
    }
}
