#   <StarRailAssistant:An automated program that helps you complete daily tasks of StarRail.>
#   Copyright © <2024> <Shasnow>

#   This file is part of StarRailAssistant.

#   StarRailAssistant is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free Software Foundation,
#   either version 3 of the License, or (at your option) any later version.

#   StarRailAssistant is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#   without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#   See the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License along with StarRailAssistant.
#   If not, see <https://www.gnu.org/licenses/>.

#   yukikage@qq.com

"""
崩坏：星穹铁道助手
v0.7.0
作者：雪影
云游戏
"""
import json
import os.path
import time

import keyboard
from PySide6.QtCore import QThread, Signal
from SRACore.utils.SRAWebOperator import SRAWebOperator
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException,
                                        TimeoutException)
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from SRACore.utils.Logger import logger


class CloudGame:
    def __init__(self):
        if not os.path.exists("../../data/cookies.json"):
            logger.info("请先登录账号")
            self.account = input("请输入账号：")
            self.pwd = input("请输入密码：")
            
        # 设置Edge选项
        self.edge_options = Options()
        # self.edge_options.add_argument("--headless")  # 无头模式，不显示浏览器界面
        self.edge_options.add_argument("--disable-gpu")  # 禁用GPU加速
        self.service = Service("../../tools/msedgedriver.exe")  # 指定EdgeDriver的路径
        self.driver = webdriver.Edge(service=self.service, options=self.edge_options) # 初始化driver

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        if self.driver:
            self.driver.quit()

    def run(self):
        self._start_and_enter()
        self.confirm()

    def _start_and_enter(self):
        driver = self.driver
        logger.info("跳转到云游戏页面")
        url = "https://sr.mihoyo.com/cloud"
        driver.get(url)
        driver.set_window_size(1302, 855)
        driver.delete_all_cookies()
        logger.info("登录")
        self.login(driver)
        keyboard.wait("esc")
        WebDriverWait(driver, timeout=10).until(
            expected_conditions.presence_of_element_located((By.CLASS_NAME, "left")))
        free_time = driver.find_elements(By.CLASS_NAME, "left")
        for i in free_time:
            logger.info(i.text)
        start_game_button = driver.find_element(By.CLASS_NAME, "wel-card__content--start")
        ActionChains(driver).click(start_game_button).perform()
        WebDriverWait(driver, timeout=10).until(
            expected_conditions.presence_of_element_located((By.CLASS_NAME, "van-dialog__header")))
        van_dialog__header=driver.find_element(By.CLASS_NAME, "van-dialog__header")
        if van_dialog__header:
            logger.info("选择排队队列")
            line_item=driver.find_elements(By.CLASS_NAME, "coin-prior-choose-item-main__desc__main")
            for i in line_item:
                if i.text=="普通队列":
                    ActionChains(driver).click(i).perform()
                    break
        WebDriverWait(driver, timeout=10).until(
            expected_conditions.presence_of_element_located((By.CLASS_NAME, "waiting-in-queue")))
        logger.info("排队中")
        single_row__val=driver.find_element(By.CLASS_NAME, "single-row__val")
        wait_time_span=single_row__val.find_element(By.TAG_NAME, "span")
        wait_time=wait_time_span.text
        logger.info(f"预计等待时间：{wait_time} 分钟")
        match wait_time:
            case "<1":
                wait_time=120
            case "1~5":
                wait_time=300
            case "5~10":
                wait_time=600
            case "10~20":
                wait_time=1200
            case "20~30":
                wait_time=1800
            case ">30":
                wait_time=2400
        for i in range(1,wait_time):
            if i % 15 == 0:
                try:
                    t=single_row__val.find_element(By.TAG_NAME, "span").text
                except StaleElementReferenceException:
                    break
                logger.info(f"预计等待时间：{t} 分钟")
                if t=="<1":
                    break
            time.sleep(1)
        WebDriverWait(driver, timeout=300).until(
            expected_conditions.presence_of_element_located((By.TAG_NAME, "video")))
        logger.info("游戏启动中")
        return True

    def login(self, driver: WebDriver):
        wait = WebDriverWait(driver, timeout=120)
        if os.path.exists("../../data/cookies.json"):
            driver.delete_all_cookies()
            cookies = self.load_cookies()
            for cookie in cookies:
                driver.add_cookie(cookie)
        else:
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame("mihoyo-login-platform-iframe")
            login_with_passwd = driver.find_element(By.ID, "tab-password")
            ActionChains(driver).click(login_with_passwd).perform()
            username = driver.find_element(By.ID, "username")
            passwd = driver.find_element(By.ID, "password")
            ActionChains(driver).send_keys_to_element(username, self.account).perform()
            ActionChains(driver).send_keys_to_element(passwd, self.pwd).perform()
            el_checkbox_inner = driver.find_element(By.CLASS_NAME, "el-checkbox__inner")
            logger.info("勾选同意协议")
            ActionChains(driver).click(el_checkbox_inner).perform()
            logger.info("登录")
            login_button = driver.find_element(By.TAG_NAME, "button")
            ActionChains(driver).click(login_button).perform()
            driver.switch_to.default_content()
        wait.until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "wel-card__content--start")))
        self.save_cookies()
        return wait

    def confirm(self):
        driver = self.driver
        accept_flag = False
        next_step = 3
        while not accept_flag:
            time.sleep(5)
            span = driver.find_elements(By.TAG_NAME, "span")
            for i in span:
                if i.text == "接受":
                    ActionChains(driver).click(i).perform()
                    accept_flag = True
                    break
        while next_step > 0:
            try:
                div = driver.find_elements(By.TAG_NAME, "div")
            except Exception:
                continue
            for i in div:
                if "下一步" in i.text:
                    ActionChains(driver).click(i).perform()
                    next_step -= 1
                    break
                if "我知道了" in i.text:
                    ActionChains(driver).click(i).perform()
                    next_step = 0
                    break
        time.sleep(12)
        event_layer = driver.find_element(By.CLASS_NAME, "game-player__event-layer")
        ActionChains(driver).click(event_layer).click(event_layer).perform()
        return True

    def save_cookies(self):
        driver = self.driver
        cookies = driver.get_cookies()
        with open("../../data/cookies.json", "w") as file:
            json.dump(cookies, file, indent=4)

    @staticmethod
    def load_cookies():
        with open("../../data/cookies.json", "r") as file:
            cookies = json.load(file)
        return cookies

    @staticmethod
    def get_screenshot(driver: WebDriver):
        png = driver.get_screenshot_as_png()
        return png

    @staticmethod
    def _save_screenshot(driver: WebDriver):
        driver.save_screenshot("../../res/temp.png")

    @staticmethod
    def get_window_handle(driver: WebDriver):
        return driver.current_window_handle


class SRACloud(QThread):
    update_signal = Signal(str)

    def sent_signal(self, text):
        self.update_signal.emit(text)

    def request_stop(self):
        self.assistant.stop_flag = True

    def __init__(self):
        super().__init__()

    def run(self):
        with CloudGame() as cloud_game:
            cloud_game.run()

            # self.assistant = SRAssistant.Assistant('', True, cloud_game.driver)
            # self.assistant.log_signal.connect(self.sent_signal)
            # self.assistant.start()
            # self.assistant.wait()


if __name__ == "__main__":
    _ = SRACloud()
    _.start()
    _.wait()
