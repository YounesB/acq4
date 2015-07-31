import sys
sys.path.append('..\\..\\..\\')

import pcocam
import matplotlib.pyplot as plt

pco = pcocam._PCOCameraClass()

#cam_hand = pco.open_camera()
pco.setup_camera()
pco.record_images(12)
t = pco.return_images(3)
#a =plt.imshow(t)
#plt.show()
#pco.stop_camera(cam_hand)
#pco.close_camera(cam_hand)

