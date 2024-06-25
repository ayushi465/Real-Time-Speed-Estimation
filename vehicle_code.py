import cv2
import numpy as np
import sys
import os
from datetime import datetime

# Constants
SPEED_LIMIT = 60  # Speed limit in some units per second
FRAME_RATE = 30  # Assuming a frame rate of 30 frames per second

# Helper functions
def calculate_speed(position1, position2, frame_rate):
    # Calculate the Euclidean distance between two points
    distance = np.linalg.norm(np.array(position1) - np.array(position2))
    speed = distance * frame_rate  # speed = distance per frame * frames per second
    return speed

def log_speeding_vehicle(vehicle_id, label, speed):
    with open('speeding_vehicles.log', 'a') as log_file:
        log_file.write(f"{datetime.now()} - Vehicle ID: {vehicle_id}, Type: {label}, Speed: {speed:.2f}\n")

# Load YOLO
net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]

# Full path to the video file
video_path = os.path.join(os.getcwd(), 'road_traffic.mp4')

# Initialize video capture
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: Could not open video {video_path}")
    sys.exit()

# Initialize vehicle tracking
vehicle_positions = {}  # To store the last known position of each vehicle
vehicle_id = 0  # Unique identifier for each vehicle

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")
        break

    # Convert frame to blob
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    # Initialize lists for detected bounding boxes, confidences, and class IDs
    boxes = []
    confidences = []
    class_ids = []

    # Iterate through the detections
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:
                # Object detected
                center_x = int(detection[0] * frame.shape[1])
                center_y = int(detection[1] * frame.shape[0])
                w = int(detection[2] * frame.shape[1])
                h = int(detection[3] * frame.shape[0])
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # Apply non-maxima suppression
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

    # Define relevant classes to track (cars, buses, people)
    relevant_classes = ['car', 'bus', 'person']

    # Draw bounding boxes and track vehicle speeds
    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            label = str(classes[class_ids[i]])
            confidence = confidences[i]

            if label in relevant_classes:  # Only track relevant classes
                # Calculate the current position of the vehicle
                current_position = (x + w // 2, y + h // 2)

                # Assign a new ID if this is a new vehicle
                if vehicle_id not in vehicle_positions:
                    vehicle_positions[vehicle_id] = current_position
                    color = (0, 255, 0)  # Initial color for normal vehicles
                else:
                    # Calculate speed
                    previous_position = vehicle_positions[vehicle_id]
                    speed = calculate_speed(previous_position, current_position, FRAME_RATE)

                    # Update position
                    vehicle_positions[vehicle_id] = current_position

                    # Highlight and log if speed exceeds the limit
                    if speed > SPEED_LIMIT:
                        color = (0, 0, 255)  # Red color for speeding vehicles
                        log_speeding_vehicle(vehicle_id, label, speed)
                    else:
                        color = (0, 255, 0)  # Green color for normal vehicles

                    vehicle_id += 1

                # Draw the bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, f"{label} {confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Display the frame with detections
    cv2.imshow('video', frame)

    # Wait for Esc key to stop
    if cv2.waitKey(1) == 27:  # 27 is the Esc key
        break

# Release the video capture and destroy all OpenCV windows
cap.release()
cv2.destroyAllWindows()
