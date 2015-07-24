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
		self.lock = Mutex()
		
		self.triggerEvent = triggerE
	
	
	def __del__(self):
		self.glvar['do_close'] = 1
		self.glvar['do_libunload']=1
		_PCOCamClass.close_camera()
		
	def call(self, function, *args):
		a = function(*args)
		if a() == None:
			return a
		elif a() != 0:
			print "Function '%s%s' failed with error %08X " % (func, str(args), a())
			LIB.PCO_GetErrorText(a)
		else:
			return a

	
class _PCOCameraClass:
	def __init__(self,triggerE):
		print 'init'
		
		# dictionary to keep camera status
		self.glvar = {}
		self.glvar['do_libunload'] = 0
		self.glvar['do_close'] = 0
		self.glvar['camera_open'] = 0
		self.glvar['out_ptr'] = []
		self.lock = Mutex()
		
		self.triggerEvent = triggerE
		
	def open_camera(self):
		cameraHandle = c_void_p()
		resO = LIB.PCO_OpenCamera(byref(cameraHandle),0)
		if resO:
			print 'PCO_OpenCamera failed with error %08X ' % resO
			LIB.PCO_GetErrorText(resO)
		else:
			print 'PCO_OpenCamera done'
			self.glvar['camera_open'] = 1
			self.glvar['out_ptr'] = cameraHandle
    
	def close_camera(self):
		cameraHandle = c_void_p()
        if self.glvar['camera_open'] == 1 and self.glvar['do_close'] == 1:
			resC = LIB.PCO_CloseCamera(cameraHandle)
			if resC:
				print 'PCO_CloseCamera failed with error %08X ' % resC
				LIB.PCO_GetErrorText(resC)
			else:
				print 'PCO_CloseCamera done'
				self.glvar['camera_open'] = 0
				self.glvar['out_ptr'] = []
				
	def setup_camera(self,exposure_time=50,time_stamp=1,pixelrate=1,trigger_mode=0,hor_bin=1,vert_bin=1):
		self.open_camera()
		print 'camer_open should be 1 is :',self.glvar['camera_open']
		
		self.set_exposure_time(self.glvar['out_ptr'],exposure_time)
		self.enable_timestamp(self.glvar['out_ptr'],time_stamp)
		self.set_pixelrate(self.glvar['out_ptr'],pixelrate)
		self.set_triggermode(self.glvar['out_ptr'],trigger_mode)
		self.set_spatialbinning(self.glvar['out_ptr'],hor_bin,vert_bin)
		#self.set_storagemode(self.glvar['out_ptr'],0)
		self.show_frametime(self.glvar['out_ptr'])
		self.arm_camera(self.glvar['out_ptr'])
		#self.start_camera(self.glvar['out_ptr'])
	
	def start_camera(self,camHand):
		act_recState = c_ulong(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1:
			print 'PCO_GetRecordingState failed %08X ' % res1
			LIB.PCO_GetErrorText(res1)
	
		if act_recState.value != 1:
			res1 = LIB.PCO_SetRecordingState(camHand,1)
			print 'RecordingState set to 1'
				
	def stop_camera(self,camHand):
		act_recState = c_ulong(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1:
			print 'PCO_GetRecordingState failed %08X ' % res1
			LIB.PCO_GetErrorText(res1)
	
		if act_recState.value != 0:
			res1 = LIB.PCO_SetRecordingState(camHand,0)
			print 'RecordingState set to 0'

	def set_exposure_time(self,camHand,time):
		
		del_time = c_uint(0)
		exp_time = c_uint(0)
		del_base = c_ushort(0)
		exp_base = c_ushort(0)
		
		res1 = LIB.PCO_GetDelayExposureTime(camHand,byref(del_time),byref(exp_time),byref(del_base),byref(exp_base))
		if res1:
			print 'PCO_GetDelayExposureTime failed'
		
		print 'Exposure time set to : ',str(time),' ms'
		print 'Delay is             : ',str(del_time.value),' ms'
		
		exp_time = c_uint(time)
		exp_base = c_ushort(2)
		
		res2 = LIB.PCO_SetDelayExposureTime(camHand,del_time,exp_time,del_base,exp_base)
		if res2:
			print 'PCO_SetDelayExposureTime failed'
	def enable_timestamp(self,camHand,Stamp):
		act_recState = c_ulong(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1:
			print 'PCO_GetRecordingState failed %08X ' % res1
	
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			if res2:
				print 'PCO_SetRecordingState failed %08X ' % res2
			else:
				print 'RecordingState set to 0'
		
		
		# 0x0000 = no stamp in image
		# 0x0001 = BCD coded stamp in the first 14 pixel
		# 0x0002 = BCD coded stamp in the first 14 pixel + ASCII text
		# 0x0003 = ASCII text only (see descriptor for availability)
		
		if Stamp!=0 and Stamp!= 1 and Stamp!=2 and Stamp!=3 :
			print 'Stamp must be 0 or 1 or 2!'
			return
		
		res2 = LIB.PCO_SetTimestampMode(camHand,Stamp)
		if res2:
			print 'PCO_GetRecordingState failed'
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4:
				print 'PCO_SetRecordingState failed'
				
	def set_pixelrate(self,camHand,Rate):
		act_recState = c_ulong(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1:
			print 'PCO_GetRecordingState failed'
	
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			print 'RecordingState set to 0'
		
		cam_desc = CAM_DESC(436,)
		#print self.cam_desc.wSize, self.cam_desc.wSensorTypeDESC
		res3 = LIB.PCO_GetCameraDescription(camHand,byref(cam_desc))
		if res3:
			print 'PCO_GetCameraDescription failed with error %08X' % res4
		#bitpix = uint16(cam_desc.wDynResDESC)
		
		if Rate!=0 and Rate!= 1:
			print 'Rate must be 0 or 1'
		
		#print cam_desc.dwPixelRateDESC[0], cam_desc.dwPixelRateDESC[1]
		if cam_desc.dwPixelRateDESC[Rate]:
			res4 = LIB.PCO_SetPixelRate(camHand,cam_desc.dwPixelRateDESC[Rate])
			if res4:
				print 'PCO_SetPixelRate failed'
		
		print 'Pixelrate is  : ',cam_desc.dwPixelRateDESC[Rate]/1000000.,' MHz'
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4:
				print 'PCO_SetRecordingState failed'
	def set_triggermode(self,camHand,triggerMode):
		
		act_recState = c_ulong(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1:
			print 'PCO_GetRecordingState failed'
	
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			print 'RecordingState set to 0'
		
		if triggerMode!=0 and triggerMode!=1 and triggerMode!=2 and triggerMode!=3:
			print 'Trigger mode must be 0,1,2 or 3'
		
		act_triggerMode = c_ulong(10)
		res2a = LIB.PCO_GetTriggerMode(camHand,byref(act_triggerMode))
		if res2a:
			print 'PCO_GetTriggerMode failed with error %08X ' % res2
				
		if act_triggerMode.value != triggerMode:
			res3 = LIB.PCO_SetTriggerMode(camHand,c_ushort(triggerMode))
			if res3 :
				print 'PCO_SetTriggerMode failed with error %08X ' % res3
		
		print 'old trigger mode was : ',str(act_triggerMode.value),' new mode is: ',str(triggerMode)
		
		#if triggerMode == 0:
		#acquireMode = c_ulong(1)
		#res3b = LIB.PCO_SetAcquireMode(camHand,acquireMode)
		#if res3b:
		#	print 'PCO_GetAcquireMode failed with error %08X ' % res3b
		
		act_acquireMode = c_ulong(10)
		res3a = LIB.PCO_GetAcquireMode(camHand,byref(act_acquireMode))
		if res3a:
			print 'PCO_GetAcquireMode failed with error %08X ' % res3a
		
		
		#elif triggerMode == 0:
			#acquireMode = c_ushort(0)
			#res3c = LIB.PCO_SetAcquireMode(camHand,acquireMode)
			#if res3c:
				#print 'PCO_GetAcquireMode failed with error %08X ' % res3c
		
		print 'aquire mode is : ',str(act_acquireMode.value) #,' new mode is: ',str(acquireMode.value)
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4:
				print 'PCO_SetRecordingState failed with error %08X ' % res4
	def set_spatialbinning(self,camHand,hor_bin,vert_bin):
		
		act_recState = c_ulong(10)
		res1 = self.LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1:
			print 'PCO_GetRecordingState failed'
	
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			print 'RecordingState set to 0'
		
		#if xbin!=0 and storageMode!=1:
		#	print 'StorageMode mode must be 0 or 1'
		
		act_hor_bin = c_ushort(10)
		act_vert_bin = c_ushort(10)
		res2a = LIB.PCO_GetBinning(camHand,byref(act_hor_bin),byref(act_vert_bin))
		if res2a:
			print 'PCO_GetBinning failed with error %08X ' % res2
				
		if (act_hor_bin.value != hor_bin) or (act_vert_bin.value != vert_bin):
			res3 = LIB.PCO_SetBinning(camHand,c_ushort(hor_bin),c_ushort(vert_bin))
			if res3 :
				print 'PCO_SetBinning failed with error %08X ' % res3
			
			print 'old  hor. x vert. binning  was : ',str(act_hor_bin.value),'x',str(act_vert_bin.value),' new binning is: ',str(hor_bin),'x',str(vert_bin)
		
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4:
				print 'PCO_SetRecordingState failed with error %08X ' % res4

	def show_frametime(self,camHand):
		
		dwSec = c_uint(0)
		dwNanoSec = c_uint(0)
		res1 = LIB.PCO_GetCOCRuntime(camHand,byref(dwSec),byref(dwNanoSec))
		if res1:
			print 'PCO_GetCOCRuntime failed'
		
		self.waittime_s = double(dwNanoSec.value)
		print 'waittime',double(dwSec.value), double(dwNanoSec.value)
		self.waittime_s = self.waittime_s/1000000000.
		self.waittime_s = self.waittime_s + double(dwSec.value)
		
		
		print 'one frame needs %6.6f sec, resulting in %6.3f FPS' % (self.waittime_s,1./self.waittime_s)

def arm_camera(self,camHand):
		act_recState = c_ulong(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1:
			print 'PCO_GetRecordingState failed %08X ' % res1
	
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			if res2:
				print 'PCO_SetRecordingState failed %08X ' % res2
			else:
				print 'RecordingState set to 0'
		
		res0 = LIB.PCO_ArmCamera(camHand)
		if res0 :
			print 'PCO_ArmCamera failed'
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4:
				print 'PCO_SetRecordingState failed'		


	
	

		
