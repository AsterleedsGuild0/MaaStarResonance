from maa.context import Context

from agent.logger import logger


def get_fish_navigation(context: Context) -> str:
    """获取钓鱼导航位置参数"""
    fish_navigation_node = context.get_node_data(f"获取参数-自动钓鱼去的导航位置")
    fish_navigation = (fish_navigation_node
                     .get("attach", {})
                     .get("target", "不导航")
                     ) if fish_navigation_node else "不导航"
    logger.info("自动钓鱼去的导航位置: {}", fish_navigation)
    return str(fish_navigation)


def get_fish_equipment(context: Context, type_str: str) -> str:
    """获取钓鱼配件参数"""
    fish_equipment_node = context.get_node_data(f"获取参数-需要购买的{type_str}配件")
    fish_equipment = (fish_equipment_node
                     .get("attach", {})
                     .get("item_name", f"普通{type_str}")
                     ) if fish_equipment_node else f"普通{type_str}"
    logger.info("需要购买的{}: {}", type_str, fish_equipment)
    return str(fish_equipment)


def get_login_timeout(context: Context) -> int:
    """获取登录超时时长参数"""
    login_timeout_node = context.get_node_data("获取参数-登录超时时长")
    login_timeout = (login_timeout_node
                     .get("attach", {})
                     .get("login_timeout", 300)
                     ) if login_timeout_node else 300
    logger.info("登录超时时长: {}秒", login_timeout)
    return int(login_timeout)


def get_area_change_timeout(context: Context) -> int:
    """获取场景切换超时时长参数"""
    area_change_timeout_node = context.get_node_data("获取参数-场景切换超时时长")
    area_change_timeout = (area_change_timeout_node
                           .get("attach", {})
                           .get("area_change_timeout", 90)
                           ) if area_change_timeout_node else 90
    logger.info("场景切换超时时长: {}秒", area_change_timeout)
    return int(area_change_timeout)


def get_restart_for_except(context: Context) -> bool:
    """获取是否重启游戏参数"""
    restart_for_except_node = context.get_node_data("获取参数-是否重启游戏")
    restart_for_except = (restart_for_except_node
                          .get("attach", {})
                          .get("restart_for_except", True)
                          ) if restart_for_except_node else True
    logger.info("是否重启游戏参数: {}", restart_for_except)
    return bool(restart_for_except)


def get_max_restart_count(context: Context) -> int:
    """获取最大重启游戏次数限制参数"""
    max_restart_count_node = context.get_node_data("获取参数-最大重启游戏次数限制")
    max_restart_count = (max_restart_count_node
                         .get("attach", {})
                         .get("max_restart_count", 5)
                         ) if max_restart_count_node else 5
    logger.info("最大重启游戏次数限制: {}", max_restart_count)
    return int(max_restart_count)


def get_dest_tele_map(context: Context) -> str:
    """获取传送所需地图参数"""
    dest_map_node = context.get_node_data("获取参数-传送所需地图")
    dest_map = (dest_map_node
                         .get("attach", {})
                         .get("dest_map", "")
                         ) if dest_map_node else ""
    logger.info("传送所需地图: {}", dest_map)
    return str(dest_map)


def get_dest_tele_point(context: Context) -> str:
    """获取传送所需传送点参数"""
    dest_tele_point_node = context.get_node_data("获取参数-传送所需传送点")
    dest_tele_point = (dest_tele_point_node
                         .get("attach", {})
                         .get("dest_tele_point", "")
                         ) if dest_tele_point_node else ""
    logger.info("传送所需传送点: {}", dest_tele_point)
    return str(dest_tele_point)


def get_dest_navi_map(context: Context) -> str:
    """获取导航所需地图参数"""
    dest_map_node = context.get_node_data("获取参数-导航所需地图")
    dest_map = (dest_map_node
                         .get("attach", {})
                         .get("dest_map", "")
                         ) if dest_map_node else ""
    logger.info("导航所需地图: {}", dest_map)
    return str(dest_map)


def get_dest_navigate_point(context: Context) -> str:
    """获取导航所需导航点参数"""
    dest_navigate_point_node = context.get_node_data("获取参数-导航所需导航点")
    dest_navigate_point = (dest_navigate_point_node
                         .get("attach", {})
                         .get("dest_navigate_point", "")
                         ) if dest_navigate_point_node else ""
    logger.info("导航所需导航点: {}", dest_navigate_point)
    return str(dest_navigate_point)


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


def get_world_line_id_list(context: Context) -> list[str]:
    """获取需要切换的世界分线ID列表参数"""
    line_ids_node = context.get_node_data("获取参数-需要切换的世界分线ID列表")
    line_ids = (line_ids_node
                         .get("attach", {})
                         .get("line_ids", "")
                         ) if line_ids_node else ""
    line_id_list = str(line_ids).split(",") if line_ids else []
    logger.info("需要切换的世界分线ID列表: {}", line_id_list)
    return line_id_list


def get_need_cocoon_name(context: Context) -> str:
    """获取需要刷的茧参数"""
    cocoon_node = context.get_node_data("获取参数-需要刷的茧")
    cocoon_name = (cocoon_node
                         .get("attach", {})
                         .get("cocoon_name", "")
                         ) if cocoon_node else ""
    logger.info("需要刷的茧: {}", str(cocoon_name))
    return str(cocoon_name)


def get_hide_team_type(context: Context) -> str:
    """
    获取躲猫猫队伍类型：
    1. 无
    2. 单人匹配游戏
    3. 组队匹配游戏（队长）
    4. 组队匹配游戏（队员）
    5. 组队私人游戏（队长，队伍人数须>=5）
    6. 组队私人游戏（队员）
    """
    hide_team_type_node = context.get_node_data("获取参数-躲猫猫队伍类型")
    hide_team_type = (hide_team_type_node
                         .get("attach", {})
                         .get("hide_team_type", "无")
                         ) if hide_team_type_node else "无"
    logger.info("躲猫猫队伍类型: {}", str(hide_team_type))
    return str(hide_team_type)


def get_maj_team_type(context: Context) -> str:
    """
    获取麻将队伍类型：
    1. 无
    2. 单人匹配游戏
    3. 组队私人游戏（队长）
    4. 组队私人游戏（队员）
    """
    maj_team_type_node = context.get_node_data("获取参数-麻将队伍类型")
    maj_team_type = (maj_team_type_node
                         .get("attach", {})
                         .get("maj_team_type", "无")
                         ) if maj_team_type_node else "无"
    logger.info("麻将队伍类型: {}", str(maj_team_type))
    return str(maj_team_type)


def get_maj_wait_time_limit(context: Context) -> int:
    """
    获取麻将等待超时时间
    """
    maj_wait_time_limit_node = context.get_node_data("获取参数-麻将等待超时时间")
    maj_wait_time_limit = (maj_wait_time_limit_node
                         .get("attach", {})
                         .get("wait_time_limit", 0)
                         ) if maj_wait_time_limit_node else 0
    logger.info("麻将等待超时时间: {}", maj_wait_time_limit if maj_wait_time_limit != 0 else '无限')
    return int(maj_wait_time_limit)
