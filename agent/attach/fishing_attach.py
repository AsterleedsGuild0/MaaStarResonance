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