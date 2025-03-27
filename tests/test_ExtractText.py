import sys
from unittest import TestCase
from ExtractText import extract_text_from_video
from OCRApp import VideoOCRApp
from PyQt5.QtWidgets import QApplication


class Test(TestCase):
    def test_extract_text_from_video(self):
        # Initialize QApplication
        app = QApplication(sys.argv)

        # Set up the GUI
        ex = VideoOCRApp()
        ex.show()

        # Configure and load video
        ex.load_video("C:/Users/gregm/Videos/StarshipFT7/StarshipFT7.mp4")
        ex.hor_flag = [True]
        ex.vert_flag = [False]

        # Run the text extraction
        df = extract_text_from_video(
            gui_ref=ex,
            video_capture=None,
            roi_coordinates=[[176, 658, 348, 680]],
            roi_names=["HorBar"],
            time_interval=30,
            start_time=20,
            end_time=100,
            rec_conf=False,
            conf_thresh=False,
            enhance_contrast=False,
            show_frames=True,
            show_rois=True
        )
        print(df)

        # Execute the app and get the exit code
        exit_code = app.exec_()

        # Assert the exit code is 0 (success)
        self.assertEqual(exit_code, 0, f"GUI did not close successfully, exit code was {exit_code}")