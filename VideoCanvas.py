from PyQt5.QtCore import pyqtSignal, QPointF, Qt, QRectF
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsView, QGraphicsRectItem


class RectangleItem(QGraphicsRectItem):
    def __init__(self, *args, **kwargs):
        super(RectangleItem, self).__init__(*args, **kwargs)
        self.setPen(QPen(Qt.red,4))

class VideoCanvas(QGraphicsView):
    rectFinished = pyqtSignal(QPointF, QPointF)

    def __init__(self, scene):
        super().__init__(scene)
        self.setMouseTracking(True)
        self.dragging = False
        self.start_point = QPointF()
        self.current_rect = None
        self.regions = []
        self.region_fields = []

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.start_point = self.mapToScene(event.pos())
            self.current_rect = RectangleItem(self.start_point.x(), self.start_point.y(), 0, 0)
            self.scene().addItem(self.current_rect)

    def mouseMoveEvent(self, event):
        if self.dragging:
            end_point = self.mapToScene(event.pos())
            rect = self.current_rect.rect()
            rect.setBottomRight(end_point)
            self.current_rect.setRect(rect)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            end_point = self.mapToScene(event.pos())
            self.rectFinished.emit(self.start_point, end_point)
            self.current_rect = None

    def redraw_rectangles(self, region_fields):
        if region_fields:
            for i in range(0, len(region_fields), 7):  # 7 fields per region: x1, y1, x2, y2, name, vert, hor
                x1 = float(region_fields[i].text())
                y1 = float(region_fields[i + 1].text())
                x2 = float(region_fields[i + 2].text())
                y2 = float(region_fields[i + 3].text())
                rect = QRectF(QPointF(x1, y1), QPointF(x2, y2)).normalized()
                item = RectangleItem(rect)
                self.scene().addItem(item)