import tomllib
from typing import Any, Callable, TypedDict, cast

from SRACore.task import BaseTask, task
from SRACore.util.errors import ErrorCode, SRAError
from SRACore.util.logger import logger
from tasks.img import IMG, TPIMG

type TrailblazePowerFunc = Callable[..., bool]

class SubtaskInfo(TypedDict, total=False):
    name: str
    func: str
    cost: int
    max_count: int
    levels: list[str]
    results: list[str]


@task(order=1)
class TrailblazePowerTask(BaseTask):
    def _post_init(self):
        with open(r"tasks/config/trailblaze_power.toml", "rb") as tf:
            self.task_config = tomllib.load(tf)

        self.replenish_time: int = self.config.get('TrailblazePowerReplenishTimes', 0)
        self.replenish_way: int = self.config.get('TrailblazePowerReplenishWay', 0)
        self.replenish_flag: bool = self.config.get('TrailblazePowerReplenishEnable', False)
        self.manual_tasks: list[tuple[TrailblazePowerFunc, dict[str, int]]] = list()
        self.auto_detect_tasks: list[Any] = list()

    def run(self):
        self.manual_tasks.clear()
        self.auto_detect_tasks.clear()
        use_build_target = self.config.get('TrailblazePowerUseBuildTarget')
        if use_build_target:
            self.detect_build_target_tasklist()
        else:
            self.init_custom_tasklist()
        for task, kwargs in self.manual_tasks:
            task(**kwargs)
        if len(self.auto_detect_tasks) > 0:
            detected_tasks = self.detect_tasks()
            if detected_tasks is None:
                return self.operator.press_key('esc')  # 退出生存索引页面
            for task, kwargs in detected_tasks:
                task(**kwargs)
        return True

    def init_custom_tasklist(self):
        """初始化自定义任务清单"""
        tasklist = cast(list[dict[str, Any]], self.config['TrailblazePowerTaskList'])
        for task in tasklist:
            if task.get("AutoDetect", False):
                self.auto_detect_tasks.append({
                    "Name": task.get("Name", task["Id"]),
                    "Id": cast(str, task["Id"]),
                    "Level": cast(int, task["Level"])
                })
            else:
                self.manual_tasks.append((
                    self.get_task_by_id(cast(str, task["Id"])),
                    {"level": cast(int, task["Level"]),
                     "single_time": cast(int, task["Count"]),
                     "run_time": cast(int, task["RunTimes"])}
                ))

    def detect_build_target_tasklist(self):
        """识别培养目标任务信息"""
        self.find_session("build_target")
        logger.info("识别培养目标任务信息")
        boxes = self.operator.locate_all(TPIMG.TRAILBLAZE_POWER)  # 定位所有体力图标
        if not boxes:
            logger.error(SRAError(ErrorCode.NO_BUILD_TARGET, "未找到任何培养目标任务"))
            self.operator.press_key("esc")
            return
        target_objects = []  # 存储识别到的培养目标任务对象
        for box in boxes:
            self.operator.click_box(box, x_offset=-520, after_sleep=1)  # 点击体力图标左侧位置, 检测目标材料
            raw_res = self.operator.ocr(from_x=0.4, from_y=0.25, to_x=0.6, to_y=0.35)
            if not raw_res:  # OCR结果为空的处理逻辑仅参考
                logger.warning("培养目标OCR识别为空，跳过当前目标")
                self.operator.press_key('esc')
                self.operator.sleep(1)
                continue
            res = "".join(t[1] for t in raw_res).replace('-', "一")  # OCR结果拼接并替换可能的错误字符
            logger.info(f"识别到所需物品: {res}")
            target_objects.append(res)
            self.operator.press_key('esc')
            self.operator.sleep(1)

        for obj in target_objects:
            # 从配置文件中匹配产物对应的副本任务
            subtasks:dict[str, Any] = self.task_config.get("subtasks", {})
            if subtasks is None:
                logger.error(SRAError(ErrorCode.NO_BUILD_TARGET, "培养目标配置缺少 subtasks"))
                return
            for subtask_id, subtask_info in subtasks.items():
                subtask_results = subtask_info.get("results", [])
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
                            task_name = subtask_info.get("name", subtask_id)
                            self.auto_detect_tasks.append(
                                {"Name": task_name,
                                 "Id": subtask_id,
                                 "Level": index + 1
                                 })
                        break
                else:
                    logger.debug(f"Could not find {obj} in subtask results of {subtask_id}")
                if found:
                    break

    def detect_tasks(self) -> list[tuple[TrailblazePowerFunc, dict[str, int]]] | None:
        """
        识别体力值并计算可执行的任务列表
        返回：任务列表（格式：[(任务对象, {"level": 等级, "single_time": 单次次数, "run_time": 执行轮数})]）
        失败返回None
        """
        if not self.goto_survival_index():
            logger.error(SRAError(ErrorCode.GO_TO_SURVIVAL_INDEX_FAILED, "跳转到生存索引页面失败"))
            return None
        self.operator.sleep(0.5)  # 等待页面加载
        try:
            # OCR识别体力值并过滤无效字符
            res = self.operator.ocr(from_x=0.65625, from_y=0.0417, to_x=0.908, to_y=0.076)
            if not res:
                logger.error(SRAError(ErrorCode.OCR_RECOGNITION_FAILED, "OCR识别结果为空"))
                self.operator.press_key("esc")
                return None
            # 过滤加号（兼容全角/空格变体）+ 空字符串
            exclude_chars = {'+', '十', '满'}
            valid_res: list[str] = [r[1] for r in res if r[1] not in exclude_chars]
            reserve_tbp = int(valid_res[0].replace('满', ''))  # 后备开拓力，替换可能的错误字符
            current_tbp_str = valid_res[1].split('/')[0] if '/' in valid_res[1] else valid_res[1]
            current_tbp = int(current_tbp_str)
            immersion_dev_str = valid_res[2].split('/')[0] if '/' in valid_res[2] else valid_res[2]
            immersion_dev = int(immersion_dev_str)
        except (ValueError, IndexError) as e:
            logger.error(SRAError(ErrorCode.POWER_DETECTION_FAILED, "识别到的体力值格式错误", str(e)))
            self.operator.press_key("esc")
            return None

        logger.info(f"当前后备开拓力: {reserve_tbp}, 当前开拓力: {current_tbp}, 沉浸器: {immersion_dev}")
        # 计算可用体力, 向下取整到10的倍数，且确保大于0
        ava_current_tbp = (current_tbp // 10) * 10
        if ava_current_tbp <= 0:
            logger.warning(SRAError(ErrorCode.NO_POWER, "当前体力为0，无任务可执行"))
            return None
        # 计算每个任务的可执行次数
        valid_auto_tasks = self.auto_detect_tasks
        if not valid_auto_tasks:
            logger.warning(SRAError(ErrorCode.NO_BUILD_TARGET, "未识别到可执行任务"))
            return None

        tasks_count = len(valid_auto_tasks)
        task_cost_list = [self.get_cost_by_id(task["Id"]) for task in valid_auto_tasks]  # 获取任务体力消耗列表
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
        for i, item in enumerate(valid_auto_tasks):
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

    def _get_subtask_info(self, task_id: str) -> SubtaskInfo:
        """任务ID转任务详情"""
        task_info = self.task_config.get("subtasks", {}).get(task_id)
        if task_info is None:
            raise RuntimeError("Invalid task ID")
        return task_info

    def get_task_by_id(self, task_id: str) -> TrailblazePowerFunc:
        """任务ID转任务函数"""
        task_func = self._get_subtask_info(task_id).get("func")
        if task_func is None:
            raise RuntimeError("Invalid task func")
        return getattr(self, task_func)

    def get_cost_by_id(self, task_id: str) -> int:
        """任务ID转任务体力消耗"""
        task_cost = self._get_subtask_info(task_id).get("cost")
        if task_cost is None:
            raise RuntimeError("Invalid task cost")
        return task_cost

    def get_max_count_by_id(self, task_id: str) -> int:
        """任务ID转任务最大单次执行次数"""
        max_count = self._get_subtask_info(task_id).get("max_count")
        if max_count is None:
            raise RuntimeError("Invalid task max_count")
        return max_count

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
        level = TPIMG.ORNAMENT_EXTRACTION % level
        if not self.find_session("ornament_extraction"):
            return False
        if self.operator.locate(TPIMG.ORNAMENT_EXTRACTION_NO_SAVE):
            logger.warning(SRAError(ErrorCode.NO_SAVE, "当前暂无可用存档，请前往[差分宇宙]获取存档"))
            self.operator.press_key("esc")
            return False
        if not self.find_level(level):
            return False
        if not self.operator.click_img(level, x_offset=700):
            logger.error(SRAError(ErrorCode.CLICK_LEVEL_FAILED, "点击关卡失败"))
            return False
        if not self.operator.wait_img(TPIMG.ORNAMENT_EXTRACTION_PAGE, timeout=20):  # 等待传送
            logger.error(SRAError(ErrorCode.WAIT_TIMEOUT, "等待页面加载超时", f"当前关卡：{level}"))
            return False
        if self.operator.locate(TPIMG.NO_SAVE):
            logger.warning(SRAError(ErrorCode.NO_SAVE, "当前暂无可用存档，请前往[差分宇宙]获取存档"))
            self.operator.press_key("esc", presses=2, interval=1)
            return False
        if single_time is not None:
            for _ in range(single_time - 1):
                self.operator.sleep(0.2)
                self.operator.click_img(TPIMG.PLUS)
            self.operator.sleep(1)
        # if self.config["TrailblazePowerUseAssistant"]:
        #     self.support()
        # 支援逻辑又不通用了
        if self.operator.click_img(TPIMG.BATTLE_STAR, after_sleep=1):
            if self.operator.locate(TPIMG.LIMIT):
                logger.warning(SRAError(ErrorCode.RELICS_LIMIT, "背包内遗器数量超过限制，请先清理"))
                self.operator.sleep(2)
                self.operator.press_key("esc", interval=1, presses=2)
                return False
            if self.operator.locate(TPIMG.REPLENISH):
                if self.replenish_flag:
                    self.replenish(self.replenish_way)
                    self.operator.click_img(TPIMG.BATTLE_STAR)
                else:
                    logger.info("体力不足")
                    self.operator.press_key("esc", interval=1, presses=3)
                    return False
            box = self.operator.locate(IMG.ENSURE2)
            if box:
                self.operator.click_box(box)
            if not self.operator.wait_img(IMG.F3, timeout=240):
                pass
            self.operator.hold_key("w", 2.5)
            for i in range(1, 5):
                self.operator.press_key(str(i))
                self.operator.sleep(0.5)
                self.operator.press_key(self.settings.General.hotkeyE.lower())
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
                           x_add=700,
                           y_add=0)

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
        level_path = TPIMG.level(level_belonging, level)
        if not self.find_session(level_belonging, scroll_flag):
            return False
        if not self.find_level(level_path):
            return False
        if self.operator.click_img(level_path, x_offset=x_add, y_offset=y_add):
            if not self._battle_after_enter(multi, run_time):
                return False
        logger.info(f"任务完成：{mission_name}")
        return True

    def _battle_after_enter(self, multi: int | None, run_time: int) -> bool:
        """进入副本后的通用战斗逻辑

        Args:
            multi: 单次连续挑战次数
            run_time: 执行轮数
        """
        if not self.operator.wait_img(TPIMG.BATTLE, timeout=20):  # 等待传送
            logger.error(SRAError(ErrorCode.WAIT_BATTLE_BOTTON_TIMEOUT, "等待挑战按钮超时失败"))
            return False
        if multi is not None and multi > 1:
            for _ in range(multi - 1):
                self.operator.sleep(0.2)
                self.operator.click_img(TPIMG.PLUS)
            self.operator.sleep(1)
        if not self.operator.click_img(TPIMG.BATTLE, after_sleep=1):
            logger.error(SRAError(ErrorCode.CLICK_BATTLE_BUTTON_FAILED, "点击挑战按钮失败"))
            return False
        if self.operator.locate(TPIMG.REPLENISH):
            if self.replenish_flag and self.replenish_time != 0:
                self.replenish(self.replenish_way)
                self.operator.click_img(TPIMG.BATTLE)
            else:
                logger.info("体力不足")
                self.operator.press_key("esc", interval=1, presses=3)
                return False
        if self.config["TrailblazePowerUseAssistant"]:
            self.support()
        if not self.operator.click_img(TPIMG.BATTLE_STAR, after_sleep=1):
            logger.warning(SRAError(ErrorCode.CLICK_BATTLE_STAR_FAILED, "点击开始挑战按钮失败"))
            self.operator.press_key("esc", interval=1, presses=3)
            return False
        if self.operator.locate(TPIMG.LIMIT):
            logger.warning(SRAError(ErrorCode.RELICS_LIMIT, "背包内遗器数量超过限制，请先清理"))
            self.operator.sleep(3)
            self.operator.press_key("esc", interval=1, presses=3)
            return False
        if self.operator.locate(IMG.ENSURE):
            logger.info("编队中存在无法战斗的角色")
            self.operator.press_key("esc", presses=3, interval=1.5)
            return False
        self.battle_star(run_time)
        return True

    def battle_star(self, run_time: int):
        logger.info("开始战斗")
        if self.operator.wait_img(IMG.Q):
            self.operator.press_key("v")
        logger.info("请检查自动战斗和倍速是否开启")
        while run_time > 1:
            logger.info(f"剩余次数{run_time}")
            battle_status = self.wait_battle_end()
            if battle_status == 1:
                logger.warning("战斗失败")
                self.operator.click_point(0.5, 0.5)  # 点击屏幕中心
                break

            if not self.operator.click_img(TPIMG.AGAIN):
                logger.error(SRAError(ErrorCode.CLICK_AGAIN_BUTTON_FAILED, "点击再次挑战按钮失败"))
                continue
            if self.operator.wait_img(TPIMG.REPLENISH, timeout=2):
                if self.replenish_flag and self.replenish_time:
                    self.replenish(self.replenish_way)
                    self.operator.click_img(TPIMG.AGAIN)
                else:
                    logger.info("体力不足")
                    self.operator.press_key("esc")
                    if not self.operator.click_img(TPIMG.QUIT_BATTLE):
                        logger.error(SRAError(ErrorCode.QUIT_BATTLE_FAILED, "退出战斗失败"))
                    logger.info("退出战斗")
                    result, _ = self.operator.wait_any_img([TPIMG.BATTLE, IMG.ENTER], timeout=10)
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
                if not self.operator.click_img(TPIMG.QUIT_BATTLE):
                    logger.error(SRAError(ErrorCode.QUIT_BATTLE_FAILED, "退出战斗失败"))
            logger.info("退出战斗")
            resources, _ = self.operator.wait_any_img([TPIMG.BATTLE, IMG.ENTER])
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
                TPIMG.QUIT_BATTLE,
                TPIMG.BATTLE_FAILURE,
                TPIMG.LIGHT_CONE
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
        """选择支援角色（固定选第一个可用角色）

        处理重复角色场景：
        - 第一个支援角色有替换图标（与队伍中角色重复）→ 直接入队，游戏自动替换
        - 没有替换图标 → 先踢掉 4 号位角色腾出位置，再入队
        """
        # 解除已有的支援角色
        if self.operator.click_img(TPIMG.REMOVE_SUPPORT, after_sleep=1):
            self.operator.move_rel(0, 100)

        # 点击支援按钮，打开支援角色列表
        _, target_box = self.operator.locate_any(
            [TPIMG.SUPPORT, TPIMG.SUPPORT2])
        if target_box is None:
            logger.warning("未找到支援按钮")
            return
        self.operator.click_box(target_box, after_sleep=1)

        # 第一个支援角色头像区域
        x1, y1, x2, y2 = 45, 190, 155, 320

        # 检查第一个支援角色是否有替换图标（与队伍中角色重复）
        w, h = self.operator.width, self.operator.height
        has_replace = self.operator.locate(
            TPIMG.DUPLICATE_REPLACED,
            from_x=x1 / w, from_y=y1 / h,
            to_x=x2 / w, to_y=y2 / h,
            confidence=0.7
        ) is not None

        if not has_replace:
            # 没有替换图标，先踢掉 4 号位角色腾出位置
            logger.info("未检测到替换图标，踢掉4号位角色")
            self.operator.click_point(0.892, 0.534, tag="踢掉4号位角色", after_sleep=1)

        # 点击第一个支援角色
        self.operator.click_point(
            (x1 + x2) // 2,
            (y1 + y2) // 2,
            tag="选择第一个支援角色",
            after_sleep=1,
        )

        # 确认入队
        self.operator.click_img(IMG.ENSURE2, after_sleep=1)

    def find_session(self, name, scroll_flag=False):
        name1 = TPIMG.session(name)
        name2 = TPIMG.session(name, onclick=True)
        if not self.goto_survival_index():
            return False
        if scroll_flag:
            self.operator.move_to(0.25, 0.5)
            self.operator.sleep(1)
            for _ in range(10):
                self.operator.scroll(-5)
        self.operator.sleep(0.5)
        _, result = self.operator.locate_any([name1, name2])
        if result:
            self.operator.click_box(result)
        else:
            logger.error(SRAError(ErrorCode.SESSION_NOT_FOUND, f"未找到副本类别：{name}"))
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
                        TPIMG.RESERVED_TRAILBLAZE_POWER_ONCLICK) or self.operator.click_img(
                    TPIMG.RESERVED_TRAILBLAZE_POWER):
                    # click('resources/img/count.png', x_add=200)
                    # if self.replenish_time>300:
                    #     write("300")
                    #     self.replenish_time-=299
                    # else:
                    #     write(str(self.replenish_time))
                    #     self.replenish_time=1
                    self.operator.click_img(IMG.ENSURE, after_sleep=1)
                    self.operator.click_img(IMG.ENSURE, after_sleep=1)
                    self.operator.click_point(0.5, 0.7)  # 点击屏幕中心
                    logger.info("已使用后备开拓力进行补充")
                else:
                    logger.error(SRAError(ErrorCode.REPLENISH_POWER_FAILED, "补充体力失败", "补充方式：使用后备开拓力"))
                    return False
            elif way == 1:
                if self.operator.click_img(TPIMG.FUEL) or self.operator.locate(
                        TPIMG.FUEL_ONCLICK):
                    self.operator.click_img(IMG.ENSURE, after_sleep=1.5)
                    self.operator.click_img(IMG.ENSURE, after_sleep=1.5)
                    self.operator.click_point(0.5, 0.7)  # 点击屏幕中心
                    logger.info("已使用燃料进行补充")
                else:
                    logger.error(SRAError(ErrorCode.REPLENISH_POWER_FAILED, "补充体力失败", "补充方式：使用燃料"))
                    return False
            elif way == 2:
                if self.operator.click_img(TPIMG.STELLAR_JADE) or self.operator.locate(
                        TPIMG.STELLAR_JADE_ONCLICK):
                    self.operator.click_img(IMG.ENSURE, after_sleep=2)
                    self.operator.click_img(IMG.ENSURE, after_sleep=3)
                    self.operator.click_point(0.5, 0.7)
                    logger.info("已使用星琼进行补充")
                else:
                    logger.error(SRAError(ErrorCode.REPLENISH_POWER_FAILED, "补充体力失败", "补充方式：使用星琼"))
                    return False
            self.replenish_time -= 1
            return True
        else:
            return False

    def goto_survival_index(self) -> bool:
        """前往生存索引页面"""
        logger.info("前往生存索引页面")
        index, box = self.operator.wait_any_img([
            IMG.ENTER,
            IMG.SURVIVAL_INDEX,
            IMG.SURVIVAL_INDEX_ONCLICK
        ], timeout=30, interval=0.5)
        if index == 2:
            # 已经在生存索引页面
            return True
        elif index == 1:
            # 生存索引页面，点击进入
            self.operator.click_box(box)  # type: ignore
            return self.operator.wait_img(IMG.SURVIVAL_INDEX_ONCLICK, timeout=10) is not None
        elif index == 0:
            # 主页面，按快捷键进入生存索引页面
            self.operator.press_key(self.settings.General.hotkeyF4.lower())
            self.operator.sleep(1.5)
            return self.goto_survival_index()  # 递归调用，直到进入生存索引页面
        else:
            return False
