import cv2
import numpy as np


def build_filters():
    filters = []
    ksize = 31
    theta = [cv2.getGaborKernel((ksize, ksize), 0.3, theta, 9.0, 0.6, 50, ktype=cv2.CV_32F)
             for theta in np.arange(0, np.pi, np.pi / 16)]
    kern = theta[-1]
    kern /= 1.5 * kern.sum()
    filters.append(kern)
    return filters


def process(img, filters):
    accum = np.zeros_like(img)
    for kern in filters:
        fimg = cv2.filter2D(img, cv2.CV_8UC3, kern)
        np.maximum(accum, fimg, accum)
    return accum


def main():
    net = cv2.dnn.readNet("YOLOFI2.weights", "YOLOFI.cfg")
    cap = cv2.VideoCapture("test.mp4")
    with open("obj.names", "r")as f:
        layers_names = net.getLayerNames()
        outputlayers = [layers_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
        frame_id = 0
        image_counter = 0

        while True:
            _, frame = cap.read()
            frame_id += 1
            beltdetected = False
            height, width, channels = frame.shape

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.equalizeHist(frame)
            first_clahe = cv2.createCLAHE(clipLimit=250.0, tileGridSize=(8, 8))
            frame = first_clahe.apply(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            frame = cv2.convertScaleAbs(frame, alpha=1, beta=-40)
            cv2.fastNlMeansDenoising(frame, frame, 1, 7, 21)

            second_clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
            R, G, B = cv2.split(frame)

            output1_R = second_clahe.apply(R)
            output1_G = second_clahe.apply(G)
            output1_B = second_clahe.apply(B)

            frame = cv2.merge((output1_R, output1_G, output1_B))

            cv2.fastNlMeansDenoising(frame, frame, 3, 5, 11)

            filters = build_filters()
            frame = process(frame, filters)

            blob = cv2.dnn.blobFromImage(frame, 0.00392, (480, 480), (0, 0, 0), True, crop=False)
            net.setInput(blob)
            outs = net.forward(outputlayers)

            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    if confidence > 0.2:
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        if class_id == 0:
                            beltdetected = True

            print(image_counter, ' ', beltdetected)
            image_counter += 1
            cv2.imshow("Image", frame)
            key = cv2.waitKey(1)
            if key == 27:
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
