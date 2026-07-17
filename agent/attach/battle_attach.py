from maa.context import Context

from agent.logger import logger


def get_unstable_space_type(context: Context) -> str:
    """
    获取不稳定空间队伍类型：
    1. 无
    2. 单人匹配游戏
    3. 组队匹配游戏（队长）
    4. 组队匹配游戏（队员）
    """
    unstable_space_type_node = context.get_node_data("获取参数-不稳定空间队伍类型")
    unstable_space_type = (unstable_space_type_node
                         .get("attach", {})
                         .get("unstable_space_type", "无")
                         ) if unstable_space_type_node else "无"
    logger.info("不稳定空间队伍类型: {}", str(unstable_space_type))
    return str(unstable_space_type)


def get_use_auto_attack(context: Context) -> bool:
    """
    获取战斗是否开启自动战斗
    """
    use_auto_attack_node = context.get_node_data("获取参数-是否开启自动战斗")
    use_auto_attack = (use_auto_attack_node
                         .get("attach", {})
                         .get("use_auto_attack", True)
                         ) if use_auto_attack_node else True
    logger.info("是否开启自动战斗: {}", bool(use_auto_attack))
    return bool(use_auto_attack)
