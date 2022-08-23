import cv2

# Load File
from numpy import array

in_path = r'temp/temp_image_inside.png'
in_file = open(in_path, 'r')
in_contents = in_file.read()
print(in_contents)

# Write data to image
out_path = r'temp/temp_image_inside.png'
out_file = open(out_path, 'w')
out_file.write(in_contents)
