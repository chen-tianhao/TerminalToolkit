"""
yc_move.py - YC 运动耗时计算模块

计算 YC（场桥）各组件（龙门架 Gantry、小车 Trolley、起升 Hoist）的运动耗时。
"""

import json
import math
import os
from dataclasses import dataclass
from typing import Tuple, Optional

from slot import Slot
from block import Block

# 单例参数缓存
_params: Optional['YCParameters'] = None


@dataclass
class YCParameters:
    """YC 运动学参数"""
    # 速度 (m/s)
    hoist_with_swl_load: float
    hoist_with_empty_spreader: float
    trolley_with_load: float
    gantry_with_load: float
    # 起升加速度 (m/s²)
    hoist_accel_with_empty: float
    hoist_accel_with_swl: float
    # 下降加速度 (m/s²)
    lower_accel_with_empty: float
    lower_accel_with_swl: float
    # 运行加速度 (m/s²)
    trolley_accel: float
    gantry_accel: float
    # 有效安全作业提升高度
    effective_safe_operation_lift: float
    operating_effective_trolley_travel: float


@dataclass
class YCMovePos:
    """YC 位置坐标（米）"""
    gantry: float  # bay 方向
    trolley: float  # row 方向
    hoist: float  # 高度方向

"""
读取KinematicsYC/paras/KinematicsYC.json中的
速度参数：
with_swl_load_mps / with_empty_spreader_mps / with_swl_load_mps / 
with_empty_spreader_mps / with_swl_load_mps和with_empty_spreader_mps，
以及加速度参数：
hoist_with_empty_spreader_mpss / hoist_with_swl_load_mpss / 
lower_with_empty_spreader_mpss / lower_with_swl_load_mpss / 
trolley_travel_mpss / gantry_travel_mpss。
"""
def read_para(json_path: str = None) -> YCParameters:
    """
    读取 KinematicsYC.json 配置文件

    Args:
        json_path: JSON 文件路径，默认使用相对于本文件的路径

    Returns:
        YCParameters 对象
    """
    global _params

    if _params is not None:
        return _params

    if json_path is None:
        json_path = os.path.join(os.path.dirname(__file__), '..', 'paras', 'KinematicsYC.json')

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    speed = data['speed_and_duty']
    accel = data['accelerations_decelerations']
    dimensions = data['overall_dimensions']

    _params = YCParameters(
        hoist_with_swl_load=float(speed['hoisting_speed']['with_swl_load_mps']),
        hoist_with_empty_spreader=float(speed['hoisting_speed']['with_empty_spreader_mps']),
        trolley_with_load=float(speed['trolley_travel_speed']['with_swl_load_mps']),
        gantry_with_load=float(speed['gantry_travel_speed']['with_swl_load_mps']),
        hoist_accel_with_empty=float(accel['hoist_with_empty_spreader_mpss']),
        hoist_accel_with_swl=float(accel['hoist_with_swl_load_mpss']),
        lower_accel_with_empty=float(accel['lower_with_empty_spreader_mpss']),
        lower_accel_with_swl=float(accel['lower_with_swl_load_mpss']),
        trolley_accel=float(accel['trolley_travel_mpss']),
        gantry_accel=float(accel['gantry_travel_mpss']),
        effective_safe_operation_lift=float(dimensions['effective_safe_operation_lift_m']),
        operating_effective_trolley_travel=float(dimensions['operating_effective_trolley_travel_m'])
    )

    return _params


def get_params() -> YCParameters:
    """获取缓存的参数，若未读取则先读取"""
    global _params
    if _params is None:
        return read_para()
    return _params

# 基于梯形速度曲线的运动耗时计算，在Gentry_time / Trolley_time / Hoist_time中被调用
def _motion_time(distance: float, v_max: float, a: float) -> float:
    """
    计算运动耗时（梯形速度曲线）

    Args:
        distance: 运动距离（米）
        v_max: 最大速度 (m/s)
        a: 加速度 (m/s²)

    Returns:
        运动耗时（秒）
    """
    if distance <= 0:
        return 0.0
    if v_max <= 0 or a <= 0:
        return float('inf')

    d = abs(distance)
    d_crit = v_max * v_max / a  # 达到最大速度所需的临界距离

    if d >= d_crit:
        # 可以达到最大速度：加速 + 匀速 + 减速
        t_accel = v_max / a
        t_decel = v_max / a
        t_cruise = (d - d_crit) / v_max
        return t_accel + t_cruise + t_decel
    else:
        # 无法达到最大速度，使用三角速度曲线
        # 峰值速度 v = sqrt(a*d)
        # 时间 t = 2*v/a = 2*sqrt(d/a)
        return 2.0 * math.sqrt(d / a)


def parse_agv_pos(bay_index: int) -> float:
    """
    根据 bay_index 解析 gantry 目标位置

    Args:
        bay_index: AGV 所在的 bay 索引（1 ~ num_bays*2-1）

    Returns:
        gantry_pos — 单位：米
        遵循 visual_blk.py 中的坐标系：gantry_pos = bay_index / 2 * slot_length
    """
    return bay_index / 2 * Block.slot_length


