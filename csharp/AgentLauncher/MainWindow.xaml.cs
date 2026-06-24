using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using AgentLauncher.Helpers;
using AgentLauncher.Models;
using AgentLauncher.Services;

namespace AgentLauncher;

public class DirItem
{
    public string Label { get; set; } = "";
    public string Path { get; set; } = "";
    public string? ParentName { get; set; }
    public bool IsHeader { get; set; }
    public bool IsExpanded { get; set; }
    public string DisplayLabel { get; set; } = "";
}

public partial class MainWindow : Window
{
    private static readonly string[] BaseDirs =
    {
        @"D:\Quantitative Trading",
        @"D:\University\Kaggle",
        @"D:\Obsidian_Lorien_Lab",
        @"D:\University\比赛\AFAC2026挑战组-赛题一：市场参与者交易行为识别与资金流向分析",
        @"C:\Users\Lorien\terminal-manager",
    };
    private static readonly string HomeDir =
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

    private IntPtr _trayIconHandle;
    private bool _trayAdded;
    private readonly SessionMonitorService _monitor = new();
    private SessionPanel? _sessionPanel;
    private readonly Dictionary<string, bool> _expanded = new();
    private readonly HashSet<string> _createdSessions = new();
    private readonly Dictionary<string, string> _lastStatuses = new();
    private string? _lastPanelIdKey;
    private AggregateStats? _lastStats;

    public MainWindow()
    {
        InitializeComponent();

        this.SourceInitialized += (s, e) =>
        {
            NativeMethods.ApplyDarkMode(this);
            var hwnd = new WindowInteropHelper(this).Handle;
            var hwndSource = HwndSource.FromHwnd(hwnd);
            hwndSource?.AddHook(WndProc);
            CreateTrayIcon();
        };

        this.Closing += OnClosing;
        this.ContentRendered += (s, e) =>
        {
            PopulateDirectories();
            LoadCurrentSettings();
            _monitor.OnUpdate += OnStatsUpdate;
            var initStats = _monitor.Scan();
            _monitor.Start();
            CreateSessionPanel();
            if (_sessionPanel != null && initStats.Sessions.Count > 0)
                _sessionPanel.Rebuild(initStats);
        };

        DirListBox.KeyDown += (s, e) =>
        {
            if (e.Key == Key.Enter) LaunchSelected();
        };
    }

    // ── WndProc for tray messages ──

