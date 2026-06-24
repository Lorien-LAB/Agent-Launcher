using System.Globalization;
using System.Windows.Data;
using System.Windows.Media;

namespace AgentLauncher.Converters;

public class StatusToColorConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is string status)
        {
            return status == "busy"
                ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#A6E3A1"))
                : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#585B70"));
        }
        return new SolidColorBrush((Color)ColorConverter.ConvertFromString("#585B70"));
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

public class BoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        bool b = value is true;
        bool invert = parameter is string s && s == "invert";
        return (b ^ invert) ? System.Windows.Visibility.Visible : System.Windows.Visibility.Collapsed;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

public class PercentageToWidthConverter : IMultiValueConverter
{
    public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
    {
        if (values.Length >= 2 && values[0] is double pct && values[1] is double totalWidth)
        {
            return Math.Max(3, totalWidth * Math.Max(0.005, pct / 100.0));
        }
        return 3.0;
    }

    public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
