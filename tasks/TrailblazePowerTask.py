import tomllib
from typing import Any, Callable

from SRACore.task import BaseTask
from SRACore.util.logger import logger

type TrailblazePowerFunc = Callable[[int, int, int], bool]


class TrailblazePowerTask(BaseTask):
    def _post_init(self):
        with open(r"tasks/config/trailblaze_power.toml", "rb") as tf:
            self.task_config = tomllib.load(tf)

        self.replenish_time = self.config.get('TrailblazePowerReplenishTimes')
        self.replenish_way = self.config.get('TrailblazePowerReplenishWay')
        self.replenish_flag = self.config.get('TrailblazePowerReplenishEnable')
        self.manual_tasks: list[tuple[TrailblazePowerFunc, dict[str, Any]]] = list()
        self.auto_detect_tasks = list()

    def run(self):
        self.manual_tasks.clear()
        self.auto_detect_tasks.clear()
        use_build_target = self.config.get('TrailblazePowerUseBuildTarget')
        if use_build_target:
            self.detect_build_target_tasklist()
        else:
            self.init_custom_tasklist()
        for task, kwargs in self.manual_tasks:
            if self.stop_flag:
                return False
            task(**kwargs)
        if len(self.auto_detect_tasks) > 0:
            detected_tasks = self.detect_tasks()
            if detected_tasks is None:
                return self.operator.press_key('esc')  # 退出生存索引页面
            for task, kwargs in detected_tasks:
                if self.stop_flag:
                    return False
                task(**kwargs)
        return True

    def init_custom_tasklist(self):
        """初始化自定义任务清单"""
        tasklist: list[dict[str, Any]] = self.config['TrailblazePowerTaskList']
        for task in tasklist:
            if task.get("AutoDetect", False):
                self.auto_detect_tasks.append(task)
            else:
                self.manual_tasks.append((
                    self.get_task_by_id(task["Id"]),
                    {"level": task["Level"],
                     "single_time": task["Count"],
                     "run_time": task["RunTimes"]}
                ))

    def detect_build_target_tasklist(self):
        """识别培养目标任务信息"""
        self.find_session("build_target")
        logger.info("识别培养目标任务信息")
        boxes = self.operator.locate_all("resources/img/tp/trailblaze_power.png")  # 定位所有体力图标
        if not boxes:
            logger.error("未找到任何培养目标任务")
            self.operator.press_key("esc")
            return
        target_objects = []  # 存储识别到的培养目标任务对象
        for box in boxes:
            self.operator.click_box(box, x_offset=-520, after_sleep=1)  # 点击体力图标左侧位置, 检测目标材料
            raw_res = self.operator.ocr(from_x=0.4, from_y=0.25, to_x=0.6, to_y=0.35)
            res = "".join(t[1] for t in raw_res).replace('-', "一")  # OCR结果拼接并替换可能的错误字符
            logger.info(f"识别到所需物品: {res}")
            target_objects.append(res)
            self.operator.press_key('esc')
            self.operator.sleep(1)

        for obj in target_objects:
            # 从配置文件中匹配产物对应的副本任务
            for subtask_id, subtask_info in self.task_config.get("subtasks").items():
                subtask_results = subtask_info.get("results")
                if subtask_results is None:
                    continue
                found = False  # 标记是否找到对应结果
                for index, r in enumerate(subtask_results):
                    if obj in r:
                        logger.info(f"{obj} 需要刷取 {subtask_info.get('name')} 的关卡 {index + 1}")
                        found = True
                        if subtask_id == "echo_of_war":
                            # 历战余响特殊处理
                            self.manual_tasks.append((self.get_task_by_id(subtask_id), {
                                "level": index + 1,
                                "single_time": 3,
                                "run_time": 1
                            }))
                        else:
                            self.auto_detect_tasks.append(
                                {"Name": subtask_info.get("name"),
                                 "Id": subtask_id,
                                 "Level": index + 1
                                 })
                        break
                else:
                    logger.debug(f"Could not find {obj} in subtask results of {subtask_id}")
                if found:
                    break

    def detect_tasks(self) -> list[Any] | None:
        """
        识别体力值并计算可执行的任务列表
        返回：任务列表（格式：[(任务对象, {"level": 等级, "single_time": 单次次数, "run_time": 执行轮数})]）
        失败返回None
        """
        if not self.goto_survival_index():
            logger.error("跳转生存索引页面失败")
            return None
        self.operator.sleep(0.5)  # 等待页面加载
        try:
            # OCR识别体力值并过滤无效字符
            res = self.operator.ocr(from_x=0.65625, from_y=0.0417, to_x=0.908, to_y=0.076)
            if not res:
                logger.error("OCR识别结果为空")
                self.operator.press_key("esc")
                return None
            # 过滤加号（兼容全角/空格变体）+ 空字符串
            exclude_chars = {'+', '十', '＋', '满'}
            valid_res:list[str] = [r[1] for r in res if r[1] not in exclude_chars]
            reserve_tbp = int(valid_res[0].replace('满', ''))  # 后备开拓力，替换可能的错误字符
            current_tbp_str = valid_res[1].split('/')[0] if '/' in valid_res[1] else valid_res[1]
            current_tbp = int(current_tbp_str)
            immersion_dev_str = valid_res[2].split('/')[0] if '/' in valid_res[2] else valid_res[2]
            immersion_dev = int(immersion_dev_str)
        except (ValueError, IndexError) as e:
            logger.error(f"体力识别失败, 无法进行自动检测: {e}")
            self.operator.press_key("esc")
            return None

        logger.info(f"当前后备开拓力: {reserve_tbp}, 当前开拓力: {current_tbp}, 沉浸器: {immersion_dev}")
        # 计算可用体力, 向下取整到10的倍数，且确保大于0
        ava_current_tbp = (current_tbp // 10) * 10
        if ava_current_tbp <= 0:
            logger.warning("可用开拓力为0，无任务可执行")
            return None
        # 计算每个任务的可执行次数
        tasks_count = len(self.auto_detect_tasks)
        task_cost_list = [self.get_cost_by_id(task.get("Id")) for task in self.auto_detect_tasks]  # 获取任务体力消耗列表
        sum_cost = sum(task_cost_list)
        min_cost = min(task_cost_list)
        base = ava_current_tbp // sum_cost  # 基础可执行次数
        remain = ava_current_tbp % sum_cost  # 剩余体力
        logger.info(f"每个任务基础可执行次数: {base}, 剩余体力: {remain}")
        tasks_times = [base for _ in range(tasks_count)]  # 初始化每个任务的执行次数列表
        # 分配剩余体力
        # 将任务按体力升序排序，保留原始索引 (体力值, 原索引)
        sorted_tasks = sorted((val, idx) for idx, val in enumerate(task_cost_list))
        # 分配剩余体力：小体力任务优先，尽可能多分配
        while remain >= min_cost:
            for val, idx in sorted_tasks:
                if remain >= val:
                    tasks_times[idx] += 1
                    remain -= val
                # 剩余体力不足，直接退出
                if remain < min_cost:
                    break

        # 生成最终任务列表
        tasks = []
        for i, item in enumerate(self.auto_detect_tasks):
            task_func = self.get_task_by_id(item["Id"])
            run_time = tasks_times[i]
            logger.info(f"任务 {item['Name']} ({item['Level']}) 将执行 {run_time} 次")
            if run_time == 0:
                continue  # 跳过执行次数为0的任务
            max_single_time = self.get_max_count_by_id(item["Id"])
            while run_time > 0:
                single_time = min(run_time, max_single_time)
                tasks.append((
                    task_func,
                    {
                        "level": item["Level"],
                        "single_time": single_time,
                        "run_time": 1
                    }
                ))
                run_time -= single_time
        return tasks if tasks else None

    def _get_task_detail_by_id(self, detail: str, task_id: str):
        """任务ID转任务详情"""
        task_info = self.task_config.get("subtasks", {}).get(task_id)
        if not task_info:
            raise RuntimeError("Invalid task ID")
        return task_info.get(detail)

    def get_task_by_id(self, task_id: str) -> TrailblazePowerFunc:
        """任务ID转任务函数"""
        task_func = self._get_task_detail_by_id("func", task_id)
        return getattr(self, task_func)

    def get_cost_by_id(self, task_id: str):
        """任务ID转任务体力消耗"""
        return self._get_task_detail_by_id("cost", task_id)

    def get_max_count_by_id(self, task_id: str):
        """任务ID转任务最大单次执行次数"""
        return self._get_task_detail_by_id("max_count", task_id)

    def ornament_extraction(self, level, single_time: int | None = None, run_time=1, **_) -> bool:
        """Ornament extraction

        Args:
            level (int): The index of level in /resources/img.
            run_time (int): The time of battle.
            single_time (None|int): If this mission can battle multiply at a single time,
        Returns:
            None
        """
        logger.info("执行任务：饰品提取")
        level = f"resources/img/tp/ornament_extraction ({level}).png"
        if not self.find_session("ornament_extraction"):
            return False
        if self.operator.locate("resources/img/tp/ornament_extraction_no_save.png"):
            logger.warning("当前暂无可用存档，请前往[差分宇宙]获取存档")
            self.operator.press_key("esc")
            return False
        if not self.find_level(level):
            return False
        if not self.operator.click_img(level, x_offset=700):
            logger.error("发生错误，错误编号3")
            return False
        if not self.operator.wait_img('resources/img/tp/ornament_extraction_page.png', timeout=20):  # 等待传送
            logger.error("检测超时，编号4")
            return False
        if single_time is not None:
            for _ in range(single_time - 1):
                self.operator.sleep(0.2)
                self.operator.click_img("resources/img/plus.png")
            self.operator.sleep(1)
        if self.config["TrailblazePowerUseAssistant"]:
            self.support()
        if self.operator.click_img("resources/img/battle_star.png", after_sleep=1):
            if self.operator.locate("resources/img/limit.png"):
                logger.warning("背包内遗器持有数量已达上限，请先清理")
                self.operator.sleep(2)
                self.operator.press_key("esc", interval=1, presses=2)
                return False
            if self.operator.locate("resources/img/replenish.png"):
                if self.replenish_flag:
                    self.replenish(self.replenish_way)
                    self.operator.click_img("resources/img/battle_star.png")
                else:
                    logger.info("体力不足")
                    self.operator.press_key("esc", interval=1, presses=3)
                    return False
            if not self.operator.wait_img("resources/img/f3.png", timeout=240):
                pass
            self.operator.hold_key("w", 2.5)
            for i in range(1, 5):
                self.operator.press_key(str(i))
                self.operator.sleep(0.5)
                self.operator.press_key(self.settings.get('TechniqueHotkey', 'e').lower())
                self.operator.sleep(2)
            self.operator.click_point(0.5, 0.5)
            self.battle_star(run_time)
        logger.info("任务完成：饰品提取")
        return True

    def calyx_golden(self, level, single_time=1, run_time=1, **_):
        return self.battle("拟造花萼（金）",
                           "calyx(golden)",
                           level,
                           run_time,
                           False,
                           single_time)

    def calyx_crimson(self, level, single_time=1, run_time=1, **_):
        return self.battle("拟造花萼（赤）",
                           "calyx(crimson)",
                           level,
                           run_time,
                           False,
                           single_time,
                           x_add = 700,
                           y_add = 0)

    def stagnant_shadow(self, level, single_time=1, run_time=1, **_):
        return self.battle("凝滞虚影",
                           "stagnant_shadow",
                           level,
                           run_time,
                           True,
                           single_time)

    def caver_of_corrosion(self, level, single_time=1, run_time=1, **_):
        return self.battle("侵蚀隧洞",
                           "caver_of_corrosion",
                           level,
                           run_time,
                           True,
                           single_time,
                           x_add=700)

    def echo_of_war(self, level, single_time=1, run_time=1, **_):
        return self.battle("历战余响",
                           "echo_of_war",
                           level,
                           run_time,
                           True,
                           single_time,
                           x_add=770,
                           y_add=25)

    def battle(self,
               mission_name: str,
               level_belonging: str,
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
        level_path = f"resources/img/tp/{level_belonging} ({level}).png"
        if not self.find_session(level_belonging, scroll_flag):
            return False
        if not self.find_level(level_path):
            return False
        if self.operator.click_img(level_path, x_offset=x_add, y_offset=y_add):
            if not self._battle_after_enter(multi, run_time):
                return False
        logger.info(f"任务完成：{mission_name}")
        return True

    def _battle_after_enter(self, multi: int | None, run_time: int, skip_wait: bool = False) -> bool:
        """进入副本后的通用战斗逻辑

        Args:
            multi: 单次连续挑战次数
            run_time: 执行轮数
            skip_wait: 是否跳过等待传送（已在外部完成时设为True）
        """
        if not skip_wait:
            if not self.operator.wait_img('resources/img/battle.png', timeout=20):  # 等待传送
                logger.error("检测超时，编号4")
                return False
        if multi is not None and multi > 1:
            for _ in range(multi - 1):
                self.operator.sleep(0.2)
                self.operator.click_img("resources/img/plus.png")
            self.operator.sleep(1)
        if not self.operator.click_img("resources/img/battle.png", after_sleep=1):
            logger.error("发生错误，错误编号3")
            return False
        if self.operator.locate("resources/img/replenish.png"):
            if self.replenish_flag and self.replenish_time != 0:
                self.replenish(self.replenish_way)
                self.operator.click_img("resources/img/battle.png")
            else:
                logger.info("体力不足")
                self.operator.press_key("esc", interval=1, presses=3)
                return False
        if self.config["TrailblazePowerUseAssistant"]:
            self.support()
        if not self.operator.click_img("resources/img/battle_star.png", after_sleep=1):
            logger.warning("发生错误，错误编号4")
            self.operator.press_key("esc", interval=1, presses=3)
            return False
        if self.operator.locate("resources/img/limit.png"):
            logger.warning("背包内遗器已达上限，请先清理")
            self.operator.sleep(3)
            self.operator.press_key("esc", interval=1, presses=3)
            return False
        if self.operator.locate("resources/img/ensure.png"):
            logger.info("编队中存在无法战斗的角色")
            self.operator.press_key("esc", presses=3, interval=1.5)
            return False
        self.battle_star(run_time)
        return True

    def battle_star(self, run_time: int):
        logger.info("开始战斗")
        if self.operator.wait_img("resources/img/q.png"):
            self.operator.press_key("v")
        logger.info("请检查自动战斗和倍速是否开启")
        while run_time > 1:
            logger.info(f"剩余次数{run_time}")
            battle_status = self.wait_battle_end()
            if battle_status == 1:
                logger.warning("战斗失败")
                self.operator.click_point(0.5, 0.5)  # 点击屏幕中心
                break

            if not self.operator.click_img("resources/img/again.png"):
                logger.error("发生错误，错误编号5")
                continue
            if self.operator.wait_img("resources/img/replenish.png", timeout=2):
                if self.replenish_flag and self.replenish_time:
                    self.replenish(self.replenish_way)
                    self.operator.click_img("resources/img/again.png")
                else:
                    logger.info("体力不足")
                    self.operator.press_key("esc")
                    if not self.operator.click_img("resources/img/quit_battle.png"):
                        logger.error("发生错误，错误编号12")
                    logger.info("退出战斗")
                    result, _ = self.operator.wait_any_img(["resources/img/battle.png", "resources/img/enter.png"],
                                                           timeout=10)
                    if result == 0:
                        self.operator.press_key("esc", wait=1)
                    elif result == 1:
                        pass
                    break
            if self.config["TrailblazePowerUseAssistant"]:
                self.support()

            run_time -= 1
            self.operator.sleep(3)
        else:
            battle_status = self.wait_battle_end()
            if battle_status == 1:
                logger.warning("战斗失败")
                self.operator.click_point(0.5, 0.5)  # 点击屏幕中心
            else:
                if not self.operator.click_img("resources/img/quit_battle.png"):
                    logger.error("发生错误，错误编号12")
            logger.info("退出战斗")
            resources, _ = self.operator.wait_any_img(["resources/img/battle.png", "resources/img/enter.png"])
            if resources == 0:
                self.operator.press_key("esc", wait=1)
            elif resources == 1:
                pass

    def wait_battle_end(self):
        """Wait battle end

        Returns:
            battle status index:
             - ``0``->battle ended normally.
             - ``1``->battle failed.
             - ``-1``->unknown error.
        """
        logger.info("等待战斗结束")
        while True:
            self.operator.sleep(1)
            # 检查战斗结束状态
            index, _ = self.operator.locate_any([
                "resources/img/quit_battle.png",
                "resources/img/battle_failure.png",
                "resources/img/light_cone.png"
            ], trace=False)
            if index == -1:
                continue  # 继续等待战斗结束
            if index == 2:
                logger.info("获得光锥")
                self.operator.click_point(0.5, 0.8)  # 点击屏幕中心偏下位置关闭弹窗
                continue  # 继续检测战斗结束状态
            logger.info("战斗结束")
            return index

    def find_level(self, level: str) -> bool:
        """Fine battle level

        Returns:
            True if found.
        """
        self.operator.move_to(0.45, 0.5)
        times = 0
        while True:
            times += 1
            if times == 20:
                return False
            self.operator.sleep(0.5)
            if self.operator.locate(level):
                return True
            else:
                for _ in range(12):
                    self.operator.scroll(-1)

    def support(self):
        if self.operator.click_img("resources/img/remove_support.png", after_sleep=1):
            self.operator.move_rel(0, 100)
        target_index, target_box = self.operator.locate_any(
            ["resources/img/tp/support.png", "resources/img/tp/support2.png"])
        self.operator.click_box(target_box, after_sleep=1)
        if target_index == 0:
            self.operator.click_img("resources/img/enter_line.png")
        elif target_index == 1:
            self.operator.click_point(0.1646, 0.2241, tag="支援1号位")
        self.operator.sleep(1)
        self.operator.click_img("resources/img/ensure2.png", after_sleep=1)  # 点掉可能出现的提示框

    def find_session(self, name, scroll_flag=False):
        name1 = f"resources/img/tp/{name}.png"
        name2 = f"resources/img/tp/{name}_onclick.png"
        if not self.goto_survival_index():
            return False
        if scroll_flag:
            self.operator.move_to(0.25, 0.5)
            self.operator.sleep(1)
            for i in range(10):
                self.operator.scroll(-5)
        self.operator.sleep(0.5)
        _, result = self.operator.locate_any([name1, name2])
        if result:
            self.operator.click_box(result)
        else:
            logger.error("发生错误，错误编号2")
            self.operator.press_key("esc")
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
                if self.operator.locate(
                        "resources/img/reserved_trailblaze_power_onclick.png") or self.operator.click_img(
                        "resources/img/reserved_trailblaze_power.png"):
                    # click('resources/img/count.png', x_add=200)
                    # if self.replenish_time>300:
                    #     write("300")
                    #     self.replenish_time-=299
                    # else:
                    #     write(str(self.replenish_time))
                    #     self.replenish_time=1
                    self.operator.click_img("resources/img/ensure.png", after_sleep=1)
                    self.operator.click_img("resources/img/ensure.png", after_sleep=1)
                    self.operator.click_point(0.5, 0.7)  # 点击屏幕中心
                    logger.info("已使用后备开拓力进行补充")
                else:
                    logger.error("发生错误，错误编号13")
                    return False
            elif way == 1:
                if self.operator.click_img("resources/img/fuel.png") or self.operator.locate(
                        "resources/img/fuel_onclick.png"):
                    self.operator.click_img("resources/img/ensure.png", after_sleep=1.5)
                    self.operator.click_img("resources/img/ensure.png", after_sleep=1.5)
                    self.operator.click_point(0.5, 0.7)  # 点击屏幕中心
                    logger.info("已使用燃料进行补充")
                else:
                    logger.error("发生错误，错误编号14")
                    return False
            elif way == 2:
                if self.operator.click_img("resources/img/stellar_jade.png") or self.operator.locate(
                        "resources/img/stellar_jade_onclick.png"):
                    self.operator.click_img("resources/img/ensure.png", after_sleep=2)
                    self.operator.click_img("resources/img/ensure.png", after_sleep=3)
                    self.operator.click_point(0.5, 0.7)
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
        index, box = self.operator.wait_any_img([
            "resources/img/enter.png",
            "resources/img/survival_index.png",
            "resources/img/survival_index_onclick.png"
        ], timeout=30, interval=0.5)
        if index == 2:
            # 已经在生存索引页面
            return True
        elif index == 1:
            # 生存索引页面，点击进入
            self.operator.click_box(box)
            return self.operator.wait_img("resources/img/survival_index_onclick.png", timeout=10) is not None
        elif index == 0:
            # 主页面，按快捷键进入生存索引页面
            self.operator.press_key(self.settings.get('GuideHotkey', 'f4').lower())
            self.operator.sleep(1.5)
            return self.goto_survival_index()  # 递归调用，直到进入生存索引页面
        else:
            return False
