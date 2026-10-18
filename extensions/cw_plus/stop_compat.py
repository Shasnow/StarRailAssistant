"""兼容 2.24.0 宿主对普通扩展卡片停止命令的限制。"""

from functools import wraps


EXTENSION_ID = "CurrencyWarsPlus"
_PATCH_MARKER = "_currency_wars_plus_stop_compat"


# Yukki：只归一本扩展的停止命令，其他运行单元保持宿主规则。
def normalise_stop_statement(cli, statement):
    """仅将本扩展运行期间的指定停止转成宿主已有的普通扩展停止命令。"""
    # 使用公开的命令解析接口，不改动 cmd2 已注册的处理器或解析器内部状态。
    if not hasattr(statement, "argv"):
        statement = cli.statement_parser.parse(statement)

    tokens = statement.argv
    if not tokens or tokens[0] != "extension":
        return statement
    arguments = tokens[1:]
    json_output = "--json" in arguments
    if json_output:
        arguments = [token for token in arguments if token != "--json"]
    if arguments != ["stop", EXTENSION_ID]:
        return statement

    runner = getattr(cli, "extension_runner", None)
    info = getattr(runner, "info", None)
    if (
        runner is None
        or info is None
        or getattr(info, "mode", None) != "extension"
        or getattr(info, "status", None) != "running"
        or getattr(info, "unit", None) != EXTENSION_ID
        or not runner.is_thread_running()
    ):
        # 本扩展未运行时保留宿主行为，防止停止正在运行的任务或其他扩展。
        return statement

    command = "extension stop" + (" --json" if json_output else "")
    # 保留用户显式写入的输出重定向、管道和命令结束符。
    if statement.post_command:
        command += " " + statement.post_command
    return cli.statement_parser.parse(command)


def install_stop_compat(cli_class=None, *, host_version=None) -> bool:
    """仅为旧宿主安装一次兼容层，新宿主直接使用官方停止命令。"""
    if host_version is None:
        from SRACore.util.const import VERSION

        host_version = VERSION
    # ssyb：新版已支持按扩展标识停止，不能再次包装其命令入口。
    if host_version not in {"2.24.0", "2.24.0-beta.1", "2.24.0-beta.2"}:
        return False
    if cli_class is None:
        from SRACore.cli2 import SRACli

        cli_class = SRACli

    original_precmd = cli_class.precmd
    if getattr(original_precmd, _PATCH_MARKER, False):
        return False

    @wraps(original_precmd)
    def compatible_precmd(self, statement):
        statement = normalise_stop_statement(self, statement)
        # 继续使用宿主的 JSON 检测及原生停止处理逻辑。
        return original_precmd(self, statement)

    setattr(compatible_precmd, _PATCH_MARKER, True)
    cli_class.precmd = compatible_precmd
    return True
