using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace AgentLauncher.Helpers;

/// <summary>
/// P/Invoke declarations for Windows API features:
/// rounded corners, acrylic, DPI awareness, window enumeration, taskbar detection.
/// </summary>
public static class NativeMethods
{
    public const int GWL_EXSTYLE = -20;
    public const int WS_EX_LAYERED = 0x80000;
    public const int WS_EX_APPWINDOW = 0x40000;
    public const int WS_EX_TOOLWINDOW = 0x80;
    public const int WS_EX_TRANSPARENT = 0x20;
    public const uint LWA_ALPHA = 0x2;
    public const uint LWA_COLORKEY = 0x1;

    public const int SPI_GETWORKAREA = 0x0030;
    public const int SHAPPBAR_FLAG_AUTOHIDE = 0x00000001;
    public const int ABM_GETSTATE = 0x00000004;

    // Window composition attributes (DWM)
    public const int DWMWA_USE_IMMERSIVE_DARK_MODE = 20;
    public const int DWMWA_SYSTEMBACKDROP_TYPE = 38;
    public const int DWMWA_MICA = 1029;
    public const int DWMWA_WINDOW_CORNER_PREFERENCE = 33;

    public const int DWMWCP_ROUND = 2;
    public const int DWMWCP_ROUNDSMALL = 3;

    [DllImport("user32.dll")]
    public static extern int GetWindowLong(IntPtr hWnd, int nIndex);

