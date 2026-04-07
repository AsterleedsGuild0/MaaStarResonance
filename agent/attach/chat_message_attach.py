from maa.context import Context

from agent.logger import logger


def get_chat_loop_limit(context: Context) -> int:
    """获取聊天框发消息的次数上限参数"""
    loop_limit_node = context.get_node_data("获取参数-聊天框发消息的次数上限")
    loop_limit = (loop_limit_node
                         .get("attach", {})
                         .get("limit", 0)
                         ) if loop_limit_node else 0
    logger.info("聊天框发消息的次数上限: {}", loop_limit)
    return int(loop_limit)


def get_chat_loop_interval(context: Context) -> int:
    """获取聊天框发消息的周期参数"""
    loop_interval_node = context.get_node_data("获取参数-聊天框发消息的周期")
    loop_interval = (loop_interval_node
                         .get("attach", {})
                         .get("loop_interval", 120)
                         ) if loop_interval_node else 120
    logger.info("聊天框发消息的周期: {}秒一次", loop_interval)
    return int(loop_interval)


def get_chat_channel(context: Context) -> str:
    """获取聊天框频道参数"""
    chat_channel_node = context.get_node_data("获取参数-输入聊天框频道")
    chat_channel = (chat_channel_node
                         .get("attach", {})
                         .get("channel", "世界")
                         ) if chat_channel_node else "世界"
    logger.info("输入聊天框频道类型: {}", chat_channel)
    return str(chat_channel)


def get_chat_channel_id_list(context: Context) -> list[str]:
    """获取需要发送消息的世界频道分线ID参数"""
    channel_ids_node = context.get_node_data("获取参数-需要发送消息的世界频道分线ID")
    channel_ids = (channel_ids_node
                         .get("attach", {})
                         .get("channel_ids", "")
                         ) if channel_ids_node else ""
    channel_id_list = str(channel_ids).split(",") if channel_ids else []
    logger.info("需要发送消息的世界频道分线ID列表: {}", channel_id_list)
    return channel_id_list


def get_chat_message_content(context: Context) -> str:
    """获取输入聊天框的消息内容参数"""
    message_content_node = context.get_node_data("获取参数-输入聊天框的消息内容")
    message_content = (message_content_node
                         .get("attach", {})
                         .get("content", "")
                         ) if message_content_node else ""
    logger.info("输入聊天框的消息内容: {}", str(message_content))
    return str(message_content)


def get_chat_message_need_team(context: Context) -> bool:
    """获取需要发送的消息是否需要队伍人数信息参数"""
    need_team_node = context.get_node_data("获取参数-需要发送的消息是否需要队伍人数信息")
    need_team = (need_team_node
                         .get("attach", {})
                         .get("need_number", False)
                         ) if need_team_node else False
    logger.info("需要发送的消息是否需要队伍人数信息: {}", need_team)
    return bool(need_team)


def get_full_team_force_send(context: Context) -> bool:
    """获取队伍已满时是否还需要发送消息参数"""
    force_send_node = context.get_node_data("获取参数-队伍已满时是否还需要发送消息")
    force_send = (force_send_node
                         .get("attach", {})
                         .get("force_send", False)
                         ) if force_send_node else False
    logger.info("队伍已满时是否还需要发送消息: {}", force_send)
    return bool(force_send)