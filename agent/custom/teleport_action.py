import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail, Rect
from maa.custom_action import CustomAction
from rapidfuzz import fuzz

from agent.attach.common_attach import get_dest_tele_map, get_dest_navigate_point, get_dest_tele_point, \
    get_dest_navi_map
from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
from agent.constant.map_point import MAP_POINT_DATA, NAVIGATE_DATA
from agent.custom.app_manage_action import get_area_change_timeout
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.logger import logger


@AgentServer.custom_action("TeleportPoint")
class TeleportPointAction(CustomAction):

    @exit_power_saving_mode()
    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        dest_map = get_dest_tele_map(context)
        dest_tele_point = get_dest_tele_point(context)
        logger.info(f"目的地图: {dest_map}, 目的传送点: {dest_tele_point}")
        if not dest_map or not dest_tele_point:
            logger.error("目的地图或目的传送点参数不能为空！")
            return False
        return teleport_or_navigate(context, dest_map, dest_tele_point, "传送", MAP_POINT_DATA)


@AgentServer.custom_action("NavigatePoint")
class NavigatePointAction(CustomAction):

    @exit_power_saving_mode()
    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        dest_map = get_dest_navi_map(context)
        dest_navigate_point = get_dest_navigate_point(context)
        logger.info(f"目的地图: {dest_map}, 目的导航点: {dest_navigate_point}")
        if not dest_map or not dest_navigate_point:
            logger.error("目的地图或目的导航点参数不能为空！")
            return False
        return teleport_or_navigate(context, dest_map, dest_navigate_point, "导航", NAVIGATE_DATA)


def teleport_or_navigate(context: Context, dest_map: str | None, dest_point: str, type_str: str, point_data: dict) -> bool:
    """
    传送 或者 导航
    
    Args:
        context: 控制器上下文
        dest_map: 目的地图 (不传会尝试根据 目的地点 去自动反查，查不到会返回：暂不支持的地图)
        dest_point: 目的地点
        type_str: 类型：传送 | 导航
        point_data: 地点数据MAP

    Returns:
        是否成功
    """
    # 0. 基本参数判断
    if not point_data:
        logger.error(f"地点数据缺失！")
        return False
    if dest_map is None and dest_point is not None:
        # 目的地点不为空，但目的地图为空：自动判断地图
        for map_name, locations in point_data.items():
            if dest_point in locations:
                dest_map = map_name
                break
    if dest_map not in point_data:
        logger.error(f"暂不支持的地图：{dest_map}，可能是命名不同或暂未支持")
        return False
    if dest_point not in point_data[dest_map]:
        logger.error(f"暂不支持的{type_str}点：{dest_map}-{dest_point}，可能是命名不同或暂未支持")
        return False
    # 场景切换超时时间
    area_change_timeout = get_area_change_timeout(context)

    # 1. 切换地图
    need_next = switch_map(context, dest_map)  # type: ignore
    if not need_next:
        return False
    time.sleep(2)

    # 2. 在目标地点坐标点击
    xy = point_data[dest_map][dest_point]
    floor_xy = xy.get("floor", {})
    # 有楼层坐标 | 说明可能有上下几层的，需要先切换楼层
    if floor_xy:
        context.tasker.controller.post_click(floor_xy["x"], floor_xy["y"]).wait()
        time.sleep(2)
    # 点击地点坐标
    context.tasker.controller.post_click(xy["x"], xy["y"]).wait()
    time.sleep(2)

    # 3. 判断是否可以直接过去
    img = context.tasker.controller.post_screencap().wait().get()
    is_direct_tp: RecognitionDetail | None = context.run_recognition(
        f"图片识别地点是否可以直接{type_str}",
        img
    )
    if is_direct_tp and not is_direct_tp.hit:
        # 3.1 不能直接过去：继续选择地点
        logger.info("无法直接过去，可能是图标重合，继续选择")
        img = context.tasker.controller.post_screencap().wait().get()
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "[\\S\\s]+",
                    "roi": [853, 207, 348, 311],
                }
            },
        )
        if not ocr_result or not ocr_result.hit:
            logger.error(f"无法识别到地点名字")
            return False

        # 匹配图标名优先用别称
        alias = xy.get("alias", dest_point)
        # 重新用fuzzy匹配赋分 | 更安全更稳定，尤其是在背景可能变化的地图地点这里
        for item in ocr_result.all_results:
            score = fuzz.ratio(item.text, alias)  # type: ignore
            item.score = score  # type: ignore
        # 重新根据匹配分数排序
        sorted_items = sorted(
            ocr_result.all_results, key=lambda obj: obj.score, reverse=True  # type: ignore
        )
        item = sorted_items[0]
        rect = Rect(*item.box)  # type: ignore
        logger.info(f"目的地点： {rect}, {item.text}")  # type: ignore
        point_x = int(rect.x + rect.w / 2)
        point_y = int(rect.y + rect.h / 2)
        # 选择地点
        context.tasker.controller.post_click(point_x, point_y).wait()
        time.sleep(2)
        # 再次判断是否可以直接过去
        img = context.tasker.controller.post_screencap().wait().get()
        is_direct_tp: RecognitionDetail | None = context.run_recognition(
            f"图片识别地点是否可以直接{type_str}", img
        )
        if not is_direct_tp or not is_direct_tp.hit:
            logger.error(f"{type_str}失败：无法找到{type_str}按钮")
            return False

    # 4. 点击按钮过去
    context.tasker.controller.post_click(1000, 650).wait()
    logger.info(f"点击进行{type_str}至 [{dest_map}：{dest_point}] 等待{type_str}完成...")
    time.sleep(5)

    # 5. 再次识别是否已经打开地图：是就说明当前状态无法导航
    img = context.tasker.controller.post_screencap().wait().get()
    is_open_map: RecognitionDetail | None = context.run_recognition("图片识别是否已经打开地图", img)
    if is_open_map and is_open_map.hit:
        logger.error("检测到当前状态无法导航，请检查当前是否无法上载具！")
        return False

    # 6. 等待进入游戏主页面
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= area_change_timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        area_change_result: RecognitionDetail | None = context.run_recognition("图片识别是否在主页面", img)
        if area_change_result and area_change_result.hit:
            del area_change_result, img
            logger.info(f"检测到已经成功切换场景，传送已完成，如果是导航请自行等待到达目的地点！")
            return True
        del area_change_result, img
        time.sleep(2)

    # 7. 超时未进入游戏主页面
    logger.error(f"{type_str}切换场景超时，未检测到主页面，请检查应用状态！")
    return False


