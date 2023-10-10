'''
DEVELOPER: Mohamad Issam Sayyaf
EMAIL: issamsayyaf97@gmail.com
'''

'''
Sure, here's a step-by-step explanation of the code:

Import necessary modules:

cv2: OpenCV for image and video processing.
dlib: A toolkit for machine learning and computer vision.
numpy: A library for the Python programming language, adding support for large, multi-dimensional arrays and matrices, along with a large collection of high-level mathematical functions.
face_recognition: A library for face recognition.
threading: A library to implement threading.
Initialize the face detector, facial landmark predictor, and face recognition model:

dlib.get_frontal_face_detector(): A pre-trained face detector provided by dlib.
dlib.shape_predictor(): A pre-trained model that predicts the positions of 68 (x, y)-coordinates that map to facial structures on the face. The coordinates are part of the 68 point iBUG 300-W dataset.
dlib.face_recognition_model_v1(): A pre-trained face recognition model provided by dlib.
Load known faces:

face_recognition.load_image_file(): Load an image file (.jpg, .png, etc.) into a numpy array.
face_recognition.face_locations(): Given an image, return the bounding box locations of all faces in the image.
face_recognition.face_encodings(): Given a list of face images, each as a numpy array, return an array of 128-dimensional face encodings (one for each face in the image list).
Initialize the video capture object cap.

Initialize the decision threshold at 0.6. This threshold will be used to decide if the detected face is close enough to any known face encodings.

Initialize frame and frame_to_display variables to None, and initialize a threading lock object lock. These will be used to synchronize the main thread (which reads frames from the video and displays them) and the face recognition thread (which processes the frames to detect and recognize faces).

Define the face_recognition_thread() function:

This function runs in a loop as long as the program is running.
If frame is not None, it locks the thread, converts the frame to grayscale, and detects faces in the frame.
For each face, it predicts the facial landmarks, aligns the face based on these landmarks, computes the face encoding, and compares this encoding with the known face encodings.
It then finds the best match among the known faces, and if the distance to this face encoding is less than the decision threshold, it draws a rectangle around the face and labels it with the name of the best match. Otherwise, it labels the face as 'Unknown'.
Finally, it updates frame_to_display with the processed frame.
Start the face recognition thread.

The main loop of the program:

In each iteration, it reads a frame from the video. If reading fails (ret is False), it breaks the loop.
If frame_to_display is not None, it displays this frame in an OpenCV window.
If the 'q' key is pressed, it breaks the loop.
After the main loop, it releases the video capture and closes all OpenCV windows.

'''


import cv2
import dlib
import numpy as np
import face_recognition
import threading
import multiprocessing


# Unknown Counter
unknow_counter = 0

# Load the face detector, the pre-trained facial landmark predictor, and the face recognition model
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')
face_rec = dlib.face_recognition_model_v1('dlib_face_recognition_resnet_model_v1.dat')

# Load known faces
# Load the JPEG image
image = face_recognition.load_image_file("issam.jpg")

# Find the face locations in the image
face_locations = face_recognition.face_locations(image)

# Generate the face encodings
face_encodings = face_recognition.face_encodings(image, face_locations)
known_faces = {'issam':face_encodings[0]} # This should be filled with people's names and their face encodings

# Load the video capture
cap = cv2.VideoCapture('udp://10.0.0.1:6001')

# Add decision threshold
decision_threshold = 0.6

frame_number = 0
process_every_n_frames = 5  # Change this to process every nth frame

frame = None
frame_to_display = None
lock = threading.Lock()

def face_recognition_thread():
    global frame, frame_to_display, lock
    while True:
        if frame is not None:
            # Lock the thread while processing the frame
            with lock:
                # Convert the frame to grayscale for face detection
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Detect faces in the frame
                faces = detector(gray)

                for face in faces:
                    # Get the landmarks
                    landmarks = predictor(gray, face)

                    # Perform face alignment
                    aligned_face = dlib.get_face_chip(frame, landmarks)

                    # Get the face encoding
                    face_encoding = face_rec.compute_face_descriptor(aligned_face)

                    # Compare the face encoding with known faces
                    matches = {name: np.linalg.norm(face_encoding - encoding) for name, encoding in known_faces.items()}

                    # Find the best match and draw a rectangle around the face
                    best_match = min(matches, key=matches.get)
                    
                    # Add decision threshold
                    if matches[best_match] < decision_threshold:
                        x, y, w, h = face.left(), face.top(), face.width(), face.height()
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.putText(frame, best_match, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
                    else:
                        cv2.putText(frame, 'Unknown', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
                        unknow_counter = unknow_counter + 1

                # Update the frame to display
                frame_to_display = frame

# Start the face recognition thread
#threading.Thread(target=face_recognition_thread, daemon=True).start()
x = multiprocessing.Process(target=face_recognition_thread, daemon=True)
x.start()
#x.join()

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Display the frame with detected faces
    if frame_to_display is not None:
        cv2.imshow('Face Recognition', frame_to_display)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
    # Check if the CAP_PROP_BITRATE property is supported by the video capture backend
    '''if cv2.CAP_PROP_BITRATE in [cv2.CAP_PROP_FFMPEG_BITRATE, cv2.CAP_PROP_GSTREAMER_BITRATE]:
        # Get the received bitrate from the video capture
        received_bitrate = cap.get(cv2.CAP_PROP_BITRATE)
        print("Received Bitrate:", received_bitrate)
    else:
        print("Bitrate information is not supported by the video capture backend.")'''
# Release the video capture and close the display window
cap.release()
cv2.destroyAllWindows()


