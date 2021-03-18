from detect.tracker import CentroidTracker
from detect.track_object import TrackableObject
from imutils.video import VideoStream
from imutils.video import FPS
import numpy as np
import datetime
import argparse
import imutils
import time
import dlib
import cv2
import threading
from copy import deepcopy
import yagmail

thread_lock = threading.Lock()
thread_exit = False

class myThread(threading.Thread):

    def __init__(self, camera_id,count):
        
        super(myThread, self).__init__()
        self.count=count
        self.camera_id = camera_id
        self.cap = cv2.VideoCapture(self.camera_id)
        self.size = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.img_height=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.img_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame = np.zeros((self.img_height, self.img_width, 3), dtype=np.uint8)
        self.flag = False
        self.out = cv2.VideoWriter(str(self.count)+'.avi', self.fourcc, self.fps, self.size)

    def get_frame(self):

        return self.frame

    def run(self):

        global thread_exit
        while not thread_exit:
            time.sleep(0.05)
            ret, frame = self.cap.read()
            self.out.write(frame)            
            if ret:
                thread_lock.acquire()
                self.frame = frame
                thread_lock.release()
            else:
                thread_exit = True
        self.cap.release()


class email_Thread(threading.Thread):

    def __init__(self, email_id,img):

        super(email_Thread, self).__init__()
        self.id = email_id
        self.img=img

    def run(self):

        yag = yagmail.SMTP( user="E_community@126.com", password="RBDKKPTULOUARLFK", host='smtp.126.com')
        contents = ['小区中有高空抛物行为发生，请速去查看~']
        yag.send(self.id, '智能小区检测警报', contents,[self.img])
        yag.close()
        

def flag():

    global thread_exit
    thread_exit=True

def main(path,email):

    f1 = open("record_sta.txt", "a+")
    f2=open("record_end.txt","a+")
    count=0
    global thread_exit
    thread_exit=False
    count1 = 0
    f3 = open("Number.txt")
    count1 = f3.read()
    f3.close()
    if count1 != "":
        count1 = eval(count1)
        count1 += 1
        f3=open("Number.txt","w")
        f3.write(str(count1))
    else:
        count1=1
        f3=open("Number.txt","w")
        f3.write("1")
    f3.close()
    thread = myThread(path,count1)
    thread.start()
    record_sta = {}
    record_end={}
    es = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 4))
    background = None
    skip_frame=2
    total_frame=1
    ct = CentroidTracker(maxDisappeared=100, maxDistance=100)
    trackers = []
    trackableObjects = {}
    H=None
    W=None
    thread_lock.acquire()
    frame = thread.get_frame()
    thread_lock.release()
    times = 1    
    while not thread_exit:
        if times==1:
            time.sleep(2)
            times=2        
        thread_lock.acquire()
        frame = thread.get_frame()       
        thread_lock.release()
        total_frame+=1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rects=[]
        if W is None or H is None:
            (H, W) = frame.shape[:2]
        if total_frame%skip_frame!=0:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_frame = cv2.GaussianBlur(gray_frame, (3, 3), 0)
            diff = cv2.absdiff(background, gray_frame)  
            retval, diff = cv2.threshold(diff,50, 255, cv2.THRESH_BINARY)  
            diff = cv2.dilate(diff, es, iterations=0)  
            for tracker in trackers:   
                tracker.update(rgb)  
                pos = tracker.get_position()   
                startX = int(pos.left())
                startY = int(pos.top())
                endX = int(pos.right())
                endY = int(pos.bottom())
                rects.append((startX, startY, endX, endY))
        else:
            trackers = []            
            if background is None:  
                background = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  
                background = cv2.GaussianBlur(background, (3, 3), 0)  
                continue  
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_frame = cv2.GaussianBlur(gray_frame, (3, 3), 0)
            diff = cv2.absdiff(background, gray_frame)  
            retval, diff = cv2.threshold(diff,50, 255, cv2.THRESH_BINARY)  
            diff = cv2.dilate(diff, es, iterations=0)  
            cnts, hierarchy = cv2.findContours(diff.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            for c in cnts:
                if cv2.contourArea(c) < 50:
                    continue
                (x, y, w, h) = cv2.boundingRect(c)
                tracker = dlib.correlation_tracker()    
                rect = dlib.rectangle(x,y,x+w,y+h)     
                tracker.start_track(rgb, rect)         
                trackers.append(tracker)            
        objects = ct.update(rects)
        for (objectID, centroid) in objects.items():
            sta = record_sta.get(objectID, None)
            if sta is None:
                record_sta[objectID] = count
                record_end[objectID] = count
            to = trackableObjects.get(objectID, None) 
            if to is None:
                to = TrackableObject(objectID, centroid)
            else:
                y = [c[1] for c in to.centroids]
                direction = centroid[1] - np.mean(y)
                to.centroids.append(centroid)
                if abs(direction) > 10:
                    record_end[objectID]=count
                    if not to.counted:
                        count += 1
                        to.counted = True
                        now_time = str(datetime.datetime.now().year) + '_' + str(datetime.datetime.now().month) + '_' + str(datetime.datetime.now().day) + '_' + str(datetime.datetime.now().hour) + '_'+ str(datetime.datetime.now().minute) + '_' + str(datetime.datetime.now().second)
                        cv2.imwrite("throw_" + now_time + ".png", frame)
                        send = email_Thread(email, "throw_" + now_time + ".png")
                        send.start()
                    cv2.rectangle(frame, (centroid[2],centroid[3]), (centroid[4],centroid[5]), (0, 255, 0), 2)
            trackableObjects[objectID] = to               
        diff = cv2.merge((diff, diff, diff))        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            thread_exit = True
        yield (frame,count)
    f1.write(str(record_sta))
    f1.write("\n")
    f2.write(str(record_end))
    f2.write("\n")
    thread.join()
    yield 1