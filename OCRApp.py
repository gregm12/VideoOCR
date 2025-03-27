import cv2
from PyQt5.QtCore import Qt, QPointF, QDir, QFileInfo, QUrl
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QCheckBox, \
    QGraphicsScene, QFileDialog

from ExtractText import extract_text_from_video
from VideoCanvas import VideoCanvas

default_path = ''
default_scale = '2'
default_interval = '30'  

class VideoOCRApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.video_capture = None
        self.frame = None
        self.csv_path = "output.csv"
        self.region_fields = []
        self.b_record_confidence = False

    def initUI(self):
        self.setWindowTitle('Video OCR Tool')
        self.setGeometry(100, 100, 600, 400)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()

        # File selection
        h_layout = QHBoxLayout()
        self.file_path = QLineEdit(default_path)
        self.file_path.setReadOnly(True)
        file_select_btn = QPushButton('Select Video File')
        file_select_btn.clicked.connect(self.select_file)
        h_layout.addWidget(QLabel('Video File Path:'))
        h_layout.addWidget(file_select_btn)
        layout.addLayout(h_layout)
        layout.addWidget(self.file_path)

        # Frame sampling info
        self.scale_factor = QLineEdit(default_scale)
        self.scale_factor.setFixedWidth(30)
        self.interval = QLineEdit(default_interval)
        self.interval.setFixedWidth(30)
        self.start_time = QLineEdit('0')
        self.stop_time = QLineEdit('100')
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel('Preview Scale (1/x):'))
        h_layout.addWidget(self.scale_factor)
        h_layout.addWidget(QLabel('Sample every nth frame:'))
        h_layout.addWidget(self.interval)
        h_layout.addWidget(QLabel('Start Time (s):'))
        h_layout.addWidget(self.start_time)
        h_layout.addWidget(QLabel('Stop Time (s):'))
        h_layout.addWidget(self.stop_time)
        layout.addLayout(h_layout)

        # Immediately update the preview if these change
        self.scale_factor.textChanged.connect(self.update_preview)
        self.start_time.textChanged.connect(self.update_preview)

        # Start OCR button & OCR confidence settings
        h_layout = QHBoxLayout()
        #Threshold
        self.conf_thresh = QLineEdit('0.3')
        self.conf_thresh.setFixedWidth(40)
        h_layout.addWidget(QLabel('OCR Conf. Threshold:'),0)
        h_layout.addWidget(self.conf_thresh,0)
        #Confidence
        self.record_confidence = QCheckBox('Record Conf.')
        h_layout.addWidget(self.record_confidence,0)
        layout.addLayout(h_layout)
        #Contrast
        self.enhance_contrast = QCheckBox('Enhance Contrast')
        h_layout.addWidget(self.enhance_contrast,0)
        layout.addLayout(h_layout)
        #show frames?
        self.show_frames = QCheckBox('Show Video')
        self.show_frames.setCheckState(2) #Set checked by default
        h_layout.addWidget(self.show_frames,0)
        layout.addLayout(h_layout)
        #show ROIs
        self.show_rois = QCheckBox('Show Fields')
        self.show_rois.setCheckState(2) #Set checked by default
        h_layout.addWidget(self.show_rois,0)
        layout.addLayout(h_layout)
        #Start
        start_btn = QPushButton('Start OCR')
        h_layout.addWidget(start_btn,1)
        start_btn.clicked.connect(self.start_processing)

        # Canvas for image display and  region selection
        self.scene = QGraphicsScene()
        self.view = VideoCanvas(self.scene)
        self.view.rectFinished.connect(self.add_region_info)
        layout.addWidget(self.view)

        # Region info container
        self.region_container = QWidget()
        self.region_layout = QVBoxLayout()  # QVBoxLayout to stack horizontal layouts
        self.region_container.setLayout(self.region_layout)
        layout.addWidget(self.region_container)

        '''
        #Open CSV button
        open_csv_btn = QPushButton('Open CSV in Explorer')
        open_csv_btn.clicked.connect(self.open_csv_in_explorer)
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(open_csv_btn)
        layout.addLayout(csv_layout)
        '''

        #finalize i guess
        main_widget.setLayout(layout)

        if len(self.file_path.text()) > 0:
            self.load_video(self.file_path.text())
            

    def update_preview(self):
        if self.video_capture and self.video_capture.isOpened():
            try:
                start_frame = int(float(self.start_time.text()) * self.video_capture.get(cv2.CAP_PROP_FPS))
            except:
                start_frame = 0
                print('Start time error!')
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            ret, frame = self.video_capture.read()
            if ret:
                self.frame = []
                self.frame = frame
                self.resize_canvas_to_video()
                self.display_frame()
        else:
            print("Error opening video file")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_path:
            self.file_path.setText(file_path)
            self.load_video(file_path)

    def load_video(self, path):
        self.video_capture = cv2.VideoCapture(path)
        self.update_preview()

    def resize_canvas_to_video(self):
        if self.frame is not None and len(self.scale_factor.text()) > 0:
            try:
                scale_by = int(self.scale_factor.text())
                height, width, _ = self.frame.shape
                self.view.setFixedSize(width // scale_by, height // scale_by)
                self.view2.setFixedSize(10,10)
            except:
                print('Ah, bad scaling!')

    def display_frame(self):
        if self.frame is not None:
            height, width, channels = self.frame.shape
            bytes_per_line = channels * width
            q_image = QImage(self.frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            pixmap = QPixmap.fromImage(q_image)
            self.scene.clear()
            self.scene.addPixmap(pixmap)
            self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            try:
                self.view.redraw_rectangles(self.region_fields)
            except:
                pass

    def display_roi(self, image, x_loc, y_loc):
        if image is not None:
            height, width = image.shape
            q_image = QImage(image.data, width, height, width, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image)
            patch = self.scene.addPixmap(pixmap)
            patch.setPos(x_loc, y_loc)

    def add_region_info(self, start_point, end_point):
        top_left = QPointF(min(start_point.x(), end_point.x()), min(start_point.y(), end_point.y()))
        bottom_right = QPointF(max(start_point.x(), end_point.x()), max(start_point.y(), end_point.y()))
        x1_field = QLineEdit(f"{top_left.x():.2f}")
        y1_field = QLineEdit(f"{top_left.y():.2f}")
        x2_field = QLineEdit(f"{bottom_right.x():.2f}")
        y2_field = QLineEdit(f"{bottom_right.y():.2f}")
        vert_prog = QCheckBox("Vertical Bar")
        hor_prog = QCheckBox("Horizonal Bar")
        delete = QPushButton("Delete")
        update = QPushButton("Update")
        if self.region_fields: #default name to all subsequent entries.
            name_field = QLineEdit("region"+str(int(len(self.region_fields)/5)))
        else:
            name_field = QLineEdit("timestamp")

        # Create a horizontal layout for each region
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("X1:"))
        h_layout.addWidget(x1_field)
        h_layout.addWidget(QLabel("Y1:"))
        h_layout.addWidget(y1_field)
        h_layout.addWidget(QLabel("X2:"))
        h_layout.addWidget(x2_field)
        h_layout.addWidget(QLabel("Y2:"))
        h_layout.addWidget(y2_field)
        h_layout.addWidget(vert_prog)
        h_layout.addWidget(hor_prog)
        h_layout.addWidget(QLabel("Data:"))
        h_layout.addWidget(name_field)
        h_layout.addWidget(update)
        h_layout.addWidget(delete)
        self.region_layout.addLayout(h_layout)
        
        # Store all widgets and layout for this region in a tuple for easy deletion
        self.region_fields.extend([x1_field, y1_field, x2_field, y2_field, name_field, vert_prog, hor_prog])
        region_items = (h_layout, x1_field, y1_field, x2_field, y2_field, name_field, vert_prog, hor_prog, update, delete)
        
        delete.clicked.connect(lambda: self.delete_region(region_items)) # Delete this region and update frame
        update.clicked.connect(lambda: self.display_frame()) # This should really just be one button for all regions, but eh.
        
    def delete_region(self, items):
        h_layout, *widgets = items
        # Remove widgets from region_fields list
        for widget in widgets[:-2]:  # Exclude delete & update button
            if widget in self.region_fields:
                self.region_fields.remove(widget)
        # Delete widgets
        for widget in widgets:
            widget.deleteLater()
        # Remove layout
        while h_layout.count():
            item = h_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Remove layout from parent
        self.region_layout.removeItem(h_layout)
        # Update the canvas - Really we should just update the rectangles, but this is easier
        self.display_frame()   
            
    def start_processing(self):
        self.regions = []
        self.names = []
        self.vert_flag = []
        self.hor_flag = []
        for i in range(0, len(self.region_fields), 7):  # 7 fields per region: x1, y1, x2, y2, name
            x1 = int(float(self.region_fields[i].text()))
            y1 = int(float(self.region_fields[i + 1].text()))
            x2 = int(float(self.region_fields[i + 2].text()))
            y2 = int(float(self.region_fields[i + 3].text()))
            self.regions.append([x1, y1, x2, y2])
            self.names.append(self.region_fields[i + 4].text())
            self.vert_flag.append(self.region_fields[i + 5].isChecked())
            self.hor_flag.append(self.region_fields[i + 6].isChecked())

        # Do the work
        #df = extract_text_from_video(self.video_capture, self.regions, self.names, int(self.interval.text()), float(self.start_time.text()), float(self.stop_time.text()), self)
        df = extract_text_from_video(self)
        # Data cleanup
        # df[0] = df[0].apply(lambda x: time_string_to_minutes(x))
        try:
            df[0] = df[0].interpolate(method='linear')
        except:
            print("couldn't normalize the time")
        #df_for_export = convert_to_float(df_for_export)
        df.to_csv(self.file_path.text()+".csv", index=False)

    def open_csv_in_explorer(self):
        if hasattr(self, 'file_path') and self.file_path.text():
            csv_path = self.file_path.text()+".csv"
            directory = QDir.toNativeSeparators(QDir.cleanPath(csv_path))
            if QFileInfo(directory).exists():
                QFileInfo(directory).openUrl(QUrl.fromLocalFile(directory))
            else:
                print(f"Directory does not exist: {directory}")
        else:
            print("No CSV file path set.")
