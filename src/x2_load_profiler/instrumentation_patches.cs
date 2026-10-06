using System;
using Common.Content;
using Common.Content.AsyncOperations;
using Common.Content.Managers;
using Common.Content.Tasks;
using HarmonyLib;
using Xenonauts.MainMenu.UI;

namespace X2LoadProfiler {

    // Applied from the lifecycle instead of PatchAll, so the profiler and the auto-load harness cost nothing unless asked for
    public static class InstrumentationPatches {

        private static readonly Type[] LoadTaskCtor = { typeof(ILoader), typeof(ContentManager), typeof(Descriptor), typeof(IAssetParameters), typeof(Descriptor), typeof(bool), typeof(bool) };
        private static readonly Type[] BundleOperationCtor = { typeof(IContentManager), typeof(UnityEngine.AssetBundle), typeof(Descriptor) };

        public static void ApplyProfiler(Harmony patcher) {
            var updateTasks = AccessTools.Method(typeof(ContentManager), "UpdateTasks");
            patcher.Patch(updateTasks, Method(typeof(UpdateTasksPatch), "Prefix"), Method(typeof(UpdateTasksPatch), "Postfix"));
            patcher.Patch(AccessTools.Method(typeof(AssetBundleFileLoadOperation), nameof(AssetBundleFileLoadOperation.CanStart)), postfix: Method(typeof(BundleCanStartPatch), "Postfix"));
            patcher.Patch(AccessTools.Method(typeof(AssetBundleFileLoadOperation), nameof(AssetBundleFileLoadOperation.Start)), postfix: Method(typeof(BundleStartPatch), "Postfix"));
            patcher.Patch(AccessTools.Method(typeof(AssetBundleFileLoadOperation), nameof(AssetBundleFileLoadOperation.Update)), postfix: Method(typeof(BundleUpdatePatch), "Postfix"));
            patcher.Patch(AccessTools.Constructor(typeof(LoadTask), LoadTaskCtor), postfix: Method(typeof(CaptureLoadTaskPatch), "Postfix"));
            patcher.Patch(AccessTools.Constructor(typeof(AssetBundleFileLoadOperation), BundleOperationCtor), postfix: Method(typeof(CaptureRequestPatch), "Postfix"));
            patcher.Patch(AccessTools.Method(typeof(ContentManager), "InternalUnload"), Method(typeof(CaptureUnloadPatch), "Prefix"));
            patcher.Patch(AccessTools.Method(typeof(ContentManager), "InternalGet"), Method(typeof(CaptureReadPatch), "Prefix"));
        }

        public static void ApplyAutoLoad(Harmony patcher) {
            patcher.Patch(AccessTools.Method(typeof(MainMenuElement), nameof(MainMenuElement.OnEnter)), postfix: Method(typeof(AutoLoadEnterPatch), "Postfix"));
            patcher.Patch(AccessTools.Method(typeof(ContentManager), "UpdateTasks"), postfix: Method(typeof(AutoLoadTickPatch), "Postfix"));
        }

        private static HarmonyMethod Method(Type type, string name) {
            return new HarmonyMethod(AccessTools.Method(type, name));
        }
    }

}
