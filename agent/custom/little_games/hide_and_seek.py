import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction, RecognitionDetail

from agent.attach.common_attach import get_hide_team_type
from agent.constant.map_point import NAVIGATE_DATA
from agent.custom.app_manage_action import wait_for_switch
from agent.custom.general.general import ensure_main_page
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.custom.teleport_action import teleport_or_navigate
from agent.logger import logger
from agent.utils.param_utils import CustomActionParam


@AgentServer.custom_action("HideSeekPoint")
class HideSeekPointAction(CustomAction):

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
        logger.info(f"本次任务设置的最大躲猫猫次数: {max_game_count if max_game_count != 0 else '无限'}")

        # 躲猫猫队伍类型
        hide_team_type = get_hide_team_type(context)
        if hide_team_type == "无":
            logger.error("请先选择躲猫猫队伍类型！")
            return False
        # 是否是队长：队长要去NPC那边开本，队员不用干活
        is_leader = hide_team_type in ["单人匹配游戏", "组队匹配游戏（队长）", "组队私人游戏（队长，队伍人数须>=5）"]
        # 是否是开黑模式：开黑模式直接点开始按钮，匹配模式要等待匹配到              
        is_private = hide_team_type in ["组队私人游戏（队长，队伍人数须>=5）", "组队私人游戏（队员）"]

        while not context.tasker.stopping:
            logger.info(f"=== 已成功躲猫猫 {self.game_count} 次 ===")
            # 检查是否已经躲猫猫足够次数了
            if max_game_count != 0 and max_game_count <= self.game_count:
                logger.info(f"已成功躲猫猫了您所配置的{self.game_count}次，躲猫猫结束！")
                return True
            
            if is_leader:
                # 确保到达躲猫猫的入口
                has_entry = ensure_hide_entry(context)
                if not has_entry:
                    return False
            
                # 点击不思议的追逃游戏
                context.tasker.controller.post_click(852, 400).wait()
                time.sleep(1)
            
            # 确保开始游戏 | 匹配/开黑模式
            has_next = ensure_into_game(context, is_leader, is_private)
            if not has_next:
                logger.error("无法开始游戏，躲猫猫任务将直接停止...")
                return False

            # 等待场景切换完成
            wait_for_switch(context)

            # 等待躲猫猫游戏对局结束
            ensure_for_end(context)
            # 等待场景切换完成后开始下一轮
            wait_for_switch(context)

            if is_leader:
                # 多等待10秒 | 对齐不同设备切换场景的加载速度
                logger.info(f"等待10秒后进行下一轮躲猫猫...")
                time.sleep(10)
        
        logger.warning("躲猫猫任务已结束！")
        return True


def ensure_into_game(context: Context, is_leader: bool, is_private: bool, timeout: int = 300) -> bool:
    """
    确保开始游戏 | 匹配/开黑模式
    """
    # 循环检测是否到准备页面
    start_time = time.time()
    elapsed_time = 0

    # 循环等待游戏开始
    while elapsed_time <= timeout and not context.tasker.stopping:
        logger.info(f"检测并准备进入游戏")
        elapsed_time = time.time() - start_time

        if not is_leader:
            if check_is_ready(context):
                # 点击确认进入副本
                context.tasker.controller.post_click(1148, 657).wait()
                return True
            # 没有就继续循环 | 不执行下面队长的逻辑
            continue

        img = context.tasker.controller.post_screencap().wait().get()
        if is_private:
            # 点击右下角开黑模式
            ocr_result: RecognitionDetail | None = context.run_recognition(
                "通用文字识别",
                img,
                pipeline_override={
                    "通用文字识别": {
                        "expected": "开黑模式",
                        "roi": [941, 641, 98, 29],
                    }
                },
            )
            if ocr_result and ocr_result.hit:
                context.tasker.controller.post_click(990, 656).wait()
        else:
            # 点击右下角匹配模式
            ocr_result: RecognitionDetail | None = context.run_recognition(
                "通用文字识别",
                img,
                pipeline_override={
                    "通用文字识别": {
                        "expected": "匹配进入",
                        "roi": [1128, 641, 93, 31],
                    }
                },
            )
            if ocr_result and ocr_result.hit:
                context.tasker.controller.post_click(1175, 656).wait()

        # 每隔两秒检测一次
        time.sleep(2)
        if check_is_ready(context):
            return True
        
        time.sleep(2)
        if check_is_ready(context):
            return True
    
    logger.error(f"超 300 秒未确保开始游戏！")
    return False


def ensure_hide_entry(context: Context, timeout: int = 120) -> bool:
    """
    确保到达躲猫猫的入口
    """
    # 先检测一下是否可以直接进
    if check_is_entry(context):
        return True

    # 不行才导航过去
    teleport_or_navigate(context, "游星岛", "不思议的追逃游戏", "导航", NAVIGATE_DATA)

    # 循环检测是否到达躲猫猫入口
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        if check_is_entry(context):
            logger.info(f"检测到已经到达躲猫猫的入口！")
            return True
        time.sleep(2)
    logger.error("超 120 秒未到达躲猫猫的入口！")
    return False


def ensure_for_end(context: Context, timeout: int = 1200) -> bool:
    """
    确保躲猫猫游戏对局结束
    """
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        if wait_for_end(context):
            logger.info(f"检测到躲猫猫游戏对局结束！")
            return True
        time.sleep(5)
    logger.error("超 1200 秒躲猫猫游戏对局未结束！")
    return False


def wait_for_end(context: Context):
    """
    等待游戏彻底结束
    """
    img = context.tasker.controller.post_screencap().wait().get()
    ocr_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {
                "expected": "退出副本",
                "roi": [67, 29, 90, 29],
            }
        },
    )
    if ocr_result and ocr_result.hit:
        logger.info(f"检测到躲猫猫游戏对局已结束")
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
                "expected": ["(确认|取消)"],
                "roi": [1128, 640, 58, 35]
            }
        },
    )
    if ocr_result and ocr_result.hit:
        logger.info(f"检测到准备按钮，准备进入躲猫猫...")
        return True
    else:
        return False


def check_is_entry(context: Context) -> bool:
    """
    检测当前是否到躲猫猫的入口处
    """
    img = context.tasker.controller.post_screencap().wait().get()
    ocr_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {
                "expected": "不思议",
                "roi": [874, 387, 64, 26],
            }
        },
    )
    if ocr_result and ocr_result.hit:
        logger.info(f"检测到已经到达躲猫猫的入口！")
        return True
    else:
        return False
