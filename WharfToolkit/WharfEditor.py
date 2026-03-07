import json
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QGraphicsView, QGraphicsScene,
                             QGraphicsRectItem, QGraphicsTextItem, QToolBar,
                             QLabel, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen, QFont, QCursor

# 码头长度
WHARF_LENGTH = 3764

# 调整大小的手柄边距（像素）
RESIZE_MARGIN = 6


class VesselItem(QGraphicsRectItem):
    """船只矩形项，支持拖动和调整大小"""

    def __init__(self, vessel_id, wharf, start_pos, end_pos, start_time, end_time,
                 scene_width, scene_height, time_range, has_depart_event=True):
        super().__init__()

        self.vessel_id = vessel_id
        self.wharf = wharf
        self.has_depart_event = has_depart_event

        # 实际数据
        self.start_pos = start_pos  # wharfmark_start
        self.end_pos = end_pos      # wharfmark_end
        self.start_time = start_time
        self.end_time = end_time if end_time is not None else time_range[1]

        self.time_range = time_range  # (min_time, max_time)
        self.scene_width = scene_width
        self.scene_height = scene_height

        # 调整大小状态
        self._resizing = False
        self._resize_edge = None  # 'left', 'right', 'top', 'bottom', 或组合
        self._resize_start_pos = None
        self._resize_start_rect = None

        # 设置矩形位置（使用 setPos + setRect 的方式）
        self._update_rect_from_data()

        self.setFlags(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        # 设置颜色
        color = QColor(100, 150, 250, 180)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.darkBlue, 2))

        # 添加标签
        self.label = QGraphicsTextItem(self.vessel_id, self)
        self.label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.label.setDefaultTextColor(QColor(0, 0, 139))
        self._update_label_pos()

    def _data_to_scene_rect(self):
        """将数据转换为场景坐标矩形"""
        x = (self.start_pos / WHARF_LENGTH) * self.scene_width
        y = ((self.start_time - self.time_range[0]) /
             (self.time_range[1] - self.time_range[0])) * self.scene_height
        width = ((self.end_pos - self.start_pos) / WHARF_LENGTH) * self.scene_width
        height = ((self.end_time - self.start_time) /
                  (self.time_range[1] - self.time_range[0])) * self.scene_height

        # 确保最小尺寸
        width = max(width, 20)
        height = max(height, 10)

        return QRectF(x, y, width, height)

    def _update_rect_from_data(self):
        """根据数据更新图形位置"""
        scene_rect = self._data_to_scene_rect()
        # 使用 setPos 设置场景位置，rect 使用本地坐标 (0,0) 开始
        self.setPos(scene_rect.x(), scene_rect.y())
        self.setRect(0, 0, scene_rect.width(), scene_rect.height())

    def _scene_rect_to_data(self):
        """从当前场景位置+本地rect反算数据"""
        # 场景坐标 = pos() + rect 本地坐标
        sx = self.pos().x() + self.rect().x()
        sy = self.pos().y() + self.rect().y()
        sw = self.rect().width()
        sh = self.rect().height()

        self.start_pos = (sx / self.scene_width) * WHARF_LENGTH
        self.end_pos = ((sx + sw) / self.scene_width) * WHARF_LENGTH
        self.start_time = (sy / self.scene_height) * (
            self.time_range[1] - self.time_range[0]) + self.time_range[0]
        self.end_time = ((sy + sh) / self.scene_height) * (
            self.time_range[1] - self.time_range[0]) + self.time_range[0]

        # 边界限制
        self.start_pos = max(0, min(self.start_pos, WHARF_LENGTH))
        self.end_pos = max(self.start_pos, min(self.end_pos, WHARF_LENGTH))
        self.start_time = max(self.time_range[0], min(self.start_time, self.time_range[1]))
        self.end_time = max(self.start_time, min(self.end_time, self.time_range[1]))

    def _update_label_pos(self):
        """更新标签位置到矩形中心"""
        rect = self.rect()
        lw = self.label.boundingRect().width()
        lh = self.label.boundingRect().height()
        self.label.setPos(rect.x() + rect.width() / 2 - lw / 2,
                          rect.y() + rect.height() / 2 - lh / 2)

    def _get_resize_edge(self, local_pos):
        """判断鼠标在哪个边缘上"""
        rect = self.rect()
        edges = set()

        if abs(local_pos.x() - rect.left()) < RESIZE_MARGIN:
            edges.add('left')
        elif abs(local_pos.x() - rect.right()) < RESIZE_MARGIN:
            edges.add('right')

        if abs(local_pos.y() - rect.top()) < RESIZE_MARGIN:
            edges.add('top')
        elif abs(local_pos.y() - rect.bottom()) < RESIZE_MARGIN:
            edges.add('bottom')

        return edges if edges else None

    def hoverMoveEvent(self, event):
        """鼠标悬停时改变光标"""
        edges = self._get_resize_edge(event.pos())
        if edges is None:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        elif edges == {'left'} or edges == {'right'}:
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif edges == {'top'} or edges == {'bottom'}:
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        elif edges == {'left', 'top'} or edges == {'right', 'bottom'}:
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif edges == {'right', 'top'} or edges == {'left', 'bottom'}:
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """鼠标按下：判断是拖动还是调整大小"""
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._get_resize_edge(event.pos())
            if edges:
                self._resizing = True
                self._resize_edge = edges
                self._resize_start_pos = event.scenePos()
                self._resize_start_rect = self.rect()
                # 阻止默认拖动行为
                event.accept()
                return
        self._resizing = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动：执行调整大小或拖动"""
        if self._resizing and self._resize_edge:
            delta = event.scenePos() - self._resize_start_pos
            rect = QRectF(self._resize_start_rect)

            if 'left' in self._resize_edge:
                new_left = rect.left() + delta.x()
                if rect.right() - new_left >= 20:  # 最小宽度
                    rect.setLeft(new_left)
            if 'right' in self._resize_edge:
                new_right = rect.right() + delta.x()
                if new_right - rect.left() >= 20:
                    rect.setRight(new_right)
            if 'top' in self._resize_edge:
                new_top = rect.top() + delta.y()
                if rect.bottom() - new_top >= 10:  # 最小高度
                    rect.setTop(new_top)
            if 'bottom' in self._resize_edge:
                new_bottom = rect.bottom() + delta.y()
                if new_bottom - rect.top() >= 10:
                    rect.setBottom(new_bottom)

            self.setRect(rect)
            self._scene_rect_to_data()
            self._update_label_pos()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        if self._resizing:
            self._resizing = False
            self._resize_edge = None
            self._scene_rect_to_data()
            self._update_label_pos()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        """处理拖动后的位置更新"""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            # 拖动改变 pos()，rect() 不变，需要根据新的 pos+rect 反算数据
            self._scene_rect_to_data()
            self._update_label_pos()
        return super().itemChange(change, value)

    def update_position(self):
        """从数据刷新图形"""
        self._update_rect_from_data()
        self._update_label_pos()


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
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
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

        # 绘制刻度标签
        for i in range(0, WHARF_LENGTH + 1, 500):
            x = (i / WHARF_LENGTH) * self.scene_width
            tick_label = self.scene.addText(str(i))
            tick_label.setFont(QFont("Arial", 6))
            tick_label.setPos(x - 10, -15)

        # X轴标签
        x_label = self.scene.addText("wharfmark position →")
        x_label.setPos(self.scene_width - 130, self.scene_height - 20)

        # Y轴标签
        y_label = self.scene.addText("time ↓")
        y_label.setPos(5, self.scene_height - 20)

    def add_vessel(self, vessel_id, start_pos, end_pos, start_time, end_time, time_range,
                   has_depart_event=True):
        """添加船只"""
        item = VesselItem(vessel_id, self.wharf_name, start_pos, end_pos,
                         start_time, end_time, self.scene_width, self.scene_height,
                         time_range, has_depart_event)
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

    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1 / factor, 1 / factor)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wharf Occupancy Editor")
        self.setGeometry(100, 100, 1200, 700)

        # 数据
        self.events = []
        self.json_file = 'event_vessel_depart_40_hm.json'

        # 记录哪些vessel有depart事件
        self.vessels_with_depart = set()

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

        status_label = QLabel("  Drag to move | Drag edges to resize | Scroll to zoom")
        toolbar.addWidget(status_label)

    def _load_json(self):
        """加载JSON文件"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.events = json.load(f)

            # 建立vessel到wharf的映射
            vessel_info = {}
            self.vessels_with_depart = set()

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
                    self.vessels_with_depart.add(event['vesselId'])

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

                has_depart = vessel_id in self.vessels_with_depart

                view.add_vessel(
                    vessel_id,
                    info['wharfmark_start'],
                    info['wharfmark_end'],
                    info['start_time'],
                    info.get('end_time'),
                    time_range,
                    has_depart_event=has_depart
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
                    'wharfmark_start': round(item.start_pos, 2),
                    'wharfmark_end': round(item.end_pos, 2),
                    'start_time': round(item.start_time, 2),
                    'end_time': round(item.end_time, 2),
                    'has_depart_event': item.has_depart_event
                }

            for vessel_id, item in self.view_s.vessel_items.items():
                vessel_updates[vessel_id] = {
                    'wharfmark_start': round(item.start_pos, 2),
                    'wharfmark_end': round(item.end_pos, 2),
                    'start_time': round(item.start_time, 2),
                    'end_time': round(item.end_time, 2),
                    'has_depart_event': item.has_depart_event
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
                        if update['has_depart_event']:
                            event['time'] = update['end_time']

            # 按time升序排列
            self.events.sort(key=lambda e: e.get('time', 0))

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
