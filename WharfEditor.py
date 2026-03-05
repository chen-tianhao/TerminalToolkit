import json
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QGraphicsView, QGraphicsScene,
                             QGraphicsRectItem, QGraphicsTextItem, QToolBar,
                             QLabel, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen, QFont

# 码头长度
WHARF_LENGTH = 3764


class VesselItem(QGraphicsRectItem):
    """船只矩形项，支持拖动和调整大小"""

    def __init__(self, vessel_id, wharf, start_pos, end_pos, start_time, end_time, scene_width, scene_height, time_range):
        super().__init__()

        self.vessel_id = vessel_id
        self.wharf = wharf

        # 实际数据
        self.start_pos = start_pos  # wharfmark_start
        self.end_pos = end_pos      # wharfmark_end
        self.start_time = start_time
        self.end_time = end_time if end_time is not None else time_range[1]

        self.time_range = time_range  # (min_time, max_time)
        self.scene_width = scene_width
        self.scene_height = scene_height

        # 设置矩形
        self.setRect(self._data_to_rect())
        self.setFlags(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        # 设置颜色
        color = QColor(100, 150, 250, 180)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.darkBlue, 2))

        # 添加标签
        self.label = QGraphicsTextItem(self.vessel_id, self)
        self.label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.label.setDefaultTextColor(QColor(0, 0, 139))

    def _data_to_rect(self):
        """将数据转换为场景矩形"""
        # X: wharfmark -> scene x
        x = (self.start_pos / WHARF_LENGTH) * self.scene_width

        # Y: time -> scene y (向下增加，原点左上角)
        y = ((self.start_time - self.time_range[0]) / (self.time_range[1] - self.time_range[0])) * self.scene_height

        # 宽度
        width = ((self.end_pos - self.start_pos) / WHARF_LENGTH) * self.scene_width

        # 高度
        height = ((self.end_time - self.start_time) / (self.time_range[1] - self.time_range[0])) * self.scene_height

        # 确保最小尺寸
        width = max(width, 20)
        height = max(height, 10)

        return QRectF(x, y, width, height)

    def _rect_to_data(self, rect):
        """将场景矩形转换为数据"""
        # X -> wharfmark
        self.start_pos = (rect.x() / self.scene_width) * WHARF_LENGTH
        self.end_pos = ((rect.x() + rect.width()) / self.scene_width) * WHARF_LENGTH

        # Y -> time (向下增加)
        self.start_time = (rect.y() / self.scene_height) * (self.time_range[1] - self.time_range[0]) + self.time_range[0]
        self.end_time = ((rect.y() + rect.height()) / self.scene_height) * (self.time_range[1] - self.time_range[0]) + self.time_range[0]

        # 边界限制
        self.start_pos = max(0, min(self.start_pos, WHARF_LENGTH))
        self.end_pos = max(self.start_pos, min(self.end_pos, WHARF_LENGTH))
        self.start_time = max(self.time_range[0], min(self.start_time, self.time_range[1]))
        self.end_time = max(self.start_time, min(self.end_time, self.time_range[1]))

    def itemChange(self, change, value):
        """处理项变化"""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            rect = self.rect()
            self._rect_to_data(rect)

            # 更新标签位置
            self.label.setPos(rect.width() / 2 - self.label.boundingRect().width() / 2,
                              rect.height() / 2 - self.label.boundingRect().height() / 2)

        return super().itemChange(change, value)

    def update_position(self):
        """更新位置（从数据到图形）"""
        self.setRect(self._data_to_rect())
        rect = self.rect()
        self.label.setPos(rect.width() / 2 - self.label.boundingRect().width() / 2,
                          rect.height() / 2 - self.label.boundingRect().height() / 2)


