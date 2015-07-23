# -*- coding: utf-8 -*-
from ctypes import *
import sys, numpy, time, re, os
from acq4.util.clibrary import *
from collections import OrderedDict
from acq4.util.debug import backtrace
import acq4.util.ptime as ptime
from acq4.util.Mutex import Mutex

__all__ = ['PCOCam']


### Load header files, open DLL
modDir = os.path.dirname(__file__)
headerFiles = [
    #"C:\Program Files\Photometrics\PVCam32\SDK\inc\master.h",
    #"C:\Program Files\Photometrics\PVCam32\SDK\inc\pvcam.h"
    os.path.join(modDir, "Pco_ConvStructures.h"),
    os.path.join(modDir, "PCO_err.h"),
	os.path.join(modDir, "PCO_errt.h"),
	os.path.join(modDir, "PCO_Structures.h"),
	os.path.join(modDir, "PfcamExport.h"),
	os.path.join(modDir, "errcodes.h"),
	os.path.join(modDir, "pcc_struct.h"),
	os.path.join(modDir, "Pccam.h"),
	os.path.join(modDir, "pccamdef.h"),
	os.path.join(modDir, "Pco_ConvDlgExport.h"),
	os.path.join(modDir, "Pco_ConvExport.h"),
	os.path.join(modDir, "SC2_CamExport.h"),
	os.path.join(modDir, "sc2_structures.h")
]
HEADERS = CParser(headerFiles, cache=os.path.join(modDir, 'pcocam_headers.cache'), copyFrom=winDefs())
LIB = CLibrary(windll.SC2_Cam, HEADERS, prefix='PCO_')

def init():
    ## System-specific code
    global PVCam
    PVCam = _PVCamClass()

class _PCOCamClass:
	
	PCOCAM_CREATED = False
    
    
	def __init__(self,triggerE):
		print 'init'
		
		# dictionary to keep camera status
		self.glvar = {}
		self.glvar['do_libunload'] = 0
		self.glvar['do_close'] = 0
		self.glvar['camera_open'] = 0
		self.glvar['out_ptr'] = []
		
		self.triggerEvent = triggerE
	
	def reloadDriver(self):
		self.__init__()
	
	# def setup_camera(self,exposure_time=50,time_stamp=1,pixelrate=1,trigger_mode=0,hor_bin=1,vert_bin=1):
		# self.open_camera()
		
		# print 'camer_open should be 1 is :',self.glvar['camera_open']
		
		# self.set_exposure_time(self.glvar['out_ptr'],exposure_time)
		
		# self.enable_timestamp(self.glvar['out_ptr'],time_stamp)
		# self.set_pixelrate(self.glvar['out_ptr'],pixelrate)
		# self.set_triggermode(self.glvar['out_ptr'],trigger_mode)
		# self.set_spatialbinning(self.glvar['out_ptr'],hor_bin,vert_bin)
		# #self.set_storagemode(self.glvar['out_ptr'],0)
		# self.show_frametime(self.glvar['out_ptr'])
		# self.arm_camera(self.glvar['out_ptr'])
		
		# #self.start_camera(self.glvar['out_ptr'])
	
	def __del__(self):
		self.glvar['do_close'] = 1
		self.glvar['do_libunload']=1
		self.close_camera()
    
	def open_camera(self):
		cameraHandle = c_void_p()
		resO = LIB.PCO_OpenCamera(byref(cameraHandle),0)
		if resO:
			print 'PCO_OpenCamera failed with error %08X ' % resO
			LIB.PCO_GetErrorText(resO)
		else:
			print 'PCO_OpenCamera done'
			self.glvar['camera_open'] = 1
    
	def close_camera(self):
		cameraHandle = c_void_p()
        if self.isOpen:
			resC = LIB.PCO_CloseCamera(cameraHandle)
			if resC:
				print 'PCO_CloseCamera failed with error %08X ' % resC
				LIB.PCO_GetErrorText(resC)
			else:
				print 'PCO_CloseCamera done'
				self.glvar['camera_open'] = 0
	
	# def start_camera(self,camHand):
		# act_recState = c_ulong(10)
		# res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		# if res1:
			# print 'PCO_GetRecordingState failed %08X ' % res1
			# LIB.PCO_GetErrorText(res1)
	
		# if act_recState.value != 1:
			# res1 = LIB.PCO_SetRecordingState(camHand,1)
			# print 'RecordingState set to 1'
				
	# def stop_camera(self,camHand):
		# act_recState = c_ulong(10)
		# res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		# if res1:
			# print 'PCO_GetRecordingState failed %08X ' % res1
			# LIB.PCO_GetErrorText(res1)
	
		# if act_recState.value != 0:
			# res1 = LIB.PCO_SetRecordingState(camHand,0)
			# print 'RecordingState set to 0'				
	
	
#class _CameraClass:


	
	

		
