using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

public class AutoLoadSettingsTests {

    private const string SavePath = "C:/users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2/Saves/ellz_1bf479e6/auto/auto_groundcombat_turn_10_start-62.json";

    [Fact]
    public void Empty_text_requests_no_load() {
        var s = AutoLoadSettings.Parse("");
        Assert.Null(s.SavePath);
        Assert.Empty(s.Rejected);
    }

    [Fact]
    public void Parses_save_path_and_defaults_reseed_to_true() {
        var s = AutoLoadSettings.Parse($"save={SavePath}\n");
        Assert.Equal(SavePath, s.SavePath);
        Assert.True(s.Reseed);
    }

    [Fact]
    public void Parses_reseed_false() {
        var s = AutoLoadSettings.Parse($"save={SavePath}\nreseed=false\n");
        Assert.False(s.Reseed);
    }

    [Fact]
    public void Path_may_contain_equals_signs() {
        var s = AutoLoadSettings.Parse("save=C:/a=b/save.json");
        Assert.Equal("C:/a=b/save.json", s.SavePath);
    }

    [Fact]
    public void Ignores_comments_blank_lines_and_surrounding_whitespace() {
        var s = AutoLoadSettings.Parse($"# note\n\n  save = {SavePath}  \r\n");
        Assert.Equal(SavePath, s.SavePath);
        Assert.Empty(s.Rejected);
    }

    [Fact]
    public void Rejects_unknown_keys_and_bad_values() {
        var s = AutoLoadSettings.Parse("bogus=1\nreseed=maybe\nsave=\nno equals sign\n");
        Assert.Null(s.SavePath);
        Assert.Equal(4, s.Rejected.Count);
    }

    [Fact]
    public void Describe_reports_none_without_a_save() {
        Assert.Equal("none", AutoLoadSettings.Parse("").Describe());
    }

    [Fact]
    public void Describe_lists_save_and_reseed() {
        Assert.Equal($"save={SavePath} reseed=true", AutoLoadSettings.Parse($"save={SavePath}").Describe());
    }
}
