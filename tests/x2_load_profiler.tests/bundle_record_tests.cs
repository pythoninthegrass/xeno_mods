using X2LoadProfiler;

namespace X2LoadProfiler.Tests;

public class BundleRecordTests {

    private static readonly DateTime Done = new DateTime(2026, 10, 5, 22, 30, 1, 123);

    [Fact]
    public void Load_line_is_tab_separated_in_fixed_column_order() {
        string line = BundleRecord.LoadLine(7, Done, 12.34, 56.78, "Texture2D", "strategy/a.png", "bundle1", "xenonauts", "ParentTemplate", 3.21, 0.9f);
        Assert.Equal("L\t7\t2026-10-05 22:30:01.123\t12.3\t56.8\tTexture2D\tstrategy/a.png\tbundle1\txenonauts\tParentTemplate\t3.2\t0.90", line);
    }

    [Fact]
    public void Missing_or_empty_fields_become_a_dash() {
        string line = BundleRecord.LoadLine(1, Done, 0, 0, null, "p", "", "pack", null, null, null);
        Assert.Equal("L\t1\t2026-10-05 22:30:01.123\t0.0\t0.0\t-\tp\t-\tpack\t-\t-\t-", line);
    }

    [Fact]
    public void Tabs_and_line_breaks_inside_a_field_become_spaces() {
        string line = BundleRecord.UnloadLine(Done, "T", "a\tb\nc");
        Assert.Equal("U\t2026-10-05 22:30:01.123\tT\ta b c", line);
    }

    [Fact]
    public void Numbers_use_the_invariant_culture() {
        var old = System.Globalization.CultureInfo.CurrentCulture;
        System.Globalization.CultureInfo.CurrentCulture = new System.Globalization.CultureInfo("de-DE");
        try {
            Assert.Contains("\t1.5\t", BundleRecord.LoadLine(1, Done, 1.5, 2.5, "t", "p", "b", "k", "q", 0.5, 0.25f));
        } finally {
            System.Globalization.CultureInfo.CurrentCulture = old;
        }
    }
}
