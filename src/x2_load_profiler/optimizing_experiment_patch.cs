using System;
using System.Reflection;
using Common.Content.Managers;
using HarmonyLib;
using Xenonauts;

namespace X2LoadProfiler {

    // Applies OptimizingExperiment values: the frame budget at the UpdateTasks call, the static readonly constants through reflection
    public static class OptimizingExperimentPatch {

        public static void Apply(Harmony patcher, OptimizingExperiment experiment, Action<string> trace) {
            long? cm = experiment.Get(OptimizingExperiment.CmFrameLoadBudget);
            if (cm != null) {
                OptimizingExperiment.ForcedCmFrameLoadBudget = cm;
                patcher.Patch(AccessTools.Method(typeof(ContentManager), "UpdateTasks"), new HarmonyMethod(AccessTools.Method(typeof(OptimizingExperimentPatch), nameof(UpdateTasksPrefix))));
            }
            SetStatic(experiment, OptimizingExperiment.PromiseHandlingBudget, trace);
            SetStatic(experiment, OptimizingExperiment.StrategyInitializeFrameBudget, trace);
        }

        public static void UpdateTasksPrefix(ref long maxMilliseconds) {
            if (OptimizingExperiment.ForcedCmFrameLoadBudget != null) {
                maxMilliseconds = OptimizingExperiment.ForcedCmFrameLoadBudget.Value;
            }
        }

        private static void SetStatic(OptimizingExperiment experiment, string name, Action<string> trace) {
            long? value = experiment.Get(name);
            if (value == null) {
                return;
            }
            FieldInfo? field = typeof(XenonautsConstants.Optimizing).GetField(name, BindingFlags.Public | BindingFlags.Static);
            if (field == null) {
                trace($"Optimizing {name} field not found");
                return;
            }
            object before = field.GetValue(null);
            field.SetValue(null, Convert.ChangeType(value.Value, field.FieldType));
            trace($"Optimizing {name} {before} -> {field.GetValue(null)}");
        }
    }

}
