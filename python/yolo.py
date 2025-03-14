import cv2
import time
import sys
import numpy as np
from pushsafer import Client
from datetime import datetime, timedelta
import requests
import base64

# Für Pushsafer
client = Client("6LkoMFc8uZc88t3wCIhH")

# Für WP API
url = 'https://hotel-infos.online/wp-json/wp/v2'
user = "Waleed499"
password = "9cWz IlHt qMtV XK6b sOQ8 Q38L"
creds = user + ':' + password
token = base64.b64encode(creds.encode())
header = {'Authorization': 'Basic ' + token.decode('utf-8')}

def build_model(is_cuda):
    net = cv2.dnn.readNet("config_files/yolov5s.onnx")
    if is_cuda:
        print("Attempty to use CUDA")
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA_FP16)
    else:
        print("Running on CPU")
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return net

INPUT_WIDTH = 640
INPUT_HEIGHT = 640
SCORE_THRESHOLD = 0.2
NMS_THRESHOLD = 0.4
CONFIDENCE_THRESHOLD = 0.4

def detect(image, net):
    blob = cv2.dnn.blobFromImage(image, 1/255.0, (INPUT_WIDTH, INPUT_HEIGHT), swapRB=True, crop=False)
    net.setInput(blob)
    preds = net.forward()
    return preds

# Videoquelle Input
def load_capture():
    capture = cv2.VideoCapture("rtsp://Av1qjDJrF5IP:Yd7XkViTYLYf@192.168.188.115/live0")
    return capture

def load_classes():
    class_list = []
    with open("config_files/classes.txt", "r") as f:
        class_list = [cname.strip() for cname in f.readlines()]
    return class_list

class_list = load_classes()

def wrap_detection(input_image, output_data):
    class_ids = []
    confidences = []
    boxes = []

    rows = output_data.shape[0]

    image_width, image_height, _ = input_image.shape

    x_factor = image_width / INPUT_WIDTH
    y_factor =  image_height / INPUT_HEIGHT

    for r in range(rows):
        row = output_data[r]
        confidence = row[4]
        # Confidence = Wahrscheinlichkeit
        if confidence >= 0.4:

            classes_scores = row[5:]
            _, _, _, max_indx = cv2.minMaxLoc(classes_scores)
            class_id = max_indx[1]
            if (classes_scores[class_id] > .25):

                confidences.append(confidence)

                class_ids.append(class_id)

                x, y, w, h = row[0].item(), row[1].item(), row[2].item(), row[3].item() 
                left = int((x - 0.5 * w) * x_factor)
                top = int((y - 0.5 * h) * y_factor)
                width = int(w * x_factor)
                height = int(h * y_factor)
                box = np.array([left, top, width, height])
                boxes.append(box)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.25, 0.45) 

    result_class_ids = []
    result_confidences = []
    result_boxes = []

    for i in indexes:
        result_confidences.append(confidences[i])
        result_class_ids.append(class_ids[i])
        result_boxes.append(boxes[i])

    return result_class_ids, result_confidences, result_boxes

def format_yolov5(frame):

    row, col, _ = frame.shape
    _max = max(col, row)
    result = np.zeros((_max, _max, 3), np.uint8)
    result[0:row, 0:col] = frame
    return result


colors = [(255, 255, 0), (0, 255, 0), (0, 255, 255), (255, 0, 0)]

is_cuda = len(sys.argv) > 1 and sys.argv[1] == "cuda"

net = build_model(is_cuda)

start = time.time_ns()
frame_count = 0
total_frames = 0
fps = -1

# Parking Slots Array
slots = [0] * 7
slotsCounter = [0] * 7

# Auto Slot Koordinaten definieren
# y ist immer gleich (alle in einer Reihe) --> nur x Koordinaten vergleichen
# slotCoord = [x1, x2]
slotCoord1 = [-10, 190]
slotCoord2 = [110, 310]
slotCoord3 = [220, 470]
slotCoord4 = [350, 630]
slotCoord5 = [530, 760]
slotCoord6 = [700, 950]
slotCoord7 = [850, 1100]
slotCoords = [slotCoord1, slotCoord2, slotCoord3, slotCoord4, slotCoord5, slotCoord6, slotCoord7]