class WharfGraphicsView(QGraphicsView):
    """码头图形视图"""

    def __init__(self, wharf_name, parent=None):
        super().__init__(parent)
        self.wharf_name = wharf_name

        # 创建场景
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 设置视图属性
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 场景大小
        self.scene_width = 500
        self.scene_height = 600
        self.setMinimumSize(self.scene_width, self.scene_height)
        self.scene.setSceneRect(0, 0, self.scene_width, self.scene_height)

        # 绘制背景网格
        self._draw_background()

        # 船只项字典
        self.vessel_items = {}

    def _draw_background(self):
        """绘制背景网格"""
        # 背景
        self.scene.addRect(0, 0, self.scene_width, self.scene_height,
                          QPen(Qt.GlobalColor.gray), QBrush(QColor(245, 245, 245)))

        # 绘制刻度线（每500米）
        for i in range(0, WHARF_LENGTH + 1, 500):
            x = (i / WHARF_LENGTH) * self.scene_width
            self.scene.addLine(x, 0, x, self.scene_height,
                             QPen(Qt.GlobalColor.lightGray, 1, Qt.PenStyle.DashLine))

        # 标题
        title = self.scene.addText(f"{self.wharf_name} (Length: {WHARF_LENGTH})")
        title.setPos(5, 5)
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        # X轴标签
        x_label = self.scene.addText("wharfmark position ->")
        x_label.setPos(self.scene_width - 120, self.scene_height - 20)

        # Y轴标签
        y_label = self.scene.addText("time ->")
        y_label.setPos(5, self.scene_height - 20)

    def add_vessel(self, vessel_id, start_pos, end_pos, start_time, end_time, time_range):
        """添加船只"""
        item = VesselItem(vessel_id, self.wharf_name, start_pos, end_pos,
                         start_time, end_time, self.scene_width, self.scene_height, time_range)
        self.scene.addItem(item)
        self.vessel_items[vessel_id] = item
        return item

    def get_vessel_data(self, vessel_id):
        """获取船只数据"""
        if vessel_id in self.vessel_items:
            item = self.vessel_items[vessel_id]
            return {
                'vessel_id': item.vessel_id,
                'wharf': item.wharf,
                'wharfmark_start': item.start_pos,
                'wharfmark_end': item.end_pos,
                'start_time': item.start_time,
                'end_time': item.end_time
            }
        return None


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wharf Occupancy Editor")
        self.setGeometry(100, 100, 1200, 700)

        # 数据
        self.events = []
        self.json_file = 'event_vessel_depart_40_hm.json'

        # 创建界面
        self._create_ui()

        # 加载数据
        self._load_json()

    def _create_ui(self):
        """创建界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)

        # 创建两个视图
        self.view_n = WharfGraphicsView("wharf_N")
        self.view_s = WharfGraphicsView("wharf_S")

        layout.addWidget(self.view_n)
        layout.addWidget(self.view_s)

        # 工具栏
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        save_action = toolbar.addAction("Save JSON")
        save_action.triggered.connect(self._save_json)

        reload_action = toolbar.addAction("Reload")
        reload_action.triggered.connect(self._load_json)

        status_label = QLabel("Drag rectangles to move")
        toolbar.addWidget(status_label)

    def _load_json(self):
        """加载JSON文件"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.events = json.load(f)

            # 建立vessel到wharf的映射
            vessel_info = {}
            for event in self.events:
                if event.get('eventName') == 'OnStart':
                    vessel_info[event['vesselId']] = {
                        'wharf': event.get('wharf'),
                        'wharfmark_start': event.get('wharfmark_start'),
                        'wharfmark_end': event.get('wharfmark_end'),
                        'start_time': event.get('time')
                    }
                elif event.get('eventName') == 'OnReadyToDepart':
                    if event['vesselId'] in vessel_info:
                        vessel_info[event['vesselId']]['end_time'] = event['time']

            # 计算时间范围
            times = [e['time'] for e in self.events]
            time_range = (min(times), max(times))

            # 添加船只到视图
            self.view_n.scene.clear()
            self.view_n._draw_background()
            self.view_n.vessel_items = {}

            self.view_s.scene.clear()
            self.view_s._draw_background()
            self.view_s.vessel_items = {}

            for vessel_id, info in vessel_info.items():
                wharf = info['wharf']
                if wharf == 'wharf_N':
                    view = self.view_n
                elif wharf == 'wharf_S':
                    view = self.view_s
                else:
                    continue

                view.add_vessel(
                    vessel_id,
                    info['wharfmark_start'],
                    info['wharfmark_end'],
                    info['start_time'],
                    info.get('end_time'),
                    time_range
                )

            print(f"Loaded {len(vessel_info)} vessels")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load JSON: {str(e)}")

    def _save_json(self):
        """保存JSON文件"""
        try:
            # 从视图中收集更新后的数据
            vessel_updates = {}

            for vessel_id, item in self.view_n.vessel_items.items():
                vessel_updates[vessel_id] = {
                    'wharfmark_start': item.start_pos,
                    'wharfmark_end': item.end_pos,
                    'start_time': item.start_time,
                    'end_time': item.end_time
                }

            for vessel_id, item in self.view_s.vessel_items.items():
                vessel_updates[vessel_id] = {
                    'wharfmark_start': item.start_pos,
                    'wharfmark_end': item.end_pos,
                    'start_time': item.start_time,
                    'end_time': item.end_time
                }

            # 更新events列表
            for event in self.events:
                vessel_id = event['vesselId']
                if vessel_id in vessel_updates:
                    update = vessel_updates[vessel_id]

                    if event.get('eventName') == 'OnStart':
                        event['wharfmark_start'] = update['wharfmark_start']
                        event['wharfmark_end'] = update['wharfmark_end']
                        event['time'] = update['start_time']
                    elif event.get('eventName') == 'OnReadyToDepart':
                        event['time'] = update['end_time']

            # 保存到文件
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, indent=2, ensure_ascii=False)

            QMessageBox.information(self, "Success", "JSON file saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save JSON: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
