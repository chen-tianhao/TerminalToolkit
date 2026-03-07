import json

# 码头长度
WHARF_LENGTH = 3764

def load_json_data(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_overlap(start1, end1, start2, end2):
    """检查两个区间是否重叠"""
    return start1 < end2 and start2 < end1

def calculate_wharf_utilization(events, wharf_name, last_time):
    """
    计算指定码头的占用率
    """
    # 记录当前停靠的船只 {vesselId: {'start': time, 'wharfmark_start': start, 'wharfmark_end': end}}
    docked_vessels = {}

    # 记录重叠错误
    overlap_errors = []

    # 计算总占用面积*时间
    total_occupied_area_time = 0

    for event in events:
        # 只处理属于该码头的事件
        wharf = event.get('wharf')
        if wharf != wharf_name:
            continue

        time = event['time']
        event_name = event['eventName']

        if event_name == 'OnStart':
            vessel_id = event['vesselId']
            wharfmark_start = event['wharfmark_start']
            wharfmark_end = event['wharfmark_end']

            # 检查是否与已停靠的船只重叠
            for existing_vessel_id, existing_info in docked_vessels.items():
                if check_overlap(wharfmark_start, wharfmark_end,
                                 existing_info['wharfmark_start'], existing_info['wharfmark_end']):
                    overlap_errors.append((vessel_id, existing_vessel_id))

            # 记录船只停靠信息
            docked_vessels[vessel_id] = {
                'start': time,
                'wharfmark_start': wharfmark_start,
                'wharfmark_end': wharfmark_end
            }

        elif event_name == 'OnReadyToDepart':
            vessel_id = event['vesselId']

            if vessel_id in docked_vessels:
                info = docked_vessels[vessel_id]
                # 计算占用时间
                duration = time - info['start']
                # 计算占用面积
                area = info['wharfmark_end'] - info['wharfmark_start']
                # 累加 面积 * 时间
                total_occupied_area_time += area * duration
                # 释放泊位
                del docked_vessels[vessel_id]

    # 处理最后仍在停靠的船只，使用最后时刻作为结束时间
    for vessel_id, info in docked_vessels.items():
        duration = last_time - info['start']
        area = info['wharfmark_end'] - info['wharfmark_start']
        total_occupied_area_time += area * duration

    return total_occupied_area_time, overlap_errors

def build_vessel_wharf_map(events):
    """建立vesselId到wharf的映射（从OnStart事件中获取）"""
    vessel_map = {}
    for event in events:
        if event.get('eventName') == 'OnStart':
            vessel_map[event['vesselId']] = event.get('wharf')
    return vessel_map

def main():
    # 读取JSON数据
    events = load_json_data('event_vessel_depart_40_hm.json')

    # 按时间排序
    events.sort(key=lambda x: x['time'])

    # 建立vesselId到wharf的映射
    vessel_wharf_map = build_vessel_wharf_map(events)

    # 为OnReadyToDepart事件添加wharf字段
    for event in events:
        if event.get('eventName') == 'OnReadyToDepart':
            vessel_id = event['vesselId']
            if vessel_id in vessel_wharf_map:
                event['wharf'] = vessel_wharf_map[vessel_id]

    # 获取最后时刻的时间
    last_time = events[-1]['time']

    # 计算wharf_N的占用率
    occupied_area_time_N, errors_N = calculate_wharf_utilization(events, 'wharf_N', last_time)
    utilization_N = occupied_area_time_N / (WHARF_LENGTH * last_time)

    # 计算wharf_S的占用率
    occupied_area_time_S, errors_S = calculate_wharf_utilization(events, 'wharf_S', last_time)
    utilization_S = occupied_area_time_S / (WHARF_LENGTH * last_time)

    # 打印结果
    print(f"wharf_N utilization: {utilization_N:.6f}")
    print(f"wharf_S utilization: {utilization_S:.6f}")

    # 打印重叠错误
    all_errors = errors_N + errors_S
    if all_errors:
        print("\nPosition overlap errors:")
        for vessel1, vessel2 in all_errors:
            print(f"  Vessel {vessel1} overlaps with vessel {vessel2}")

if __name__ == '__main__':
    main()
