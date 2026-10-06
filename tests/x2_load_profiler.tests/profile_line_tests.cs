using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

public class ProfileLineTests {

    private static readonly UpdateTasksSnapshot Update = new UpdateTasksSnapshot(60, 12.5, 3, 4, 5, 16.66);
    private static readonly BundleLoadSnapshot Bundles = new BundleLoadSnapshot(7, 8, 10, 9, 123.4, 456.7);

    [Fact]
    public void Line_lists_update_and_bundle_counters_in_a_fixed_order() {
        Assert.Equal(
            "[X2LoadProfiler] frames=60 updateMs=12.5 processing=3 pending=4 completed=5 wallMsPerFrame=16.7 bundleStarted=7 bundleDone=8 bundleInFlight=9 bundleBlockedPolls=10 bundleMeanMs=123 bundleMaxMs=457",
            ProfileLine.Format(Update, Bundles));
    }

    [Fact]
    public void Numbers_use_the_invariant_culture() {
        var old = System.Globalization.CultureInfo.CurrentCulture;
        System.Globalization.CultureInfo.CurrentCulture = new System.Globalization.CultureInfo("de-DE");
        try {
            Assert.Contains("updateMs=12.5 ", ProfileLine.Format(Update, Bundles));
        } finally {
            System.Globalization.CultureInfo.CurrentCulture = old;
        }
    }
}
