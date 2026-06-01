using Avalonia;
using Avalonia.Media;
using Avalonia.Styling;
using Avalonia.VisualTree;
using ColorTextBlock.Avalonia;
using Markdown.Avalonia;

namespace SRAFrontend.Controls;

/// <summary>
/// 修复了暗色主题下标题颜色问题的 MarkdownScrollViewer
/// 解决 Markdown.Avalonia.Tight 库标题硬编码为黑色的问题
/// </summary>
public class ThemedMarkdownScrollViewer : MarkdownScrollViewer
{
    public ThemedMarkdownScrollViewer()
    {
        LayoutUpdated += OnLayoutUpdated;
    }

    private void OnLayoutUpdated(object? sender, System.EventArgs e)
    {
        ForceHeadingColor(this);
    }

    private void ForceHeadingColor(Visual? visual)
    {
        if (visual == null) return;

        // 只处理 Heading 类的 CTextBlock
        if (visual is CTextBlock ctb &&
            (ctb.Classes.Contains("Heading1") ||
             ctb.Classes.Contains("Heading2") ||
             ctb.Classes.Contains("Heading3") ||
             ctb.Classes.Contains("Heading4") ||
             ctb.Classes.Contains("Heading5") ||
             ctb.Classes.Contains("Heading6")))
        {
            // 根据当前主题动态设置颜色
            var targetColor = GetThemeForegroundColor();
            if (!Equals(ctb.Foreground, targetColor))
            {
                ctb.Foreground = targetColor;
            }
        }

        foreach (var child in visual.GetVisualChildren())
        {
            ForceHeadingColor(child);
        }
    }

    /// <summary>
    /// 根据当前主题获取合适的前景色
    /// </summary>
    private IBrush GetThemeForegroundColor()
    {
        var app = Application.Current;
        if (app == null) return Brushes.White;

        var themeVariant = app.ActualThemeVariant;
        
        // 根据主题返回相应的颜色
        return themeVariant == ThemeVariant.Dark ? Brushes.White : Brushes.Black;
    }
}