# 切换地图
def switch_map(context: Context, dest_map: str) -> bool:
    # 1. 打开地图
    context.tasker.controller.post_click_key(ANDROID_KEY_EVENT_DATA["KEYCODE_M"]).wait()
    time.sleep(3)

    # 2. 是否已经打开地图了
    img = context.tasker.controller.post_screencap().wait().get()
    is_open_map: RecognitionDetail | None = context.run_recognition("图片识别是否已经打开地图", img)
    if not is_open_map or not is_open_map.hit:
        # 说明这里可能是游星岛
        if dest_map == "游星岛":
            logger.info("无法检测地图左下角标识，且目的地点是游星岛，您可能已经在该地图，将尝试直接传送或导航")
            return True
        else:
            logger.error("无法检测地图左下角标识，请检查是否在剧情中或游星岛传送其他地图！")
            return False

    # 3. 点击左下角按钮展开地图
    context.tasker.controller.post_click(150, 666).wait()
    time.sleep(1)

    # 4. OCR搜索地图名字并点击
    img = context.tasker.controller.post_screencap().wait().get()
    ocr_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {"expected": dest_map, "roi": [13, 288, 246, 341]}
        },
    )
    if not ocr_result or not ocr_result.hit:
        # 5. 第一次识别失败：说明地图可能比较多，需要滚动一下再次识别
        logger.info("第一次识别失败，尝试滚动后再次识别地图名字...")
        context.tasker.controller.post_swipe(100, 606, 100, 120, 1500).wait()
        img = context.tasker.controller.post_screencap().wait().get()
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {"expected": dest_map, "roi": [13, 288, 246, 341]}
            },
        )
        if not ocr_result or not ocr_result.hit:
            logger.error("两次识别后还是无法识别到地图名字，地图切换失败！")
            return False
    # 6. 获得最好结果坐标
    item = ocr_result.best_result
    rect = Rect(*item.box)  # type: ignore
    logger.info(f"目的地图： {rect}, {item.text}")  # type: ignore
    point_x = int(rect.x + rect.w / 2)
    point_y = int(rect.y + rect.h / 2)
    # 7. 选择地图
    context.tasker.controller.post_click(point_x, point_y).wait()
    return True
