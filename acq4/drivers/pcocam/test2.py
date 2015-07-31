import sys
sys.path.append('..\\..\\..\\')

import pcocam

pco = pcocam._PCOCameraClass()

#cam_hand = pco.open_camera()
pco.setup_camera()
pco.record_images(10)
#pco.stop_camera(cam_hand)
#pco.close_camera(cam_hand)

