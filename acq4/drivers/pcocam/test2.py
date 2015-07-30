import sys
sys.path.append('..\\..\\..\\')

import pcocam

pco = pcocam._PCOCameraClass()

cam_hand = pco.open_camera()
pco.setup_camera()
pco.get_live_image(cam_hand,1)
#pco.stop_camera(cam_hand)
#pco.close_camera(cam_hand)

