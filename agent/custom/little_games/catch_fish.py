import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction, RecognitionDetail

from agent.attach.little_game_attach import get_game_need_line
from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
from agent.constant.map_point import NAVIGATE_DATA
from agent.custom.general.general import ensure_main_page
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.custom.general.world_line_switcher import switch_line
from agent.custom.teleport_action import teleport_or_navigate
from agent.logger import logger
from agent.utils.param_utils import CustomActionParam


@AgentServer.custom_action("CatchFishPoint")
class CatchFishPointAction(CustomAction):

    def __init__(self):
        super().__init__()
        self.game_count = None
        self.is_first_time = None

    @exit_power_saving_mode()
    @ensure_main_page()
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:

        self.game_count = 0
        self.is_first_time = True

        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        max_game_count = int(params.data["max_game_count"]) if params.data["max_game_count"] else 0
        logger.info(f"本次任务设置的最大游鱼暴走次数: {max_game_count if max_game_count != 0 else '无限'}")

        # 第一次小游戏前所需切换的分线
        need_line = get_game_need_line(context)

        while not context.tasker.stopping:
            logger.info(f"=== 已成功游鱼暴走 {self.game_count} 次 ===")
            # 检查是否已经游戏足够次数了
            if max_game_count != 0 and max_game_count <= self.game_count:
                logger.info(f"已成功游鱼暴走了您所配置的{self.game_count}次，任务结束！")
                return True

            # 确保到达游鱼暴走的入口
            has_entry = ensure_catch_entry(context)
            if not has_entry:
                return False

            if need_line and self.is_first_time:
                switch_line(context, [str(need_line)])
                time.sleep(1)
            self.is_first_time = False

            # 确保进入游鱼暴走
            has_next = ensure_into_catch(context)
            if not has_next:
                return False

            # 已经在游戏中了，等待游戏结束
            logger.info("等待游戏结束后开启下一轮...")
            while True:
                if context.tasker.stopping:
                    logger.warning("游鱼暴走任务已结束！")
                    return True
                # 随便点击个位置防止月卡或者锁屏
                context.tasker.controller.post_click(638, 343).wait()
                time.sleep(0.5)
                # 不在游戏中就准备进行下一轮
                if not check_in_the_event(context):
                    time.sleep(6)
                    break
                time.sleep(5)
            
            self.game_count += 1

        logger.warning("游鱼暴走任务已结束！")
        return True


def ensure_into_catch(context: Context) -> bool:
    """
    确保进入游鱼暴走
    """
    while not context.tasker.stopping:
        # 先点击进入按钮，并等待 6 秒看是否进入小游戏
        context.tasker.controller.post_click(895, 344).wait()
        time.sleep(6)
        # 检测是否已经进入游鱼暴走游戏
        if check_has_spin(context):
            return True

    logger.error("游鱼暴走被手动中止！")
    return False


def ensure_catch_entry(context: Context, timeout: int = 120) -> bool:
    """确保到达游鱼暴走的入口"""
    # 先检测一下是否可以直接进
    if check_is_entry(context):
        return True

    # 第一次不行的话尝试向左走几步 | 可能是上一把刚结束的情况，走几步就能再次到入口
    context.tasker.controller.post_key_down(ANDROID_KEY_EVENT_DATA["KEYCODE_A"]).wait()
    time.sleep(1.5)
    context.tasker.controller.post_key_down(ANDROID_KEY_EVENT_DATA["KEYCODE_W"]).wait()
    time.sleep(0.8)
    context.tasker.controller.post_key_up(ANDROID_KEY_EVENT_DATA["KEYCODE_A"]).wait()
    context.tasker.controller.post_key_up(ANDROID_KEY_EVENT_DATA["KEYCODE_W"]).wait()
    time.sleep(0.5)

    # 再次检测是否可以直接进
    if check_is_entry(context):
        return True

    # 第二次还不行才导航过去
    teleport_or_navigate(context, "游星岛", "游鱼暴走", "导航", NAVIGATE_DATA)

    # 循环检测是否到达游鱼暴走的入口
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        if check_is_entry(context):
            logger.info(f"检测到已经到达游鱼暴走的入口！")
            return True
        time.sleep(2)
    logger.error(f"超 {timeout} 秒未到达游鱼暴走的入口 或 小游戏暂未开启！")
    return False


def check_is_entry(context: Context) -> bool:
    """
    检测当前是否到游鱼暴走的入口处
    """
    img = context.tasker.controller.post_screencap().wait().get()
    ocr_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {
                "expected": "报名",
                "roi": [871, 329, 51, 30],
            }
        },
    )
    if ocr_result and ocr_result.hit:
        return True
    else:
        return False


def check_has_spin(context: Context) -> bool:
    """
    检测当前是否已经进入游鱼暴走游戏
    """
    img = context.tasker.controller.post_screencap().wait().get()
    try:
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "游鱼暴走",
                    "roi": [77, 214, 92, 27],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            return True
        else:
            return False
    finally:
        del img


def check_in_the_event(context: Context) -> bool:
    """
    检测当前是否还在活动中
    """
    img = context.tasker.controller.post_screencap().wait().get()
    check_result: RecognitionDetail | None = context.run_recognition("检测是否在活动中", img)
    if check_result and check_result.hit:
        return True
    else:
        return False
