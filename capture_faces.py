import cv2
import numpy as np
import os
import shutil
import face_recognition
from scipy.spatial import distance

# ---------------------------
# Parameters
# ---------------------------
DATASET_DIR = "dataset"
ENCODINGS_DIR = "encodings"
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(ENCODINGS_DIR, exist_ok=True)

EYE_AR_THRESH = 0.23  # Eye Aspect Ratio threshold
EYE_AR_CONSEC_FRAMES = 3  # Frames to confirm blink


# ---------------------------
# Eye Aspect Ratio
# ---------------------------
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)


# ---------------------------
# Liveness Detection (Blink Detection using OpenCV)
# ---------------------------
def is_live_face():
    print("[INFO] Starting camera for liveness detection...")
    cap = cv2.VideoCapture(0)

    # Haar cascade for eye detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

    blink_counter = 0
    total_blinks = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to grab frame.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            roi_gray = gray[y:y + h, x:x + w]
            roi_color = frame[y:y + h, x:x + w]

            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) >= 2:  # Both eyes detected
                blink_counter = 0
            else:
                blink_counter += 1

            if blink_counter >= EYE_AR_CONSEC_FRAMES:
                total_blinks += 1
                blink_counter = 0

            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.putText(frame, f"Blinks: {total_blinks}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("Liveness Detection", frame)

        if total_blinks >= 2:
            print("[INFO] Liveness confirmed.")
            cap.release()
            cv2.destroyAllWindows()
            return True

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return False


# ---------------------------
# Face Encoding & Save
# ---------------------------
def capture_and_encode(username: str):
    print(f"[INFO] Starting capture for {username}...")

    if not is_live_face():
        return "⚠️ Liveness check failed! Spoof detected."

    print("[INFO] Capturing face image...")
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return "❌ Failed to capture image."

    temp_image_path = f"{username.lower()}_temp.jpg"
    cv2.imwrite(temp_image_path, frame)

    # Get face encodings
    image = face_recognition.load_image_file(temp_image_path)
    face_locations = face_recognition.face_locations(image)
    face_encodings = face_recognition.face_encodings(image, face_locations)

    if len(face_encodings) == 0:
        os.remove(temp_image_path)
        return "❌ No face detected in the image."

    encoding = face_encodings[0]

    final_image_path = os.path.join(DATASET_DIR, f"{username.lower()}.jpg")
    shutil.move(temp_image_path, final_image_path)

    encoding_path = os.path.join(ENCODINGS_DIR, f"{username.lower()}.npy")
    np.save(encoding_path, encoding)

    return f"✅ Encoding saved for {username} (Live face detected)."


# ---------------------------
# Run Script
# ---------------------------
if __name__ == "__main__":
    username = input("Enter username: ")
    result = capture_and_encode(username)
    print(result)
