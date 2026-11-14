"""自动切号扩展：在任务注册后接管 ``StartGameTask`` 的登录流程。

具体实现见 :mod:`extensions.account_switch.plugin`；开关由扩展配置的
``enabled`` 字段控制，目标账号提示来自 ``account_hint`` 字段，关闭时会还原
对任务类的修改。该扩展没有执行逻辑，前端只提供启用/禁用。
"""

from pydantic import BaseModel, Field

from SRACore.extension import BaseExtension, extension
from SRACore.task import TaskRegistry


class AccountSwitchConfig(BaseModel):
    enabled: bool = Field(default=False, alias="enabled", description="是否启用自动切号")
    account_hint: str = Field(
        default="",
        alias="account_hint",
        description="目标账号：完整手机号/账号、脱敏片段（138****5678）或邮箱（qin***@qq.com）",
    )


@extension(name="自动切号", description="免密码历史账号切号（AUTO-MAS 花名册 / 配置中的账号提示）",
           executable=False)
class AccountSwitchExtension(BaseExtension[AccountSwitchConfig]):
    @classmethod
    def on_tasks_registered(cls, tasks: TaskRegistry,
                            config: AccountSwitchConfig | None = None) -> None:
        from extensions.account_switch import plugin

        if config is not None and not config.enabled:
            plugin.uninstall()
            return
        plugin.install(tasks, config)
