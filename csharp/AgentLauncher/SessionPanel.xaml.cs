using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shapes;
using AgentLauncher.Models;

namespace AgentLauncher;

/// <summary>
/// Floating borderless panel for real-time session monitoring.
/// Features: rounded corners, drag, edge snapping, per-letter wave animation,
/// star indicators, HSL gradient progress bars with sawtooth fill.
/// </summary>
public partial class SessionPanel : Window
{
    // ── Animation state ──
    private double _phase;
    private readonly List<List<(TextBlock label, Color baseColor, double offset)>> _waveLabelGroups = new();
    private readonly List<(Canvas canvas, double size, double cx, double cy)> _dotCanvases = new();
    private readonly List<(Canvas canvas, double barW, double fillW, double barH, double pct)> _waveBars = new();
    private readonly List<TextBlock> _barTexts = new();
    private long _frameCount;

    // ── Drag state ──
    private Point _dragStart;

    // ── Colors ──
    private static readonly Color CText = ColorFromHex("#CDD6F4");
    private static readonly Color CGreen = ColorFromHex("#A6E3A1");
    private static readonly Color CYellow = ColorFromHex("#F9E2AF");
    private static readonly Color CSubtle = ColorFromHex("#585B70");
    private static readonly Color CListBg = ColorFromHex("#313244");
    private static readonly Color CBorder = ColorFromHex("#45475A");
    private static readonly Color CMauve = ColorFromHex("#CBA6F7");
    private static readonly Color CBase = ColorFromHex("#1E1E2E");
    private static readonly Color CSub = ColorFromHex("#A6ADC8");

    private int _panelH;

    public SessionPanel()
    {
        InitializeComponent();
        this.Loaded += (s, e) =>
        {
            PositionDefault();
            CompositionTarget.Rendering += OnRendering;
        };
    }

    // ── Window Setup ──

    private void PositionDefault()
    {
        // Use WPF's built-in WorkArea — reliable, no P/Invoke needed
        var area = SystemParameters.WorkArea;
        double sw = area.Right;
        double sb = area.Bottom;
        double w = this.ActualWidth > 10 ? this.ActualWidth : 420;
        double h = this.ActualHeight > 10 ? this.ActualHeight : 320;
        this.Left = Math.Max(0, sw - w - 10);
        this.Top = Math.Max(0, sb - h - 10);
    }

    // ── Drag ──

