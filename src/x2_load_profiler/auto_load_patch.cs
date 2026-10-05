using System.IO;
using System.Reflection;
using Artitas;
using Artitas.Utils;
using Common.Content.DataStructures;
using Common.Content.Descriptors;
using Common.Content.Managers;
using HarmonyLib;
using log4net;
using Xenonauts;
using Xenonauts.Common.Events;
using Xenonauts.MainMenu.UI;

namespace X2LoadProfiler {

    // Remembers the save named in auto_load.txt on the first main menu entry in a process, then queues it once the screen transition ends
    public static class AutoLoad {

        private static readonly ILog Log = ArtitasLogger.GetLogger(MethodBase.GetCurrentMethod()!.DeclaringType);

        public static string? ConfigPath;

        private static bool _done;
        private static World? _world;
        private static AutoLoadSettings? _settings;

        public static void OnMainMenuEntered(World world) {
            if (_done || ConfigPath == null || !File.Exists(ConfigPath)) {
                return;
            }
            _done = true;

            var settings = AutoLoadSettings.Parse(File.ReadAllText(ConfigPath));
            foreach (string line in settings.Rejected) {
                Log.Warn($"[X2LoadProfiler] AutoLoad line rejected: {line}");
            }
            if (settings.SavePath == null) {
                Log.Warn($"[X2LoadProfiler] AutoLoad has no save in {ConfigPath}");
                return;
            }

            Log.Warn($"[X2LoadProfiler] AutoLoad waiting for the main menu transition to end: {settings.Describe()}");
            _world = world;
            _settings = settings;
        }

        public static void Tick() {
            if (_settings == null || XenonautsMain.Instance.ScreenManager.IsTransitioning) {
                return;
            }

            var settings = _settings;
            var world = _world!;
            _settings = null;
            _world = null;
            Log.Warn($"[X2LoadProfiler] AutoLoad queueing {settings.Describe()}");
            world.QueueEvent(new LoadGameCommand(new FileDescriptor(settings.SavePath!, typeof(SaveGame)), settings.Reseed));
        }
    }

    [HarmonyPatch(typeof(MainMenuElement), nameof(MainMenuElement.OnEnter))]
    public static class AutoLoadEnterPatch {

        [HarmonyPostfix]
        public static void Postfix(MainMenuElement __instance) {
            AutoLoad.OnMainMenuEntered(Traverse.Create(__instance).Property("World").GetValue<World>());
        }
    }

    [HarmonyPatch(typeof(ContentManager), "UpdateTasks")]
    public static class AutoLoadTickPatch {

        [HarmonyPostfix]
        public static void Postfix() {
            AutoLoad.Tick();
        }
    }

}
