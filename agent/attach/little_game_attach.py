from maa.context import Context

from agent.logger import logger


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
