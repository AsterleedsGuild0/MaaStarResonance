import re
import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from agent.attach.chat_message_attach import get_chat_channel, get_chat_loop_interval, get_chat_loop_limit, \
    get_chat_message_content, get_chat_channel_id_list, get_chat_message_need_team, get_full_team_force_send
from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
from agent.constant.world_channel import CHANNEL_DATA
from agent.custom.general.general import default_ensure_main_page
from agent.custom.general.power_saving_mode import default_exit_power_save
from agent.logger import logger


# 循环发送聊天频道消息
@AgentServer.custom_action("SendMessageLoop")
class SendMessageLoopAction(CustomAction):

    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        # 循环周期间隔时间
        loop_interval = get_chat_loop_interval(context)
        if loop_interval and loop_interval < 30:
            logger.error("如需设置循环周期间隔，则时间必须大于30秒")
            return False
        # 发送消息次数上限
        limit = get_chat_loop_limit(context)
        return send_message_loop(context, loop_interval, limit)


# 发送聊天频道消息
@AgentServer.custom_action("SendMessage")
class SendMessageAction(CustomAction):

    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        return send_message(context)


# 发送循环消息
def send_message_loop(context: Context, loop_interval, limit, check_interval = 2) -> bool:
    """
    发送循环消息

    Args:
        context: 控制器上下文
        loop_interval: 发送消息任务循环间隔
        limit: 发送消息次数上限
        check_interval: 检查间隔，默认2秒一次
    """
    # 已发送次数
    send_count = 0
    # 距离上次发送已经等待的时间
    elapsed = loop_interval

    # 循环发送
    while not context.tasker.stopping:
        if 0 < limit <= send_count:
            break

        # 每 2 秒检测一次状态
        time.sleep(check_interval)
        elapsed += check_interval

        # 只有当累计等待时间达到或超过 loop_interval 才发送
        if elapsed >= loop_interval:
            send_message(context)
            send_count += 1
            # 把已累计时间清零（或减去一个周期，用于更精细的补偿）
            elapsed = 0
            logger.info(f"[循环消息] 已完成发送消息 {send_count} 轮")
    return True


