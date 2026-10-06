using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

public class UnityExperimentSettingsTests {

    [Fact]
    public void Empty_text_sets_nothing() {
        var s = UnityExperimentSettings.Parse("");
        Assert.Null(s.BackgroundLoadingPriority);
        Assert.Null(s.AsyncUploadTimeSlice);
        Assert.Null(s.AsyncUploadBufferSize);
        Assert.Null(s.AsyncUploadPersistentBuffer);
        Assert.Empty(s.Rejected);
    }

    [Fact]
    public void Parses_all_four_keys() {
        var s = UnityExperimentSettings.Parse("backgroundLoadingPriority=High\nasyncUploadTimeSlice=8\nasyncUploadBufferSize=256\nasyncUploadPersistentBuffer=false\n");
        Assert.Equal("High", s.BackgroundLoadingPriority);
        Assert.Equal(8, s.AsyncUploadTimeSlice);
        Assert.Equal(256, s.AsyncUploadBufferSize);
        Assert.False(s.AsyncUploadPersistentBuffer);
    }

    [Fact]
    public void Ignores_comments_blank_lines_and_surrounding_whitespace() {
        var s = UnityExperimentSettings.Parse("# note\n\n  asyncUploadTimeSlice = 4  \r\n");
        Assert.Equal(4, s.AsyncUploadTimeSlice);
        Assert.Empty(s.Rejected);
    }

    [Fact]
    public void Rejects_unknown_keys_and_bad_values() {
        var s = UnityExperimentSettings.Parse("bogus=1\nasyncUploadTimeSlice=fast\nasyncUploadPersistentBuffer=maybe\nnoequals\n");
        Assert.Null(s.AsyncUploadTimeSlice);
        Assert.Null(s.AsyncUploadPersistentBuffer);
        Assert.Equal(4, s.Rejected.Count);
    }

    [Fact]
    public void Describe_lists_only_the_keys_that_were_set() {
        var s = UnityExperimentSettings.Parse("backgroundLoadingPriority=High\nasyncUploadTimeSlice=8");
        Assert.Equal("backgroundLoadingPriority=High asyncUploadTimeSlice=8", s.Describe());
    }

    [Fact]
    public void Describe_is_none_when_nothing_was_set() {
        Assert.Equal("none", UnityExperimentSettings.Parse("").Describe());
    }

    [Fact]
    public void Parses_frame_pacing_keys() {
        var s = UnityExperimentSettings.Parse("vSyncCount=0\ntargetFrameRate=-1\n");
        Assert.Equal(0, s.VSyncCount);
        Assert.Equal(-1, s.TargetFrameRate);
        Assert.Empty(s.Rejected);
    }

    [Fact]
    public void Frame_pacing_keys_are_unset_by_default_and_rejected_when_not_numbers() {
        var s = UnityExperimentSettings.Parse("vSyncCount=off\n");
        Assert.Null(s.VSyncCount);
        Assert.Null(s.TargetFrameRate);
        Assert.Single(s.Rejected);
    }

    [Fact]
    public void Describe_includes_frame_pacing_keys() {
        var s = UnityExperimentSettings.Parse("vSyncCount=0\ntargetFrameRate=240");
        Assert.Equal("vSyncCount=0 targetFrameRate=240", s.Describe());
    }

    [Fact]
    public void Forced_value_wins_over_the_requested_one() {
        Assert.Equal(8, UnityExperimentSettings.Resolve(33, 8));
    }

    [Fact]
    public void Requested_value_is_kept_when_nothing_is_forced() {
        Assert.Equal(33, UnityExperimentSettings.Resolve(33, null));
        Assert.True(UnityExperimentSettings.Resolve(true, null));
    }
}
