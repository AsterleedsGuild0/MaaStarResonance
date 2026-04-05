import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction, RecognitionDetail

from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
from agent.constant.map_point import NAVIGATE_DATA
from agent.custom.app_manage_action import wait_for_switch
from agent.custom.general.general import ensure_main_page
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.custom.general.world_line_switcher import switch_line
from agent.custom.teleport_action import teleport_or_navigate
from agent.logger import logger
from agent.utils.param_utils import CustomActionParam


@AgentServer.custom_action("BeatChenMinPoint")
class BeatChenMinPointAction(CustomAction):

    def __init__(self):
        super().__init__()
        self.beat_count = None
        self.tried_count = None
        self.is_first_line = None

    @exit_power_saving_mode()
    @ensure_main_page()
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:

        self.beat_count = 0
        self.tried_count = 0
        self.is_first_line = True

        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        max_beat_count = int(params.data["max_beat_count"]) if params.data["max_beat_count"] else 0
        logger.info(f"本次任务设置的最大暴打次数: {max_beat_count if max_beat_count != 0 else '无限'}")

        while not context.tasker.stopping:
            logger.info(f"=== 已成功暴打陈敏 {self.beat_count} 次 ===")
            # 检查是否已经暴打足够次数了
            if max_beat_count != 0 and max_beat_count <= self.beat_count:
                logger.info(f"已成功暴打了您所配置的{self.beat_count}次陈敏，暴打结束！")
                return True

            # 确保到达暴打陈敏的入口
            has_entry = ensure_chen_entry(context)
            if not has_entry:
                return False

            # 确保切到一条能暴打陈敏的分线
            has_next = self.ensure_can_beat_chen(context)
            if not has_next:
                # 所有线都打不了就结束任务
                return False

            # 已经在游戏中了：先向前走几步
            logger.info("向前走几步靠近陈敏，等待一会后开始暴打2次")
            context.tasker.controller.post_key_down(ANDROID_KEY_EVENT_DATA["KEYCODE_W"]).wait()
            time.sleep(0.8)
            context.tasker.controller.post_key_up(ANDROID_KEY_EVENT_DATA["KEYCODE_W"]).wait()

            # 按几下攻击键
            time.sleep(5)
            context.tasker.controller.post_click(1122, 550, 1, 1).wait()
            time.sleep(5)
            context.tasker.controller.post_click(1122, 550, 1, 1).wait()

            # 等待一会后开启下一轮暴打
            logger.info("等待70秒暴打结束...")
            wait_count = 0
            while wait_count < 14 and not context.tasker.stopping:
                wait_count += 1
                time.sleep(5)
            
            self.beat_count += 1

        logger.warning("暴打陈敏已结束！")
        return True

    def ensure_can_beat_chen(self, context: Context) -> bool:
        """
        循环检测是否可进入暴打陈敏，不可进入则切线。
        11-60 线全部尝试一轮，若都失败则返回 False。
        """

        # 避开 1-10 线
        line_list = [str(i) for i in range(11, 61)]
        total_lines = len(line_list)

        while self.tried_count < total_lines:  # type: ignore
            if context.tasker.stopping:
                logger.warning("暴打陈敏检测已被手动停止")
                return False

            # 获取当前索引 和 尝试的分线
            index = self.tried_count % total_lines  # type: ignore
            if self.is_first_line:
                current_line = "初始"
            else:
                current_line = line_list[index]
            logger.info(f"尝试切线次数={self.tried_count}，准备在 {current_line} 分线尝试暴打陈敏")

            # 先点击进入按钮，并等待 6 秒看是否进入小游戏
            context.tasker.controller.post_click(895, 344).wait()
            time.sleep(6)

            # 检测是否已经进入暴打陈敏游戏
            if check_can_beat_chen(context):
                logger.info(f"检测到当前线路 {current_line} 已经进入暴打陈敏游戏")
                return True
            else:
                logger.info(f"当前线路 {current_line} 不可进入暴打陈敏，准备切线...")
                self.is_first_line = False

            # 当前的分线列表
            need_switch_list = line_list[index:] + line_list[:index]
            # 尝试切换分线
            has_next = switch_line(context, need_switch_list)
            # 尝试次数 + 1
            self.tried_count += 1  # type: ignore
            # 切换失败，通常表示已经在这条线了
            if not has_next:
                break

            # 等待场景切换完成
            wait_for_switch(context)

        logger.error("分线 11 至 60 线均无法进入暴打陈敏！")
        return False


def ensure_chen_entry(context: Context, timeout: int = 120) -> bool:
    """确保到达暴打陈敏的入口"""
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
    teleport_or_navigate(context, "游星岛", "异次元惩戒", "导航", NAVIGATE_DATA)

    # 循环检测是否到达暴打陈敏的入口
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        if check_is_entry(context):
            logger.info(f"检测到已经到达暴打陈敏的入口！")
            return True
        time.sleep(2)
    logger.error(f"超 {timeout} 秒未到达暴打陈敏的入口！")
    return False


def check_is_entry(context: Context) -> bool:
    """
    检测当前是否到暴打陈敏的入口处
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
        logger.info(f"检测到已经到达暴打陈敏的入口！")
        return True
    else:
        return False


def check_can_beat_chen(context: Context) -> bool:
    """
    检测当前是否已经进入暴打陈敏游戏
    """
    img = context.tasker.controller.post_screencap().wait().get()
    try:
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "异次元惩戒",
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
