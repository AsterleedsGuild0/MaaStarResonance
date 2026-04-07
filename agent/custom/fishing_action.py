import re
import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail, Rect
from maa.custom_action import CustomAction

from agent.attach.fishing_attach import get_restart_for_except, get_max_restart_count, get_fish_equipment, \
    get_fish_navigation
from agent.constant.fish import FISH_LIST
from agent.constant.map_point import NAVIGATE_DATA
from agent.custom.app_manage_action import restart_and_login_xhgm, wait_for_switch
from agent.custom.general.ad_close import close_ad
from agent.custom.general.general import default_ensure_main_page
from agent.custom.general.world_line_switcher import switch_line
from agent.custom.teleport_action import teleport_or_navigate
from agent.logger import logger
from agent.utils.fuzzy_utils import get_best_match_single
from agent.utils.other_utils import print_center_block
from agent.utils.param_utils import CustomActionParam
from agent.utils.time_utlls import format_seconds_to_hms


# 自动钓鱼任务
@AgentServer.custom_action("AutoFishing")
class AutoFishingAction(CustomAction):

    def __init__(self):
        super().__init__()
        # 初始变量
        self.fishing_start_time = None
        self.fishing_count = None
        self.success_fishing_count = None
        self.except_count = None
        self.ssr_fish_count = None
        self.sr_fish_count = None
        self.r_fish_count = None
        self.used_rod_count = None
        self.used_bait_count = None
        self.restart_count = None

        # 收竿触控通道常量
        self.REEL_IN_CONTACT = 0
        # 方向触控通道常量
        self.BOWING_CONTACT = 1
        # 鱼鱼稀有度列表
        self.FISH_RARITY_LIST = ["常见", "珍稀", "神话"]
        # 鱼鱼名称列表
        self.FISH_NAME_LIST = FISH_LIST

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        """
        超究极无敌变异进化全自动钓鱼：
        1. 可在钓鱼点上 或者 钓鱼界面 开始本任务，无需关心省电模式
        2. 已有鱼竿/鱼饵，会自动使用第一个，如果用完了会自动执行购买，鱼竿只买1个，鱼饵买200个
        3. 自动无限钓鱼不会停止，除非遇到意外情况
        4. 等待鱼鱼咬钩最长等待30秒

        Args:
            context: 控制器上下文
            argv: 运行参数
                - max_success_fishing_count: 需要的最大成功钓鱼数量，默认设置0为无限钓鱼

        Returns:
            钓鱼结果：True / False
        """

        logger.warning(f"!!! 即将开始钓鱼，建议根据文档选择合适的钓鱼点 !!!")

        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        max_success_fishing_count = int(params.data["max_success_fishing_count"]) if params.data["max_success_fishing_count"] else 0
        # 获取是否重启游戏参数
        restart_for_except = get_restart_for_except(context)
        # 获取最大重启游戏次数限制参数
        max_restart_count = get_max_restart_count(context)
        # 获取自动钓鱼去的导航位置
        fish_navigation = get_fish_navigation(context)
        if fish_navigation == "不导航":
            logger.info(f"本次自动钓鱼不需要导航，即原地钓鱼")
        else:
            teleport_or_navigate(context, None, fish_navigation, "导航", NAVIGATE_DATA)  # TODO 钓鱼点位置未录入
            # 确保到达钓鱼点入口
            has_entry = self.ensure_fish_entry(context)
            if not has_entry:
                return False
        # 打印参数信息
        logger.info(f"本次任务设置的最大钓到的鱼鱼数量: {max_success_fishing_count if max_success_fishing_count != 0 else '无限'}")
        logger.info(f"如遇到不可恢复异常，是否重启游戏: {'是' if restart_for_except else '否'}")
        logger.info(f"最大重启游戏次数限制: {max_restart_count}")
        
        # 起始钓鱼时间
        self.fishing_start_time = time.time()
        # 累计钓鱼次数
        self.fishing_count = 0
        # 成功钓鱼次数
        self.success_fishing_count = 0
        # 出现意外次数
        self.except_count = 0
        # 神话鱼
        self.ssr_fish_count = 0
        # 珍稀鱼
        self.sr_fish_count = 0
        # 常见鱼
        self.r_fish_count = 0
        # 消耗的鱼竿数量
        self.used_rod_count = 0
        # 消耗的鱼饵数量
        self.used_bait_count = 0
        # 重启游戏次数
        self.restart_count = 0

        # 开始钓鱼循环
        while self.check_running(context):
            # 检查是否已经钓到足够数量的鱼鱼了
            if max_success_fishing_count != 0 and max_success_fishing_count <= self.success_fishing_count:
                logger.info(f"[任务结束] 已成功钓到了您所配置的{self.success_fishing_count}条鱼鱼，自动钓鱼结束！")
                return True
            
            self.fishing_count += 1
            # 打印当前钓鱼统计信息
            delta_time = time.time() - self.fishing_start_time
            success_rate = (self.success_fishing_count / max(1, self.fishing_count - 1 - self.except_count) * 100) if self.fishing_count > 1 else 0.0
            exception_rate = (self.except_count / (self.fishing_count - 1) * 100) if self.fishing_count > 1 else 0.0
            avg_fish_per_rod = self.success_fishing_count / (self.used_rod_count + 1)
            print_center_block([
                f"累计进行 {self.fishing_count - 1} 次自动钓鱼 / 耗时 {format_seconds_to_hms(delta_time)}",
                f"成功钓上 {self.success_fishing_count} 只 => 神话{self.ssr_fish_count}只 / 珍稀{self.sr_fish_count}只 / 常见{self.r_fish_count}只",
                f"每条鱼鱼平均耗时 => {round(delta_time / max(1, self.success_fishing_count), 1)} 秒",
                f"消耗配件 => {self.used_rod_count}个鱼竿 / {self.used_bait_count}个鱼饵",
                f"每个鱼竿平均可钓 => {round(avg_fish_per_rod, 1)} 条鱼",
                f"钓鱼成功率 => {round(success_rate, 1)}% / 可恢复异常率：{round(exception_rate, 1)}%"
            ])
            
            # 1.1 直接点击一下指定位置 | 可以直接解决月卡和省电模式问题
            context.tasker.controller.post_click(640, 10).wait()
            time.sleep(1)

            # 2. 环境检查
            env_check_result = self.env_check(context, restart_for_except, max_restart_count)
            if env_check_result == -1:
                logger.error("[任务结束] 自动钓鱼环境检查出现无法重试错误，结束任务")
                return False
            elif env_check_result > 0:
                # 等待指定时间后继续下一次循环
                time.sleep(env_check_result)
                continue
            else:
                # 环境检查通过，等待1秒继续钓鱼流程
                time.sleep(1)

            # 3.1 检测配件：鱼竿
            self.ensure_equipment(
                context,
                "鱼竿",
                add_task="检测是否需要添加鱼竿",
                add_action="点击添加鱼竿",
                buy_task="检测是否需要购买鱼竿",
                buy_action_prefix=[
                    "点击前往购买鱼竿页面"
                ],
                buy_action_suffix=[
                    "点击钓鱼配件购买按钮"
                ],
                use_action="点击使用鱼竿"
            )

            # 3.2 检测配件：鱼饵
            self.ensure_equipment(
                context,
                "鱼饵",
                add_task="检测是否需要添加鱼饵",
                add_action="点击添加鱼饵",
                buy_task="检测是否需要购买鱼饵",
                buy_action_prefix=[
                    "点击前往购买鱼饵页面"
                ],
                buy_action_suffix=[
                    "点击钓鱼配件最大数量按钮",
                    "点击钓鱼配件购买按钮",
                    "点击确认购买按钮"
                ],
                use_action="点击使用鱼饵"
            )
            
            # 4. 开始抛竿
            logger.info("[任务准备] 开始抛竿，等待鱼鱼咬钩...")
            context.run_action("点击抛竿按钮")
            time.sleep(1)

            # 5. 检测鱼鱼是否咬钩 | 检测30秒，检测时间长，如果有中断命令就直接结束
            need_next = True  # 是否需要进行下一步 | 不需要就是被手动终止任务了
            wait_for_fish_times = 0
            while wait_for_fish_times < 60:
                if not self.check_running(context):
                    need_next = False
                    break
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                is_hooked: RecognitionDetail | None = context.run_recognition("检测鱼鱼是否咬钩", img)
                if is_hooked and is_hooked.hit:
                    del is_hooked, img
                    logger.info("[执行钓鱼] 鱼鱼咬钩了！")
                    self.click_reel(context)
                    break
                time.sleep(0.4)
                wait_for_fish_times += 1
            # 超时还没检测到鱼鱼咬钩 | 重新开始检测环境
            if wait_for_fish_times >= 60:
                logger.info("[执行钓鱼] 超过30秒未检测到鱼鱼咬钩，将重新开始环境检测")
                continue
            # 30秒检测内如果没有下一次了，说明钓鱼被强制结束了
            if not need_next:
                break

            # 6. 开始收线循环
            need_next = self.reel_loop(context)
            # 没有下一次了，说明钓鱼被强制结束了
            if not need_next:
                break
            time.sleep(3)

            # 7.1 本次钓鱼完成，检测并点击继续钓鱼按钮进行第二次钓鱼
            img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
            is_continue_fishing: RecognitionDetail | None = context.run_recognition("检测继续钓鱼", img)
            if is_continue_fishing and is_continue_fishing.hit:
                self.success_fishing_count += 1
                # 检查钓鱼结果
                self.check_fishing_result(context, img)
                time.sleep(1.5)
                # 点击继续钓鱼按钮
                context.run_action("点击继续钓鱼按钮")
            else:
                logger.info(f"[钓鱼结果] 鱼鱼跑掉了...")
            del is_continue_fishing, img
            time.sleep(1)

        logger.warning("[任务结束] 自动钓鱼已结束！")
        return True

    @staticmethod
    def ensure_fish_entry(context: Context, timeout: int = 120) -> bool:
        """确保导航到达钓鱼点的入口"""
        start_time = time.time()
        elapsed_time = 0
        # 循环检测是否到达不稳定空间的入口
        while elapsed_time <= timeout and not context.tasker.stopping:
            elapsed_time = time.time() - start_time
            img = context.tasker.controller.post_screencap().wait().get()
            fishing_result: RecognitionDetail | None = context.run_recognition("检测进入钓鱼按钮", img)
            if fishing_result and fishing_result.hit:
                del fishing_result, img
                logger.info(f"检测到已经到达钓鱼点入口！")
                return True
            del fishing_result, img
            time.sleep(2)
        logger.error("超 120 秒未到达钓鱼点入口！")
        return False
    
    def env_check(
        self,
        context: Context,
        restart_for_except: bool = True,
        max_restart_count: int = 5
    ) -> int:
        """
        环境检查

        Args:
            context: 控制器上下文
            restart_for_except: 如遇到不可恢复异常，是否重启游戏，默认True重启
            max_restart_count: 最大重启游戏次数限制，默认5次

        Returns:
            等待下次钓鱼的时间（秒），0表示环境检查通过可以钓鱼，-1表示出现不可恢复错误需要结束任务
        """
        # 1. 检测继续钓鱼按钮 | 每次正常循环的钓鱼都会执行，优先检测
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        is_continue_fishing: RecognitionDetail | None = context.run_recognition("检测继续钓鱼", img)
        if is_continue_fishing and is_continue_fishing.hit:
            logger.info("[任务准备] 检测到继续钓鱼按钮，将点击按钮，环境检查通过")
            time.sleep(1)
            context.run_action("点击继续钓鱼按钮")
            del is_continue_fishing, img
            return 0

        # 2. 检测进入钓鱼按钮 | 仅有首次启动和异常情况才可能触发
        has_fishing = False
        fishing_result: RecognitionDetail | None = context.run_recognition("检测进入钓鱼按钮", img)
        if fishing_result and fishing_result.hit:
            logger.info("[任务准备] 检测到钓鱼按钮，等待5秒后进入钓鱼台...")
            context.run_action("点击进入钓鱼按钮")
            # 走5秒，有些地方会卡住比较慢
            time.sleep(5)
            # 识别出了：走进钓鱼台，并重新截图 | 仅有首次启动和异常情况才可能触发
            img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
            has_fishing = True
        elif fishing_result:
            # 部分钓鱼地点背景影响严重，以防万一再次判断
            target_chars = {"钓", "鱼"}
            texts = {item.text for item in fishing_result.all_results}  # type: ignore
            if target_chars.issubset(texts):
                logger.info("[任务准备] 疑似钓鱼按钮，等待5秒尝试进入钓鱼台...")
                context.run_action("点击进入钓鱼按钮")
                # 走5秒，有些地方会卡住比较慢
                time.sleep(5)
                # 疑似识别出了：走进钓鱼台，并重新截图 | 仅有首次启动和异常情况才可能触发
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                has_fishing = True
            else:
                logger.info('[任务准备] 没有检测到钓鱼按钮，可能已经在钓鱼中，将直接检测抛竿按钮')
        else:
            logger.error('[任务结束] 识别节点不存在，逻辑不可达，请GitHub提交Issue反馈')
            return -1

        # 3. 检测抛竿按钮 | 仅有首次启动就在抛竿界面才可能触发
        reeling_result: RecognitionDetail | None = context.run_recognition("检测抛竿按钮", img)
        if reeling_result and reeling_result.hit:
            logger.info("[任务准备] 检测到抛竿按钮，环境检查通过")
            del fishing_result, reeling_result, img
            return 0
        
        # 4. 钓鱼台满人
        if has_fishing and reeling_result and not reeling_result.hit:
            logger.warning('[任务准备] 进入钓鱼台后未检测到抛竿按钮，可能钓鱼台已满，尝试自动切换分线！')
            time.sleep(2)
            default_ensure_main_page(context)
            time.sleep(2)
            switch_line(context, ["40", "41", "42", "43", "44", "45", "46", "47", "48", "49"])
            return 1
        
        # 5. 检查其他意外情况
        self.except_count += 1  # type: ignore
        logger.warning('[任务准备] 出现异常：可能是遇到掉线/切线情况，尝试自动处理...')
        disconnect_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {"expected": "确认", "roi": [767, 517, 59, 27]}
            },
        )
        if disconnect_result and disconnect_result.hit:
            # 6.1 有确认按钮：很有可能是掉线了
            logger.info("[任务准备] 有确认按钮，可能是掉线重连按钮，正在点击重连，等待30秒后重试...")
            context.tasker.controller.post_click(797, 532).wait()
            time.sleep(2)

            # 6.2 检测是否有再次确认按钮
            disconnect_result: RecognitionDetail | None = context.run_recognition(
                "通用文字识别",
                img,
                pipeline_override={
                    "通用文字识别": {"expected": "确认", "roi": [614, 518, 50, 28]}
                },
            )
            if disconnect_result and disconnect_result.hit:
                # 6.3 大概率是服务器炸了，要回到主界面了
                logger.info("[任务准备] 检测到再次确认按钮，继续点击确认，等待30秒后重试...")
                context.tasker.controller.post_click(637, 529).wait()
        else:
            # 7.1 检测一下是否在登录页面
            logger.info("[任务准备] 检测不到确认按钮，可能是回到主界面...")
            login_result: RecognitionDetail | None = context.run_recognition("点击连接开始", img)
            if login_result and login_result.hit:
                logger.info("[任务准备] 检测到主界面连接开始按钮，准备登录游戏...")
                # 识别到开始界面
                context.tasker.controller.post_click(639, 602).wait()
                time.sleep(8)
                # 识别出了：进入选角色界面，并重新截图
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
            del login_result

            # 7.2 检测一下是否在选择角色进入游戏页面
            entry_result: RecognitionDetail | None = context.run_recognition("点击进入游戏", img)
            if entry_result and entry_result.hit:
                # 识别到进入游戏
                logger.info("[任务准备] 登录结束，点击进入游戏，等待90秒...")
                context.tasker.controller.post_click(1103, 632).wait()
                del entry_result
                # 等待场景切换
                wait_for_switch(context)
                # 处理广告
                close_ad(context)
                return 1
            del entry_result

            # 7.3 检测是否登录失效
            no_login_result: RecognitionDetail | None = context.run_recognition("检测是否需要登录", img)
            if no_login_result and no_login_result.hit:
                del no_login_result, img
                logger.info("检测到星痕共鸣登录信息失效，需要登录账号！")
                return -1

            # 7.4 若开启不可恢复异常重启选项，则直接重启游戏
            if restart_for_except and self.restart_count < max_restart_count:  # type: ignore
                logger.info("[任务准备] 检测不到进入游戏按钮，准备直接重启游戏...")
                # 等待游戏重启完成
                restart_result = restart_and_login_xhgm(context)
                # 处理广告
                close_ad(context)
                self.restart_count += 1  # type: ignore
                if restart_result:
                    return 1
                else:
                    return -1
            logger.info("[任务准备] 检测不到进入游戏按钮，等待30秒...")
        del disconnect_result, fishing_result, reeling_result, img
        # 等待30秒后直接进入下个循环
        return 30
    
    def ensure_equipment(
        self,
        context: Context,
        type_str: str,
        add_task: str,
        add_action: str,
        buy_task: str,
        buy_action_prefix: list[str],
        buy_action_suffix: list[str],
        use_action: str
    ) -> None:
        """
        检查钓鱼配件

        Args:
            context: 控制器上下文
            type_str: 配件类型字符串（鱼竿 / 鱼饵）
            add_task: 检测是否需要添加配件任务名称
            add_action: 点击添加配件动作名称
            buy_task: 检测是否需要购买配件任务名称
            buy_action_prefix: 购买配件前的动作名称列表
            buy_action_suffix: 购买配件后的动作名称列表
            use_action: 点击使用配件动作名称
            
        Returns:
            None
        """
        # 1. 检测添加按钮
        img = context.tasker.controller.post_screencap().wait().get()
        det = context.run_recognition(add_task, img)
        if not det or not det.hit:
            return
        logger.info(f"[任务准备] 检测到需要添加{type_str}")

        # 2. 点击添加按钮
        context.run_action(add_action)
        time.sleep(2)

        # 3. 检测是否需要购买，如果需要就购买
        img = context.tasker.controller.post_screencap().wait().get()
        need_buy = context.run_recognition(buy_task, img)
        if need_buy and need_buy.hit:
            logger.info(f"[任务准备] 检测到{type_str}不足，需要购买")
            if type_str == "鱼竿":
                self.used_rod_count += 1  # type: ignore
                logger.info(f"[任务准备] 当前将购买1个{type_str}")
            else:
                logger.info(f"[任务准备] 当前将购买200个{type_str}")
            # 3.1 执行一连串购买前步骤
            for act in buy_action_prefix:
                context.run_action(act)
                time.sleep(2)

            # 3.2 执行检测购买目标
            fish_equipment = get_fish_equipment(context, type_str)
            img = context.tasker.controller.post_screencap().wait().get()
            ocr_result: RecognitionDetail | None = context.run_recognition(
                "通用文字识别",
                img,
                pipeline_override={
                    "通用文字识别": {"expected": fish_equipment, "roi": [134, 153, 1022, 297]}
                },
            )
            if not ocr_result or not ocr_result.hit:
                logger.error(f"[任务准备] 购买{fish_equipment}失败，未识别到购买目标")
                context.run_action("ESC")
                time.sleep(2)
                return

            # 3.3 获得最好结果坐标
            item = ocr_result.best_result
            rect = Rect(*item.box)  # type: ignore
            logger.info(f"识别到配件目标： {rect}, {item.text}")  # type: ignore
            point_x = int(rect.x + rect.w / 2)
            point_y = int(rect.y + rect.h / 2)

            # 3.4 点击购买目标
            context.tasker.controller.post_click(point_x, point_y).wait()
            time.sleep(2)

            # 3.5 执行一连串购买后步骤
            for act in buy_action_suffix:
                context.run_action(act)
                time.sleep(2)
            logger.info(f"[任务准备] {type_str}购买完成，将退回钓鱼界面")

            # 3.6 购买完回到钓鱼界面
            context.run_action("ESC")
            time.sleep(2)

            # 3.7 再次检测和点击添加按钮
            img = context.tasker.controller.post_screencap().wait().get()
            context.run_recognition(add_task, img)
            context.run_action(add_action)
            time.sleep(2)

        # 4. 使用配件
        logger.info(f"[任务准备] 点击使用已有的{type_str}")
        context.run_action(use_action)
        time.sleep(2)

    def reel_loop(self, context: Context) -> bool:
        """
        钓鱼循环逻辑：
        0. 基础设置：
            - 检测间隔${loop_interval}秒
            - 最长收线时间${max_reel_time}秒
            - 首次按下收线键延迟${check_delay}秒再检测是否结束钓鱼
        1. 收线键的两种状态：
            - 长按模式 -> 一直按住收线键
            - 节奏模式 -> 点击一次收线键后等待${reel_cooldown}秒，再次点击
        2. 初始状态 -> 收线键：长按模式；方向键：不动
        3. 识别到箭头：
            - 识别冷却期${arrow_cooldown}未到 -> 不改变方向键
            - 同方向 -> 不改变方向键
            - 不同方向但前一次方向键已松开 -> 改变方向键长按
            - 不同方向但前一次方向键未松开 -> 松开方向键
        4. 张力上限检测：
            - 没超过${max_tension}% -> 收线键进入长按模式
            - 超过${max_tension}% -> 收线键进入节奏模式

        Args:
            context: 控制器上下文

        Returns:
            是否继续下一次钓鱼：True / False
        """

        # ========== 可配置参数 ==========
        loop_interval = 0.3  # 循环检测间隔
        max_reel_time = 150  # 最长收线时间，防止意外卡死
        check_delay = 2 # 首次按下收线键的结束检测延迟
        reel_cooldown = 0.2  # 节奏模式下每次点击收线后的冷却时间  | 向上取整至循环检测间隔的倍数
        arrow_cooldown = 0.2  # 箭头方向检测的冷却时间 | 向上取整至循环检测间隔的倍数
        max_tension = 85  # 最大张力限制
        max_no_tension_count = 8  # 连续多少次未检测到张力后，判定不在收线状态

        # ========== 状态变量 ==========
        first_start_time = time.time()  # 循环开始时间
        is_reel_pressed = False  # 当前收线键状态
        is_rhythm_mode = False  # False: 长按模式 / True: 节奏模式
        init_time = first_start_time  # 首次按下收线键的时间
        last_reel_click_time = 0.0  # 上次点击收线键的时间
        last_arrow_detect_time = 0.0  # 上次确认箭头的时间戳
        last_arrow_direction = None  # 上次箭头方向
        is_bow_pressed = False  # 当前方向键状态
        no_tension_count = 0  # 连续未检测到张力的次数

        while self.check_running(context):
            loop_start_perf = time.perf_counter()
            now = time.time()

            # ===== 最大收线时间保护 =====
            if now - first_start_time >= max_reel_time:
                logger.warning(f"[执行钓鱼] 收线时间超过{max_reel_time}秒，强制结束本次钓鱼")
                time.sleep(1)  # 缓冲1秒
                if is_reel_pressed:
                    self.stop_reel_in(context)
                if is_bow_pressed:
                    self.stop_bow(context)
                # 按ESC回到主界面
                default_ensure_main_page(context)
                return True

            # ===== 获取截图 =====
            img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()

            # ===== 张力检测 / 收线状态判断 =====
            tension_hit: RecognitionDetail | None = context.run_recognition("检测张力百分比", img)
            tension_num = None
            if tension_hit and tension_hit.hit and tension_hit.best_result:
                tension_raw_text = tension_hit.best_result.text  # type: ignore
                tension_match = re.search(r"\d+", tension_raw_text)
                if tension_match:
                    tension_num = int(tension_match.group())
                    no_tension_count = 0

                    target_rhythm_mode = tension_num >= max_tension
                    if target_rhythm_mode != is_rhythm_mode:
                        is_rhythm_mode = target_rhythm_mode
                        if is_rhythm_mode:
                            # 从长按切到节奏模式，先松开长按
                            if is_reel_pressed and self.stop_reel_in(context):
                                is_reel_pressed = False
                            last_reel_click_time = 0.0
                            logger.info(f"[执行钓鱼] 当前张力 {tension_num}% 超过{max_tension}% -> 收线键切换为 节奏模式")
                        else:
                            logger.info(f"[执行钓鱼] 当前张力 {tension_num}% 低于{max_tension}% -> 收线键切换为 长按模式")

            # 首次开始收线后的保护时间内，不做“丢失张力即退出”的判断
            if now - init_time > check_delay and tension_num is None:
                no_tension_count += 1
                if no_tension_count >= max_no_tension_count:
                    self.used_bait_count += 1  # type: ignore
                    logger.info(f"[执行钓鱼] 连续 {max_no_tension_count} 次未检测到张力，等待一会检测'继续钓鱼'按钮...")
                    del img
                    if is_reel_pressed:
                        self.stop_reel_in(context)
                    if is_bow_pressed:
                        self.stop_bow(context)
                    return True

            # ===== 箭头检测 =====
            confirmed_arrow = None
            if now - last_arrow_detect_time >= arrow_cooldown:
                confirmed_arrow = self.get_bow_direction(context, img)

            # 检测完就删除截图
            del img

            # ===== 根据箭头结果处理方向键状态 =====
            if confirmed_arrow is not None:
                last_arrow_detect_time = now
                if last_arrow_direction is None:
                    # 首次识别到箭头，按住方向键
                    if self.start_bow(context, confirmed_arrow):
                        is_bow_pressed = True
                        last_arrow_direction = confirmed_arrow
                elif confirmed_arrow == last_arrow_direction:
                    # 同方向：不改变方向键
                    pass
                elif is_bow_pressed:
                    # 不同方向且当前还按着：先松开
                    logger.info("[执行钓鱼] 方向变化且上次方向键未松开 -> 先松开方向键")
                    if self.stop_bow(context):
                        is_bow_pressed = False
                else:
                    # 不同方向且当前已松开：切换并按住新方向
                    logger.info(f"[执行钓鱼] 方向变化 -> 切换并按住新方向: {confirmed_arrow}")
                    if self.start_bow(context, confirmed_arrow):
                        is_bow_pressed = True
                        last_arrow_direction = confirmed_arrow

            # ===== 根据张力模式控制收线键 =====
            if not is_rhythm_mode:
                # 长按模式：持续按住收线键
                if not is_reel_pressed and self.start_reel_in(context):
                    is_reel_pressed = True
            else:
                # 点击节奏模式：点击一次后等待冷却
                current_time = time.time()
                if current_time - last_reel_click_time >= reel_cooldown:
                    if self.click_reel(context):
                        last_reel_click_time = time.time()

            # ===== 控制循环频率 =====
            elapsed = time.perf_counter() - loop_start_perf
            time.sleep(max(0.0, loop_interval - elapsed))

        return False

    @staticmethod
    def get_bow_direction(context: Context, img: numpy.ndarray, score_threshold: float = 0.6,
                          min_score_diff: float = 0.05) -> str | None:
        """
        获取箭头方向（'左' / '右' / None）带分数阈值：
        1. 左右箭头分数低于 score_threshold 视为无效
        2. 分数差小于 min_score_diff，则视为无效（避免接近分数误判）
        3. 返回方向字符串或 None

        Args:
            context: 控制器上下文
            img: 当前截图
            score_threshold: 分数阈值
            min_score_diff: 分数差阈值

        Returns:
            箭头方向字符串或 None
        """
        bow_left_task: RecognitionDetail | None = context.run_recognition("检查向左箭头", img)
        bow_right_task: RecognitionDetail | None = context.run_recognition("检查向右箭头", img)

        if not bow_left_task and not bow_right_task:
            return None

        bow_left_score = bow_left_task.best_result.score if (bow_left_task and bow_left_task.best_result) else 0.0  # type: ignore
        bow_right_score = bow_right_task.best_result.score if (bow_right_task and bow_right_task.best_result) else 0.0  # type: ignore

        # logger.debug(f"[箭头识别] 左分数: {bow_left_score:.3f}, 右分数: {bow_right_score:.3f}")

        # 阈值过滤
        if bow_left_score < score_threshold and bow_right_score < score_threshold:
            del bow_left_score, bow_right_score, bow_left_task, bow_right_task
            return None

        # 差异过滤
        if abs(bow_left_score - bow_right_score) < min_score_diff:
            del bow_left_score, bow_right_score, bow_left_task, bow_right_task
            return None

        bow_direction = None
        if bow_left_score >= score_threshold and bow_left_score > bow_right_score:
            bow_direction = "左"
        elif bow_right_score >= score_threshold and bow_right_score > bow_left_score:
            bow_direction = "右"
        del bow_left_score, bow_right_score, bow_left_task, bow_right_task
        return bow_direction

    def click_reel(self, context: Context) -> bool:
        """
        点击一次收线键
        """
        result = context.tasker.controller.post_click(1160, 585, self.REEL_IN_CONTACT, 1).wait()
        return result.succeeded

    def start_reel_in(self, context: Context) -> bool:
        """
        开始收线动作
        """
        result = context.tasker.controller.post_touch_down(1160, 585, self.REEL_IN_CONTACT, 1).wait()
        return result.succeeded

    def stop_reel_in(self, context: Context) -> bool:
        """
        停止收线动作
        """
        result = context.tasker.controller.post_touch_up(self.REEL_IN_CONTACT).wait()
        return result.succeeded

    def start_bow(self, context: Context, direction: str) -> bool:
        """
        开始箭头转向动作
        """
        if direction == "左":
            x = 150
        elif direction == "右":
            x = 320
        else:
            return False
        y = 530
        result = context.tasker.controller.post_touch_down(x, y, self.BOWING_CONTACT, 1).wait()
        return result.succeeded

    def stop_bow(self, context: Context) -> bool:
        """
        停止箭头转向动作
        """
        result = context.tasker.controller.post_touch_up(self.BOWING_CONTACT).wait()
        return result.succeeded

    @staticmethod
    def check_running(context: Context) -> bool:
        """
        检查任务是否正在被停止 | 钓鱼有三个循环，理论上最多触发5次停止事件就会停下了
        """
        if context.tasker.stopping:
            logger.info("[任务结束] 监听到自动钓鱼任务被结束，将结束循环，请耐心等待一小会")
            return False
        return True

    def check_fishing_result(self, context: Context, img: numpy.ndarray) -> None:
        """
        检查该次成功的钓鱼结果

        Args:
            context: 控制器上下文
            img: 钓鱼结果截图
        
        Returns:
            None
        """
        # 稀有度
        rarity_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {"expected": "[\\S\\s]*", "roi": [734, 531, 91, 23]}
            }
        )
        rare = "未知"
        if rarity_result and rarity_result.hit:
            fish_rarity = rarity_result.best_result.text  # type: ignore
            rare = get_best_match_single(fish_rarity, self.FISH_RARITY_LIST)
            # 计数
            if rare == "神话":
                self.ssr_fish_count += 1  # type: ignore
            elif rare == "珍稀":
                self.sr_fish_count += 1  # type: ignore
            elif rare == "常见":
                self.r_fish_count += 1  # type: ignore
        del rarity_result

        # 鱼名
        fish_name_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {"expected": "[\\S\\s]*", "roi": [711, 488, 264, 36]}
            }
        )
        fish = "未知"
        if fish_name_result and fish_name_result.hit:
            fish_name = fish_name_result.best_result.text  # type: ignore
            fish = get_best_match_single(fish_name, self.FISH_NAME_LIST)
        del fish_name_result

        logger.info(f"[钓鱼结果] 钓上了 [{fish}] 稀有度：[{rare}]")
