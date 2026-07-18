import enum
import json
import threading
import time
from io import BytesIO

from PIL import Image
from loguru import logger
from rapidocr import RapidOCR
from selenium import webdriver
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.by import By
from selenium.webdriver.common.webdriver import LocalWebDriver as WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from SRACore.operators.ioperator import IOperator
from SRACore.util.const import CacheDir
from SRACore.util.errors import ThreadStoppedError


class BrowserType(enum.StrEnum):
    EDGE = "Microsoft Edge"
    CHROME = "Chrome for Testing"
    FIREFOX = "Firefox"


class WebDriverManager:
    # 多浏览器驱动缓存池
    _driver_pool: dict[BrowserType, WebDriver] = {}
    # 全局常量统一管理
    CLOUD_URL = "https://sr.mihoyo.com/cloud"
    WINDOW_SIZE = {
        BrowserType.EDGE: (1936, 1164),
        BrowserType.CHROME: (1936, 1112),
        BrowserType.FIREFOX: (1936, 1112),
    }
    COMMON_CLI_ARGS = [
        "--disable-infobars",
        "--lang=zh-CN",
        "--log-level=3",
        "--disable-blink-features=AutomationControlled",
        "--force-device-scale-factor=1",
        '--user-data-dir=' + str(CacheDir / "selenium_profile")
    ]

    @classmethod
    def get_driver(cls, browser: BrowserType, binary_path: str = "", headless: bool = False) -> WebDriver:
        # 复用已存在的驱动实例
        if browser in cls._driver_pool:
            return cls._driver_pool[browser]

        match browser:
            case BrowserType.EDGE:
                from selenium.webdriver.edge.options import Options
                opt = Options()
                cls._build_options(opt, binary_path, headless)
                width, height = cls.WINDOW_SIZE[browser]
                driver = webdriver.Edge(options=opt)
                driver.set_window_size(width, height)
            case BrowserType.CHROME:
                from selenium.webdriver.chrome.options import Options
                opt = Options()
                cls._build_options(opt, binary_path, headless)
                width, height = cls.WINDOW_SIZE[browser]
                driver = webdriver.Chrome(options=opt)
                driver.set_window_size(width, height)
            case BrowserType.FIREFOX:
                from selenium.webdriver.firefox.options import Options
                opt = Options()
                cls._build_options(opt, binary_path, headless)
                width, height = cls.WINDOW_SIZE[browser]
                driver = webdriver.Firefox(options=opt)
                driver.set_window_size(width, height)
            case _:
                raise ValueError(f"未知浏览器类型 {browser}")
        # 加入缓存池
        cls._driver_pool[browser] = driver
        return driver

    @staticmethod
    def _build_options(opt: webdriver.EdgeOptions | webdriver.ChromeOptions | webdriver.FirefoxOptions, binary_path: str, headless: bool):
        if binary_path:
            opt.binary_location = binary_path
        if headless:
            opt.add_argument("--headless")
        # 公共参数批量添加
        for arg in WebDriverManager.COMMON_CLI_ARGS:
            opt.add_argument(arg)
        opt.add_argument(f"--app={WebDriverManager.CLOUD_URL}")

    @classmethod
    def close_browser(cls, browser: BrowserType):
        """关闭单个浏览器进程"""
        if browser not in cls._driver_pool:
            return
        drv = cls._driver_pool.pop(browser)
        drv.quit()

    @classmethod
    def dispose_all(cls):
        for drv in cls._driver_pool.values():
            drv.quit()
        cls._driver_pool.clear()


