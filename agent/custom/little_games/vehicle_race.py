import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction, RecognitionDetail
from maa.define import Rect

from agent.attach.little_game_attach import get_vehicle_team_type, get_game_wait_time_limit
from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
from agent.constant.little_games import VEHICLE_CLICK_DATA
from agent.constant.map_point import NAVIGATE_DATA
from agent.custom.app_manage_action import wait_for_switch
from agent.custom.general.general import ensure_main_page
from agent.custom.general.move_battle import attack_rotate_view
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.custom.teleport_action import teleport_or_navigate
from agent.logger import logger
from agent.utils.param_utils import CustomActionParam


@AgentServer.custom_action("VehicleRacePoint")
class VehicleRacePointAction(CustomAction):

    def __init__(self):
        super().__init__()
        self.game_count = None

    @exit_power_saving_mode()
    @ensure_main_page()
    def run(
            self,
            context: Context,
            argv: CustomAction.RunArg,
    ) -> bool:

        self.game_count = 0

        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        max_game_count = int(params.data["max_game_count"]) if params.data["max_game_count"] else 0
        logger.info(f"本次任务设置的最大环城载具赛次数: {max_game_count if max_game_count != 0 else '无限'}")

        # 游戏等待超时时间
        wait_time_limit = get_game_wait_time_limit(context)

        # 队伍类型
        team_type = get_vehicle_team_type(context)
        if team_type == "无":
            logger.error("请先选择队伍类型！")
            return False
        # 是否是队长：队长要去NPC那边开本，队员不用干活
        is_leader = team_type in ["单人匹配游戏", "组队匹配游戏（队长）"]

        while not context.tasker.stopping:
            logger.info(f"=== 已成功环城载具赛 {self.game_count} 次 ===")
            # 检查是否已经游戏足够次数了
            if max_game_count != 0 and max_game_count <= self.game_count:
                logger.info(f"已成功环城载具赛了您所配置的{self.game_count}次，任务结束！")
                return True

            if is_leader:
                # 确保到达环城载具赛的入口
                if not ensure_race_entry(context):
                    return False

            # 确保进入环城载具赛
            has_next = ensure_into_race(context, is_leader, wait_time_limit)
            if not has_next:
                return False

            # 具体游戏操作
            time.sleep(2)
            has_next = game_content_cycle(context)
            if not has_next:
                return False

            # 结束了，准备 P 出副本
            logger.info("本轮游戏结束，准备 P 出副本...")
            time.sleep(2)
            context.tasker.controller.post_key_down(ANDROID_KEY_EVENT_DATA["KEYCODE_P"]).wait()
            time.sleep(2)
            context.tasker.controller.post_click(798, 535).wait()
            time.sleep(2)
            wait_for_switch(context)

            self.game_count += 1

        logger.warning("环城载具赛任务已结束！")
        return True


def ensure_into_race(context: Context, is_leader: bool, timeout: int = 300) -> bool:
    """
    确保开始对局
    """
    # 循环检测是否到准备页面
    start_time = time.time()
    elapsed_time = 0

    # 循环等待游戏开始
    while (timeout == 0 or elapsed_time <= timeout) and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        time.sleep(1.5)
        # 随便点击个位置防止月卡或者锁屏
        context.tasker.controller.post_click(638, 343).wait()
        time.sleep(0.5)

        # 如果在对局中就返回
        if check_in_match(context):
            return True

        if check_is_ready(context):
            logger.info("尝试点击进入环城载具赛对局...")
            # 点击确认进入副本
            time.sleep(0.5)
            context.tasker.controller.post_click(1142, 618).wait()

        if is_leader:
            # 没进入副本就再次检测
            rect = check_is_entry(context)
            if rect:
                # 点击进行匹配
                point_x = int(rect.x + rect.w / 2)
                point_y = int(rect.y + rect.h / 2)
                context.tasker.controller.post_click(point_x, point_y).wait()
                time.sleep(2)

    logger.error(f"等待环城载具赛对局超时或被手动停止：{timeout}")
    return False


def ensure_race_entry(context: Context, timeout: int = 120) -> bool:
    """确保到达环城载具赛的入口"""
    # 先检测一下是否可以直接进
    if check_is_entry(context):
        logger.info(f"检测到已经到达环城载具赛的入口！")
        return True

    # 不行才导航过去
    teleport_or_navigate(context, "游星岛", "欢闹游乐特派员", "导航", NAVIGATE_DATA)

    # 循环检测是否到达环城载具赛的入口
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        if check_is_entry(context):
            logger.info(f"检测到已经到达环城载具赛的入口！")
            return True
        time.sleep(2)
    logger.error(f"超 {timeout} 秒未到达环城载具赛的入口 或 小游戏暂未开启！")
    return False


