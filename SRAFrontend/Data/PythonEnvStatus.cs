namespace SRAFrontend.Data;

/// <summary>
/// Python 环境状态枚举
/// </summary>
public enum PythonEnvStatus
{
    /// <summary>
    /// 环境完全就绪
    /// </summary>
    AllSet = 0,

    /// <summary>
    /// Python 未安装
    /// </summary>
    PythonNotInstalled = 1,

    /// <summary>
    /// Python 版本不匹配（需 3.12.x）
    /// </summary>
    PythonVersionMismatch = 2,

    /// <summary>
    /// Pip 未安装
    /// </summary>
    PipNotInstalled = 3,

    /// <summary>
    /// 依赖包（requirements.txt）未安装
    /// </summary>
    RequirementsNotInstalled = 4
    
}