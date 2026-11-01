/*
 * SRA-cli 启动器
 *
 * 取代旧版由 Nuitka 打包的 SRA-cli.exe：把命令行原样转发给随包分发的内嵌
 * Python 运行时，即
 *
 *     <程序根目录>\python\python.exe <程序根目录>\main.py <原参数...>
 *
 * 与旧版保持一致的行为：
 *   - 控制台程序，标准输入/输出/错误原样继承（管道与重定向均可用）
 *   - 清单取 asInvoker，不强制提权；需要管理员权限时由 SRACore 启动后自行提权
 *   - 以子进程退出码作为自身退出码，便于脚本判断任务成败；Ctrl+C / Ctrl+Break
 *     时本进程不退出，等子进程优雅退出后再转发其退出码
 *
 * 工作目录固定为程序根目录：tasks/ 与 resources/ 均按 cwd 解析，若沿用调用方
 * 的当前目录，从其他位置执行时会出现找不到任务或资源的问题。
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#define SRA_MAX_COMMAND_LINE 32767  /* Windows CreateProcess 命令行长度上限 */
#define SRA_BUFFER_COUNT(array) (sizeof(array) / sizeof((array)[0]))

/*
 * 输出诊断信息。
 *
 * 不能用 fputws/fwprintf：把宽字符写进被重定向的（字节流）stderr 时，CRT 会按 "C"
 * 区域逐字符转换，遇到中文即停止，提示信息会被截断。控制台句柄需要 UTF-16，
 * 管道/重定向则转成 UTF-8 字节写出，与前端约定的编码一致。
 */
static void write_error(const wchar_t *text)
{
    HANDLE handle = GetStdHandle(STD_ERROR_HANDLE);
    DWORD mode;
    DWORD written;
    DWORD length;
    int utf8_length;
    char *utf8;

    if (handle == NULL || handle == INVALID_HANDLE_VALUE || text == NULL || *text == L'\0')
        return;

    length = (DWORD)wcslen(text);
    if (GetConsoleMode(handle, &mode))
    {
        WriteConsoleW(handle, text, length, &written, NULL);
        return;
    }

    utf8_length = WideCharToMultiByte(CP_UTF8, 0, text, (int)length, NULL, 0, NULL, NULL);
    if (utf8_length <= 0)
        return;

    utf8 = (char *)malloc((size_t)utf8_length);
    if (utf8 == NULL)
        return;

    if (WideCharToMultiByte(CP_UTF8, 0, text, (int)length, utf8, utf8_length, NULL, NULL) > 0)
        WriteFile(handle, utf8, (DWORD)utf8_length, &written, NULL);
    free(utf8);
}

/* 只格式化数字，避免在字节流上使用带宽字符串参数的格式化输出 */
static void write_error_code(const wchar_t *prefix, DWORD code)
{
    wchar_t buffer[32];

    write_error(prefix);
    swprintf(buffer, SRA_BUFFER_COUNT(buffer), L"%lu\n", (unsigned long)code);
    write_error(buffer);
}

/*
 * 按 CommandLineToArgvW 的解析规则转义单个参数并写入 dst，返回新的写入位置。
 * 直接拼接原文会在参数含空格、引号或结尾反斜杠时被错误拆分，因此必须转义。
 */
static wchar_t *append_quoted(wchar_t *dst, const wchar_t *arg)
{
    const wchar_t *p;
    int need_quote = (*arg == L'\0') || (wcspbrk(arg, L" \t\n\v\"") != NULL);

    if (need_quote)
        *dst++ = L'"';

    for (p = arg;; ++p)
    {
        size_t backslashes = 0;
        size_t i;

        while (*p == L'\\')
        {
            ++backslashes;
            ++p;
        }

        if (*p == L'\0')
        {
            /* 引号内的结尾反斜杠需加倍，否则会与收尾引号组合成转义引号 */
            size_t count = need_quote ? backslashes * 2 : backslashes;

            for (i = 0; i < count; ++i)
                *dst++ = L'\\';
            break;
        }

        if (*p == L'"')
        {
            for (i = 0; i < backslashes * 2 + 1; ++i)
                *dst++ = L'\\';
            *dst++ = L'"';
        }
        else
        {
            for (i = 0; i < backslashes; ++i)
                *dst++ = L'\\';
            *dst++ = *p;
        }
    }

    if (need_quote)
        *dst++ = L'"';

    *dst = L'\0';
    return dst;
}

/* 复制标准流句柄并标记为可继承，保证子进程在管道/重定向下仍能读写 */
static BOOL duplicate_std_handle(DWORD std_id, HANDLE *target)
{
    HANDLE source = GetStdHandle(std_id);

    if (source == NULL || source == INVALID_HANDLE_VALUE)
        return FALSE;

    return DuplicateHandle(GetCurrentProcess(), source, GetCurrentProcess(), target, 0, TRUE,
                           DUPLICATE_SAME_ACCESS);
}

/*
 * 控制台事件处理：Ctrl+C / Ctrl+Break 时本进程不退出，留在原地等子进程优雅退出后
 * 转发其退出码；其余事件（关窗、注销、关机）交回默认处理。
 *
 * 注意不要改用 SetConsoleCtrlHandler(NULL, TRUE)：那是"忽略 Ctrl+C 输入"的过滤通道，
 * 会让整个控制台的 Ctrl+C 投递失效，子进程也收不到信号，表现为 serve 无法用 Ctrl+C
 * 中止（快捷键 Pause 反而可以）。普通处理函数只拦截本进程，不影响投递。
 */