# 发送消息
def send_message(context: Context) -> bool:
    # 退出省电模式
    default_exit_power_save(context)
    time.sleep(1)
    # 确保回到主界面
    default_ensure_main_page(context, strict=False)
    time.sleep(1)

    # 本轮成功次数
    success_count = 0

    # 0. 变量检查
    message_content_raw = get_chat_message_content(context)
    if not message_content_raw:
        logger.error("需要发送的消息内容为空，请先设置内容")
        return False
    channel_name = get_chat_channel(context)
    channel_id_list = get_chat_channel_id_list(context)
    need_team = get_chat_message_need_team(context)
    force_send = get_full_team_force_send(context)

    # 1. 获取队伍人数信息(如果需要)
    if need_team:
        current_num, total_num, team_name = get_team_info(context, force_send)
        if not total_num:
            return False
        message_content = handle_message(message_content_raw, current_num, total_num, team_name)
        time.sleep(1)
    else:
        message_content = message_content_raw

    # 2. 检测并打开聊天框
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    chat_button: RecognitionDetail | None = context.run_recognition("检测聊天按钮", img)
    if not chat_button or not chat_button.hit:
        logger.error("未检测到聊天按钮，无法发送消息")
        return False
    context.tasker.controller.post_click(490, 600).wait()

    # 3. 切换到对应频道
    wait_times = 0
    need_next = False
    channel_dict = CHANNEL_DATA.get(channel_name, {})
    x, y, w, h = channel_dict["roi"]
    channel_id_dict = channel_dict.get("channel", {})
    while wait_times <= 10 and not context.tasker.stopping:
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        world_chat: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {"expected": channel_name, "roi": [x, y, w, h]}
            },
        )
        if world_chat and world_chat.hit:
            need_next = True
            break
        wait_times += 1
        time.sleep(2)
    if not need_next:
        logger.error(f"未检测到 {channel_name} 频道，无法发送消息")
        context.run_action("ESC")
        return False
        
    # 点击对应文字的中间位置
    point_x = int(x + w / 2)
    point_y = int(y + h / 2)
    context.tasker.controller.post_click(point_x, point_y).wait()

    # 如果不是世界频道就做个假的循环
    if not channel_id_dict:
        channel_id_list = ["0"]
    # 根据世界频道分线ID列表循环处理
    for channel_id in channel_id_list:
        if context.tasker.stopping:
            context.run_action("ESC")
            return True

        # 4. 切换世界频道分线（如果需要）
        need_next = change_channel(channel_id, channel_id_dict, context, 1)
        if not need_next:
            continue
        # 5. 点击输入框
        time.sleep(2)
        context.tasker.controller.post_click(275, 680).wait()
        # 6. 输入内容
        time.sleep(2)
        context.run_action("输入聊天框内容", pipeline_override={
            "输入聊天框内容": {
                "action": {
                    "type": "InputText",
                    "param": {
                        "input_text": message_content
                    }
                }
            }
        })
        # 7. 点击确定按钮
        time.sleep(2)
        context.tasker.controller.post_click(1217, 668).wait()
        # 8. 检测并点击发送图标
        time.sleep(2)
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        send_button: RecognitionDetail | None = context.run_recognition("检测发送消息按钮", img)
        if send_button and send_button.hit:
            context.tasker.controller.post_click(807, 681).wait()
            success_count += 1
            logger.info(f"已成功向 {channel_name} 频道 {channel_id} 发送消息内容")
        else:
            logger.error(f"向 {channel_name} 频道 {channel_id} 发送消息内容失败：识别不到发送按钮")

    logger.info(f"===== 本轮发送 {channel_name} 频道消息已经成功：{success_count} / {len(channel_id_list)} ====")

    # 9. 结束并关闭
    time.sleep(2)
    default_ensure_main_page(context, strict=False)
    return True


def change_channel(channel_id: str, channel_id_dict: dict, context: Context, interval: float = 0.5) -> bool:
    """
    根据 channel_id 切换频道

    Args:
        channel_id: 频道ID
        channel_id_dict: 频道ID坐标字典
        context: 控制器上下文
        interval: 每次按键之间的间隔秒数，默认 0.5

    Returns:
        切换成功与否
    """
    # 没有频道ID字典 | 说明不是世界频道直接进行下一步
    if not channel_id_dict:
        return True
    
    # 检测切换前的频道ID
    time.sleep(2)
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    old_channel: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {"expected": "[0-9]+", "roi": [234, 22, 75, 32]}
        },
    )
    if not old_channel or not old_channel.hit:
        logger.warning("无法识别到切换前的频道ID，将跳过此次发送！")
        return False
    old_channel_id_raw = old_channel.best_result.text  # type: ignore
    old_channel_id = re.search(r"\d+", old_channel_id_raw).group()  # type: ignore
    logger.info(f"切换前的频道ID：{old_channel_id}")

    # 判断是否已经符合要求
    if old_channel_id == channel_id:
        logger.info("当前已经是所需要发送的频道了，将开始发送消息...")
        return True

    # 点击开始切换
    context.tasker.controller.post_click(275, 41).wait()
    time.sleep(2)

    # 输入
    for digit in channel_id:
        if digit not in channel_id_dict:
            continue
        x, y = channel_id_dict[digit]
        context.tasker.controller.post_click(x, y).wait()
        time.sleep(interval)

    # 识别并点击切换按钮
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    switch_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {"expected": "OK", "roi": [339, 191, 40, 35]}
        },
    )
    if not switch_result or not switch_result.hit:
        logger.warning(f"聊天世界频道: {channel_id} 识别切换频道按钮失败，将跳过此次发送！")
        return False
    context.tasker.controller.post_click(359, 208).wait()
    
    # 检测切换后的频道ID
    time.sleep(2)
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    new_channel: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {"expected": "[0-9]+", "roi": [234, 22, 75, 32]}
        },
    )
    if not new_channel or not new_channel.hit:
        logger.warning("无法识别到切换后频道ID，可能识别有误，但仍将继续完成此次发送！")
        return True
    new_channel_id_raw = new_channel.best_result.text  # type: ignore
    new_channel_id = re.search(r"\d+", new_channel_id_raw).group()  # type: ignore
    logger.info(f"切换后频道ID：{new_channel_id}")

    # 判断是否成功切换
    if str(new_channel_id) != channel_id:
        logger.warning("频道切换失败，可能是频道人数已满，将跳过此次发送！")
        return False

    logger.info(f"世界频道切换成功：{old_channel_id} -> {channel_id}，将开始发送消息...")
    return True


