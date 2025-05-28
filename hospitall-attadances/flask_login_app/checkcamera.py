import cv2
import time

cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("❌ Camera not accessible")
    exit()

time.sleep(1)  # let camera warm up

for i in range(10):
    ret, frame = cam.read()
    print(f"Frame {i}: ret = {ret}, frame is None = {frame is None}")
    if ret:
        cv2.imshow("Webcam", frame)
        cv2.waitKey(500)

cam.release()
cv2.destroyAllWindows()
