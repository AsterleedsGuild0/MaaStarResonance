import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction, RecognitionDetail

from agent.attach.battle_attach import get_unstable_space_type, get_use_auto_attack
from agent.attach.common_attach import get_area_change_timeout
from agent.custom.general.general import ensure_main_page
from agent.custom.general.move_battle import auto_attack, check_alive
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.logger import logger
from agent.utils.param_utils import CustomActionParam


@AgentServer.custom_action("UnstableSpacePoint")
class UnstableSpacePointAction(CustomAction):

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
    
        # 队伍类型
        team_type = get_unstable_space_type(context)
        if team_type == "无":
            logger.error("请先选择队伍类型！")
            return False
        
        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        max_game_count = int(params.data["max_game_count"]) if params.data["max_game_count"] else 0
        logger.info(f"本次任务设置的最大不稳定空间战斗次数: {max_game_count if max_game_count != 0 else '无限'}")
        
        # 自动战斗是否开启
        use_auto_attack = get_use_auto_attack(context)

        # 是否是队长：队长要去NPC那边开本，队员不用干活
        is_leader = team_type in ["单人匹配游戏", "组队匹配游戏（队长）"]

        while not context.tasker.stopping:
            logger.info(f"=== 已成功挑战不稳定空间 {self.game_count} 次 ===")
            # 检查是否已经游戏足够次数了
            if max_game_count != 0 and max_game_count <= self.game_count:
                logger.info(f"已成功挑战了您所配置的{self.game_count}次不稳定空间，任务结束！")
                return True

            # 主战斗循环
            has_next = mian_unstable_space(context, is_leader, use_auto_attack)
            if not has_next:
                break
            
            self.game_count += 1
    
        return False


# 主战斗循环
def mian_unstable_space(context: Context, is_leader: bool, use_auto_attack: bool):
    if is_leader:
        # 循环检测进入不稳定空间的按钮
        has_entry = ensure_space_entry(context)
        if not has_entry:
            return False

    # 确保进入不稳定空间战斗
    ensure_into_battle(context, is_leader)
    logger.info("已进入副本，等待副本完成...")

    if use_auto_attack:
        # 开始自动战斗
        logger.info("打开自动战斗...")
        auto_attack(context, 1)

    # 开始检测副本状态和角色存活状态
    while not context.tasker.stopping:
        # 检测是否还在副本内
        img = context.tasker.controller.post_screencap().wait().get()

        # 检测下一步按钮
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "下一步",
                    "roi": [598, 626, 69, 33],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            context.tasker.controller.post_click(632, 644).wait()
            time.sleep(0.5)

        # 检测离开按钮并离开副本
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "离开",
                    "roi": [1139, 661, 50, 29],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            context.tasker.controller.post_click(1165, 678).wait()
            time.sleep(0.5)
            logger.info("战斗完成，等待返回主界面...")
            wait_for_switch_or_next(context)
            return True

        # 检测是否存活并复活
        check_alive(context)

        time.sleep(2)

    logger.error("不稳定空间战斗被手动终止或者出现异常！")
    return False


def ensure_space_entry(context: Context, timeout: int = 120) -> bool:
    """确保到达不稳定空间的入口"""
    start_time = time.time()
    elapsed_time = 0
    # 循环检测是否到达不稳定空间的入口
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img = context.tasker.controller.post_screencap().wait().get()
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "不稳",
                    "roi": [878, 333, 39, 24],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            del ocr_result, img
            logger.info(f"检测到已经到达不稳定空间的入口！")
            return True
        del ocr_result, img
        time.sleep(2)
    logger.error("超 120 秒未到达不稳定空间的入口！")
    return False



def ensure_into_battle(context: Context, is_leader: bool, timeout: int = 0) -> bool:
    """
    确保进入不稳定空间战斗
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
        img = context.tasker.controller.post_screencap().wait().get()
        is_into_instance = context.run_recognition("图片识别副本退出按钮", img)
        if is_into_instance and is_into_instance.hit:
            return True

        if is_leader:
            # 检测到不稳定入口按钮就点击
            ocr_result: RecognitionDetail | None = context.run_recognition(
                "通用文字识别",
                img,
                pipeline_override={
                    "通用文字识别": {
                        "expected": "不稳",
                        "roi": [878, 333, 39, 24],
                    }
                },
            )
            if ocr_result and ocr_result.hit:
                context.tasker.controller.post_click(916, 345).wait()
                time.sleep(2)

            # 检测到单双人按钮就点击
            ocr_result: RecognitionDetail | None = context.run_recognition(
                "通用文字识别",
                img,
                pipeline_override={
                    "通用文字识别": {
                        "expected": "双人",
                        "roi": [963, 582, 37, 20],
                    }
                },
            )
            if ocr_result and ocr_result.hit:
                context.tasker.controller.post_click(915, 591).wait()
                time.sleep(1)

                # 检测到进入副本按钮就点击
                ocr_result: RecognitionDetail | None = context.run_recognition(
                    "通用文字识别",
                    img,
                    pipeline_override={
                        "通用文字识别": {
                            "expected": "进入副本",
                            "roi": [1129, 645, 87, 23],
                        }
                    },
                )
                if ocr_result and ocr_result.hit:
                    context.tasker.controller.post_click(1170, 657).wait()
                    time.sleep(1)

        else:
            # 检测是否有确认按钮并点击
            ocr_result: RecognitionDetail | None = context.run_recognition(
                "通用文字识别",
                img,
                pipeline_override={
                    "通用文字识别": {
                        "expected": "确认",
                        "roi": [1130, 649, 51, 30],
                    }
                },
            )
            if ocr_result and ocr_result.hit:
                context.tasker.controller.post_click(1156, 664).wait()
                time.sleep(0.5)
        
        # 保底措施：检测下一步按钮就是已经结算 | 目的是可能有部分设备加载慢，跳过了战斗阶段
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "下一步",
                    "roi": [598, 626, 69, 33],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            context.tasker.controller.post_click(1156, 664).wait()
            time.sleep(0.5)
            return True

    logger.error(f"确保进入不稳定空间战斗超时或被手动停止：{timeout}")
    return False


def wait_for_switch_or_next(context: Context) -> bool:
    """等待场景切换或开始下一把"""
    area_change_timeout = get_area_change_timeout(context)
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= area_change_timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()

        area_change_result: RecognitionDetail | None = context.run_recognition("图片识别是否在主页面", img)
        if area_change_result and area_change_result.hit:
            logger.info("检测到星痕共鸣已经成功切换场景！")
            return True
        
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "确认",
                    "roi": [1130, 649, 51, 30],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            logger.info("检测到不稳定空间已开始下一把")
            return True

        time.sleep(2)
    # 超时未进入游戏主页面
    logger.error(f"星痕共鸣切换场景超过{area_change_timeout}秒限制 或者 被手动停止，请检查游戏状态！")
    return False
