from maa.context import Context

from agent.logger import logger


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