class BrowserOperator(IOperator):
    def __init__(self, ocr_engine: RapidOCR, stop_event: threading.Event | None = None):
        super().__init__(ocr_engine, stop_event)
        self.type = "Browser"
        self.height = 1080
        self.width = 1920
        self.clipboard: str = ""
        # noinspection PyTypeChecker
        self._driver: WebDriver = None  # pyright: ignore[reportAttributeAccessIssue]


    @property
    def driver(self):
        if self._driver is None:
            browser_type = self.settings.General.cloudGameBrowser
            binary_path = self.settings.General.cloudGameBrowserPath
            headless = self.settings.General.cloudGameBrowserHeadless
            self._driver = WebDriverManager.get_driver(BrowserType(browser_type), binary_path, headless)
        return self._driver

    def login(self, account, password):
        start_btn_xpath = '//*[@id="app"]/div[1]/div[3]/div[1]/div/div[2]/div[2]'
        try:
            WebDriverWait(self.driver, 10).until(
                expected_conditions.presence_of_element_located((By.XPATH, start_btn_xpath)))
            logger.info("检测到已登录状态")
            logged_in = True
        except Exception:
            logged_in = self._password_login(account, password, start_btn_xpath)

        if not logged_in:
            logger.error("登录失败")
            return -1

        self.load_initial_local_storage()
        try:
            self.driver.find_element(By.XPATH, '/html/body/div[6]/div[3]/button[1]').click()  # 下次再说
        except NoSuchElementException:
            pass
        try:
            self.driver.find_element(By.CLASS_NAME, 'guide-close-btn__x').click()  # 关闭引导
        except NoSuchElementException:
            pass
        start_box = self.driver.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[3]/div[1]/div/div[2]/div[2]')
        start_box.click()
        if self._wait_in_queue(3600):
            self.confirm()
            return 1
        else:
            return -1

    def _password_login(self, account, password, start_btn_xpath) -> bool:
        logger.info("使用账号密码登录...")
        try:
            wait = WebDriverWait(self.driver, 60)
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "iframe")))
            self.driver.switch_to.frame("mihoyo-login-platform-iframe")
            self.driver.find_element(By.ID, "tab-password").click()
            username = self.driver.find_element(By.ID, "username")
            passwd = self.driver.find_element(By.ID, "password")
            username.send_keys(account)
            passwd.send_keys(password)
            self.driver.find_element(By.XPATH, '//*[@id="app"]/div/div/form/label/span[1]').click()
            self.driver.find_element(By.XPATH, '//*[@id="app"]/div/div/form/button').click()
            self.driver.switch_to.default_content()
            wait.until(expected_conditions.presence_of_element_located((By.XPATH, start_btn_xpath)))
            return True
        except Exception as e:
            logger.error(f"账号密码登录失败: {e}")
            return False

    def confirm(self):
        wait = WebDriverWait(self.driver, 30, 1)
        try:
            wait.until(expected_conditions.element_to_be_clickable((By.CLASS_NAME, 'van-dialog__confirm')))  # 等待接受按钮可点击
            self.driver.find_element(By.CLASS_NAME, 'van-dialog__confirm').click()  # 接受协议
            for _ in range(4):
                self.click_point(0.5, 0.5, after_sleep=1)
            return True
        except (TimeoutException, NoSuchElementException):
            return True

    def load_initial_local_storage(self):
        data = {
            "clgm_web_app_settings_hkrpg_cn": "{\"kickoutMinMigratedFromUseConfig\":true,\"showGameMenuSettingGuideMigratedFromUseConfig\":true,\"showGameMenuSettingGuide\":false,\"gameLang\":\"zh-CN\",\"videoModeSmoothFirstToggleConfirmed\":true,\"videoMode\":0}",
            "clgm_web_app_client_store_config_hkrpg_cn": "{\"showGameMenuGuide\":false,\"volume\":1,\"showGameStatBar\":false,\"gameStatBarType\":\"verbose\",\"speedLimitGearId\":\"0\",\"fabPosition\":{\"x\":0.0,\"y\":0.35},\"showMouseStatusGuide\":false,\"enableVolume\":true}"
        }
        for key, value in data.items():
            self.driver.execute_script(
                "window.localStorage.setItem(arguments[0], arguments[1]);",
                key,
                value,
            )

    def _wait_in_queue(self, timeout=600) -> bool:
        """排队等待进入"""
        in_queue_selector = "[class*='waiting-in-queue']"
        cloud_game_selector = ".game-player"
        select_queue_selector = "[aria-labelledby*='请选择排队队列']"

        try:
            # 检查是否需要排队
            status = WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("""
                    if (document.querySelector(arguments[0])) return "game_running";
                    else if (document.querySelector(arguments[1])) return "in_queue";
                    else if (document.querySelector(arguments[2])) return "select_queue";
                    else return null;
                """, cloud_game_selector, in_queue_selector, select_queue_selector)
            )

            select_retries = 0
            while status == "select_queue":
                select_retries += 1
                if select_retries >= 5:
                    logger.error("选择排队队列超时")
                    return False
                logger.info("检测到选择排队队列界面，选择普通队列")
                self.driver.execute_script("""
                    try {
                        document.getElementsByClassName("coin-prior-choose-item-include-info")[1].click();
                    } catch(e) {}
                """)
                time.sleep(2)
                status = WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("""
                        if (document.querySelector(arguments[0])) return "game_running";
                        else if (document.querySelector(arguments[1])) return "in_queue";
                        else if (document.querySelector(arguments[2])) return "select_queue";
                        else return null;
                    """, cloud_game_selector, in_queue_selector, select_queue_selector)
                )

            if status == "game_running":
                logger.info("游戏已启动，无需排队")
                return True
            elif status == "in_queue":
                logger.info("正在排队...")
                last_wait_time = None
                poll_interval = 5  # 每5秒检测一次
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.stop_event and self.stop_event.is_set():
                        raise ThreadStoppedError("排队等待中断", "线程已停止")
                    # 检查是否已退出排队
                    if not self.driver.find_elements(By.CSS_SELECTOR, in_queue_selector):
                        logger.info("排队成功，正在进入游戏")
                        return True
                    # 检测预计等待时间
                    wait_time = self.driver.execute_script("""
                        // 方式1: "预估排队时间30分钟以上，建议开拓者错峰进行游戏~"
                        var timeHide = document.querySelector('.time-hide__text');
                        if (timeHide && timeHide.textContent) {
                            return timeHide.textContent.trim();
                        }
                        // 方式2: "预计等待时间 10~20 分钟"
                        var singleRow = document.querySelector('.single-row');
                        if (singleRow) {
                            var valEl = singleRow.querySelector('.single-row__val');
                            if (valEl && valEl.textContent) {
                                return '预计等待时间: ' + valEl.textContent.replace(/\\s+/g, '').trim();
                            }
                        }
                        return null;
                    """)
                    if wait_time and wait_time != last_wait_time:
                        logger.info(f"当前状态: {wait_time}")
                        last_wait_time = wait_time
                    self.sleep(poll_interval)
                logger.info("排队超时")
                return False
        except Exception as e:
            logger.error(f"等待排队异常: {e}")
        return False

    def change_auto_battle(self, status: bool) -> None:
        """从 local storage 中读取并修改 auto battle"""
        ls = json.loads(self.driver.execute_script("return JSON.stringify(localStorage)"))
        cloud = json.loads(ls.get("cg_hkrpg_cn_cloudData", "{}"))
        cloud.setdefault("value", {})
        save = json.loads(cloud["value"].get("RPGCloudSave", "{}") or "{}")
        int_dicts = save.get("IntDicts", {})

        int_dicts["OtherSettings_AutoBattleOpen"] = int(status)
        logger.debug(f"设置自动战斗为 {'开启' if status else '关闭'}")
        int_dicts["OtherSettings_IsSaveBattleSpeed"] = int(status)
        logger.debug(f"设置沿用自动战斗状态")

        # 如果存在 App_LastUserID，添加 User_{UID}_SpeedUpOpen 配置
        uid = int_dicts.get("App_LastUserID")
        if uid:
            int_dicts[f"User_{uid}_SpeedUpOpen"] = int(status)
            logger.debug(f"设置战斗二倍速为 {'开启' if status else '关闭'}")
        else:
            logger.debug("未检测到 UID，跳过设置战斗二倍速")

        save["IntDicts"] = int_dicts
        cloud["value"]["RPGCloudSave"] = json.dumps(save)
        ls["cg_hkrpg_cn_cloudData"] = json.dumps(cloud)

        for k, v in ls.items():
            self.driver.execute_script(f"localStorage.setItem('{k}', arguments[0]);", v)

    def is_window_active(self) -> bool:
        return True

    def screenshot(self, *, from_x: float | None = None, from_y: float | None = None, to_x: float | None = None,
                   to_y: float | None = None, background: bool = True) -> Image.Image:
        png = self.driver.get_screenshot_as_png()
        img = Image.open(BytesIO(png))
        if from_x is not None and from_y is not None and to_x is not None and to_y is not None:
            left = from_x * self.width
            upper = from_y * self.height
            right = to_x * self.width
            bottom = to_y * self.height
            return img.crop((left, upper, right, bottom))
        return img

    def click_point(self, x: int | float, y: int | float, x_offset: int | float = 0, y_offset: int | float = 0,
                    after_sleep: float = 0, tag: str = "", trace: bool = False) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("点击中断", "线程已停止")
        if isinstance(x_offset, float) and isinstance(y_offset, float):
            x_offset = int(self.width * x_offset)
            y_offset = int(self.height * y_offset)

        if isinstance(x, int) and isinstance(y, int):
            action = ActionBuilder(self.driver)
            action.pointer_action.move_to_location(x + x_offset, y + y_offset)
            action.pointer_action.click()
            action.perform()
            self.sleep(after_sleep + 0.2)
            return True
        elif isinstance(x, float) and isinstance(y, float):
            x = int(self.left + self.width * x + x_offset)
            y = int(self.top + self.height * y + y_offset)
            if trace:
                logger.debug(f"Click point: ({x}, {y}), tag: {tag}")
            action = ActionBuilder(self.driver)
            action.pointer_action.move_to_location(x, y)
            action.pointer_action.click()
            action.perform()
            self.sleep(after_sleep + 0.2)
            return True
        else:
            raise ValueError(
                f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")

    @staticmethod
    def convert_key(key: str) -> str:
        # 这里可以添加更多的按键转换规则
        if key == 'esc':
            return Keys.ESCAPE
        elif key.startswith('f'):
            return getattr(Keys, key.upper(), key)
        else:
            return key

    def press_key(self, key: str, presses: int = 1, interval: float = 0, wait: float = 0, trace: bool = True) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("按键中断", "线程已停止")
        try:
            self.sleep(wait)
            if trace:
                logger.debug(f"Press key: {key}")
            key = self.convert_key(key)
            for _ in range(presses):
                ActionChains(self.driver).send_keys(key).perform()
                self.sleep(interval)
            return True
        except Exception as e:
            if trace:
                logger.debug(f"Failed to press key: {e}")
            return False

    def hold_key(self, key: str, duration: float = 0) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("按键中断", "线程已停止")
        try:
            key = self.convert_key(key)
            logger.debug(f"Hold key {key}")
            ActionChains(self.driver).key_down(key).perform()
            self.sleep(duration)
            ActionChains(self.driver).key_up(key).perform()
            return True
        except Exception as e:
            logger.debug(f"Failed to hold key: {e}")
            return False

    def copy(self, text: str) -> None:
        self.clipboard = text

    def paste(self) -> None:
        content = self.clipboard
        ActionChains(self.driver).send_keys(content).perform()

    def move_rel(self, x_offset: int, y_offset: int) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("鼠标移动中断", "线程已停止")
        try:
            ActionChains(self.driver).move_by_offset(x_offset, y_offset).perform()
            return True
        except Exception as e:
            logger.debug(f"Error moving cursor: {e}")
            return False

    def move_to(self, x: int | float, y: int | float, duration: float = 0.0, trace: bool = True) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("鼠标移动中断", "线程已停止")
        try:
            if trace:
                logger.debug(f"Move cursor to ({x}, {y}), duration: {duration}s")
            if isinstance(x, int) and isinstance(y, int):
                action = ActionBuilder(self.driver)
                action.pointer_action.move_to_location(x, y)
                action.perform()
            elif isinstance(x, float) and isinstance(y, float):
                x = int(self.left + self.width * x)
                y = int(self.top + self.height * y)
                action = ActionBuilder(self.driver)
                action.pointer_action.move_to_location(x, y)
                action.perform()
            else:
                raise ValueError(
                    f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")
            return True
        except Exception as e:
            logger.debug(f"Error moving cursor: {e}")
            return False

    def mouse_down(self, x: int | float, y: int | float, trace: bool = True) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("点击中断", "线程已停止")
        try:
            if trace:
                logger.debug(f"Mouse down: ({x}, {y})")
            if isinstance(x, int) and isinstance(y, int):
                action = ActionBuilder(self.driver)
                action.pointer_action.move_to_location(x, y)
                action.pointer_action.pointer_down()
                action.perform()
            elif isinstance(x, float) and isinstance(y, float):
                x = int(self.left + self.width * x)
                y = int(self.top + self.height * y)
                action = ActionBuilder(self.driver)
                action.pointer_action.move_to_location(x, y)
                action.pointer_action.pointer_down()
                action.perform()
            else:
                raise ValueError(
                    f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")
            self.sleep(0.2)
            return True
        except Exception as e:
            logger.debug(f"Error pressing mouse button: {e}")
            return False

    def mouse_up(self, x: int | float | None = None, y: int | float | None = None, trace: bool = True) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("点击中断", "线程已停止")
        try:
            if trace:
                logger.debug("Mouse up")
            action = ActionBuilder(self.driver)
            action.pointer_action.pointer_up()
            action.perform()
            self.sleep(0.2)
            return True
        except Exception as e:
            logger.debug(f"Error releasing mouse button: {e}")
            return False

    def scroll(self, distance: int) -> bool:
        ActionChains(self.driver).scroll_by_amount(0, -distance).perform()
        return True