def game_content_cycle(context: Context) -> bool:
    """
    游戏内容循环
    """
    check_id = 1
    while check_id < 15:
        # 按键实现
        logger.info(f"环城载具赛比赛检查点ID：{check_id}")
        has_next = check_key_service(context, check_id)
        if not has_next:
            return False

        if check_id != 1:
            # 最多 3 次检测检查点
            time.sleep(1)
            check_point = get_check_point(context)
            if not check_point:
                # 旋转视角再次检测
                attack_rotate_view(context, 1)
                check_point = get_check_point(context)
            if not check_point:
                # 旋转视角再次检测
                attack_rotate_view(context, 1)
                check_point = get_check_point(context)
        else:
            check_point = 2

        if not check_point or check_point == check_id + 1:
            logger.info(f"成功执行完检查点ID：{check_id}")
            # 任务 ID + 1
            check_id += 1
        else:
            logger.warning(f"检查点ID：{check_id} 执行失败，再次尝试该检查点任务")

        # 回检查点
        time.sleep(1)
        context.tasker.controller.post_click(868, 522, 1, 1).wait()
        start_time = time.time()
        elapsed_time = 0
        while elapsed_time <= 90 and not context.tasker.stopping:
            elapsed_time = time.time() - start_time
            if check_in_match(context):
                break
            time.sleep(2)

    return True


def check_key_service(context: Context, check_id: int):
    """
    检查点按键实现方法
    """
    # 每个检查点的路径数据
    scripts = VEHICLE_CLICK_DATA.get(f"check_{check_id}", [])
    for script in scripts:
        if context.tasker.stopping:
            return False

        # 获取参数
        delay = script.get("delay", 0)
        action_type = script.get("action_type", "")
        key_name = script.get("key_name", "")
        x = script.get("x", 0)
        y = script.get("y", 0)

        # 先进行延迟
        time.sleep(delay / 1000)

        # 判断类型
        match action_type:
            case "post_key_down":
                # 按下按键
                logger.info(f"按键按下: {key_name}")
                context.tasker.controller.post_key_down(ANDROID_KEY_EVENT_DATA[key_name]).wait()
            case "post_key_up":
                # 松开按键
                logger.info(f"按键松开: {key_name}")
                context.tasker.controller.post_key_up(ANDROID_KEY_EVENT_DATA[key_name]).wait()
            case "post_click":
                # 鼠标点击
                logger.info(f"鼠标点击: {x}, {y}")
                context.tasker.controller.post_click(x, y, 1, 1).wait()
            case _:
                pass
    return True


def check_is_entry(context: Context) -> Rect | None:
    """
    检测当前是否到环城载具赛的入口处
    """
    img = context.tasker.controller.post_screencap().wait().get()
    ocr_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {
                "expected": "参加<环",
                "roi": [875, 331, 72, 82],
            }
        },
    )
    if ocr_result and ocr_result.hit:
        # 获得最好结果坐标
        item = ocr_result.best_result
        return Rect(*item.box)  # type: ignore
    else:
        return None


def check_is_ready(context: Context) -> bool:
    """
    检测是否进入准备页面
    """
    img = context.tasker.controller.post_screencap().wait().get()
    ocr_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {
                "expected": ["接受"],
                "roi": [1116, 602, 52, 31]
            }
        },
    )
    if ocr_result and ocr_result.hit:
        logger.info(f"检测到准备按钮，准备进入环城载具赛...")
        return True
    else:
        return False


def check_in_match(context: Context) -> bool:
    """
    检测是否在比赛中
    """
    img = context.tasker.controller.post_screencap().wait().get()
    reg_result: RecognitionDetail | None = context.run_recognition("检测倒计时图标", img)
    if reg_result and reg_result.hit:
        logger.info(f"检测到已经在比赛中...")
        return True
    else:
        return False


def get_check_point(context: Context) -> int | None:
    """
    获取当前检查点
    """
    img = context.tasker.controller.post_screencap().wait().get()
    ocr_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {
                "expected": ["(\\d+/15)"],
                "roi": [1116, 602, 52, 31]
            }
        },
    )
    if ocr_result and ocr_result.hit:
        check_point = str(ocr_result.best_result.text)  # type:ignore
        check_point = check_point.replace("(", "").replace("15)", "")
        logger.info(f"获取到当前检查点为：{check_point}")
        return int(check_point)
    else:
        return None


@AgentServer.custom_action("VehicleCheckPoint")
class VehicleCheckPointAction(CustomAction):

    @exit_power_saving_mode()
    @ensure_main_page()
    def run(
            self,
            context: Context,
            argv: CustomAction.RunArg,
    ) -> bool:

        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        check_id = int(params.data["check_id"]) if params.data["check_id"] else 1
        logger.info(f"环城载具赛比赛检查点ID：{check_id}")

        has_next = check_key_service(context, check_id)
        if not has_next:
            return False

        logger.info(f"成功执行完检查点ID：{check_id}")
        return True
