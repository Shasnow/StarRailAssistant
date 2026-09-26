import base64
import enum
import json
import threading
import time
from collections.abc import Callable
from io import BytesIO

import psutil
from PIL import Image
from loguru import logger
from rapidocr import RapidOCR
from selenium import webdriver
from selenium.common import NoSuchElementException, SessionNotCreatedException, TimeoutException
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.by import By
from selenium.webdriver.common.webdriver import LocalWebDriver as WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from SRACore.models.app_settings import AppSettings
from SRACore.operators.ioperator import IOperator
from SRACore.operators.model import WindowContext
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
    def get_driver(cls, browser: BrowserType, binary_path: str = "", headless: bool = False, mute_audio: bool = False) -> WebDriver:
        # 复用已存在的驱动实例
        if browser in cls._driver_pool:
            return cls._driver_pool[browser]

        match browser:
            case BrowserType.EDGE:
                from selenium.webdriver.edge.options import Options
                opt = Options()
                cls._build_options(opt, binary_path, headless, mute_audio)
                width, height = cls.WINDOW_SIZE[browser] if not headless else (1920, 1080)
                driver = cls._launch(lambda: webdriver.Edge(options=opt), browser)
            case BrowserType.CHROME:
                from selenium.webdriver.chrome.options import Options
                opt = Options()
                cls._build_options(opt, binary_path, headless, mute_audio)
                width, height = cls.WINDOW_SIZE[browser] if not headless else (1920, 1080)
                driver = cls._launch(lambda: webdriver.Chrome(options=opt), browser)
            case BrowserType.FIREFOX:
                from selenium.webdriver.firefox.options import Options
                opt = Options()
                cls._build_options(opt, binary_path, headless, mute_audio)
                width, height = cls.WINDOW_SIZE[browser] if not headless else (1920, 1080)
                driver = cls._launch(lambda: webdriver.Firefox(options=opt), browser)
            case _:
                raise ValueError(f"未知浏览器类型 {browser}")
        if headless and browser is not BrowserType.FIREFOX:
            # 无头模式下 set_window_size 设置的是含模拟边框的窗口尺寸，
            # 截图截取的却是视口，直接用 CDP 把渲染视口设为目标分辨率
            cls._set_viewport_size(driver, width, height)
        else:
            driver.set_window_size(width, height)
        # 加入缓存池
        cls._driver_pool[browser] = driver
        return driver

    @staticmethod
    def _set_viewport_size(driver: WebDriver, width: int, height: int):
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                               {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})

    @classmethod
    def _launch(cls, create: Callable[[], WebDriver], browser: BrowserType) -> WebDriver:
        """创建 WebDriver；因残留进程占用 profile 或锁文件损坏导致启动崩溃时，清理后重试一次"""
        try:
            return create()
        except SessionNotCreatedException as e:
            logger.warning(f"{browser} 启动失败，清理残留浏览器进程与锁文件后重试: {e.msg.splitlines()[0] if e.msg else e}")
        cls._kill_stale_browser_processes()
        cls._clean_profile_locks()
        return create()

    # 复用 profile 的 Chromium 系浏览器进程名
    _STALE_PROCESS_NAMES = {"msedge.exe", "chrome.exe"}

    @classmethod
    def _kill_stale_browser_processes(cls):
        """结束仍在占用 selenium_profile 的残留浏览器进程（不影响用户正常使用的浏览器窗口）"""
        profile_arg = str(CacheDir / "selenium_profile")
        stale_pids = []
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                name = (proc.info["name"] or "").lower()
                if name not in cls._STALE_PROCESS_NAMES:
                    continue
                cmdline = " ".join(proc.info["cmdline"] or [])
                if profile_arg in cmdline:
                    stale_pids.append(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        for pid in stale_pids:
            try:
                psutil.Process(pid).kill()
                logger.info(f"已结束占用 selenium_profile 的残留浏览器进程 (PID {pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if stale_pids:
            psutil.wait_procs([psutil.Process(pid) for pid in stale_pids if psutil.pid_exists(pid)], timeout=5)

    @staticmethod
    def _clean_profile_locks():
        """清理 profile 中进程被强杀后残留的锁文件"""
        profile_dir = CacheDir / "selenium_profile"
        for lock_name in ("DevToolsActivePort", "lockfile", "SingletonLock", "SingletonCookie", "SingletonSocket"):
            lock_path = profile_dir / lock_name
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                logger.debug(f"清理锁文件失败: {lock_path}")

    @staticmethod
    def _build_options(opt: webdriver.EdgeOptions | webdriver.ChromeOptions | webdriver.FirefoxOptions,
                       binary_path: str, headless: bool, mute_audio: bool = False):
        if binary_path:
            opt.binary_location = binary_path
        if headless:
            opt.add_argument("--headless")
        if mute_audio:
            opt.add_argument("--mute-audio")
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
    def __init__(self, ocr_engine: RapidOCR, settings: AppSettings,
                 stop_event: threading.Event | None = None,
                 window_context: WindowContext | None = None):
        super().__init__(ocr_engine, settings, stop_event, window_context)
        self.type = "Browser"
        self.window_context.width = 1920
        self.window_context.height = 1080
        self.clipboard: str = ""
        # noinspection PyTypeChecker
        self._driver: WebDriver = None  # pyright: ignore[reportAttributeAccessIssue]

    @property
    def driver(self):
        if self._driver is None:
            browser_type = self.settings.General.cloudGameBrowser
            binary_path = self.settings.General.cloudGameBrowserPath
            headless = self.settings.General.isCloudGameBrowserHeadless
            mute_audio = self.settings.General.isCloudGameBrowserMuteAudio

            self._driver = WebDriverManager.get_driver(BrowserType(browser_type), binary_path, headless, mute_audio)
            # 以实际渲染视口为准，避免窗口边框/工具栏导致比例坐标与截图偏差
            self.window_context.width, self.window_context.height = \
                self._driver.execute_script("return [window.innerWidth, window.innerHeight]")
            if headless and not getattr(self._driver, "_pointer_lock_guarded", False):
                self._configure_pointer_lock()
                # 标记在 driver 实例上：driver 被池化复用时避免重复注入
                setattr(self._driver, "_pointer_lock_guarded", True)
        return self._driver

    # 无窗口运行时禁止网页锁定系统鼠标指针（Pointer Lock 会捕获真实光标）
    DISABLE_POINTER_LOCK_SCRIPT = """
        (() => {
            const blocked = function () {
                return Promise.reject(new DOMException(
                    'Pointer Lock is disabled in background mode.',
                    'NotAllowedError'
                ));
            };
            Object.defineProperty(Element.prototype, 'requestPointerLock', {
                configurable: true,
                writable: true,
                value: blocked,
            });
            if (document.pointerLockElement && document.exitPointerLock) {
                document.exitPointerLock();
            }
        })();
    """

    def _configure_pointer_lock(self) -> None:
        """禁用无头模式下的 Pointer Lock"""
        try:
            self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": self.DISABLE_POINTER_LOCK_SCRIPT,
                "runImmediately": True,
            })
            logger.debug("无头模式已禁用 Pointer Lock")
        except Exception as e:
            logger.warning(f"无头模式禁用 Pointer Lock 失败: {e}")

    def login(self, account, password, relogin: bool = False):
        if relogin:
            # 精确删除登录态 cookies，保留 DEVICEFP_SEED_TIME、DEVICEFP、_MHYUUID 等非登录信息
            login_cookies = [
                "uni_web_token", 
                "Ituid_v2", "Ituid", "Itoken_v2", "Itoken", "Itmid_v2",
                "cookie_token_v2", "cookie_token",
                "account_mid_v2", "account_id_v2", "account_id",
            ]
            for name in login_cookies:
                self.driver.delete_cookie(name)
            self.driver.refresh()
            logger.info("已清除登录态 Cookie，准备重新登录")
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
        """确认协议"""
        wait = WebDriverWait(self.driver, 30, 1)
        try:
            wait.until(expected_conditions.element_to_be_clickable((By.CLASS_NAME, 'van-dialog__confirm')))  # 等待接受按钮可点击
            self.driver.find_element(By.CLASS_NAME, 'van-dialog__confirm').click()  # 接受协议
            for _ in range(4):
                self.click_point(0.5, 0.5, after_sleep=1)
            return True
        except (TimeoutException, NoSuchElementException):
            return True

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
                if self.stop_event and self.stop_event.is_set():
                    logger.error("线程已停止，排队等待中断")  # 线程已停止
                    return False
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

    def _capture_jpeg(self, quality: int, region: tuple[float, float, float, float] | None,
                      resize: tuple[int, int] | None) -> bytes | None:
        """用 CDP 让浏览器合成器直接输出目标尺寸的 JPEG（裁剪与缩放一并完成）。

        省去「整幅 PNG 解码 → PIL 重采样 → 重新编码」三步，宽高比匹配时可直接落盘原始字节。
        Firefox 没有 CDP，返回 None 由调用方回退到 Selenium 截图。
        """
        if BrowserType(self.settings.General.cloudGameBrowser) is BrowserType.FIREFOX:
            return None
        viewport_w, viewport_h = self.window_context.width, self.window_context.height
        if region is None:
            clip_x, clip_y, clip_w, clip_h = 0, 0, viewport_w, viewport_h
        else:
            from_x, from_y, to_x, to_y = region
            clip_x, clip_y = from_x * viewport_w, from_y * viewport_h
            clip_w, clip_h = (to_x - from_x) * viewport_w, (to_y - from_y) * viewport_h
        # clip.scale 由合成器在缩放阶段完成重采样，避免把原始分辨率的整幅图像送回 Python
        scale = resize[0] / clip_w if resize and clip_w else 1
        try:
            result = self.driver.execute_cdp_cmd("Page.captureScreenshot", {
                "format": "jpeg",
                "quality": quality,
                "clip": {"x": clip_x, "y": clip_y, "width": clip_w, "height": clip_h, "scale": scale},
            })
        except Exception as e:
            logger.warning(f"CDP 截图失败，回退到 Selenium 截图: {e}")
            return None
        return base64.b64decode(result["data"])

    def screenshot(self, *, from_x: float | None = None, from_y: float | None = None, to_x: float | None = None,
                   to_y: float | None = None, background: bool = True, resize: tuple[int, int] | None = None,
                   save_path: str | None = None, jpeg_quality: int | None = None) -> Image.Image:
        # 指定 jpeg_quality 时优先走 CDP：浏览器直接产出目标尺寸的 JPEG。
        # 内部 OCR/模板匹配不传该参数，继续走下面的无损 PNG 路径
        if jpeg_quality is not None:
            region = ((from_x, from_y, to_x, to_y)
                      if from_x is not None and from_y is not None and to_x is not None and to_y is not None
                      else None)
            raw = self._capture_jpeg(jpeg_quality, region, resize)
            if raw is not None:
                img = Image.open(BytesIO(raw))
                img.load()
                if resize is not None and img.size != tuple(resize):
                    # 合成器只能等比缩放，宽高比不符时补一次精确重采样（常规 16:9 不会触发）
                    img = img.resize(resize, Image.Resampling.LANCZOS)
                    if save_path:
                        img.save(save_path, format="JPEG", quality=jpeg_quality)
                elif save_path:
                    with open(save_path, "wb") as f:
                        f.write(raw)  # 直接落盘，免去二次编解码
                return img

        png = self.driver.get_screenshot_as_png()
        img = Image.open(BytesIO(png))
        if from_x is not None and from_y is not None and to_x is not None and to_y is not None:
            left = from_x * self.window_context.width
            upper = from_y * self.window_context.height
            right = to_x * self.window_context.width
            bottom = to_y * self.window_context.height
            img = img.crop((left, upper, right, bottom))
        if resize:
            img = img.resize(resize, Image.Resampling.LANCZOS)
        if save_path:
            if jpeg_quality is not None:
                # JPEG 不支持 alpha/调色板模式，先统一转 RGB
                img.convert("RGB").save(save_path, format="JPEG", quality=jpeg_quality)
            else:
                img.save(save_path)
        return img

    def click_point(self, x: int | float, y: int | float, x_offset: int | float = 0, y_offset: int | float = 0,
                    after_sleep: float = 0, tag: str = "", trace: bool = False) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("点击中断", "线程已停止")
        if isinstance(x_offset, float) and isinstance(y_offset, float):
            x_offset = int(self.window_context.width * x_offset)
            y_offset = int(self.window_context.height * y_offset)

        if isinstance(x, int) and isinstance(y, int):
            action = ActionBuilder(self.driver)
            action.pointer_action.move_to_location(x + x_offset, y + y_offset)
            action.pointer_action.click()
            action.perform()
            self.sleep(after_sleep + 0.2)
            return True
        elif isinstance(x, float) and isinstance(y, float):
            x = int(self.window_context.left + self.window_context.width * x + x_offset)
            y = int(self.window_context.top + self.window_context.height * y + y_offset)
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
            keys = [self.convert_key(k.strip()) for k in key.split("+") if k.strip()]
            if trace:
                logger.debug(f"Press key: {key}")
            for _ in range(presses):
                chain = ActionChains(self.driver)
                for k in keys:
                    chain.key_down(k)
                for k in reversed(keys):
                    chain.key_up(k)
                chain.perform()
                self.sleep(interval)
            return True
        except Exception as e:
            if trace:
                logger.debug(f"Failed to press key: {e}")
            return False

    def hold_key(self, key: str, duration: float = 0, trace: bool = True) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("按键中断", "线程已停止")
        try:
            keys = [self.convert_key(k.strip()) for k in key.split("+") if k.strip()]
            if trace:
                logger.debug(f"Hold key {key}")
            for k in keys:
                ActionChains(self.driver).key_down(k).perform()
            self.sleep(duration)
            for k in reversed(keys):
                ActionChains(self.driver).key_up(k).perform()
            return True
        except Exception as e:
            logger.debug(f"Failed to hold key: {e}")
            return False

    def copy(self, text: str) -> None:
        self.clipboard = text

    def paste(self) -> None:
        content = self.clipboard
        ActionChains(self.driver).send_keys(content).perform()

    def move_rel(self, x_offset: int, y_offset: int, trace: bool = True) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("鼠标移动中断", "线程已停止")
        try:
            if trace:
                logger.debug(f"Move cursor relative: ({x_offset}, {y_offset})")
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
                x = int(self.window_context.left + self.window_context.width * x)
                y = int(self.window_context.top + self.window_context.height * y)
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
                x = int(self.window_context.left + self.window_context.width * x)
                y = int(self.window_context.top + self.window_context.height * y)
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

    def scroll(self, clicks: int, x: int | float | None = None, y: int | float | None = None, trace: bool = True) -> bool:
        if trace:
            logger.debug(f"Scroll: {clicks} clicks, ({x}, {y})")
        if x and y:
            self.move_to(x, y)
        ActionChains(self.driver).scroll_by_amount(0, -clicks).perform()
        return True

    def kill(self):
        browser_type = BrowserType(self.settings.General.cloudGameBrowser)
        WebDriverManager.close_browser(browser_type)
        self._driver = None  # pyright: ignore[reportAttributeAccessIssue]