# Mauszeiger Position ausgeben
def printMousePos(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print('Mausklick bei ({}, {})'.format(x, y))

# Sekunden pro Frame
sPF = 2
calcedFPS = 1/sPF

while True:
    capture = load_capture()
    ret, frame = capture.read()
    
    if frame is None:
        print("End of stream")
        break

    # Region Of Interest
    # frame=frame[y1:y2,x1:x2]
    frame=frame[500:680,30:1110]

    inputImage = format_yolov5(frame)
    outs = detect(inputImage, net)

    class_ids, confidences, boxes = wrap_detection(inputImage, outs[0])

    frame_count += 1
    total_frames += 1

    for (classid, confidence, box) in zip(class_ids, confidences, boxes):
        color = colors[int(classid) % len(colors)]
        # box[0] = x1, box[1] = y1, box[2] = width, box[3] = height
        cv2.rectangle(frame, box, color, 2)
        cv2.rectangle(frame, (box[0], box[1] - 20), (box[0] + box[2], box[1]), color, -1)
        cv2.putText(frame, class_list[classid], (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,0))
        for i in range(len(slotCoords)):
            # Box des erkannten Objekt muss zwischen den entsprechenden Slot Koordinaten liegen und 
            # Breite (box[2]) muss größer als 40 sein (um kleine Objekte von weiter weg rauszufiltern)
            if(slotCoords[i][0] <= box[0] and box[0]+box[2] <= slotCoords[i][1] and box[2] > 30):
                #print("Auto in Slot " + str(i+1) + " detektiert!")
                # Pro besetztem Slot 20 Puffer addieren
                if (slotsCounter[i] < 100):
                    slotsCounter[i] = slotsCounter[i] + 20
    
    # automatisch 8 Puffer abziehen von jedem Slot
    # danach direkt prüfen wieviel Puffer pro Slot da ist
    for i in range(len(slotsCounter)):
        if(slotsCounter[i]>0):
            slotsCounter[i] = slotsCounter[i] - 8
        if(slotsCounter[i]<10):
            slots[i]=0
            #resp = client.send_message("Slot " + str(i) + " ist frei geworden.", "Slot " + str(i) + " ist frei", "39569", "1", "4", "2")
            #print(resp)
        if(slotsCounter[i]>=50):
            slots[i]=1

    if frame_count >= 30:
        end = time.time_ns()
        fps = 1000000000 * frame_count / (end - start)
        frame_count = 0
        start = time.time_ns()
    
    if fps > 0:
        fps_label = "FPS: %.2f" % fps
        cv2.putText(frame, fps_label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)


    cv2.imshow("output", frame)
    
    # Auf Mausevents horchen
    cv2.setMouseCallback("output", printMousePos)
    
    print("Parking Slots Belegung - 0 = frei, 1 = belegt \n",slotsCounter,"\n",slots)

    capture.release()

    # Alle 5 Frames -> Update auf WP
    if frame_count%5 == 0:
        content = ' | '.join(map(str, slots))
        # Für WP API
        post = {
            'date': str(datetime.now() - timedelta(hours=2)),
            'title': 'Parkplätze (' + str(datetime.now().strftime("%H:%M:%S") + ' Uhr)'),
            'content': content,
            'status': 'publish'
        }
        r = requests.post(url + '/posts/185/', headers=header, json=post)
        print(r)
    
    # waitKey 1000ms = 1s damit fps runter geht --> CPU Auslastung von 90% auf 30%
    if cv2.waitKey(sPF*1000) > -1:
        print("-----")
        print("finished by user")
        break
    print("|\n|\n|\n|")


print("Total frames: " + str(total_frames))