from SRACore.triggers.BaseTrigger import BaseTrigger


class AutoPlotTrigger(BaseTrigger):
    def __init__(self):
        super().__init__()
        self.name = '自动对话'
        self.can_skip = True  # 是否可以跳过对话, 默认可以跳过
        self.skip_plot = False  # 是否跳过对话
        self.active_window = False

    def run(self):
        if not self.plot_status_check():
            self.can_skip = True
            return
        self.press_key("space", trace=False)
        if self.skip_plot and self.can_skip:
            self.skip_check()
        for i in range(5, 0, -1):
            if self.locate(f"resources/img/{i}.png", from_x=0.63, from_y=0.375, to_x=0.67, to_y=0.72, trace=False):
                self.press_key(str(i), trace=False)
                break

    def plot_status_check(self):
        """
        检测是否处于对话状态
        """
        self.sleep(1)
        return self.locate_any(["resources/img/dialog.png", "resources/img/m.png"],
                               from_x=0.067,
                               from_y=0.033,
                               to_x=0.156,
                               to_y=0.076,
                               trace=False)[0] != -1

    def skip_check(self):
        """
        检测是否可以跳过对话
        """
        self.click_point(0.8225, 0.055)  # 尝试点击跳过键
        if self.click_img('resources/img/ensure.png'):  # 如果出现确认跳过按钮，说明可以跳过
            self.can_skip = True
        else:
            self.can_skip = False
