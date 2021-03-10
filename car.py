import cv2
import numpy as np
import yaml
import datetime

# RGB color in Opencv
COLOR_BLACK = (0, 0, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_WHITE = (255, 255, 255)


# draw the contours of cars in an image via coordinates
def draw_contours(image,
                  coordinates,
                  label,
                  font_color,
                  border_color=COLOR_RED,
                  line_thickness=1,
                  font=cv2.FONT_HERSHEY_SIMPLEX,
                  font_scale=0.5):
    cv2.drawContours(image,
                     [coordinates],
                     contourIdx=-1,
                     color=border_color,
                     thickness=2,
                     lineType=cv2.LINE_8)
    moments = cv2.moments(coordinates)

    center = (int(moments["m10"] / moments["m00"]) - 3,
              int(moments["m01"] / moments["m00"]) + 3)

    cv2.putText(image,
                label,
                center,
                font,
                font_scale,
                font_color,
                line_thickness,
                cv2.LINE_AA)


# draw triangles to record the coordinates of cars
class CoordinatesGenerator:
    # press q to finish the generation of coordinates
    KEY_RESET = ord("r")
    KEY_QUIT = ord("q")

    def __init__(self, image, output, color):
        self.output = output
        self.caption = 'Background'
        self.color = color

        self.image = image.copy()
        self.click_count = 0
        self.ids = 0
        self.coordinates = []

        cv2.namedWindow(self.caption, cv2.WINDOW_GUI_EXPANDED)
        cv2.setMouseCallback(self.caption, self.__mouse_callback)

    def generate(self):
        while True:
            cv2.imshow(self.caption, self.image)
            key = cv2.waitKey(0)

            if key == CoordinatesGenerator.KEY_RESET:
                self.image = self.image.copy()
            elif key == CoordinatesGenerator.KEY_QUIT:
                break
        cv2.destroyWindow(self.caption)

    def __mouse_callback(self, event, x, y, flags, params):

        if event == cv2.EVENT_LBUTTONDOWN:
            self.coordinates.append((x, y))
            self.click_count += 1

            if self.click_count >= 4:
                self.__handle_done()

            elif self.click_count > 1:
                self.__handle_click_progress()

        cv2.imshow(self.caption, self.image)

    def __handle_click_progress(self):
        cv2.line(self.image, self.coordinates[-2], self.coordinates[-1], (255, 0, 0), 1)

    def __handle_done(self):
        cv2.line(self.image,
                 self.coordinates[2],
                 self.coordinates[3],
                 self.color,
                 1)
        cv2.line(self.image,
                 self.coordinates[3],
                 self.coordinates[0],
                 self.color,
                 1)

        self.click_count = 0

        coordinates = np.array(self.coordinates)

        self.output.write("-\n          id: " + str(self.ids) + "\n          coordinates: [" +
                          "[" + str(self.coordinates[0][0]) + "," + str(self.coordinates[0][1]) + "]," +
                          "[" + str(self.coordinates[1][0]) + "," + str(self.coordinates[1][1]) + "]," +
                          "[" + str(self.coordinates[2][0]) + "," + str(self.coordinates[2][1]) + "]," +
                          "[" + str(self.coordinates[3][0]) + "," + str(self.coordinates[3][1]) + "]]\n")

        draw_contours(self.image, coordinates, str(self.ids + 1), COLOR_WHITE)

        for i in range(0, 4):
            self.coordinates.pop()

        self.ids += 1


def status_changed(coordinates_status, index, status):
    return status != coordinates_status[index]


def same_status(coordinates_status, index, status):
    return status == coordinates_status[index]


def _coordinates(p):
    return np.array(p["coordinates"])

def flag():
    global thread_exit
    thread_exit=True

def main(path):
    global thread_exit
    thread_exit=False
    data_file = 'coordinates.yml'
    video_file = path
    cap = cv2.VideoCapture(video_file)
    _, image = cap.read()

    with open(data_file, "r") as data:
        points = yaml.load(data)
        LAPLACIAN = 1.4
        DETECT_DELAY = 1
        video = video_file
        coordinates_data = points
        start_frame = 1
        contours = []
        bounds = []
        Lmask = []

        count = 0
        capture = cv2.VideoCapture(video)
        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        for p in coordinates_data:
            count = count + 1
            coordinates = _coordinates(p)

            rect = cv2.boundingRect(coordinates)

            new_coordinates = coordinates.copy()
            new_coordinates[:, 0] = coordinates[:, 0] - rect[0]
            new_coordinates[:, 1] = coordinates[:, 1] - rect[1]

            contours.append(coordinates)
            bounds.append(rect)

            mask = cv2.drawContours(
                np.zeros((rect[3], rect[2]), dtype=np.uint8),
                [new_coordinates],
                contourIdx=-1,
                color=255,
                thickness=-1,
                lineType=cv2.LINE_8)

            mask = mask == 255
            Lmask.append(mask)

        count_new = count
        statuses = [False] * len(coordinates_data)
        times = [None] * len(coordinates_data)

        while capture.isOpened() and not thread_exit:
            result, frame = capture.read()
            count = count_new
            if frame is None:
                break

            if not result:
                raise

            blurred = cv2.GaussianBlur(frame.copy(), (5, 5), 3)
            grayed = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
            new_frame = frame.copy()

            position_in_seconds = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

            for index, c in enumerate(coordinates_data):
                coordinates = _coordinates(p)

                rect = bounds[index]

                roi_gray = grayed[rect[1]:(rect[1] + rect[3]), rect[0]:(rect[0] + rect[2])]
                laplacian = cv2.Laplacian(roi_gray, cv2.CV_64F)

                coordinates[:, 0] = coordinates[:, 0] - rect[0]
                coordinates[:, 1] = coordinates[:, 1] - rect[1]

                status = np.mean(np.abs(laplacian * Lmask[index])) < LAPLACIAN

                if times[index] is not None and same_status(statuses, index, status):
                    times[index] = None
                    continue

                if times[index] is not None and status_changed(statuses, index, status):
                    if position_in_seconds - times[index] >= DETECT_DELAY:
                        statuses[index] = status
                        times[index] = None
                    continue

                if times[index] is None and status_changed(statuses, index, status):
                    times[index] = position_in_seconds

            for index, p in enumerate(coordinates_data):
                coordinates = _coordinates(p)

                if statuses[index]:
                    color = COLOR_GREEN
                    count = count - 1
                else:
                    color = COLOR_BLUE
                draw_contours(new_frame, coordinates, str(p["id"] + 1), COLOR_WHITE, color)

            text = "Parking Left: {} / {}".format(count_new - count, count_new)
            cv2.putText(new_frame, str(text), (60, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_RED, 2)
            key = cv2.waitKey(1) & 0xff
            yield (new_frame,count_new - count)
            if key == 27:
                break
        yield 1
        capture.release()
        cv2.destroyAllWindows()