    private void Header_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        _dragStart = e.GetPosition(this);
        this.CaptureMouse();
        this.MouseMove += Panel_MouseMove;
        this.MouseLeftButtonUp += Panel_MouseLeftButtonUp;
    }

    private void Panel_MouseMove(object sender, MouseEventArgs e)
    {
        if (e.LeftButton == MouseButtonState.Pressed)
        {
            var pos = e.GetPosition(this);
            double x = this.Left + pos.X - _dragStart.X;
            double y = this.Top + pos.Y - _dragStart.Y;

            var area = SystemParameters.WorkArea;
            double sw = area.Right;
            double sb = area.Bottom;
            double pw = this.ActualWidth;
            double ph = this.ActualHeight;
            const int snap = 40;

            if (Math.Abs(x) < snap) x = 0;
            if (Math.Abs(x + pw - sw) < snap) x = sw - pw;
            if (Math.Abs(y) < snap) y = 0;
            if (Math.Abs(y + ph - sb) < snap) y = sb - ph;

            this.Left = x;
            this.Top = y;
        }
    }

    private void Panel_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        this.MouseMove -= Panel_MouseMove;
        this.MouseLeftButtonUp -= Panel_MouseLeftButtonUp;
        this.ReleaseMouseCapture();
    }

    // ── Patch-Only Update (anti-flicker: only update percentage text) ──

    public void PatchValues(AggregateStats stats)
    {
        for (int i = 0; i < stats.Sessions.Count && i < _barTexts.Count; i++)
        {
            _barTexts[i].Text = $"{stats.Sessions[i].ContextPct:F1}%";
        }
    }

    // ── Full Rebuild ──

    public void Rebuild(AggregateStats stats)
    {
        BodyPanel.Children.Clear();
        _waveLabelGroups.Clear();
        _dotCanvases.Clear();
        _waveBars.Clear();
        _barTexts.Clear();

        // Separator
        BodyPanel.Children.Add(new Border
        {
            Height = 1,
            Background = new SolidColorBrush(CBorder),
            Margin = new Thickness(0, 0, 0, 2)
        });

        if (stats.Sessions.Count == 0)
        {
            BodyPanel.Children.Add(new TextBlock
            {
                Text = "No active sessions",
                Foreground = new SolidColorBrush(CSubtle),
                FontFamily = new FontFamily("Segoe UI"),
                FontSize = 10,
                Margin = new Thickness(0, 10, 0, 0),
                HorizontalAlignment = HorizontalAlignment.Center
            });
            return;
        }

        int row = 0;
        foreach (var se in stats.Sessions.Take(12))
        {
            var rowGrid = new Grid
            {
                Margin = new Thickness(0, 1, 0, 1)
            };
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });  // star
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) }); // info

            // ── Star indicator ──
            double d = 16, r = d / 2;
            var dotCanvas = new Canvas
            {
                Width = d,
                Height = d,
                Background = new SolidColorBrush(CBase),
                Margin = new Thickness(2, 2, 0, 0)
            };
            DrawStar(dotCanvas, d, r, se, row);
            Grid.SetColumn(dotCanvas, 0);
            rowGrid.Children.Add(dotCanvas);

            // Track for animation if busy
            if (se.IsBusy)
                _dotCanvases.Add((dotCanvas, d, r, r));

            // ── Info panel ──
            var infoStack = new StackPanel
            {
                Margin = new Thickness(6, 0, 6, 0)
            };
            Grid.SetColumn(infoStack, 1);
            rowGrid.Children.Add(infoStack);

            // Line 1: Directory name + model + git + subagents
            var line1 = new WrapPanel { Margin = new Thickness(0, 1, 0, 0) };

            if (se.IsBusy)
            {
                // Per-letter wave for directory name
                var waveGroup = new List<(TextBlock, Color, double)>();
                for (int ci = 0; ci < se.ShortDir.Length; ci++)
                {
                    var ch = se.ShortDir[ci].ToString();
                    var tb = new TextBlock
                    {
                        Text = ch,
                        Foreground = new SolidColorBrush(CText),
                        FontFamily = new FontFamily("Consolas"),
                        FontSize = 11,
                        FontWeight = FontWeights.Bold
                    };
                    line1.Children.Add(tb);
                    waveGroup.Add((tb, CText, 0.35));
                }
                _waveLabelGroups.Add(waveGroup);
            }
            else
            {
                line1.Children.Add(new TextBlock
                {
                    Text = se.ShortDir,
                    Foreground = new SolidColorBrush(CText),
                    FontFamily = new FontFamily("Consolas"),
                    FontSize = 12,
                    FontWeight = FontWeights.Bold
                });
            }

            // Model badge
            if (!string.IsNullOrEmpty(se.Model) && se.Model != "?")
            {
                line1.Children.Add(new TextBlock
                {
                    Text = $" [{se.ModelShort}]",
                    Foreground = new SolidColorBrush(CSubtle),
                    FontFamily = new FontFamily("Consolas"),
                    FontSize = 10
                });
            }

            // Git branch
            if (!string.IsNullOrEmpty(se.GitBranch))
            {
                line1.Children.Add(new TextBlock
                {
                    Text = $" {se.GitBranch}",
                    Foreground = new SolidColorBrush(CSubtle),
                    FontFamily = new FontFamily("Consolas"),
                    FontSize = 10
                });
            }

            // Subagent count
            if (se.SubagentCount > 0)
            {
                line1.Children.Add(new TextBlock
                {
                    Text = $" [{se.SubagentCount}]",
                    Foreground = new SolidColorBrush(CMauve),
                    FontFamily = new FontFamily("Consolas"),
                    FontSize = 10
                });
            }

            // Status word
            if (se.IsBusy)
            {
                line1.Children.Add(new TextBlock { Text = "  ", Foreground = new SolidColorBrush(CBase), FontSize = 10 });
                var statusGroup = new List<(TextBlock, Color, double)>();
                foreach (var ch in "RUNNING")
                {
                    var tb = new TextBlock
                    {
                        Text = ch.ToString(),
                        Foreground = new SolidColorBrush(CGreen),
                        FontFamily = new FontFamily("Consolas"),
                        FontSize = 11,
                        FontWeight = FontWeights.Bold
                    };
                    line1.Children.Add(tb);
                    statusGroup.Add((tb, CGreen, 0.4));
                }
                // Find the wave group we just added and add the status chars to it
                if (_waveLabelGroups.Count > 0)
                    _waveLabelGroups[^1].AddRange(statusGroup);
            }
            else if (se.IsNewlyCompleted)
            {
                line1.Children.Add(new TextBlock { Text = "  ", Foreground = new SolidColorBrush(CBase), FontSize = 10 });
                for (int ci = 0; ci < "DONE".Length; ci++)
                {
                    line1.Children.Add(new TextBlock
                    {
                        Text = "DONE"[ci].ToString(),
                        Foreground = new SolidColorBrush(CYellow),
                        FontFamily = new FontFamily("Consolas"),
                        FontSize = 11,
                        FontWeight = FontWeights.Bold
                    });
                }
            }

            infoStack.Children.Add(line1);

            // Line 2: Progress bar + percentage
            var line2 = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                Margin = new Thickness(0, 2, 0, 0)
            };

            double barW = 200, barH = 5;
            var barCanvas = new Canvas
            {
                Width = barW,
                Height = barH,
                Background = Brushes.Transparent
            };

            // Background
            barCanvas.Children.Add(new System.Windows.Shapes.Rectangle
            {
                Width = barW,
                Height = barH,
                Fill = new SolidColorBrush(CListBg)
            });

            // Foreground gradient segments
            double fillW = Math.Max(3, barW * Math.Max(0.005, se.ContextPct / 100.0));
            DrawGradientBar(barCanvas, barW, barH, fillW, se.ContextPct, 0); // initial static fill

            line2.Children.Add(barCanvas);

            // Track for animation
            if (se.IsBusy)
                _waveBars.Add((barCanvas, barW, fillW, barH, se.ContextPct));

            // Percentage label
            var pctLabel = new TextBlock
            {
                Text = $"{se.ContextPct:F1}%",
                Foreground = new SolidColorBrush(CSub),
                FontFamily = new FontFamily("Consolas"),
                FontSize = 10,
                VerticalAlignment = VerticalAlignment.Center,
                Margin = new Thickness(6, 0, 0, 0)
            };
            line2.Children.Add(pctLabel);
            _barTexts.Add(pctLabel);

            infoStack.Children.Add(line2);
            BodyPanel.Children.Add(rowGrid);
            row++;
        }

        // Resize panel height — compute from row count for exact fit
        int sessionCount = stats.Sessions.Count;
        double neededH;
        if (sessionCount == 0)
        {
            neededH = 80;
        }
        else
        {
            // Each row: ~48px (star 16 + text ~20 + bar ~8 + padding ~4)
            const double rowHeight = 48;
            // header 28 + separator 1 + body top/bottom padding 14 + rows
            neededH = 28 + 1 + 14 + rowHeight * sessionCount + 8;
        }
        neededH = Math.Max(80, neededH);

        double sb = SystemParameters.WorkArea.Bottom;
        double y2 = this.Top;
        double bottomEdge = y2 + _panelH;
        if (Math.Abs(bottomEdge - sb) < 60)
            y2 = Math.Max(0, sb - neededH);
        else if (y2 <= 5)
            y2 = 0;

        this.Height = neededH;
        this.Top = y2;
        _panelH = (int)neededH;
    }

    // ── Star Drawing ──

    private static void DrawStar(Canvas cv, double d, double r, SessionSnapshot se, int row)
    {
        double cx = r, cy = r;

        if (se.IsBusy)
        {
            // Will be animated in OnRendering
            double sz = r - 2;
            var pts = StarPoints(cx, cy, sz);
            cv.Children.Add(new Polygon
            {
                Points = new PointCollection(pts),
                Fill = new SolidColorBrush(CGreen),
                StrokeThickness = 0
            });
        }
        else if (se.IsNewlyCompleted)
        {
            double sz = r - 2;
            var pts = StarPoints(cx, cy, sz);
            cv.Children.Add(new Polygon
            {
                Points = new PointCollection(pts),
                Fill = new SolidColorBrush(CYellow),
                StrokeThickness = 0
            });
        }
        else
        {
            double sz = r - 6;
            var pts = StarPoints(cx, cy, sz);
            cv.Children.Add(new Polygon
            {
                Points = new PointCollection(pts),
                Fill = Brushes.Transparent,
                Stroke = new SolidColorBrush(CSubtle),
                StrokeThickness = 1
            });
        }
    }

    private static Point[] StarPoints(double cx, double cy, double sz)
    {
        double p = 0.38; // indent ratio
        return new[]
        {
            new Point(cx, cy - sz),           // top
            new Point(cx + sz * p, cy - sz * p), // top-right indent
            new Point(cx + sz, cy),           // right
            new Point(cx + sz * p, cy + sz * p), // bottom-right indent
            new Point(cx, cy + sz),           // bottom
            new Point(cx - sz * p, cy + sz * p), // bottom-left indent
            new Point(cx - sz, cy),           // left
            new Point(cx - sz * p, cy - sz * p), // top-left indent
        };
    }

    // ── Gradient Bar ──

    private static void DrawGradientBar(Canvas cv, double barW, double barH, double fillW, double pct, double animT)
    {
        // Remove existing fill segments (keep background rect at index 0)
        while (cv.Children.Count > 1) cv.Children.RemoveAt(1);

        int nSeg = 20;
        for (int i = 0; i < nSeg; i++)
        {
            double tVal = i / (double)(nSeg - 1) * Math.Min(pct / 100.0, 1.0);
            double hue = (1.0 - tVal) * 0.33;
            var (r, g, b) = HsvToRgb(hue, 0.9, 0.95);

            double x0 = fillW * i / nSeg;
            double x1 = fillW * (i + 1) / nSeg;
            if (x1 <= x0) continue;

            var brush = new SolidColorBrush(Color.FromRgb((byte)(r * 255), (byte)(g * 255), (byte)(b * 255)));
            cv.Children.Add(new System.Windows.Shapes.Rectangle
            {
                Width = x1 - x0,
                Height = barH,
                Fill = brush,
                Margin = new Thickness(x0, 0, 0, 0),
                HorizontalAlignment = HorizontalAlignment.Left,
                RadiusX = 1,
                RadiusY = 1
            });
        }
    }

    // ── Animation Loop ──

    private void OnRendering(object? sender, EventArgs e)
    {
        _frameCount++;
        // Update clock once per second (60fps / 60 = 1s)
        if (_frameCount % 60 == 0 && ClockLabel != null)
        {
            try { ClockLabel.Text = DateTime.Now.ToString("HH:mm:ss"); }
            catch { }
        }

        // Update phase ~10fps equivalent
        if (_frameCount % 6 != 0) return;

        _phase = (_phase + 0.14) % (2 * Math.PI);
        double phase = _phase;

        // ── Per-letter wave animation ──
        foreach (var group in _waveLabelGroups)
        {
            int ci = 0;
            foreach (var (label, baseColor, offset) in group)
            {
                try
                {
                    label.Foreground = new SolidColorBrush(PulseColor(baseColor, phase - ci * offset));
                }
                catch { }
                ci++;
            }
        }

        // ── Star dot animation ──
        foreach (var (cv, d, cx, cy) in _dotCanvases)
        {
            try
            {
                // Clear previous star polygons (keep only if needed)
                cv.Children.Clear();
                double sz = (d / 2.0 - 4) * (0.85 + 0.15 * Math.Sin(phase));
                var col = PulseColor(CGreen, phase);
                var pts = StarPoints(cx, cy, sz);
                cv.Children.Add(new Polygon
                {
                    Points = new PointCollection(pts),
                    Fill = new SolidColorBrush(col),
                    StrokeThickness = 0
                });
                // Glow ring
                var glowCol = PulseColor(CGreen, phase - 0.4);
                var pts2 = StarPoints(cx, cy, sz + 1);
                cv.Children.Add(new Polygon
                {
                    Points = new PointCollection(pts2),
                    Fill = Brushes.Transparent,
                    Stroke = new SolidColorBrush(glowCol),
                    StrokeThickness = 1
                });
            }
            catch { }
        }

        // ── Progress bar sawtooth animation ──
        foreach (var (cv, barW, fillW, barH, pct) in _waveBars)
        {
            try
            {
                // Sawtooth: 0 → peak → instant reset
                double t = (phase * 0.5) % 1;
                double animatedFillW = Math.Max(3, fillW * t);
                DrawGradientBar(cv, barW, barH, animatedFillW, pct, t);
            }
            catch { }
        }
    }

    // ── Color Helpers ──

    private static Color PulseColor(Color baseColor, double phase)
    {
        // sin² pulse: 0→1→0, scaled to 0→170 boost
        double intensity = Math.Pow(Math.Sin(phase), 2);
        byte boost = (byte)(170 * intensity);
        byte r = (byte)Math.Min(255, baseColor.R + boost);
        byte g = (byte)Math.Min(255, baseColor.G + boost);
        byte b = (byte)Math.Min(255, baseColor.B + boost);
        return Color.FromRgb(r, g, b);
    }

    private static (double r, double g, double b) HsvToRgb(double h, double s, double v)
    {
        int hi = (int)(h * 6) % 6;
        double f = h * 6 - Math.Floor(h * 6);
        double p = v * (1 - s);
        double q = v * (1 - f * s);
        double t = v * (1 - (1 - f) * s);

        return hi switch
        {
            0 => (v, t, p),
            1 => (q, v, p),
            2 => (p, v, t),
            3 => (p, q, v),
            4 => (t, p, v),
            _ => (v, p, q),
        };
    }

    private static Color ColorFromHex(string hex)
    {
        return (Color)ColorConverter.ConvertFromString(hex);
    }
}