static BOOL WINAPI on_console_event(DWORD type)
{
    return (type == CTRL_C_EVENT || type == CTRL_BREAK_EVENT) ? TRUE : FALSE;
}

int wmain(int argc, wchar_t **argv)
{
    wchar_t home[MAX_PATH];
    wchar_t python_path[2 * MAX_PATH];
    wchar_t script_path[2 * MAX_PATH];
    wchar_t *separator;
    wchar_t *command_line;
    wchar_t *cursor;
    DWORD length;
    DWORD exit_code = 2;
    int i;
    STARTUPINFOW startup;
    PROCESS_INFORMATION process;

    length = GetModuleFileNameW(NULL, home, MAX_PATH);
    if (length == 0 || length >= MAX_PATH)
    {
        write_error(L"SRA-cli: 无法获取程序所在目录。\n");
        return 2;
    }

    separator = wcsrchr(home, L'\\');
    if (separator == NULL)
    {
        write_error(L"SRA-cli: 程序路径异常，无法解析所在目录。\n");
        return 2;
    }
    *separator = L'\0';

    lstrcpynW(python_path, home, (int)SRA_BUFFER_COUNT(python_path));
    lstrcatW(python_path, L"\\python\\python.exe");

    lstrcpynW(script_path, home, (int)SRA_BUFFER_COUNT(script_path));
    lstrcatW(script_path, L"\\main.py");

    if (GetFileAttributesW(python_path) == INVALID_FILE_ATTRIBUTES ||
        GetFileAttributesW(script_path) == INVALID_FILE_ATTRIBUTES)
    {
        write_error(L"SRA-cli: 未找到随包分发的内嵌 Python 运行时，");
        write_error(L"请确认 SRA-cli.exe 位于程序根目录。\n");
        write_error(L"         缺失：");
        write_error(python_path);
        write_error(L"\n         缺失：");
        write_error(script_path);
        write_error(L"\n");
        return 2;
    }

    /*
     * 缓冲长度按最坏情况预留：每个参数最多翻倍（反斜杠加倍）再各加一对引号，
     * 还原后的参数总长不超过原始命令行，故取原始长度的两倍再加两个路径的空间。
     */
    command_line = (wchar_t *)malloc((wcslen(GetCommandLineW()) + 4 * MAX_PATH + 16) * 2 *
                                     sizeof(wchar_t) + sizeof(wchar_t) * 64);
    if (command_line == NULL)
    {
        write_error(L"SRA-cli: 内存不足，无法构造命令行。\n");
        return 2;
    }

    cursor = append_quoted(command_line, python_path);
    *cursor++ = L' ';
    cursor = append_quoted(cursor, script_path);
    for (i = 1; i < argc; ++i)
    {
        *cursor++ = L' ';
        cursor = append_quoted(cursor, argv[i]);
    }

    if (wcslen(command_line) >= SRA_MAX_COMMAND_LINE)
    {
        write_error(L"SRA-cli: 命令行过长，超过 Windows 允许的 32767 个字符。\n");
        free(command_line);
        return 2;
    }

    ZeroMemory(&startup, sizeof(startup));
    startup.cb = sizeof(startup);
    ZeroMemory(&process, sizeof(process));

    /* 三个标准流句柄齐备时才显式传递，否则退回继承父进程控制台 */
    if (duplicate_std_handle(STD_INPUT_HANDLE, &startup.hStdInput) &&
        duplicate_std_handle(STD_OUTPUT_HANDLE, &startup.hStdOutput) &&
        duplicate_std_handle(STD_ERROR_HANDLE, &startup.hStdError))
    {
        startup.dwFlags = STARTF_USESTDHANDLES;
    }
    else
    {
        if (startup.hStdInput != NULL)
            CloseHandle(startup.hStdInput);
        if (startup.hStdOutput != NULL)
            CloseHandle(startup.hStdOutput);
        if (startup.hStdError != NULL)
            CloseHandle(startup.hStdError);
        ZeroMemory(&startup.hStdInput, sizeof(HANDLE) * 3);
    }

    SetConsoleCtrlHandler(on_console_event, TRUE);

    /* 禁止加载用户级 site-packages（%APPDATA%\Python\Python3xx）。内嵌运行时启用了 site，
     * 会把本机全局安装的包也纳入 sys.path，可能覆盖随包分发的依赖版本；
     * 子进程环境块传 NULL 即继承父进程环境，故在此设置 */
    SetEnvironmentVariableW(L"PYTHONNOUSERSITE", L"1");

    if (!CreateProcessW(NULL, command_line, NULL, NULL, TRUE, 0, NULL, home, &startup, &process))
    {
        write_error(L"SRA-cli: 启动内嵌 Python 运行时失败。\n");
        write_error_code(L"         错误代码：", GetLastError());
        free(command_line);
        return 2;
    }

    WaitForSingleObject(process.hProcess, INFINITE);
    GetExitCodeProcess(process.hProcess, &exit_code);

    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    if (startup.dwFlags == STARTF_USESTDHANDLES)
    {
        CloseHandle(startup.hStdInput);
        CloseHandle(startup.hStdOutput);
        CloseHandle(startup.hStdError);
    }
    free(command_line);

    return (int)exit_code;
}