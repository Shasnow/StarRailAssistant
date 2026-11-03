using Xunit;

// 资源文化、SukiTheme、Application.RequestedThemeVariant 都是进程级状态，用例必须串行。
[assembly: CollectionBehavior(DisableTestParallelization = true)]
