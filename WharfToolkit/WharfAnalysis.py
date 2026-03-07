import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# 码头长度
WHARF_LENGTH = 3764

def load_json_data(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_vessel_wharf_map(events):
    """建立vesselId到wharf的映射（从OnStart事件中获取）"""
    vessel_map = {}
    for event in events:
        if event.get('eventName') == 'OnStart':
            vessel_map[event['vesselId']] = event.get('wharf')
    return vessel_map

def get_vessel_intervals(events, wharf_name):
    """获取指定码头的船只停泊区间"""
    # 排序事件
    events_sorted = sorted(events, key=lambda x: x['time'])

    # 建立vesselId到wharf的映射
    vessel_wharf_map = build_vessel_wharf_map(events_sorted)

    # 收集OnStart和OnReadyToDepart事件
    vessel_data = {}

    for event in events_sorted:
        event_name = event.get('eventName')
        vessel_id = event['vesselId']

        # 确定事件所属的wharf
        wharf = event.get('wharf')
        if wharf is None and vessel_id in vessel_wharf_map:
            wharf = vessel_wharf_map[vessel_id]

        # 只处理目标wharf的事件
        if wharf != wharf_name:
            continue

        if vessel_id not in vessel_data:
            vessel_data[vessel_id] = {}

        if event_name == 'OnStart':
            vessel_data[vessel_id]['start_time'] = event['time']
            vessel_data[vessel_id]['wharfmark_start'] = event['wharfmark_start']
            vessel_data[vessel_id]['wharfmark_end'] = event['wharfmark_end']
        elif event_name == 'OnReadyToDepart':
            vessel_data[vessel_id]['end_time'] = event['time']

    # 转换为区间列表
    intervals = []
    for vessel_id, data in vessel_data.items():
        if 'start_time' in data:
            end_time = data.get('end_time')
            intervals.append({
                'vessel_id': vessel_id,
                'start_time': data['start_time'],
                'end_time': end_time,
                'wharfmark_start': data['wharfmark_start'],
                'wharfmark_end': data['wharfmark_end']
            })

    return intervals

def draw_wharf_chart(intervals, wharf_name, output_filename):
    """绘制码头占用图"""
    if not intervals:
        print(f"No data for {wharf_name}")
        return

    # 获取时间范围
    all_times = []
    for iv in intervals:
        all_times.append(iv['start_time'])
        if iv['end_time'] is not None:
            all_times.append(iv['end_time'])

    time_min = min(all_times)
    time_max = max(all_times)

    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 10))

    # 设置坐标轴
    ax.set_xlim(0, WHARF_LENGTH)
    ax.set_ylim(time_max, time_min)  # Y轴向下，时间增加

    ax.set_xlabel('Position along wharf (wharfmark)', fontsize=12)
    ax.set_ylabel('Time', fontsize=12)
    ax.set_title(f'{wharf_name} Occupancy Chart', fontsize=14)

    # 为每个船只绘制矩形
    colors = plt.cm.tab20(range(len(intervals)))

    for i, iv in enumerate(intervals):
        x = iv['wharfmark_start']
        y_top = iv['start_time']
        width = iv['wharfmark_end'] - iv['wharfmark_start']

        # 确定底部y坐标
        if iv['end_time'] is not None:
            y_bottom = iv['end_time']
        else:
            y_bottom = time_max  # 未离开的船，使用最后时间

        height = y_bottom - y_top

        # 绘制矩形
        rect = mpatches.Rectangle(
            (x, y_top), width, height,
            linewidth=1, edgecolor='black', facecolor=colors[i], alpha=0.7
        )
        ax.add_patch(rect)

        # 添加船ID标签
        label_x = x + width / 2
        label_y = y_top + height / 2
        ax.text(label_x, label_y, iv['vessel_id'], ha='center', va='center',
                fontsize=6, fontweight='bold')

    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_filename, dpi=150)
    plt.close()
    print(f"Saved {output_filename}")

def main():
    # 读取JSON数据
    events = load_json_data('event_vessel_depart_40_hm.json')

    # 为OnReadyToDepart事件添加wharf字段
    vessel_wharf_map = build_vessel_wharf_map(events)
    for event in events:
        if event.get('eventName') == 'OnReadyToDepart':
            vessel_id = event['vesselId']
            if vessel_id in vessel_wharf_map:
                event['wharf'] = vessel_wharf_map[vessel_id]

    # 绘制wharf_N图表
    intervals_N = get_vessel_intervals(events, 'wharf_N')
    print(f"wharf_N: {len(intervals_N)} vessels")
    draw_wharf_chart(intervals_N, 'wharf_N', 'wharf_N_chart.png')

    # 绘制wharf_S图表
    intervals_S = get_vessel_intervals(events, 'wharf_S')
    print(f"wharf_S: {len(intervals_S)} vessels")
    draw_wharf_chart(intervals_S, 'wharf_S', 'wharf_S_chart.png')

    print("Done!")

if __name__ == '__main__':
    main()
