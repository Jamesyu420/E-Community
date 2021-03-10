
import cv2
import image_processing
import numpy as np

global img
global point1, point2
global g_rect, rects
rects=[]

def on_mouse(event, x, y, flags, param):
    
    global img, point1, point2, g_rect, times,rects
    img2 = img.copy()
    if event == cv2.EVENT_LBUTTONDOWN:  
        point1 = (x, y)
        cv2.circle(img2, point1, 10, (0, 255, 0), 5)
        cv2.imshow('image', img2) 
    elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON):  # 按住左键拖曳，画框
        cv2.rectangle(img2, point1, (x, y), (255, 0, 0), thickness=2)
        cv2.imshow('image', img2) 
    elif event == cv2.EVENT_LBUTTONUP:  
        point2 = (x, y)
        cv2.rectangle(img2, point1, point2, (0, 0, 255), thickness=2)
        cv2.imshow('image', img2)
        if point1!=point2:
            min_x = min(point1[0], point2[0])
            min_y = min(point1[1], point2[1])
            width = abs(point1[0] - point2[0])
            height = abs(point1[1] - point2[1])
            down_right_x = min_x+width
            up_left_x = min_x
            up_left_y = min_y
            down_right_y = min_y+height
            g_rect = [min_x, min_y, width, height]
            g_rect1=[down_right_x,up_left_x,down_right_y,up_left_y]
        rects.append(g_rect1)
        img=img2
 
def get_image_roi(rgb_image):

    bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    global img
    img = bgr_image
    cv2.namedWindow('image')
    while True:
        cv2.setMouseCallback('image', on_mouse)
        cv2.imshow('image', img)
        key=cv2.waitKey(0)
        if key == 13 or key == 32:  
            break
    cv2.destroyAllWindows()
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return rects
 
def select_user_roi(image_path):

    orig_image = image_processing.read_image(image_path)
    g_rects=get_image_roi(orig_image)
    return g_rects
 
def main(image_path):
    global rects
    rects=[]
    times=0
    img=0
    return select_user_roi(image_path)