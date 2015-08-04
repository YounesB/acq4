import sys
sys.path.append('..\\..\\..\\')

import pcocam
import matplotlib.pyplot as plt

pco = pcocam._PCOCameraClass()

#pco.list_Params()
#cam_hand = pco.open_camera()
pco.setup_camera()
pco.record_images(3)
t = pco.return_images(1)
print t
#a =plt.imshow(t[0])
#plt.show()
#pco.stop_camera(cam_hand)
#pco.close_camera(cam_hand)
