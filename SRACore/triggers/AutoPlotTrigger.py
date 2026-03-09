from SRACore.triggers.BaseTrigger import BaseTrigger
from SRACore.util.img import IMG


class AutoPlotTrigger(BaseTrigger):
    def __init__(self, operator):
        super().__init__(operator)
        self.name = '自动对话'
        self.can_skip = True  # 是否可以跳过对话, 默认可以跳过
        self.skip_plot = False  # 是否跳过对话
        self.active_window = False
        self.dialog_options = [IMG.NUMBER_5, IMG.NUMBER_4, IMG.NUMBER_3, IMG.NUMBER_2, IMG.NUMBER_1]

    def run(self):
        if not self.plot_status_check():
            self.can_skip = True
            return
        self.operator.press_key("space", trace=False)
        if self.skip_plot and self.can_skip:
            self.skip_check()
        for index, img_path in enumerate(self.dialog_options, start=1):
            if self.operator.locate(img_path, from_x=0.63, from_y=0.375, to_x=0.67, to_y=0.72, trace=False):
                # dialog_options is ordered 5..1, so convert index back to key value.
                self.operator.press_key(str(6 - index), trace=False)
                break

    def plot_status_check(self):
        """
        检测是否处于对话状态
        """
        self.operator.sleep(1)
        if not self.operator.is_window_active():
            return False
        return self.operator.locate_any([IMG.DIALOG, IMG.M], from_x=0.067, from_y=0.033,
                                        to_x=0.156, to_y=0.076, trace=False)[0] != -1

    def skip_check(self):
        """
        检测是否可以跳过对话
        """
        self.operator.click_point(0.8225, 0.055)  # 尝试点击跳过键
        if self.operator.click_img(IMG.ENSURE):  # 如果出现确认跳过按钮，说明可以跳过
            self.can_skip = True
        else:
            self.can_skip = False
