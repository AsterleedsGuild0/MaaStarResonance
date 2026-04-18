from maa.context import Context

from agent.logger import logger


def get_game_need_line(context: Context) -> int:
    """
    获取小游戏需要切换的分线
    """
    need_line_node = context.get_node_data("获取参数-第一次小游戏前所需切换的分线")
    need_line = (need_line_node
                         .get("attach", {})
                         .get("need_line", 0)
                         ) if need_line_node else 0
    logger.info("第一次小游戏前所需切换的分线: {}", need_line if need_line else '不切换')
    return int(need_line)


def get_game_wait_time_limit(context: Context) -> int:
    """
    获取游戏等待超时时间
    """
    wait_time_limit_node = context.get_node_data("获取参数-游戏等待超时时间")
    wait_time_limit = (wait_time_limit_node
                         .get("attach", {})
                         .get("wait_time_limit", 0)
                         ) if wait_time_limit_node else 0
    logger.info("游戏等待超时时间: {}", wait_time_limit if wait_time_limit != 0 else '无限')
    return int(wait_time_limit)


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


def get_vehicle_team_type(context: Context) -> str:
    """
    获取载具赛队伍类型：
    1. 无
    2. 单人匹配游戏
    3. 组队匹配游戏（队长）
    4. 组队匹配游戏（队员）
    """
    vehicle_team_type_node = context.get_node_data("获取参数-载具赛队伍类型")
    vehicle_team_type = (vehicle_team_type_node
                         .get("attach", {})
                         .get("vehicle_team_type", "无")
                         ) if vehicle_team_type_node else "无"
    logger.info("载具赛队伍类型: {}", str(vehicle_team_type))
    return str(vehicle_team_type)

