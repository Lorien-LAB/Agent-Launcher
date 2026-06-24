using System.Text.Json;
using System.Text.Json.Nodes;

namespace AgentLauncher.Services;

/// <summary>
/// Read/write Windows Terminal settings.json for acrylic/opacity/background mode.
/// </summary>
public class TerminalSettingsService
{
    private static readonly string WtSettingsPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Packages",
        "Microsoft.WindowsTerminal_8wekyb3d8bbwe",
        "LocalState",
        "settings.json"
    );

    public enum BackgroundMode { Acrylic, Opacity, None }

    /// <summary>
    /// Get current background mode and value (acrylic 0–100, opacity 0–100).
    /// </summary>
    public static (BackgroundMode mode, int value) GetCurrentMode()
    {
        try
        {
            var json = File.ReadAllText(WtSettingsPath, System.Text.Encoding.UTF8);
            var doc = JsonNode.Parse(json);
            var defaults = doc?["profiles"]?["defaults"];
            if (defaults != null)
            {
                bool? useAcrylic = (bool?)defaults["useAcrylic"];
                if (useAcrylic == true)
                {
                    double acrylicOpacity = (double?)defaults["acrylicOpacity"] ?? 0.33;
                    return (BackgroundMode.Acrylic, (int)(acrylicOpacity * 100));
                }
                int? opacity = (int?)defaults["opacity"];
                if (opacity.HasValue)
                    return (BackgroundMode.Opacity, opacity.Value);
            }
        }
        catch { }
        return (BackgroundMode.None, 100);
    }

    /// <summary>
    /// Write background mode to Windows Terminal settings.
    /// </summary>
    public static void ApplyBackground(BackgroundMode mode, int value)
    {
        try
        {
            var json = File.ReadAllText(WtSettingsPath, System.Text.Encoding.UTF8);
            var doc = JsonNode.Parse(json) ?? new JsonObject();
            doc["profiles"] ??= new JsonObject();
            doc["profiles"]!["defaults"] ??= new JsonObject();
            var defaults = doc["profiles"]!["defaults"]!;

            // Remove old keys
            var removeKeys = new[] { "useAcrylic", "acrylicOpacity", "opacity" };
            foreach (var key in removeKeys)
            {
                if (defaults[key] != null)
                    defaults.AsObject().Remove(key);
            }

            switch (mode)
            {
                case BackgroundMode.Acrylic:
                    defaults["useAcrylic"] = true;
                    defaults["acrylicOpacity"] = value / 100.0;
                    break;
                case BackgroundMode.Opacity:
                    defaults["opacity"] = value;
                    break;
                // None: just leave keys removed
            }

            var output = JsonSerializer.Serialize(doc, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(WtSettingsPath, output, System.Text.Encoding.UTF8);
        }
        catch { /* settings file may be locked or missing */ }
    }
}
