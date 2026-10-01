from ultralytics import YOLO
import cv2
import numpy as np
from collections import deque

from mqtt_client import publish_traffic_data


print("========================================")
print(" INTELLIGENT TRAFFIC CONGESTION SYSTEM")
print("========================================")



VIDEO_PATH = "videos/traffic.mp4"


PROCESS_WIDTH = 1280
PROCESS_HEIGHT = 720


CONFIDENCE = 0.35

MQTT_INTERVAL = 30


MOVEMENT_THRESHOLD = 6




print("Loading YOLO model...")

model = YOLO("yolo11n.pt")

print("YOLO model loaded.")



video = cv2.VideoCapture(VIDEO_PATH)

if not video.isOpened():

    print()
    print("ERROR: Could not open video.")
    print("Check that this file exists:")
    print(VIDEO_PATH)
    print()

    exit()



original_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
original_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = video.get(cv2.CAP_PROP_FPS)

print()
print("Video information:")
print("Original width :", original_width)
print("Original height:", original_height)
print("FPS            :", fps)
print()

print("Video started...")
print("Press Q to quit.")




vehicle_classes = {

    2: "Car",

    3: "Motorcycle",

    5: "Bus",

    7: "Truck"
}




count_history = deque(maxlen=15)




track_history = {}



frame_counter = 0




roi_normalized = np.array(
    [
        (0.39, 0.18),
        (0.88, 0.18),
        (1.00, 1.00),
        (0.32, 1.00)
    ],
    dtype=np.float32
)




