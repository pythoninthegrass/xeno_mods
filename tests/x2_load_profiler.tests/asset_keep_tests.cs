using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

public class AssetKeepTests {

    [Fact]
    public void Assets_the_target_will_load_move_from_unload_to_transfer() {
        var split = AssetKeep.Split(new[] { "a", "b", "c" }, new[] { "b", "c", "d" }, StringComparer.Ordinal);

        Assert.Equal(new[] { "b", "c" }, split.Keep);
        Assert.Equal(new[] { "a" }, split.Unload);
    }

    [Fact]
    public void Nothing_wanted_unloads_everything() {
        var split = AssetKeep.Split(new[] { "a", "b" }, Array.Empty<string>(), StringComparer.Ordinal);

        Assert.Empty(split.Keep);
        Assert.Equal(new[] { "a", "b" }, split.Unload);
    }

    [Fact]
    public void Nothing_previous_keeps_and_unloads_nothing() {
        var split = AssetKeep.Split(Array.Empty<string>(), new[] { "a" }, StringComparer.Ordinal);

        Assert.Empty(split.Keep);
        Assert.Empty(split.Unload);
    }

    [Fact]
    public void Matching_uses_the_supplied_comparer() {
        var split = AssetKeep.Split(new[] { "A" }, new[] { "a" }, StringComparer.OrdinalIgnoreCase);

        Assert.Equal(new[] { "A" }, split.Keep);
        Assert.Empty(split.Unload);
    }

    [Fact]
    public void Only_keepable_assets_move_to_transfer() {
        var split = AssetKeep.Split(new[] { "a", "b", "c" }, new[] { "a", "b", "c" }, StringComparer.Ordinal, item => item != "b");

        Assert.Equal(new[] { "a", "c" }, split.Keep);
        Assert.Equal(new[] { "b" }, split.Unload);
    }

    [Theory]
    [InlineData("Sprite", true)]
    [InlineData("AudioClip", true)]
    [InlineData("Template", false)]
    [InlineData("MapMeta", false)]
    [InlineData("", false)]
    [InlineData(null, false)]
    public void Only_leaf_asset_kinds_are_keepable(string? typeName, bool expected) {
        Assert.Equal(expected, AssetKeep.IsLeafKind(typeName));
    }

    [Fact]
    public void Switch_defaults_to_off_and_parses_like_the_profiler_switch() {
        Assert.False(AssetKeepSwitch.Enabled);
        Assert.True(AssetKeepSwitch.Parse(" true\n"));
        Assert.False(AssetKeepSwitch.Parse(null));
        Assert.False(AssetKeepSwitch.Parse("yes"));
    }
}
