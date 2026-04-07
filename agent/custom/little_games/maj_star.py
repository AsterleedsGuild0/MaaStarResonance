import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction, RecognitionDetail

from agent.attach.little_game_attach import get_maj_team_type, get_maj_wait_time_limit
from agent.constant.map_point import NAVIGATE_DATA
from agent.custom.general.general import ensure_main_page
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.custom.teleport_action import teleport_or_navigate
from agent.logger import logger
from agent.utils.param_utils import CustomActionParam


@AgentServer.custom_action("MajStarPoint")
class MajStarPointAction(CustomAction):

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
        logger.info(f"本次任务设置的最大麻将次数: {max_game_count if max_game_count != 0 else '无限'}")

        # 麻将队伍类型
        maj_wait_time_limit = get_maj_wait_time_limit(context)

        # 麻将队伍类型
        maj_team_type = get_maj_team_type(context)
        if maj_team_type == "无":
            logger.error("请先选择麻将队伍类型！")
            return False
        # 是否是队长：队长要去NPC那边开本，队员不用干活
        is_leader = maj_team_type in ["单人匹配游戏", "组队私人游戏（队长）"]

        while not context.tasker.stopping:
            logger.info(f"=== 已成功完成麻将 {self.game_count} 次 ===")
            # 检查是否已经完成足够次数了
            if max_game_count != 0 and max_game_count <= self.game_count:
                logger.info(f"已成功完成了您所配置的{self.game_count}次麻将，任务结束！")
                return True

            if is_leader:
                # 确保到达麻将的入口
                has_entry = ensure_maj_entry(context)
                if not has_entry:
                    return False
                # 点击雀牌游戏
                context.tasker.controller.post_click(857, 342).wait()
                time.sleep(2)

            # 确保开始对局
            has_next = ensure_into_game(context, is_leader, maj_wait_time_limit)
            if not has_next:
                return False

            # 正式的游戏环节
            has_next = maj_task_cycle(context)
            if not has_next:
                return False
            
            self.game_count += 1

            # 5秒后开始下一轮
            time.sleep(5)

        logger.warning("麻将任务已结束！")
        return True


def ensure_maj_entry(context: Context, timeout: int = 120) -> bool:
    """
    确保到达麻将的入口
    """
    # 先检测一下是否可以直接进
    if check_is_entry(context):
        return True

    # 不行才导航过去
    teleport_or_navigate(context, "游星岛", "雀牌游戏", "导航", NAVIGATE_DATA)

    # 循环检测是否到达麻将入口
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        if check_is_entry(context):
            logger.info(f"已经到达麻将的入口，尝试点击开始游戏")
            return True
        time.sleep(2)
    logger.error(f"超 {timeout} 秒未到达麻将的入口！")
    return False


def ensure_into_game(context: Context, is_leader: bool, timeout: int = 300) -> bool:
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
            logger.info("尝试点击进入麻将对局...")
            # 点击确认进入副本
            time.sleep(0.5)
            context.tasker.controller.post_click(1143, 618).wait()

        if is_leader:
            # 没进入副本就再次检测
            if check_is_entry(context):
                # 点击雀牌游戏
                context.tasker.controller.post_click(857, 342).wait()
                time.sleep(2)

    logger.error(f"等待麻将对局超时或被手动停止：{timeout}")
    return False


def maj_task_cycle(context: Context) -> bool:
    """
    正式的麻将对局循环
    """
    while not context.tasker.stopping:
        time.sleep(1.5)
        # 随便点击个位置防止月卡或者锁屏
        context.tasker.controller.post_click(638, 343).wait()
        time.sleep(0.5)

        img = context.tasker.controller.post_screencap().wait().get()
        # 检测自动和牌是否未开启
        reg_result: RecognitionDetail | None = context.run_recognition("检测自动和牌是否未开启", img)
        if reg_result and reg_result.hit:
            context.tasker.controller.post_click(28, 430).wait()
            time.sleep(0.5)
        # 检测跳过鸣牌是否未开启
        reg_result: RecognitionDetail | None = context.run_recognition("检测跳过鸣牌是否未开启", img)
        if reg_result and reg_result.hit:
            context.tasker.controller.post_click(28, 484).wait()
            time.sleep(0.5)
        # 检测自动摸切是否未开启
        reg_result: RecognitionDetail | None = context.run_recognition("检测自动摸切是否未开启", img)
        if reg_result and reg_result.hit:
            context.tasker.controller.post_click(28, 537).wait()
            time.sleep(0.5)
        # 检测是否需要点击跳过按钮 | 暗杠
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "跳过",
                    "roi": [745, 541, 144, 69],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            context.tasker.controller.post_click(815, 576).wait()
            time.sleep(0.5)

        # 检测是否终局
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "终局",
                    "roi": [565, 66, 144, 69],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            logger.info(f"本局麻将对局已完成，等待5秒后开启下一轮！")
            # 点击确认按钮
            time.sleep(1.5)
            context.tasker.controller.post_click(639, 662).wait()
            time.sleep(0.5)
            return True

    return False


def check_is_entry(context: Context) -> bool:
    """
    检测当前是否到麻将的入口处
    """
    img = context.tasker.controller.post_screencap().wait().get()
    ocr_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {
                "expected": "雀牌",
                "roi": [874, 330, 44, 29],
            }
        },
    )
    if ocr_result and ocr_result.hit:
        logger.info(f"检测到已经到达麻将的入口")
        return True
    else:
        return False


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
                "roi": [1113, 603, 56, 27]
            }
        },
    )
    if ocr_result and ocr_result.hit:
        logger.info(f"检测到准备按钮，准备进入麻将...")
        return True
    else:
        return False


def check_in_match(context: Context) -> bool:
    """
    检测是否在对局中
    """
    img = context.tasker.controller.post_screencap().wait().get()
    reg_result: RecognitionDetail | None = context.run_recognition("检测是否已经在麻将对局中", img)
    if reg_result and reg_result.hit:
        logger.info(f"检测到已经在对局中...")
        return True
    else:
        return False