while True:

    

    ret, frame = video.read()

    if not ret:

        print("Video finished.")

        break


    frame_counter += 1


   
    frame = cv2.resize(
        frame,
        (PROCESS_WIDTH, PROCESS_HEIGHT),
        interpolation=cv2.INTER_AREA
    )


    height, width = frame.shape[:2]


    roi_points = np.array(
        [
            (
                int(x * width),
                int(y * height)
            )

            for x, y in roi_normalized
        ],
        dtype=np.int32
    )



    results = model.track(

        frame,

        persist=True,

        classes=list(vehicle_classes.keys()),

        conf=CONFIDENCE,

        verbose=False

    )


    # ========================================================
    # 12. VEHICLE COUNTERS
    # ========================================================

    counts = {

        "Car": 0,

        "Motorcycle": 0,

        "Bus": 0,

        "Truck": 0
    }


    # ========================================================
    # 13. MOVEMENT COUNTERS
    # ========================================================

    moving_vehicles = 0

    stopped_vehicles = 0


    # ========================================================
    # 14. PROCESS DETECTIONS
    # ========================================================

    if results[0].boxes is not None:

        for box in results[0].boxes:

            # ------------------------------------------------
            # CLASS
            # ------------------------------------------------

            class_id = int(box.cls[0])

            if class_id not in vehicle_classes:

                continue


            # ------------------------------------------------
            # BOUNDING BOX
            # ------------------------------------------------

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )


            # ------------------------------------------------
            # VEHICLE CENTER
            # ------------------------------------------------

            center_x = int(
                (x1 + x2) / 2
            )

            center_y = int(
                (y1 + y2) / 2
            )


            # ------------------------------------------------
            # CHECK ROI
            # ------------------------------------------------

            inside_roi = cv2.pointPolygonTest(

                roi_points,

                (center_x, center_y),

                False
            )


            # Vehicle outside the road ROI
            if inside_roi < 0:

                continue


            # ------------------------------------------------
            # VEHICLE TYPE
            # ------------------------------------------------

            vehicle_name = vehicle_classes[class_id]

            counts[vehicle_name] += 1


            # ------------------------------------------------
            # TRACKING ID
            # ------------------------------------------------

            if box.id is None:

                continue


            track_id = int(box.id[0])


            # ------------------------------------------------
            # CREATE TRACK HISTORY
            # ------------------------------------------------

            if track_id not in track_history:

                track_history[track_id] = deque(
                    maxlen=10
                )


            # Store current center
            track_history[track_id].append(
                (center_x, center_y)
            )


            history = track_history[track_id]


            # ------------------------------------------------
            # MOVEMENT DETECTION
            # ------------------------------------------------

            if len(history) >= 5:

                old_x, old_y = history[-5]

                new_x, new_y = history[-1]


                # Calculate pixel movement
                distance = np.sqrt(

                    (new_x - old_x) ** 2 +

                    (new_y - old_y) ** 2
                )


                if distance >= MOVEMENT_THRESHOLD:

                    moving_vehicles += 1

                else:

                    stopped_vehicles += 1


    # ========================================================
    # 15. TOTAL VEHICLES
    # ========================================================

    total_vehicles = sum(
        counts.values()
    )


    # ========================================================
    # 16. ANALYZED VEHICLES
    # ========================================================

    analyzed_vehicles = (

        moving_vehicles +

        stopped_vehicles
    )


    # ========================================================
    # 17. STOPPED VEHICLE PERCENTAGE
    # ========================================================

    if analyzed_vehicles > 0:

        stopped_percentage = (

            stopped_vehicles /

            analyzed_vehicles

        ) * 100

    else:

        stopped_percentage = 0


    # ========================================================
    # 18. SMOOTH VEHICLE COUNT
    # ========================================================

    count_history.append(
        total_vehicles
    )


    average_vehicles = (

        sum(count_history) /

        len(count_history)
    )


    # ========================================================
    # 19. CONGESTION CLASSIFICATION
    # ========================================================
    #
    # These thresholds are prototype thresholds.
    #
    # They can later be calibrated using your actual traffic
    # video and project evaluation results.
    #
    # ========================================================

    if (

        average_vehicles >= 20

        and

        stopped_percentage >= 30

    ):

        congestion = "HIGH"


    elif (

        average_vehicles >= 20

        or

        stopped_percentage >= 45

    ):

        congestion = "HIGH"


    elif (

        average_vehicles >= 10

        or

        stopped_percentage >= 20

    ):

        congestion = "MEDIUM"


    else:

        congestion = "LOW"


    # ========================================================
    # 20. CREATE YOLO ANNOTATED FRAME
    # ========================================================

    annotated_frame = results[0].plot()


    # ========================================================
    # 21. DRAW ROAD ROI
    # ========================================================

    cv2.polylines(

        annotated_frame,

        [roi_points],

        True,

        (255, 0, 0),

        3
    )


    # ========================================================
    # 22. ROI LABEL
    # ========================================================

    cv2.putText(

        annotated_frame,

        "ROAD ROI",

        (30, 40),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.8,

        (255, 0, 0),

        2
    )


    # ========================================================
    # 23. DISPLAY TRACKING IDs
    # ========================================================
    #
    # We draw IDs on annotated_frame instead of the original
    # frame so they actually appear in the displayed video.
    #
    # ========================================================

    if results[0].boxes is not None:

        for box in results[0].boxes:

            if box.id is None:

                continue


            class_id = int(box.cls[0])

            if class_id not in vehicle_classes:

                continue


            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )


            center_x = int(
                (x1 + x2) / 2
            )

            center_y = int(
                (y1 + y2) / 2
            )


            inside_roi = cv2.pointPolygonTest(

                roi_points,

                (center_x, center_y),

                False
            )


            if inside_roi < 0:

                continue


            track_id = int(box.id[0])


            cv2.putText(

                annotated_frame,

                f"ID:{track_id}",

                (x1, max(y1 - 8, 15)),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.5,

                (255, 255, 0),

                2
            )


    # ========================================================
    # 24. DISPLAY VEHICLE COUNTS
    # ========================================================

    cv2.putText(

        annotated_frame,

        f"Cars: {counts['Car']}",

        (20, 80),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.7,

        (0, 255, 0),

        2
    )


    cv2.putText(

        annotated_frame,

        f"Motorcycles: {counts['Motorcycle']}",

        (20, 110),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.7,

        (0, 255, 0),

        2
    )


    cv2.putText(

        annotated_frame,

        f"Buses: {counts['Bus']}",

        (20, 140),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.7,

        (0, 255, 0),

        2
    )


    cv2.putText(

        annotated_frame,

        f"Trucks: {counts['Truck']}",

        (20, 170),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.7,

        (0, 255, 0),

        2
    )


    # ========================================================
    # 25. TOTAL VEHICLES
    # ========================================================

    cv2.putText(

        annotated_frame,

        f"VEHICLES: {total_vehicles}",

        (20, 210),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.8,

        (0, 255, 255),

        2
    )


    # ========================================================
    # 26. MOVING VEHICLES
    # ========================================================

    cv2.putText(

        annotated_frame,

        f"MOVING: {moving_vehicles}",

        (20, 245),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.75,

        (0, 255, 0),

        2
    )


    # ========================================================
    # 27. STOPPED VEHICLES
    # ========================================================

    cv2.putText(

        annotated_frame,

        f"STOPPED: {stopped_vehicles}",

        (20, 280),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.75,

        (0, 0, 255),

        2
    )


    # ========================================================
    # 28. STOPPED PERCENTAGE
    # ========================================================

    cv2.putText(

        annotated_frame,

        f"STOPPED %: {stopped_percentage:.1f}%",

        (20, 315),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.75,

        (0, 0, 255),

        2
    )


    # ========================================================
    # 29. CONGESTION STATUS
    # ========================================================

    if congestion == "HIGH":

        congestion_color = (0, 0, 255)

    elif congestion == "MEDIUM":

        congestion_color = (0, 165, 255)

    else:

        congestion_color = (0, 255, 0)


    cv2.putText(

        annotated_frame,

        f"CONGESTION: {congestion}",

        (20, 355),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.9,

        congestion_color,

        3
    )


    # ========================================================
    # 30. MQTT PUBLISH
    # ========================================================

    if frame_counter % MQTT_INTERVAL == 0:

        publish_traffic_data(

            vehicles=total_vehicles,

            moving=moving_vehicles,

            stopped=stopped_vehicles,

            stopped_percentage=stopped_percentage,

            congestion=congestion
        )


    # ========================================================
    # 31. SHOW VIDEO
    # ========================================================

    cv2.imshow(

        "Intelligent Traffic Congestion Detection",

        annotated_frame
    )


    # ========================================================
    # 32. QUIT
    # ========================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# ============================================================
# 33. CLEANUP
# ============================================================

video.release()

cv2.destroyAllWindows()

print()
print("Program stopped.")