import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction, RecognitionDetail

from agent.attach.common_attach import get_hide_team_type
from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
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
        is_leader = hide_team_type in ["单人匹配游戏", "组队匹配游戏（队长）", "组队私人游戏（队长，队伍人数须>=5）"]

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
            
            # TODO 队长根据不同队伍类型选择不同的进本方式
            
            # 确保匹配到玩家
            has_next = ensure_into_game(context, is_leader)
            if not has_next:
                logger.error("无法匹配到玩家，躲猫猫任务将直接停止...")
                return False
            
            # 点击进入副本 TODO 未录入坐标
            context.tasker.controller.post_click(0, 0).wait()
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


def ensure_into_game(context: Context, is_leader: bool = True, timeout: int = 300, try_limit: int = 10) -> bool:
    """
    确保匹配到玩家
    """
    # 尝试 try_limit 次匹配
    for try_count in range(try_limit):
        logger.info(f"本轮躲猫猫 - 第 {try_count + 1} 次尝试匹配玩家")

        if is_leader:
            # 先点击匹配按钮
            context.tasker.controller.post_click(895, 344).wait()

        # 循环检测是否到准备页面
        start_time = time.time()
        elapsed_time = 0
        while elapsed_time <= timeout + 5 and not context.tasker.stopping:
            elapsed_time = time.time() - start_time
            if check_is_ready(context):
                return True
            time.sleep(2)
        logger.error(f"超 300 秒未匹配到玩家！")
    return False


def ensure_hide_entry(context: Context, timeout: int = 120) -> bool:
    """
    确保到达躲猫猫的入口
    """
    # 先检测一下是否可以直接进
    if check_is_entry(context):
        return True

    # 第一次不行的话尝试向前走几步 | 可能是上一把刚结束的情况，走几步就能再次到入口
    context.tasker.controller.post_key_down(ANDROID_KEY_EVENT_DATA["KEYCODE_W"]).wait()
    time.sleep(1.4)
    context.tasker.controller.post_key_up(ANDROID_KEY_EVENT_DATA["KEYCODE_W"]).wait()
    time.sleep(0.5)

    # 再次检测是否可以直接进
    if check_is_entry(context):
        return True

    # 第二次还不行才导航过去
    teleport_or_navigate(context, "游星岛", "不思议的追逃游戏", "导航", NAVIGATE_DATA)  # TODO 坐标未录入

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
                "expected": "",  # TODO 副本内图标
                "roi": [0, 0, 0, 0],
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
                "expected": "准备",  # TODO 准备按钮
                "roi": [0, 0, 0, 0],
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
                "expected": "匹配",  # TODO 匹配按钮
                "roi": [871, 329, 51, 30],
            }
        },
    )
    if ocr_result and ocr_result.hit:
        logger.info(f"检测到已经到达躲猫猫的入口！")
        return True
    else:
        return False
