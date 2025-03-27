import sys
import cv2
import pandas as pd
from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from PyQt5.QtGui import QPen, QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QVBoxLayout, QWidget, QFileDialog
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem, QHBoxLayout
from numpy import floor
from ConversionUtils import time_string_to_minutes, convert_to_float
from ExtractText import extract_text_from_video

class RectangleItem(QGraphicsRectItem):
    def __init__(self, *args, **kwargs):
        super(RectangleItem, self).__init__(*args, **kwargs)
        self.setPen(QPen(Qt.red))

class CanvasView(QGraphicsView):
    rectFinished = pyqtSignal(QPointF, QPointF)

    def __init__(self, scene):
        super().__init__(scene)
        self.setMouseTracking(True)
        self.dragging = False
        self.start_point = QPointF()
        self.current_rect = None
        self.regions = []
        #self.setSceneRect(0, 0, 200, 200)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.start_point = self.mapToScene(event.pos())
            self.current_rect = RectangleItem(self.start_point.x(),self.start_point.y(), 0, 0)
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

class VideoOCRApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.video_capture = None
        self.frame = None
        self.region_fields = []

    def initUI(self):
        self.setWindowTitle('Video OCR Tool')
        self.setGeometry(100, 100, 600, 400)  # Adjust size for better visibility

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()

        # File selection
        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        file_select_btn = QPushButton('Select Video File')
        file_select_btn.clicked.connect(self.select_file)
        layout.addWidget(QLabel('Video File Path:'))
        layout.addWidget(self.file_path)
        layout.addWidget(file_select_btn)

        # Canvas for region selection
        self.scene = QGraphicsScene()
        self.view = CanvasView(self.scene)
        self.view.rectFinished.connect(self.add_region_info)
        layout.addWidget(self.view)

        # Region info container
        self.region_container = QWidget()
        self.region_layout = QVBoxLayout()  # QVBoxLayout to stack horizontal layouts
        self.region_container.setLayout(self.region_layout)
        layout.addWidget(self.region_container)

        # Frame sampling interval
        self.interval = QLineEdit('30')
        self.start_time = QLineEdit('0')
        self.stop_time = QLineEdit('100')
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel('Sample every nth frame:'))
        h_layout.addWidget(self.interval)
        h_layout.addWidget(QLabel('Start Time:'))
        h_layout.addWidget(self.start_time)
        h_layout.addWidget(QLabel('Stop Time:'))
        h_layout.addWidget(self.stop_time)
        layout.addLayout(h_layout)

        # Start OCR button
        start_btn = QPushButton('Start OCR')
        start_btn.clicked.connect(self.start_processing)
        layout.addWidget(start_btn)

        main_widget.setLayout(layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_path:
            self.file_path.setText(file_path)
            self.load_video(file_path)

    def load_video(self, path):
        self.video_capture = cv2.VideoCapture(path)
        if self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret:
                self.frame = frame
                self.resize_canvas_to_video()
                self.display_frame()
        else:
            print("Error opening video file")

    def resize_canvas_to_video(self):
        if self.frame is not None:
            height, width, _ = self.frame.shape
            q_width, q_height = width // 4, height // 4
            self.view.setFixedSize(q_width, q_height)

    def display_frame(self):
        if self.frame is not None:
            height, width, channel = self.frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(self.frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            pixmap = QPixmap.fromImage(q_image)
            self.scene.clear()
            self.scene.addPixmap(pixmap)
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def add_region_info(self, start_point, end_point):
        top_left = QPointF(min(start_point.x(), end_point.x()), min(start_point.y(), end_point.y()))
        bottom_right = QPointF(max(start_point.x(), end_point.x()), max(start_point.y(), end_point.y()))

        # Create a horizontal layout for each region
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("X1:"))
        h_layout.addWidget(QLineEdit(f"{top_left.x():.2f}"))
        h_layout.addWidget(QLabel("Y1:"))
        h_layout.addWidget(QLineEdit(f"{top_left.y():.2f}"))
        h_layout.addWidget(QLabel("X2:"))
        h_layout.addWidget(QLineEdit(f"{bottom_right.x():.2f}"))
        h_layout.addWidget(QLabel("Y2:"))
        h_layout.addWidget(QLineEdit(f"{bottom_right.y():.2f}"))
        h_layout.addWidget(QLabel("Data:"))
        h_layout.addWidget(QLineEdit("RegionName"))
        self.region_layout.addLayout(h_layout)

        # Store references to these fields
        self.region_fields.extend([x1_field, y1_field, x2_field, y2_field, name_field])

    def start_processing(self):
        print(f"Processing video: {self.file_path.text()}")
        print(f"Sample interval: {self.interval.text()}")

        regions = []
        names = []
        new_column_names = {}
        df = pd.DataFrame()
        for i in range(0, len(self.region_fields), 5):  # 5 fields per region: x1, y1, x2, y2, name
            x1 = int(floor(float(self.region_fields[i].text())))
            y1 = int(floor(float(self.region_fields[i + 1].text())))
            x2 = int(floor(float(self.region_fields[i + 2].text())))
            y2 = int(floor(float(self.region_fields[i + 3].text())))
            name = self.region_fields[i + 4].text()
            regions.append([x1, y1, x2, y2])
            names.append([name])

        print(f"Regions: {regions}")  # Here you would use these regions for OCR

        self.display_frame()
        print(df)
        df = extract_text_from_video(self.video_capture, regions, int(self.interval.text()), int(self.start_time.text()), int(self.stop_time.text()))
        print(df)
        # Data cleanup

        df[0] = df[0].apply(lambda x: time_string_to_minutes(x))
        for i in range(len(names)):
            new_column_names.update({
                i: names[i][0],
                f'{i}_conf': names[i][0] + '_Confidence',
            })

        df_for_export = df.rename(columns=new_column_names)

        #df_for_export = df.copy()
        try:
            df_for_export[0] = df_for_export[0].interpolate(method='linear')
        except:
            print("couldn't normalize the time")
        df_for_export = convert_to_float(df_for_export)

        print(df_for_export)

        df_for_export.to_csv("output.csv", index=False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VideoOCRApp()
    ex.show()
    sys.exit(app.exec_())