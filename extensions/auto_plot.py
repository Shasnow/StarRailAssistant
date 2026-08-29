from pydantic import BaseModel, Field

from SRACore.extension import BaseExtension, extension


class AutoPlotConfig(BaseModel):
    """自动剧情对话扩展配置。"""
    skip_plot: bool = Field(default=False, description="是否自动跳过剧情对话")


@extension(
    name="自动对话",
    description="自动检测并处理剧情对话，可按配置跳过剧情",
    background=True,
)
class AutoPlotExtension(BaseExtension[AutoPlotConfig]):
    """后台扩展：自动处理对话状态并在需要时跳过剧情。"""

    def __init__(self, operator, config: AutoPlotConfig):
        super().__init__(operator, config)
        self._can_skip = True

    def run(self) -> bool:
        if not self.plot_status_check():
            self._can_skip = True
            return True

        self.operator.press_key("space", trace=False)
        if self.config.skip_plot and self._can_skip:
            self.skip_check()

        for i in range(5, 0, -1):
            if self.operator.locate(
                f"resources/img/{i}.png",
                from_x=0.63,
                from_y=0.375,
                to_x=0.67,
                to_y=0.72,
                trace=False,
            ):
                self.operator.press_key(str(i), trace=False)
                break

        return True

    def plot_status_check(self):
        """检测当前是否处于对话状态。"""
        self.operator.sleep(1)
        if not self.operator.is_window_active():
            return False
        return (
            self.operator.locate_any(
                ["resources/img/dialog.png", "resources/img/m.png"],
                from_x=0.067,
                from_y=0.033,
                to_x=0.156,
                to_y=0.076,
                trace=False,
            )[0]
            != -1
        )

    def skip_check(self):
        """检测是否可以跳过对话。"""
        self.operator.click_point(0.758, 0.055, after_sleep=0.5)
        if self.operator.click_img("resources/img/ensure.png"):
            self._can_skip = True
        else:
            self._can_skip = False
