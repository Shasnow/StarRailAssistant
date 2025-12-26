from typing import Any

from SRACore.task import BaseTask
from SRACore.util.logger import logger


class TrailblazePowerTask(BaseTask):
    def __init__(self, config: dict):
        super().__init__(config)
        self.name_task_map = {
            "饰品提取": self.ornament_extraction,
            "拟造花萼（金）": self.calyx_golden,
            "拟造花萼（赤）": self.calyx_crimson,
            "凝滞虚影": self.stagnant_shadow,
            "侵蚀隧洞": self.caver_of_corrosion,
            "历战余响": self.echo_of_war
        }
        self.task_cost_map = {
            "饰品提取": 40,
            "拟造花萼（金）": 10,
            "拟造花萼（赤）": 10,
            "凝滞虚影": 30,
            "侵蚀隧洞": 40,
            "历战余响": 30
        }
        self.replenish_time = self.config.get('TrailblazePowerReplenishTimes')
        self.replenish_way = self.config.get('TrailblazePowerReplenishWay')
        self.replenish_flag = self.config.get('TrailblazePowerReplenishEnable')
        tasklist: list[dict[str, Any]] = self.config['TrailblazePowerTaskList']
        self.manual_tasks = list()
        self.auto_detect_tasklist = list()
        for task in tasklist:
            if task.get("AutoDetect", False):
                self.auto_detect_tasklist.append(task)
            else:
                self.manual_tasks.append((
                    self.name2task(task["Name"]),
                    {"level": task["Level"],
                     "single_time": task["Count"],
                     "run_time": task["RunTimes"]}
                ))

    def detect_tasks(self) -> list[Any] | None:
        if not self.goto_survival_index():
            return None
        self.sleep(0.5)  # 等待页面加载
        # 识别体力值
        res = self.ocr(from_x=0.65625, from_y=0.0417, to_x=0.908, to_y=0.076)
        valid_res=[r[1] for r in res if r[1] not in ['+', '十']]  # 过滤掉识别结果中的加号
        try:
            reserve_tbp = int(valid_res[0])
            current_tbp = int(valid_res[1].split('/')[0])
            immersion_dev = int(valid_res[2].split('/')[0])
        except (ValueError, IndexError):
            logger.error("体力识别失败，无法进行自动检测")
            self.press_key("esc")
            return None
        logger.info(f"当前后备开拓力: {reserve_tbp}, 当前开拓力: {current_tbp}, 沉浸器: {immersion_dev}")
        ava_current_tbp = current_tbp//10 * 10  # 向下取整到10的倍数
        cost_per_task = int(ava_current_tbp // len(self.auto_detect_tasklist))  # 每个任务可用体力
        tasks = []
        for task_info in self.auto_detect_tasklist:
            task_name = task_info["Name"]
            task_level = task_info["Level"]
            task_cost = self.get_task_cost(task_name)
            max_single_times = cost_per_task // task_cost  # 该任务单次可执行最大次数
            logger.info(f"{task_name} 自动检测的挑战次数: {max_single_times}")
            if max_single_times > 0:
                tasks.append((
                    self.name2task(task_name),
                    {"level": task_level,
                     "single_time": max_single_times,
                     "run_time": 1}
                ))
        return tasks


    def name2task(self, name: str):
        """任务名称转任务函数"""
        return self.name_task_map.get(name)

    def get_task_cost(self, name: str):
        """任务体力消耗"""
        return self.task_cost_map.get(name, 0)

    def run(self):
        for task, kwargs in self.manual_tasks:
            if self.stop_flag:
                return False
            task(**kwargs)
        if len(self.auto_detect_tasklist) > 0:
            detected_tasks = self.detect_tasks()
            if detected_tasks is None:
                return False
            for task, kwargs in detected_tasks:
                if self.stop_flag:
                    return False
                task(**kwargs)
        return True

    def ornament_extraction(self, level, single_time: int | None = None, run_time=1, **_)-> bool:
        """Ornament extraction

        Args:
            level (int): The index of level in /resources/img.
            run_time (int): The time of battle.
            single_time (None|int): If this mission can battle multiply at a single time,
        Returns:
            None
        """
        logger.info("执行任务：饰品提取")
        level = f"resources/img/ornament_extraction ({level}).png"
        if not self.find_session("ornament_extraction"):
            return False
        if self.locate("resources/img/no_save.png"):
            logger.warning("当前暂无可用存档，请前往[差分宇宙]获取存档")
            self.press_key("esc")
            return False
        if not self.find_level(level):
            return False
        if not self.click_img(level, x_offset=700):
            logger.error("发生错误，错误编号3")
            return False
        if not self.wait_img('resources/img/ornament_extraction_page.png', timeout=20):  # 等待传送
            logger.error("检测超时，编号4")
            return False
        if self.config.get("TrailblazePowerLineupCheck") and self.click_img("resources/img/nobody.png", after_sleep=2):
            self.click_img("resources/img/preset_formation.png", after_sleep=2)
            self.click_img("resources/img/team1.png", after_sleep=2)
        if single_time is not None:
            for _ in range(single_time - 1):
                self.sleep(0.2)
                self.click_img("resources/img/plus.png")
            self.sleep(1)
        if self.click_img("resources/img/battle_star.png", after_sleep=1):
            if self.locate("resources/img/limit.png"):
                logger.warning("背包内遗器持有数量已达上限，请先清理")
                self.sleep(2)
                self.press_key("esc", interval=1, presses=2)
                return False
            if self.locate("resources/img/replenish.png"):
                if self.replenish_flag:
                    self.replenish(self.replenish_way)
                    self.click_img("resources/img/battle_star.png")
                else:
                    logger.info("体力不足")
                    self.press_key("esc", interval=1, presses=3)
                    return False
            if not self.wait_img("resources/img/f3.png", timeout=240):
                pass
            self.hold_key("w", 2.5)
            if self.config.get("TrailblazePowerUseSkill"):
                for i in range(1, 5):
                    self.press_key(str(i))
                    self.sleep(0.5)
                    self.press_key(self.settings.get('TechniqueHotkey', 'e').lower())
                    self.sleep(2)
            self.click_point(0.5, 0.5)
            self.battle_star(run_time)
        logger.info("任务完成：饰品提取")
        return True

    def calyx_golden(self, level, single_time=1, run_time=1, **_):
        levels = ["神谕圣地", "纷争荒墟", "呓语密林",
                  "筑梦边境", "稚子的梦", "白日梦",
                  "流云渡", "太卜司", "工造司",
                  "城郊雪原", "边缘通路", "大矿区"]
        return self.battle("拟造花萼（金）",
                    "calyx(golden)",
                    levels,
                    level,
                    run_time,
                    False,
                    single_time)

    def calyx_crimson(self, level, single_time=1, run_time=1, **_):
        levels = ["鳞渊境", "收容舱段",
                  "克劳克", "支援舱段",
                  "苏乐达", "城郊雪原",
                  "绥园", "边缘通路",
                  "匹诺", "铆钉镇",
                  "白日梦", "机械聚落",
                  "丹鼎司", "大矿区",
                  "纷争"]
        return self.battle("拟造花萼（赤）",
                    "calyx(crimson)",
                    levels,
                    level,
                    run_time,
                    False,
                    single_time,
                    y_add=-30)

    def stagnant_shadow(self, level, single_time=1, run_time=1, **_):
        levels = ["溟簇之形", '职司之形', '幽府之形', '锋芒之形',
                  "嗔怒之形", '燔灼之形', '炎华之形',
                  "塞壬之形", '冰酿之形', '冰棱之形', '霜晶之形',
                  "机狼之形", '震厄之形', '鸣雷之形',
                  '烬日之形', '今宵之形', '天人之形', '风之形',
                  '凛月之形', '焦炙之形', '孽兽之形', '空海之形',
                  '役轮之形', '弦音之形', '偃偶之形', '幻光之形']
        return self.battle("凝滞虚影",
                    "stagnant_shadow",
                    levels,
                    level,
                    run_time,
                    True,
                    single_time)

    def caver_of_corrosion(self, level, single_time=1, run_time=1, **_):
        levels = ['隐救之径', '雳涌之径', '弦歌之径', '迷识之径', '勇骑之径', '梦潜之径',
                  '幽冥之径', '药使之径', '野焰之径', '圣颂之径', '睿治之径',
                  '漂泊之径', '迅拳之径', '霜风之径']
        return self.battle("侵蚀隧洞",
                    "caver_of_corrosion",
                    levels,
                    level,
                    run_time,
                    True,
                    single_time,
                    x_add=700)

    def echo_of_war(self, level, single_time=1, run_time=1, **_):
        levels = ['晨昏', '心兽', '尘梦', '蛀星',
                  '不死', '寒潮', '毁灭']
        return self.battle("历战余响",
                    "echo_of_war",
                    levels,
                    level,
                    run_time,
                    True,
                    single_time,
                    x_add=770,
                    y_add=25)

    def battle(self,
               mission_name: str,
               level_belonging: str,
               levels: list,
               level: int,
               run_time: int,
               scroll_flag: bool,
               multi: None | int = None,
               x_add: int = 650,
               y_add: int = 0):
        """Battle Any

            Note:
                Do not include the `self` parameter in the ``Args`` section.
            Args:

                mission_name (str): The name of this mission.
                level_belonging (str): The series to which the level belongs.
                levels (list): The list of levels in this series.
                level (int): The index of level in /resources/img.
                run_time (int): Number of times the task was executed.
                scroll_flag (bool): Whether scroll or not when finding session.
                multi (None|int): If this mission can battle multiply at a single time,
                                    this arg must be an int, None otherwise.
                x_add: int
                y_add: int
            Returns:
                None
        """
        logger.info(f"执行任务：{mission_name}")
        level_path = f"resources/img/{level_belonging} ({level}).png"
        if not self.find_session(level_belonging, scroll_flag):
            return False
        if not self.find_level(level_path):
            return False
        if self.click_img(level_path, x_offset=x_add, y_offset=y_add):
            if not self.wait_img('resources/img/battle.png', timeout=20):  # 等待传送
                logger.error("检测超时，编号4")
                return False
            if multi is not None:
                for _ in range(multi - 1):
                    self.sleep(0.2)
                    self.click_img("resources/img/plus.png")
                self.sleep(1)
            if not self.click_img("resources/img/battle.png", after_sleep=1):
                logger.error("发生错误，错误编号3")
                return False
            if self.locate("resources/img/replenish.png"):
                if self.replenish_flag and self.replenish_time != 0:
                    self.replenish(self.replenish_way)
                    self.click_img("resources/img/battle.png")
                else:
                    logger.info("体力不足")
                    self.press_key("esc", interval=1, presses=3)
                    return False
            if self.config["TrailblazePowerUseAssistant"]:
                self.support()
            self.sleep(1)
            if not self.click_img("resources/img/battle_star.png", after_sleep=1):
                logger.warning("发生错误，错误编号4")
                self.press_key("esc", interval=1, presses=3)
                return False
            if self.locate("resources/img/limit.png"):
                logger.warning("背包内遗器已达上限，请先清理")
                self.sleep(3)
                self.press_key("esc", interval=1, presses=3)
                return False
            if self.locate("resources/img/ensure.png"):
                logger.info("编队中存在无法战斗的角色")
                self.press_key("esc", presses=3, interval=1.5)
                return False
            else:
                self.battle_star(run_time)
        logger.info(f"任务完成：{mission_name}")
        return True

    def battle_star(self, run_time: int):
        logger.info("开始战斗")
        logger.info("请检查自动战斗和倍速是否开启")
        if self.wait_img("resources/img/q.png"):
            self.press_key("v")
        while run_time > 1:
            logger.info(f"剩余次数{run_time}")
            battle_status = self.wait_battle_end()
            if battle_status == 1:
                logger.warning("战斗失败")
                self.click_point(0.5, 0.5)  # 点击屏幕中心
                break

            if self.config["TrailblazePowerChangeLineup"]:
                self.click_img("resources/img/change_lineup.png")
            if not self.click_img("resources/img/again.png"):
                logger.error("发生错误，错误编号5")
                continue
            if self.wait_img("resources/img/replenish.png", timeout=2):
                if self.replenish_flag and self.replenish_time:
                    self.replenish(self.replenish_way)
                    self.click_img("resources/img/again.png")
                else:
                    logger.info("体力不足")
                    self.press_key("esc")
                    if not self.click_img("resources/img/quit_battle.png"):
                        logger.error("发生错误，错误编号12")
                    logger.info("退出战斗")
                    result, _ = self.wait_any_img(["resources/img/battle.png", "resources/img/enter.png"], timeout=10)
                    if result == 0:
                        self.press_key("esc", wait=1)
                    elif result == 1:
                        pass
                    break
            if self.config["TrailblazePowerUseAssistant"]:
                self.support()
            if self.config["TrailblazePowerChangeLineup"]:
                self.click_img("resources/img/battle_star.png")

            run_time -= 1
            self.sleep(3)
        else:
            battle_status = self.wait_battle_end()
            if battle_status == 1:
                logger.warning("战斗失败")
                self.click_point(0.5, 0.5)  # 点击屏幕中心
            else:
                if not self.click_img("resources/img/quit_battle.png"):
                    logger.error("发生错误，错误编号12")
            logger.info("退出战斗")
            resources, _ = self.wait_any_img(["resources/img/battle.png", "resources/img/enter.png"])
            if resources == 0:
                self.press_key("esc", wait=1)
            elif resources == 1:
                pass

    def wait_battle_end(self):
        """Wait battle end

        Returns:
            battle status index:
             - ``0``->battle ended normally.\n
             - ``1``->battle failed.\n
             - ``-1``->unknown error.
        """
        logger.info("等待战斗结束")
        while True:
            self.sleep(1)
            # 检查战斗结束状态
            index, _ = self.locate_any([
                "resources/img/quit_battle.png",
                "resources/img/battle_failure.png",
                "resources/img/light_cone.png"
            ], trace=False)
            if index == -1:
                continue  # 继续等待战斗结束
            if index == 2:
                logger.info("获得光锥")
                self.click_point(0.5, 0.8)  # 点击屏幕中心偏下位置关闭弹窗
                continue  # 继续检测战斗结束状态
            logger.info("战斗结束")
            return index

    def find_level(self, level: str) -> bool:
        """Fine battle level

        Returns:
            True if found.
        """
        self.move_to(0.45, 0.5)
        times = 0
        while True:
            times += 1
            if times == 20:
                return False
            self.sleep(0.5)
            if self.locate(level):
                return True
            else:
                for _ in range(12):
                    self.scroll(-1)

    def support(self):
        if self.click_img("resources/img/remove_support.png", after_sleep=1):
            self.move_rel(0, 100)
        if self.click_img("resources/img/support.png", after_sleep=1):
            self.click_img("resources/img/enter_line.png", after_sleep=1)

    def find_session(self, name, scroll_flag=False):
        name1 = "resources/img/" + name + ".png"
        name2 = "resources/img/" + name + "_onclick.png"
        if not self.goto_survival_index():
            return False
        if scroll_flag:
            self.sleep(1)
            self.move_rel(0, 100)
            for i in range(10):
                self.scroll(-5)
        self.sleep(0.5)
        _, result = self.locate_any([name1, name2])
        if result:
            self.click_box(result)
        else:
            logger.error("发生错误，错误编号2")
            self.press_key("esc")
            return False
        return True

    def replenish(self, way):
        """Replenish trailblaze power

        Note:
            Do not include the `self` parameter in the ``Args`` section.

            ``way``:
             - ``1``->replenishes by reserved trailblaze power.\n
             - ``2``->replenishes by fuel.\n
             - ``3``->replenishes by stellar jade.
        Args:
            way (int): Index of way in /resources/img.
        Returns:
            True if replenished successfully, False otherwise.
        """
        if self.replenish_time != 0:
            logger.info("补充体力")
            if way == 0:
                if self.locate("resources/img/reserved_trailblaze_power_onclick.png") or self.click_img(
                        "resources/img/reserved_trailblaze_power.png"):
                    # click('resources/img/count.png', x_add=200)
                    # if self.replenish_time>300:
                    #     write("300")
                    #     self.replenish_time-=299
                    # else:
                    #     write(str(self.replenish_time))
                    #     self.replenish_time=1
                    self.click_img("resources/img/ensure.png", after_sleep=1)
                    self.click_img("resources/img/ensure.png", after_sleep=1)
                    self.click_point(0.5, 0.7)  # 点击屏幕中心
                    logger.info("已使用后备开拓力进行补充")
                else:
                    logger.error("发生错误，错误编号13")
                    return False
            elif way == 1:
                if self.click_img("resources/img/fuel.png") or self.locate("resources/img/fuel_onclick.png"):
                    self.click_img("resources/img/ensure.png", after_sleep=1.5)
                    self.click_img("resources/img/ensure.png", after_sleep=1.5)
                    self.click_point(0.5, 0.7)  # 点击屏幕中心
                    logger.info("已使用燃料进行补充")
                else:
                    logger.error("发生错误，错误编号14")
                    return False
            elif way == 2:
                if self.click_img("resources/img/stellar_jade.png") or self.locate(
                        "resources/img/stellar_jade_onclick.png"):
                    self.click_img("resources/img/ensure.png", after_sleep=2)
                    self.click_img("resources/img/ensure.png", after_sleep=3)
                    self.click_point(0.5, 0.7)
                    logger.info("已使用星琼进行补充")
                else:
                    logger.error("发生错误，错误编号15")
                    return False
            self.replenish_time -= 1
            return True
        else:
            return False

    def goto_survival_index(self) -> bool:
        """前往生存索引页面"""
        logger.info("前往生存索引页面")
        index, box = self.wait_any_img([
            "resources/img/enter.png",
            "resources/img/survival_index.png",
            "resources/img/survival_index_onclick.png"
        ], timeout=30, interval=0.5)
        if index == 2:
            # 已经在生存索引页面
            return True
        elif index == 1:
            # 生存索引页面，点击进入
            self.click_box(box)
            return True
        elif index == 0:
            # 主页面，按快捷键进入生存索引页面
            self.press_key(self.settings.get('GuideHotkey', 'f4').lower())
            self.sleep(1.5)
            return self.goto_survival_index()  # 递归调用，直到进入生存索引页面
        else:
            return False