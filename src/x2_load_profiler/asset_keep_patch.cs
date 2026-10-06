using System.Collections.Generic;
using Common.Content;
using Common.Content.Descriptors;
using Common.Screens.DataStructures;
using HarmonyLib;
using Xenonauts;

namespace X2LoadProfiler {

    // Applied from the lifecycle only when the keep switch is on
    public static class AssetKeepPatch {

        public static readonly System.Reflection.MethodBase Target = AccessTools.Method(typeof(ManagedScreen<GameScreens, IScreenParameters>), "TransferManifests");

        [HarmonyPostfix]
        public static void Postfix(HashSet<Descriptor> preliminaryLoad, List<AssetManifest> transferManifests, List<AssetManifest> unloadManifests) {
            for (int i = 0; i < unloadManifests.Count; i++) {
                var split = AssetKeep.Split(unloadManifests[i], preliminaryLoad, AssetDescriptor.StrictContentPackComparer.Instance, descriptor => AssetKeep.IsLeafKind(descriptor.Type?.Name));
                transferManifests.Add(new AssetManifest("Kept for target load: " + unloadManifests[i].Name, split.Keep));
                unloadManifests[i] = new AssetManifest(unloadManifests[i].Name, split.Unload);
            }
        }
    }

}
