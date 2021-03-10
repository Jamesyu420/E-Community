from pyimagesearch.centroidtracker import CentroidTracker
from pyimagesearch.trackableobject import TrackableObject
from imutils.video import VideoStream
from imutils.video import FPS
import numpy as np
import argparse
from imutils import resize as resz
from time import sleep
from dlib import correlation_tracker, rectangle
from dlib import rectangle as dl_rectangle
import cv2
import threading
from copy import deepcopy
import yagmail


thread_lock = threading.Lock()
thread_exit = False



class myThread(threading.Thread):
    def __init__(self, camera_id):
        super(myThread, self).__init__()
        self.camera_id = camera_id
        self.cap = cv2.VideoCapture(self.camera_id)
        self.size = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))*2, int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.img_height=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.img_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame = np.zeros((self.img_height, self.img_width, 3), dtype=np.uint8)
        self.flag=False

    def get_frame(self):
        return self.frame

    def run(self):
        global thread_exit
        
        while not thread_exit:
            sleep(0.005)
            ret, frame = self.cap.read()
            if ret:
                thread_lock.acquire()
                self.frame = resz(frame,width=402)
                thread_lock.release()
            else:
                thread_exit = True

        self.cap.release()

class email_Thread(threading.Thread):
    def __init__(self, email_id):
        super(email_Thread, self).__init__()
        self.id=email_id

    def run(self):
        yag = yagmail.SMTP( user="E_community@126.com", password="RBDKKPTULOUARLFK", host='smtp.126.com')
        contents = ['This is the body, and here is just text http://somedomain/image.png',
                    'You can find an audio file attached.']
        yag.send(self.id, '智能小区检测警报', contents)
        yag.close()

def flag():
    global thread_exit
    thread_exit=True


def main(sub,email,path):
    global thread_exit
    img_height = 480
    img_width = 640
    thread = myThread(path)
    thread.start()    
    out = cv2.VideoWriter('fakemanout.avi', thread.fourcc, thread.fps, thread.size)  
    es = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 4))
    kernel = np.ones((5, 5), np.uint8)
    background = None
    skip_frame=2
    total_frame=1
    ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
    trackers = []
    trackableObjects = {}
    H=None
    W=None
    thread_lock.acquire()
    frame = thread.get_frame()
    thread_lock.release()
    times = 1
    count=0
    while not thread_exit:
        if times==1:
            sleep(2)
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
            retval, diff = cv2.threshold(diff,40, 255, cv2.THRESH_BINARY)  
            diff = cv2.dilate(diff, es, iterations=0)  
            for tracker in trackers:    
			    # set the status of our system to be 'tracking' rather
			    # than 'waiting' or 'detecting'
			    # update the tracker and grab the updated position
                tracker.update(rgb)  
                pos = tracker.get_position()   
			    # unpack the position object
                startX = int(pos.left())
                startY = int(pos.top())
                endX = int(pos.right())
                endY = int(pos.bottom())
			    # add the bounding box coordinates to the rectangles list
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
                if cv2.contourArea(c) < 1500:
                    continue
                (x, y, w, h) = cv2.boundingRect(c)
                tracker = correlation_tracker()    
                rect = dl_rectangle(x,y,x+w,y+h)     
                tracker.start_track(rgb, rect)         
                trackers.append(tracker)            
        objects = ct.update(rects) 
        for (objectID, centroid) in objects.items():
            dir="no"
            to = trackableObjects.get(objectID, None) 
		    # if there is no existing trackable object, create one
            if to is None:
                to = TrackableObject(objectID, centroid)
		    # otherwise, there is a trackable object so we can utilize it
		    # to determine direction
            else:
                y = [c[1] for c in to.centroids]
                direction = centroid[1] - np.mean(y)
                to.centroids.append(centroid)
			    # check to see if the object has been counted or not
                if not to.counted:
                    count += 1
                    to.counted = True
                    send = email_Thread(email)
                    send.start()
				    # if the direction is negative (indicating the object
				    # is moving up) AND the centroid is above the center
				    # line, count the object
                if direction < 0 :
                    dir="up"
                elif direction > 0 :
                    dir="down"
            trackableObjects[objectID] = to
            for pos in sub:
                down_right_x = pos[0]
                up_left_x = pos[1]
                up_left_y = pos[3]
                down_right_y = pos[2]
                if (down_right_x>(centroid[2]+centroid[4])/2.0>up_left_x and up_left_y<centroid[5]<down_right_y):
                    cv2.rectangle(frame, (centroid[2],centroid[3]), (centroid[4],centroid[5]), (0, 255, 0), 2)
                elif (down_right_x>(centroid[2]+centroid[4])/2.0>up_left_x and up_left_y<centroid[3]<down_right_y):
                    cv2.rectangle(frame, (centroid[2],centroid[3]), (centroid[4],centroid[5]), (0, 255, 0), 2)
        for pos in sub:
            down_right_x = pos[0]
            up_left_x = pos[1]
            up_left_y = pos[3]
            down_right_y = pos[2]
            cv2.rectangle(frame, (up_left_x, up_left_y), (down_right_x, down_right_y), (255, 255, 0), 2)
        diff = cv2.merge((diff, diff, diff))
        mix = np.hstack((frame, diff))  
        out.write(mix)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            thread_exit = True            
        yield (frame,count)
    thread.join()
    thread_exit = False
    yield 1

