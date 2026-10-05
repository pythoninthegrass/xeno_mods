# TODO

- [ ] Enable the mod in-game and confirm the `[X2LoadProfiler] Loaded` line appears in `output.log`
- [ ] Decide whether to move from the obsolete `IModLifecycle` to `IContentPackLifecycle`
- [ ] Instrumentation patch on `ContentManager.UpdateTasks` (aggregation unit-tested first)
- [ ] Baseline measurements with `optimizing.json` restored to `{}`
- [ ] Diagnose from per-second lines and update `docs/load-time-report.md`
- [ ] Implement the fix patch and compare mod on/off
- [ ] README (build, install, enable) and restore `log4net.xml` / `optimizing.json`
