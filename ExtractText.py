import re
import cv2
import easyocr
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication

def extract_text_from_video(gui_ref=None,
                            video_capture=None,
                            roi_coordinates=None,
                            roi_names=None,
                            time_interval=None,
                            start_time=None,
                            end_time=None,
                            rec_conf=None,
                            conf_thresh = None,
                            enhance_contrast = None,
                            show_frames = None,
                            show_rois = None
                            ):

  # Use attributes from 'gui_ref' if individual parameters are not provided
  if gui_ref is not None:
    video_capture = video_capture if video_capture is not None else gui_ref.video_capture
    roi_coordinates = roi_coordinates if roi_coordinates is not None else gui_ref.regions
    roi_names = roi_names if roi_names is not None else gui_ref.names
    time_interval = time_interval if time_interval is not None else int(gui_ref.interval.text())
    start_time = start_time if start_time is not None else float(gui_ref.start_time.text())
    end_time = end_time if end_time is not None else float(gui_ref.stop_time.text())
    rec_conf = rec_conf if rec_conf is not None else gui_ref.record_confidence.isChecked()
    conf_thresh = conf_thresh if conf_thresh is not None else float(gui_ref.conf_thresh.text())
    enhance_contrast = enhance_contrast if enhance_contrast is not None else gui_ref.enhance_contrast.isChecked()
    show_frames = show_frames if show_frames is not None else gui_ref.show_frames.isChecked()
    show_rois = show_rois if show_rois is not None else gui_ref.show_rois.isChecked()
  else:
    # Ensure all parameters are provided if 'self' isn't passed
    assert all(param is not None for param in
               [video_capture, roi_coordinates, roi_names, time_interval, start_time, end_time,
                gui_ref]), "All parameters must be provided if 'gui_ref' is not given."

  reader = easyocr.Reader(['en'])
  fps = video_capture.get(cv2.CAP_PROP_FPS)
  extraction = 0
  df = pd.DataFrame()
  bright_thresh = 128

  # Define a sharpening kernel
  sharpening_kernel = -(1 / 256.0) * np.array([[1, 4, 6, 4, 1],
                                   [4, 16, 24, 16, 4],
                                   [6, 24, -476, 24, 6],
                                   [4, 16, 24, 16, 4],
                                   [1, 4, 6, 4, 1]])
  alpha = 1.1  # Contrast control (1.0 - 3.0)
  beta = -40 # Brightness control (-100 - 100)

  # Calculate starting and ending frame numbers
  start_frame = int(start_time * fps)

  # Set video capture to starting frame
  video_capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

  while video_capture.isOpened() and (((extraction)*time_interval) / fps) < (end_time - start_time):
    ret, frame = video_capture.read()
    if not ret:
      break
    df.at[extraction, 'time'] = extraction * time_interval / fps #Relative Timestamp

    if show_frames:
      gui_ref.frame = frame
      gui_ref.display_frame()
      QApplication.processEvents()

    for i, (x1, y1, x2, y2) in enumerate(roi_coordinates):
      col_name = roi_names[i]
      df.at[extraction, col_name] = None

      #Parse vertical progres bars
      if gui_ref.vert_flag[i]:
        ...
      #Parse Horizontal progress bars
      elif gui_ref.hor_flag[i]:

        #Lets get the middle 1/3
        height = roi.shape[0]  # Original height
        mid_height = int(height // 10)
        if mid_height < 1:
          mid_height = 1
        elif mid_height > 6:
          mid_height = 6
        mid = y1 + abs(y2 - y1) // 2
        mid_top = mid - mid_height
        mid_bot = mid + mid_height

        roi = cv2.cvtColor(frame[mid_top:mid_bot, x1:x2], cv2.COLOR_BGR2GRAY)
        averaged_1d = np.mean(roi, axis=0).astype(np.uint8)
        # Compute the gradient (absolute differences between adjacent pixels)
        gradients = np.abs(np.diff(averaged_1d))  # Shape: (width-1,)
        # Find the index of the strongest gradient
        strongest_gradient_idx = np.argmax(gradients)  # Index of max gradient
        top_3_indices = np.argsort(gradients)[-3:][::-1]  # Top 3, descending order

        averaged = np.tile(averaged_1d[np.newaxis, :], (mid, 1))
        averaged[:, strongest_gradient_idx-1:strongest_gradient_idx+1] = 255  # Mark with a white line
        #for idx in top_3_indices:
        #  averaged[:, idx:idx + 2] = 255  # Mark the transition with a white line
        #edges = cv2.Canny(roi, 0, 60)

        df.at[extraction, col_name] = strongest_gradient_idx/len(gradients)
        if show_rois:
          show_roi_in_GUI(averaged, gui_ref, x1, mid_top)
      #Parse Text
      else:
        roi = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        if enhance_contrast:
          # Get the segment of the image we care about for this ROI, make gray, adjust contrast, sharpen
          roi = cv2.filter2D(cv2.convertScaleAbs(roi, alpha=alpha, beta=beta), -1, sharpening_kernel)

        if show_rois:
          show_roi_in_GUI(roi, gui_ref, x1, y1)

        text = reader.readtext(roi, detail=1)
        if text:
          if rec_conf:
            df.at[extraction, f'{col_name}_conf'] = float(text[0][2])
          if text[0][2] > conf_thresh:
            extracted_text = ''.join(text[0][1])
            if 'timestamp' in col_name:
              extracted_text = extracted_text.replace(".",":").replace('::',':')
            extracted_text = extracted_text.lower().replace("o", "0").replace('i','1').replace('s','5').replace('a','4').replace(',','')
            extracted_text = re.sub(r'[^0-9:.]', '', extracted_text)
            print('Found {text} with confidence {conf}'.format(text=extracted_text,conf=text[0][2]))
            df.at[extraction, col_name] = extracted_text
          else:
            print('No text detected')
    extraction += 1

    # Set our new open frame time
    new_frame = start_frame + (int(extraction * time_interval))
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, new_frame)

  return df


def show_roi_in_GUI(image, gui_ref, x1, y1):
  gui_ref.display_roi(image, x1, y1)
  QApplication.processEvents()
