using System.Windows;

namespace AgentLauncher;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        // DPI awareness
        try
        {
            Helpers.NativeMethods.SetProcessDpiAwareness(
                Helpers.NativeMethods.DPI_AWARENESS_PER_MONITOR_AWARE);
        }
        catch { }
    }
}
