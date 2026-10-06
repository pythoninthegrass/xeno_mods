using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

public class BundleConcurrencyTests {

    [Fact]
    public void Missing_file_uses_default_cap() {
        Assert.Equal(200, BundleConcurrency.ParseCap(null, 200));
    }

    [Fact]
    public void Parses_cap_ignoring_whitespace() {
        Assert.Equal(64, BundleConcurrency.ParseCap(" 64 \r\n", 200));
    }

    [Fact]
    public void Garbage_or_negative_falls_back_to_default() {
        Assert.Equal(200, BundleConcurrency.ParseCap("fast", 200));
        Assert.Equal(200, BundleConcurrency.ParseCap("-5", 200));
    }

    [Fact]
    public void Can_start_below_cap_only() {
        Assert.True(BundleConcurrency.CanStart(199, 200));
        Assert.False(BundleConcurrency.CanStart(200, 200));
    }

    [Fact]
    public void Zero_cap_means_unlimited() {
        Assert.True(BundleConcurrency.CanStart(100000, 0));
    }

    [Fact]
    public void Effective_cap_never_lowers_the_game_cap() {
        Assert.Equal(200, BundleConcurrency.EffectiveCap(25, 200));
        Assert.Equal(300, BundleConcurrency.EffectiveCap(300, 200));
    }

    [Fact]
    public void Game_cap_zero_stays_unlimited() {
        Assert.Equal(0, BundleConcurrency.EffectiveCap(0, 200));
    }

    [Fact]
    public void Mod_cap_zero_stays_unlimited() {
        Assert.Equal(0, BundleConcurrency.EffectiveCap(25, 0));
    }

    [Fact]
    public void Default_cap_is_the_measured_best() {
        Assert.Equal(300, BundleConcurrency.DefaultCap);
    }
}