def get_team_info(context: Context, force_send: bool = False) -> tuple[int, int, str]:
    """
    获取队伍信息，必须是加入协会状态。

    Args:
        context: 控制器上下文。
        force_send: 队伍已满时是否还需要发送消息。

    Returns:
        tuple[int, int, str]: 一个包含三个元素的元组，
            依次为当前队伍人数、队伍总人数和队伍名称。当未能成功识别
            队伍信息，或队伍已满且 ``force_send`` 为 False 时，返回
            ``(0, 0, "")`` 表示未获取到有效的队伍信息或本次发送被跳过。
    """
    # 先按U打开协会页面
    time.sleep(2)
    context.tasker.controller.post_click_key(ANDROID_KEY_EVENT_DATA["KEYCODE_U"]).wait()

    # 识别并点击左侧协会成员列表按钮 | 这里等待5秒，因为服务器可能很卡
    time.sleep(5)
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    clan_members_button: RecognitionDetail | None = context.run_recognition("检测协会成员列表按钮", img)
    if not clan_members_button or not clan_members_button.hit:
        logger.error("未检测到协会成员列表按钮!")
        return 0, 0, ''
    context.tasker.controller.post_click(46, 185).wait()

    # 点击协会成员列表的第一个人：就是自己 | 这里等待5秒，因为服务器可能很卡
    time.sleep(5)
    context.tasker.controller.post_click(431, 216).wait()

    # 识别弹出的自己的名片中关于队伍的信息 | 这里等待5秒，因为服务器可能很卡
    time.sleep(5)
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    team_number: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {"expected": "[0-9]+ */ *[0-9]+.*", "roi": [596, 327, 162, 20]}
        },
    )
    if not team_number or not team_number.hit:
        logger.error("未检测到个人名片中的队伍信息")
        return 0, 0, ''

    # 解析并返回
    team_number_str = team_number.best_result.text  # type: ignore
    # 再次正则解析
    search = re.search(r'([0-9]+) */ *([0-9]+)(.*)', team_number_str)
    if not search:
        logger.error("未检测到个人名片中的队伍信息")
        return 0, 0, ''
    current, total, team_name = int(search.group(1).strip()), int(search.group(2).strip()), search.group(3).strip()
    logger.info(f"队伍名：{team_name} | 队伍人数：{current} / {total}")

    if not force_send and current >= total:
        logger.warning("当前队伍人数已满，将跳过此次发送消息！")
        return 0, 0, ''

    time.sleep(2)
    default_ensure_main_page(context, strict=False)
    return current, total, team_name


def handle_message(raw_msg: str, current_num: int = 0, total_num: int = 0, team_name: str = '') -> str:
    """
    处理发送消息的变量替换

    Args:
        raw_msg: 原始消息
        current_num: 当前队伍人数
        total_num: 队伍总人数
        team_name: 游戏中的队伍名

    Returns:
        替换变量后的发送消息
    """
    raw_msg = raw_msg.replace("${当前人数}", str(current_num))
    raw_msg = raw_msg.replace("${总人数}", str(total_num))
    raw_msg = raw_msg.replace("${队伍名}", team_name)
    return raw_msg
