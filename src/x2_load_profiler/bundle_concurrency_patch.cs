using Common.Content;
using Common.Content.AsyncOperations;
using HarmonyLib;

namespace X2LoadProfiler {

    public static class BundleConcurrencyConfig {

        public static int ModCap = BundleConcurrency.DefaultCap;
    }

    [HarmonyPatch(typeof(AssetBundleFileLoadOperation), nameof(AssetBundleFileLoadOperation.CanStart))]
    public static class BundleConcurrencyPatch {

        [HarmonyPostfix]
        public static void Postfix(ref bool __result, IContentManager ____contentManager, int ____filesLoading) {
            if (__result) {
                return;
            }
            int cap = BundleConcurrency.EffectiveCap(____contentManager.GetConfig().maxConcurrentAssetBundleFilesLoading, BundleConcurrencyConfig.ModCap);
            __result = BundleConcurrency.CanStart(____filesLoading, cap);
        }
    }

}
