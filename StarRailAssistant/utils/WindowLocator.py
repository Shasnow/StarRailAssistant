import win32gui
import pyautogui

class WindowLocator:

    def __init__(self, title: str) -> None:
        self.title = title

    def find_window(self):
        """
        根据窗口标题查找窗口句柄
        """

        def enum_callback(hwnd, result):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == self.title:
                result.append(hwnd)

        windows = []
        win32gui.EnumWindows(enum_callback, windows)
        return windows[0] if windows else None
    
    def get_screen_center(self):
        x, y, screen_width, screen_height = (pyautogui.getActiveWindow().left, pyautogui.getActiveWindow().top, # type: ignore
                                            pyautogui.getActiveWindow().width, pyautogui.getActiveWindow().height) # type: ignore
        return x + screen_width // 2, y + screen_height // 2