def parse_slot_pos(slot: Slot) -> Tuple[float, float, float]:
    """
    解析 Slot 位置为 gantry、trolley、hoist 目标位置

    Args:
        slot: Slot 对象，包含 bay, row, tier 属性

    Returns:
        (gantry_pos, trolley_pos, hoist_pos) — 单位：米
        gantry: 遵循 visual_blk.py 坐标系 gantry_pos = bay / 2 * slot_length
        trolley: trolley_pos = (row - 1) * slot_width
        hoist: hoist_pos = (tier - 1) * slot_height
    """
    gantry_pos = slot.bay / 2 * Block.slot_length
    trolley_pos = (slot.row - 1) * Block.slot_width
    hoist_pos = (slot.tier - 1) * Block.slot_height

    return gantry_pos, trolley_pos, hoist_pos

"""
根据起止点在gantry方向上的分量，通过gantry相关的速度和加速度参数，计算YC gantry需要的时间，注意空载和满载swl应使用不同的参数。
"""
def gantry_time(start: float, end: float, with_load: bool) -> float:
    """
    计算龙门架（gantry）运动时间

    Args:
        start: 起点位置（米）
        end: 终点位置（米）
        with_load: 是否负载（True=满载SWL, False=空载吊具）

    Returns:
        运动耗时（秒）
    """
    params = get_params()
    distance = abs(end - start)
    # gantry 速度和加速度在空载/满载时相同
    return _motion_time(distance, params.gantry_with_load, params.gantry_accel)

"""
根据起止点在trolley方向上的分量，通过trolley相关的速度和加速度参数，计算YC trolley需要的时间，注意空载和满载swl应使用不同的参数。
"""
def trolley_time(start: float, end: float, with_load: bool) -> float:
    """
    计算小车（trolley）运动时间

    Args:
        start: 起点位置（米）
        end: 终点位置（米）
        with_load: 是否负载（True=满载SWL, False=空载吊具）

    返回:
        运动耗时（秒）
    """
    params = get_params()
    distance = abs(end - start)
    # trolley 速度和加速度在空载/满载时相同
    return _motion_time(distance, params.trolley_with_load, params.trolley_accel)


"""
根据起止点在hoist方向上的分量，通过hoist相关的速度和加速度参数，计算YC hoist需要的时间，注意空载和满载swl应使用不同的参数。
"""
def hoist_time(start: float, end: float, with_load: bool, is_hoisting: bool) -> float:
    """
    计算起升机构（hoist）运动时间

    Args:
        start: 起点高度（米）
        end: 终点高度（米）
        with_load: 是否负载（True=满载SWL, False=空载吊具）
        is_hoisting: True=起升动作，False=下降动作

    返回:
        运动耗时（秒）
    """
    params = get_params()
    distance = abs(end - start)

    if with_load:
        # 满载 SWL
        v = params.hoist_with_swl_load
        if is_hoisting:
            a = params.hoist_accel_with_swl
        else:
            a = params.lower_accel_with_swl
    else:
        # 空载吊具
        v = params.hoist_with_empty_spreader
        if is_hoisting:
            a = params.hoist_accel_with_empty
        else:
            a = params.lower_accel_with_empty

    return _motion_time(distance, v, a)

"""
侧存箱。
时间包含：空载gantry移动时间(A) + 空载trolley移动时间(B) + 空载下降时间(C) + 固定操作时间(D) + 满载提升时间(E) + 满载trolley移动时间(F) + 满载下降时间(G)
其中A和B同时发生，取较大值
计算hoist时应安全高度(effective_safe_operation_lift)作为参考基准
计算trolley移动时应考虑operating_effective_trolley_travel的限制，超过该范围则需要增加gantry移动时间
其中A发生在origin和agv之间，B可忽略，
返回A~D总时间(working_cycle)，以及E~G总时间(restore_cycle)
"""
def side_feed_stacking_time(origin_slot_idx: int, agv_bay_index: int, target_slot: Slot, fixed_op_time = 0.0) -> float:
    return 0.0

"""
侧取箱。
时间包含：空载gantry移动时间(A) + 空载trolley移动时间(B) + 空载下降时间(C) + 固定操作时间(D) + 满载提升时间(E) + 满载trolley移动时间(F) + 满载下降时间(G)
       + 固定操作时间(H) + 空载提升时间(I) +空载trolley移动时间(J)
其中A和B同时发生，取较大值
计算hoist时应安全高度(effective_safe_operation_lift)作为参考基准
计算trolley移动时应考虑operating_effective_trolley_travel的限制，超过该范围则需要增加gantry移动时间
其中A发生在origin和agv之间，B可忽略，
返回A~H总时间(working_cycle)，以及I~J总时间(restore_cycle)
"""
def side_feed_unstacking_time(origin_slot_idx: int, agv_bay_index: int, target_slot: Slot, fixed_op_time = 0.0) -> float:
    return 0.0

"""
端存箱。
"""
def end_feed_stacking_time(origin_slot_idx: int, max_bay_index: int, slot: Slot, fixed_op_time = 0.0) -> float:
    return 0.0

"""
端取箱。
"""
def end_feed_unstacking_time(origin_slot_idx: int, max_bay_index: int, slot: Slot, fixed_op_time = 0.0) -> float:
    return 0.0