    private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == NativeMethods.WM_TRAYICON)
        {
            int lp = lParam.ToInt32();
            // Windows defines: WM_LBUTTONDBLCLK=0x0203, WM_RBUTTONUP=0x0205
            if (lp == 0x0203) // left double-click
            {
                ShowFromTray();
            }
            else if (lp == 0x0205) // right-button up
            {
                ShowTrayContextMenu();
            }
            handled = true;
        }
        return IntPtr.Zero;
    }

    private void ShowTrayContextMenu()
    {
        // Use native TrackPopupMenu for proper tray context menu
        NativeMethods.GetCursorPos(out var pt);
        var menu = NativeMethods.CreatePopupMenu();
        NativeMethods.AppendMenu(menu, NativeMethods.MF_STRING, 1, "Show");
        NativeMethods.SetMenuDefaultItem(menu, 1, false);
        NativeMethods.AppendMenu(menu, NativeMethods.MF_STRING, 2, "Exit");

        var hwnd = new WindowInteropHelper(this).Handle;
        NativeMethods.SetForegroundWindow(hwnd); // required for TrackPopupMenu to work correctly

        uint cmd = NativeMethods.TrackPopupMenu(
            menu,
            NativeMethods.TPM_RETURNCMD | NativeMethods.TPM_RIGHTBUTTON,
            pt.X, pt.Y, 0, hwnd, IntPtr.Zero);

        NativeMethods.DestroyMenu(menu);

        if (cmd == 1) ShowFromTray();
        else if (cmd == 2) QuitApp();
    }

    // ── Directory Tree ──

    private void PopulateDirectories()
    {
        DirListBox.Items.Clear();
        _expanded.Clear();

        AddDirItem("~ (home)", HomeDir, null, "HOME");

        foreach (var baseDir in BaseDirs)
        {
            if (!Directory.Exists(baseDir)) continue;
            try
            {
                var subs = Directory.GetDirectories(baseDir)
                    .Select(d => new DirectoryInfo(d))
                    .Where(d => !d.Name.StartsWith("."))
                    .OrderBy(d => d.Name)
                    .ToList();
                if (subs.Count == 0) continue;

                var parentName = new DirectoryInfo(baseDir).Name;
                _expanded[parentName] = false;
                // Prefix "> " takes 2 chars before parent name
                AddDirItem($"> {parentName}", baseDir, null, "HEADER");

                foreach (var sub in subs)
                    AddDirItem($"  {sub.Name}", sub.FullName, parentName, "CHILD");
            }
            catch { }
        }
    }

    private void AddDirItem(string label, string path, string? parent, string kind)
    {
        var item = new DirItem
        {
            Label = label,
            Path = path,
            ParentName = parent,
            IsHeader = kind == "HEADER",
            DisplayLabel = label
        };
        DirListBox.Items.Add(item);
    }

    private void RefreshListDisplay()
    {
        var items = DirListBox.Items.Cast<DirItem>().ToList();
        DirListBox.Items.Clear();

        bool skip = false;
        string? skipParent = null;

        foreach (var item in items)
        {
            if (item.IsHeader)
            {
                var name = item.ParentName ?? item.Label[2..]; // "> name" → name
                bool expanded = _expanded.GetValueOrDefault(name, false);
                item.DisplayLabel = expanded ? $"v {name}" : $"> {name}";
                item.IsExpanded = expanded;
                DirListBox.Items.Add(item);

                skipParent = name;
                skip = !expanded;
            }
            else if (item.ParentName != null && skip && item.ParentName == skipParent)
            {
                continue; // skip collapsed children
            }
            else
            {
                DirListBox.Items.Add(item);
                // If we hit an item with a different parent, stop skipping
                if (skip && item.ParentName != skipParent)
                    skip = false;
            }
        }

        // Recolor headers to mauve
        for (int i = 0; i < DirListBox.Items.Count; i++)
        {
            if (DirListBox.Items[i] is DirItem di && di.IsHeader)
            {
                var container = DirListBox.ItemContainerGenerator.ContainerFromIndex(i) as ListBoxItem;
                if (container != null)
                    container.Foreground = new SolidColorBrush(
                        (Color)ColorConverter.ConvertFromString("#CBA6F7"));
            }
        }
    }

    private void DirListBox_PreviewMouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        var element = e.OriginalSource as DependencyObject;
        while (element != null && element != DirListBox)
        {
            if (element is ListBoxItem lbi && lbi.Content is DirItem item && item.IsHeader)
            {
                var name = item.ParentName ?? "";
                if (string.IsNullOrEmpty(name)) name = item.Label[2..]; // "> name" → name
                _expanded[name] = !_expanded.GetValueOrDefault(name, false);
                RefreshListDisplay();
                e.Handled = true;
                return;
            }
            element = VisualTreeHelper.GetParent(element);
        }
    }

    private void DirListBox_MouseDoubleClick(object sender, MouseButtonEventArgs e) => LaunchSelected();

    // ── Get Selected ──

    private (string label, string path)? GetSelected()
    {
        if (DirListBox.SelectedItem is DirItem item && !item.IsHeader)
            return (item.Label, item.Path);
        return null;
    }

    // ── Launch ──

    private void LaunchSelected()
    {
        var sel = GetSelected();
        if (sel == null) { StatusText.Text = "Please select a directory first"; return; }
        var (label, path) = sel.Value;
        // Strip indent prefix "  " (2 spaces) and any HOME marker
        var name = label.TrimStart();
        name = name == "~ (home)" ? "home" : name;
        StatusText.Text = LauncherService.LaunchClaude(path)
            ? $"Claude Code launched: {name}"
            : "Failed to launch";
        _ = ClearStatusAfter(5000);
    }

    private void BtnClaude_Click(object sender, RoutedEventArgs e) => LaunchSelected();
    private void BtnHermes_Click(object sender, RoutedEventArgs e) => LaunchHermes();

    private void LaunchHermes()
    {
        var sel = GetSelected();
        if (sel == null) { StatusText.Text = "Please select a directory first"; return; }
        var (label, path) = sel.Value;
        var name = label.TrimStart();
        name = name == "~ (home)" ? "home" : name;
        StatusText.Text = LauncherService.LaunchHermes(path)
            ? $"Hermes launched: {name}"
            : "Failed to launch";
        _ = ClearStatusAfter(5000);
    }

    private async Task ClearStatusAfter(int ms)
    {
        await Task.Delay(ms);
        await Dispatcher.InvokeAsync(() => StatusText.Text = "Lorien_Lab");
    }

    // ── Background Settings ──

    private void LoadCurrentSettings()
    {
        var (mode, value) = TerminalSettingsService.GetCurrentMode();
        switch (mode)
        {
            case TerminalSettingsService.BackgroundMode.Acrylic: RbAcrylic.IsChecked = true; break;
            case TerminalSettingsService.BackgroundMode.Opacity: RbOpacity.IsChecked = true; break;
            default: RbNone.IsChecked = true; break;
        }
        OpacitySlider.Value = value;
        OpacityLabel.Text = $"{value}%";
        UpdateSliderState();
    }

    private void UpdateSliderState()
    {
        bool enabled = RbNone.IsChecked != true;
        OpacitySlider.IsEnabled = enabled;
        OpacityLabel.Foreground = enabled
            ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#CDD6F4"))
            : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#585B70"));
    }

    private void OnModeChanged(object sender, RoutedEventArgs e) => UpdateSliderState();
    private void OnSliderChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (OpacityLabel != null)
            OpacityLabel.Text = $"{(int)e.NewValue}%";
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        TerminalSettingsService.BackgroundMode mode;
        if (RbAcrylic.IsChecked == true) mode = TerminalSettingsService.BackgroundMode.Acrylic;
        else if (RbOpacity.IsChecked == true) mode = TerminalSettingsService.BackgroundMode.Opacity;
        else mode = TerminalSettingsService.BackgroundMode.None;
        TerminalSettingsService.ApplyBackground(mode, (int)OpacitySlider.Value);
        StatusText.Text = $"Saved: {mode} at {(int)OpacitySlider.Value}%";
        _ = ClearStatusAfter(3000);
    }

    // ── System Tray ──

    private void CreateTrayIcon()
    {
        try
        {
            var handle = new WindowInteropHelper(this).Handle;
            if (handle == IntPtr.Zero) return;

            var exeDir = AppDomain.CurrentDomain.BaseDirectory;
            var icoPath = Path.Combine(exeDir, "Resources", "icon.ico");
            if (!File.Exists(icoPath))
                icoPath = Path.Combine(Directory.GetParent(exeDir)?.FullName ?? ".", "icon.png");

            IntPtr hIcon = IntPtr.Zero;
            try
            {
                if (File.Exists(icoPath))
                {
                    if (icoPath.EndsWith(".ico"))
                        hIcon = new System.Drawing.Icon(icoPath, 32, 32).Handle;
                    else
                        using (var bmp = new System.Drawing.Bitmap(icoPath))
                            hIcon = System.Drawing.Icon.FromHandle(bmp.GetHicon()).Handle;
                }
            }
            catch { }

            if (hIcon == IntPtr.Zero)
            {
                using var bmp = new System.Drawing.Bitmap(32, 32);
                using var g = System.Drawing.Graphics.FromImage(bmp);
                g.Clear(System.Drawing.Color.FromArgb(46, 26, 71));
                hIcon = System.Drawing.Icon.FromHandle(bmp.GetHicon()).Handle;
            }

            _trayIconHandle = hIcon;

            var nid = new NativeMethods.NOTIFYICONDATA
            {
                cbSize = Marshal.SizeOf<NativeMethods.NOTIFYICONDATA>(),
                hWnd = handle,
                uID = 1,
                uFlags = NativeMethods.NIF_ICON | NativeMethods.NIF_TIP | NativeMethods.NIF_MESSAGE,
                uCallbackMessage = NativeMethods.WM_TRAYICON,
                hIcon = hIcon,
                szTip = "Agent Launcher"
            };

            NativeMethods.Shell_NotifyIcon(NativeMethods.NIM_ADD, ref nid);
            _trayAdded = true;
        }
        catch { }
    }

    private void UpdateTrayTooltip(AggregateStats stats)
    {
        if (!_trayAdded) return;

        var tip = "Lorien_Lab";
        tip += $"\n{stats.ActiveCount} active  {stats.IdleCount} idle";
        tip += $"\n{Formatting.FmtTokens(stats.TotalInput)} in  {Formatting.FmtTokens(stats.TotalOutput)} out";
        if (stats.TotalCost > 0.001)
            tip += $"  {Formatting.FmtCost(stats.TotalCost)}";
        foreach (var s in stats.Sessions.Take(5))
        {
            var icon = s.IsBusy ? "*" : "-";
            var sn = s.ShortDir.Length > 24 ? s.ShortDir[..24] : s.ShortDir;
            var tk = Formatting.FmtTokens(s.InputTokens);
            tip += $"\n{icon} {sn,-24} {tk,6} in";
        }
        if (tip.Length > 127) tip = tip[..127];

        var handle = new WindowInteropHelper(this).Handle;
        var nid = new NativeMethods.NOTIFYICONDATA
        {
            cbSize = Marshal.SizeOf<NativeMethods.NOTIFYICONDATA>(),
            hWnd = handle,
            uID = 1,
            uFlags = NativeMethods.NIF_TIP,
            szTip = tip
        };
        NativeMethods.Shell_NotifyIcon(NativeMethods.NIM_MODIFY, ref nid);
    }

    private void OnClosing(object? sender, CancelEventArgs e)
    {
        e.Cancel = true;
        this.Hide();
    }

    private void ShowFromTray()
    {
        Dispatcher.Invoke(() =>
        {
            this.Show();
            this.WindowState = WindowState.Normal;
            this.Activate();
            this.Focus();
        });
    }

    private void QuitApp()
    {
        if (_trayAdded)
        {
            var handle = new WindowInteropHelper(this).Handle;
            var nid = new NativeMethods.NOTIFYICONDATA
            {
                cbSize = Marshal.SizeOf<NativeMethods.NOTIFYICONDATA>(),
                hWnd = handle,
                uID = 1
            };
            NativeMethods.Shell_NotifyIcon(NativeMethods.NIM_DELETE, ref nid);
            _trayAdded = false;
        }
        if (_trayIconHandle != IntPtr.Zero)
        {
            NativeMethods.DestroyIcon(_trayIconHandle);
            _trayIconHandle = IntPtr.Zero;
        }
        _monitor.Stop();
        this.Closing -= OnClosing;
        this.Close();
    }

    // ── Session Panel ──

    private void CreateSessionPanel()
    {
        if (_sessionPanel != null) return;
        _sessionPanel = new SessionPanel();
        _sessionPanel.Show();
        _sessionPanel.Activate(); // bring to front
    }

    private void OnStatsUpdate(AggregateStats stats)
    {
        Dispatcher.BeginInvoke(() =>
        {
            _lastStats = stats;
            UpdateTrayTooltip(stats);
            UpdateSessionPanel(stats);

            var curStatuses = stats.Sessions.ToDictionary(s => s.SessionId, s => s.Status);
            foreach (var kv in curStatuses)
            {
                if (_lastStatuses.TryGetValue(kv.Key, out var prev) &&
                    prev == "busy" && kv.Value == "idle")
                {
                    _createdSessions.Add(kv.Key);
                    _ = Task.Run(async () =>
                    {
                        await Task.Delay(500);
                        await Dispatcher.InvokeAsync(LauncherService.BringTerminalToFront);
                    });
                }
            }
            _lastStatuses.Clear();
            foreach (var kv in curStatuses) _lastStatuses[kv.Key] = kv.Value;

            var toRemove = _createdSessions
                .Where(s => curStatuses.GetValueOrDefault(s) != "busy").ToList();
            if (toRemove.Count > 0)
            {
                _ = Task.Run(async () =>
                {
                    await Task.Delay(5000);
                    await Dispatcher.InvokeAsync(() =>
                    {
                        foreach (var sid in toRemove) _createdSessions.Remove(sid);
                        if (_lastStats != null) UpdateSessionPanel(_lastStats);
                    });
                });
            }
        });
    }

    private void UpdateSessionPanel(AggregateStats stats)
    {
        if (_sessionPanel == null) return;

        var idKey = string.Join("|", stats.Sessions
            .Select(s => $"{s.SessionId}:{s.Status}"));
        bool same = _lastPanelIdKey == idKey;
        _lastPanelIdKey = idKey;

        foreach (var s in stats.Sessions)
            s.IsNewlyCompleted = _createdSessions.Contains(s.SessionId);

        if (same)
            _sessionPanel.PatchValues(stats);
        else
            _sessionPanel.Rebuild(stats);
    }

    protected override void OnStateChanged(EventArgs e)
    {
        base.OnStateChanged(e);
        if (WindowState == WindowState.Minimized) this.Hide();
    }
}
