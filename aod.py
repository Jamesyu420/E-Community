import numpy as np
import cv2
import datetime
import yagmail
import threading

thread_exit = False
class email_Thread(threading.Thread):
    def __init__(self, email_id,img):
        super(email_Thread, self).__init__()
        self.id = email_id
        self.img=img

    def run(self):
        yag = yagmail.SMTP( user="E_community@126.com", password="RBDKKPTULOUARLFK", host='smtp.126.com')
        contents = ['消防通道口出现了障碍物，请速去查看~']
        yag.send(self.id, '智能小区检测警报', contents,[self.img])
        yag.close()
def getForegroundMask(frame, background, th):
    # reduce noise in the frame
    frame = cv2.blur(frame, (5, 5))
    # get the absolute difference between the foreground and the background
    fgmask = cv2.absdiff(frame, background)
    # convert foreground mask to gray
    fgmask = cv2.cvtColor(fgmask, cv2.COLOR_BGR2GRAY)
    # apply threshold on the foreground mask
    _, fgmask = cv2.threshold(fgmask, th, 255, cv2.THRESH_BINARY)
    # apply morphology on the foreground mask to connect the edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, kernel)
    return fgmask


def MOGinit(history, T, nMixtures):
    # initialize a background subtraction using GMM
    fgbg = cv2.createBackgroundSubtractorMOG2(history)
    fgbg.setBackgroundRatio(T)
    fgbg.setNMixtures(nMixtures)
    return fgbg


def extract_objs(im, min_w=15, min_h=15, max_w=500, max_h=500):
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))
    arr = cv2.dilate(im, kernel, iterations=2)
    arr = np.array(arr, dtype=np.uint8)
    _, th = cv2.threshold(arr, 127, 255, 0)
    (contours, hierarchy) = cv2.findContours(th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    objs = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if (w >= min_w) & (w < max_w) & (h >= min_h) & (h < max_h):
            objs.append([x, y, w, h, 1])
        else:
            print(w, h)
    return objs


# this function returns static object map without pre-founded objects
def clean_map(m, o):
    result = np.copy(m)
    for i in range(0, len(o)):
        x, y = o[i][0], o[i][1]
        w, h = o[i][2], o[i][3]
        result[y:y + h, x:x + w] = 0
    return result

def flag():
    global thread_exit
    thread_exit=True

def main(path,email):
    thread_exit=False
    # it requires a static input video as a background
    cap = cv2.VideoCapture(path)



    # background modeling
    _, BG = cap.read()

    # setting up a kernal for morphology
    kernal = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    # MoG settled for long background model
    fgbgl = MOGinit(300, 0.4, 3)
    # MoG settled for short background model
    fgbgs = MOGinit(300, 0.4, 3)

    longBackgroundInterval = 20
    shortBackgroundINterval = 1

    counter_longfg = longBackgroundInterval  # counter for longbackgroundInterval
    counter_shortfg = shortBackgroundINterval  # counter for shortBackgroundInteral

    # static obj likelihood
    L = np.zeros(np.shape(cap.read()[1])[0:2])

    static_obj_map = np.zeros(np.shape(cap.read()[1])[0:2])

    # static obj likelihood constants
    k, maxe, thh = 7, 2000, 800

    # obj-extraction constants
    slidewindowtime = 0
    minwindowsize = 70
    stepsize = 15
    static_objs = []
    th_sp = 20 ** 2  # a th for number of static pixels
    flag = False
    count = 0

    while True:
        ret, frame = cap.read()
        if ret == 0:
            break
        if counter_longfg == longBackgroundInterval:
            frameL = np.copy(frame)
            fgbgl.apply(frameL)
            BL = fgbgl.getBackgroundImage(frameL)
            counter_longfg = 0
        else:
            counter_longfg += 1

        if counter_shortfg == shortBackgroundINterval:
            frameS = np.copy(frame)
            fgbgs.apply(frameS)
            BS = fgbgs.getBackgroundImage(frameS)
            counter_shortfg = 0
        else:
            counter_shortfg += 1

        # update short and long foregrounds
        FL = getForegroundMask(frame, BL, 70)
        FS = getForegroundMask(frame, BS, 70)
        FG = getForegroundMask(frame, BG, 70)

        # detect static pixels and apply morphology on it
        static = FL & cv2.bitwise_not(FS) & FG
        static = cv2.morphologyEx(static, cv2.MORPH_CLOSE, kernal)
        # detect non-static objects and apply morphology on it
        not_static = FS | cv2.bitwise_not(FL)
        not_static = cv2.morphologyEx(not_static, cv2.MORPH_CLOSE, kernal)

        # update static object likelihood
        L = (static == 255) * (L + 1) + ((static == 255) ^ 1) * L
        L = (not_static == 255) * (L - k) + ((not_static == 255) ^ 1) * L
        L[L > maxe] = maxe
        L[L < 0] = 0

        # update static object map
        static_obj_map[L >= thh] = 254
        static_obj_map[L < thh] = 0

        # if number of nonzero elements in static obj map greater than min window size squared there
        # could be a potential static obj, we will need to wait 200 frame to be passed if the condition
        # still true we will call "extract_objs" function and try to find these objects.
        if np.count_nonzero(clean_map(static_obj_map, static_objs)) > th_sp:
            if slidewindowtime > 200:
                new_objs = extract_objs(clean_map(static_obj_map, static_objs))
                # if we get new object, first we make sure that they are not duplicated ones and then
                # put the unique static objects in "static_objs" variable
                if new_objs:
                    for i in range(0, len(new_objs)):
                        if new_objs[i] not in static_objs:
                            static_objs.append(new_objs[i])
                slidewindowtime = 0
            else:
                slidewindowtime += 1
        else:
            slidewindowtime = 0 if slidewindowtime < 0 else slidewindowtime - 1
        # draw rectangle around static obj/s
        c = 0
        for i in range(0, len(static_objs)):
            if static_objs[i - c]:
                x, y = static_objs[i - c][0], static_objs[i - c][1]
                w, h = static_objs[i - c][2], static_objs[i - c][3]
                # check if the current static obj still in the scene 
                if not flag:
                    now_time = str(datetime.datetime.now().year) + '_' + str(datetime.datetime.now().month) + '_' + str(datetime.datetime.now().day) + '_' + str(datetime.datetime.now().hour) + '_'+ str(datetime.datetime.now().minute) + '_' + str(datetime.datetime.now().second)
                    cv2.imwrite(now_time + ".png", frame[y:y + h, x:x + w])
                    send = email_Thread(email,now_time + ".png")
                    send.start()
                    flag = True
                if np.count_nonzero(static_obj_map[y:y + h, x:x + w]) < w * h * .1:
                    static_objs.remove(static_objs[i - c])
                    flag = False
                    c += 1
                    count += 1
                    continue
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)



        yield (frame,int(count / 2))
        key = cv2.waitKey(1) & 0xff
        if key == 27:
            break
    yield 1
    cap.release()
    cv2.destroyAllWindows()