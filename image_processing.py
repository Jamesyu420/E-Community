import os
import glob
import cv2
import numpy as np
import matplotlib.pyplot as plt
 

def read_image(filename, resize_height=None, resize_width=None, normalization=False): 
    bgr_image = cv2.imread(filename)
    if bgr_image is None:
        return None
    if len(bgr_image.shape) == 2:  
        bgr_image = cv2.cvtColor(bgr_image, cv2.COLOR_GRAY2BGR) 
    rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)  
    rgb_image = resize_image(rgb_image,resize_height,resize_width)
    rgb_image = np.asanyarray(rgb_image)
    if normalization:
        rgb_image = rgb_image / 255.0
    return rgb_image
    
def resize_image(image,resize_height, resize_width):
    image_shape = np.shape(image)
    height=image_shape[0]
    width=image_shape[1]
    if (resize_height is None) and (resize_width is None):
        return image
    if resize_height is None:
        resize_height=int(height*resize_width/width)
    elif resize_width is None:
        resize_width=int(width*resize_height/height)
    image = cv2.resize(image, dsize=(resize_width, resize_height))
    return image