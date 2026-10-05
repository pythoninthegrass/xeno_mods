using Common.Content.Descriptors;
using Common.FSM.Systems;
using Common.Screens.DataStructures;
using UniversalTweenEngine;
using HarmonyLib;
using Xenonauts;
using Xenonauts.Common.Events;
using Xenonauts.GroundCombat;
using Xenonauts.UI;

namespace X2LoadTiming {

    // Same message text as the game's INFO lines, so scripts/run.py reads both sources with one parser
    [HarmonyPatch(typeof(LoadGameCommand), MethodType.Constructor, new[] { typeof(FileDescriptor), typeof(bool) })]
    public static class QueuedPatch {

        [HarmonyPostfix]
        public static void Postfix(LoadGameCommand __instance) {
            Markers.Mark($"Queued LoadGameCommand:: {__instance}");
        }
    }

    [HarmonyPatch(typeof(XenonautsLoadScreen), nameof(XenonautsLoadScreen.Intro))]
    public static class IntroCompletePatch {

        [HarmonyPostfix]
        public static void Postfix(ref Timeline __result) {
            __result.Push(() => Markers.Mark("XenonautsLoadScreen: Intro Complete"));
        }
    }

    [HarmonyPatch(typeof(XenonautsLoadScreen), nameof(XenonautsLoadScreen.Outro))]
    public static class OutroCompletePatch {

        [HarmonyPostfix]
        public static void Postfix(ref Timeline __result) {
            __result.Push(() => Markers.Mark("XenonautsLoadScreen: Outro Complete"));
        }
    }

    [HarmonyPatch(typeof(LoadScreen<GameScreens, IScreenParameters>), "CheckLoading")]
    public static class SetupPatch {

        private static readonly AccessTools.FieldRef<LoadScreen<GameScreens, IScreenParameters>, bool> StartedSetup =
            AccessTools.FieldRefAccess<LoadScreen<GameScreens, IScreenParameters>, bool>("_hasStartedSetupPhase");

        [HarmonyPrefix]
        public static void Prefix(LoadScreen<GameScreens, IScreenParameters> __instance, out bool __state) {
            __state = StartedSetup(__instance);
        }

        [HarmonyPostfix]
        public static void Postfix(LoadScreen<GameScreens, IScreenParameters> __instance, bool __state) {
            if (!__state && StartedSetup(__instance)) {
                Markers.Mark("LoadScreen, Handling Setup for GroundCombat");
            }
        }
    }

    [HarmonyPatch(typeof(GroundCombatUIStateSystem), nameof(GroundCombatUIStateSystem.BlockOnLocalPlayerTurn))]
    public static class PlayablePatch {

        [HarmonyPostfix]
        public static void Postfix(PhaseStepReport<GCPhases.TurnControl, Steps.Main> report) {
            var owner = report.GetParameter0<GCTurnParameters>().TurnOwner;
            if (owner.IsMemberOfLocalPlayers()) {
                Markers.Mark($"GCUI: BlockOnLocalPlayerTurn for {owner}");
            }
        }
    }

}