    [DllImport("user32.dll")]
    public static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);

    [DllImport("user32.dll")]
    public static extern bool SetLayeredWindowAttributes(IntPtr hWnd, uint crKey, byte bAlpha, uint dwFlags);

    [DllImport("dwmapi.dll", PreserveSig = true)]
    public static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);

    [DllImport("dwmapi.dll")]
    public static extern int DwmExtendFrameIntoClientArea(IntPtr hWnd, ref MARGINS pMarInset);

    [DllImport("user32.dll")]
    public static extern bool SetProcessDpiAwarenessContext(int dpiFlag);

    [DllImport("shcore.dll")]
    public static extern int SetProcessDpiAwareness(int awareness);

    [DllImport("gdi32.dll")]
    public static extern IntPtr CreateRoundRectRgn(int nLeft, int nTop, int nRight, int nBottom, int nWidthEllipse, int nHeightEllipse);

    [DllImport("user32.dll")]
    public static extern int SetWindowRgn(IntPtr hWnd, IntPtr hRgn, bool bRedraw);

    [DllImport("user32.dll")]
    public static extern bool SystemParametersInfoW(int uiAction, int uiParam, ref RECT pvParam, int fWinIni);

    [DllImport("user32.dll")]
    public static extern int EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextW(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern IntPtr GetDesktopWindow();

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, ref RECT lpRect);

    [DllImport("shell32.dll")]
    public static extern IntPtr SHAppBarMessage(uint dwMessage, ref APPBARDATA pData);

    [DllImport("user32.dll")]
    public static extern IntPtr MonitorFromWindow(IntPtr hwnd, uint dwFlags);

    [DllImport("user32.dll")]
    public static extern bool GetMonitorInfoW(IntPtr hMonitor, ref MONITORINFO lpmi);

    // DPI awareness levels
    public const int DPI_AWARENESS_PER_MONITOR_AWARE = 2;
    public const int DPI_AWARENESS_SYSTEM_AWARE = 1;

    // ShowWindow constants
    public const int SW_RESTORE = 9;

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left, Top, Right, Bottom;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct MARGINS
    {
        public int cxLeftWidth, cxRightWidth, cyTopHeight, cyBottomHeight;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct APPBARDATA
    {
        public int cbSize;
        public IntPtr hWnd;
        public uint uCallbackMessage;
        public uint uEdge;
        public RECT rc;
        public IntPtr lParam;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct MONITORINFO
    {
        public int cbSize;
        public RECT rcMonitor;
        public RECT rcWork;
        public uint dwFlags;
    }

    /// <summary>
    /// Apply dark title bar + rounded corners to a WPF window.
    /// </summary>
    public static void ApplyDarkMode(Window window)
    {
        var handle = new WindowInteropHelper(window).EnsureHandle();
        int dark = 1;
        DwmSetWindowAttribute(handle, DWMWA_USE_IMMERSIVE_DARK_MODE, ref dark, 4);
        int corner = DWMWCP_ROUNDSMALL;
        DwmSetWindowAttribute(handle, DWMWA_WINDOW_CORNER_PREFERENCE, ref corner, 4);
    }

    /// <summary>
    /// Apply Mica backdrop (Windows 11 only, fails silently on Win10).
    /// </summary>
    public static void ApplyMica(Window window)
    {
        var handle = new WindowInteropHelper(window).EnsureHandle();
        int backdrop = DWMWA_MICA;
        DwmSetWindowAttribute(handle, DWMWA_SYSTEMBACKDROP_TYPE, ref backdrop, 4);
    }

    /// <summary>
    /// Get the work area bottom (screen bottom minus taskbar).
    /// </summary>
    public static int GetWorkAreaBottom()
    {
        var work = new RECT();
        SystemParametersInfoW(SPI_GETWORKAREA, 0, ref work, 0);
        return work.Bottom;
    }

    /// <summary>
    /// Get the screen bottom taking auto-hide taskbar into account.
    /// </summary>
    public static int GetEffectiveScreenBottom()
    {
        var work = new RECT();
        var full = new RECT();
        SystemParametersInfoW(SPI_GETWORKAREA, 0, ref work, 0);
        GetWindowRect(GetDesktopWindow(), ref full);
        int visibleTb = full.Bottom - work.Bottom;
        if (visibleTb > 0)
            return work.Bottom;

        // Auto-hide: reserve 4px trigger zone
        try
        {
            var abd = new APPBARDATA { cbSize = Marshal.SizeOf<APPBARDATA>() };
            int state = (int)SHAppBarMessage(ABM_GETSTATE, ref abd);
            if ((state & SHAPPBAR_FLAG_AUTOHIDE) != 0)
                return full.Bottom - 4;
        }
        catch { }

        return full.Bottom;
    }

    // ── System Tray (Shell_NotifyIcon) ──

    public const int NIM_ADD = 0;
    public const int NIM_MODIFY = 1;
    public const int NIM_DELETE = 2;
    public const int NIM_SETVERSION = 4;
    public const int NIF_MESSAGE = 1;
    public const int NIF_ICON = 2;
    public const int NIF_TIP = 4;
    public const int NIF_GUID = 0x20;
    public const int NIF_INFO = 0x10;
    public const int NIIF_NONE = 0;
    public const int WM_USER = 0x0400;
    public const int WM_TRAYICON = WM_USER + 1;

    [DllImport("shell32.dll", CharSet = CharSet.Auto)]
    public static extern bool Shell_NotifyIcon(int dwMessage, ref NOTIFYICONDATA lpData);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
    public struct NOTIFYICONDATA
    {
        public int cbSize;
        public IntPtr hWnd;
        public uint uID;
        public uint uFlags;
        public uint uCallbackMessage;
        public IntPtr hIcon;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
        public string szTip;
        public uint dwState;
        public uint dwStateMask;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)]
        public string szInfo;
        public uint uVersion;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
        public string szInfoTitle;
        public uint dwInfoFlags;
        public Guid guidItem;
        public IntPtr hBalloonIcon;
    }

    [DllImport("user32.dll")]
    public static extern IntPtr LoadIcon(IntPtr hInstance, IntPtr lpIconName);

    [DllImport("user32.dll")]
    public static extern bool DestroyIcon(IntPtr hIcon);

    [DllImport("user32.dll")]
    public static extern IntPtr CreatePopupMenu();

    [DllImport("user32.dll")]
    public static extern bool AppendMenu(IntPtr hMenu, uint uFlags, uint uIDNewItem, string lpNewItem);

    [DllImport("user32.dll")]
    public static extern bool SetMenuDefaultItem(IntPtr hMenu, uint uItem, bool fByPos);

    [DllImport("user32.dll")]
    public static extern uint TrackPopupMenu(IntPtr hMenu, uint uFlags, int x, int y, int nReserved, IntPtr hWnd, IntPtr prcRect);

    [DllImport("user32.dll")]
    public static extern bool DestroyMenu(IntPtr hMenu);

    [DllImport("user32.dll")]
    public static extern bool GetCursorPos(out POINT lpPoint);

    public const uint MF_STRING = 0x00000000;
    public const uint TPM_RIGHTBUTTON = 0x0002;
    public const uint TPM_BOTTOMALIGN = 0x0020;
    public const uint TPM_RETURNCMD = 0x0100;

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT
    {
        public int X, Y;
    }

    /// <summary>
    /// Find terminal windows launched by our PIDs.
    /// </summary>
    public static IntPtr? FindTerminalWindow(HashSet<int> pids)
    {
        IntPtr? found = null;

        EnumWindows((hwnd, _) =>
        {
            var sb = new System.Text.StringBuilder(256);
            GetWindowTextW(hwnd, sb, 255);
            var title = sb.ToString();
            if (string.IsNullOrEmpty(title) ||
                (!title.Contains("Claude Code") && !title.Contains("Hermes")))
                return true;

            GetWindowThreadProcessId(hwnd, out uint pid);
            if (pids.Contains((int)pid))
            {
                found = hwnd;
                return false;
            }
            return true;
        }, IntPtr.Zero);

        return found;
    }
}
