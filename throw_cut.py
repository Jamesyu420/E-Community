
import cv2
import os

def main(input_v,output_v,start,end,name):
    
    cap = cv2.VideoCapture(input_v)
    FPS = cap.get(5)
    c = 1
    startframe = start  
    endframe = end
    out = cv2.VideoWriter(output_v+'\\'+name+".avi", cv2.VideoWriter_fourcc(*'XVID'), cap.get(cv2.CAP_PROP_FPS), (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))    
    while (True):
        ret, frame = cap.read()
        if ret:
            if startframe<= c <= endframe:  
                out.write(frame)  
            if c>endframe:
                break
            c += 1
        else:
            break
    cap.release()