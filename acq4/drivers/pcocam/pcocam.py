# -*- coding: utf-8 -*-
import sys
sys.path.append('..\\..\\..\\')

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


class _PCOCamClass:
	
	PCOCAM_CREATED = False
   
	def __init__(self):
		print 'init'
		
		# dictionary to keep camera status
		self.glvar = {}
		self.glvar['do_libunload'] = 0
		self.glvar['do_close'] = 0
		self.glvar['camera_open'] = 0
		self.glvar['out_ptr'] = []
		self.lock = Mutex()
		


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
	def __init__(self):
		print 'init'
		
		# dictionary to keep camera status
		self.glvar = {}
		self.glvar['do_libunload'] = 0
		self.glvar['camera_open'] = 0
		self.glvar['out_ptr'] = []
		self.lock = Mutex()


	def open_camera(self):
		cameraHandle = c_void_p()
		resO = LIB.PCO_OpenCamera(byref(cameraHandle),0)
		if resO():
			print resO()
			print 'PCO_OpenCamera failed with error %08X ' % resO()
		else:
			print 'PCO_OpenCamera done'
			self.glvar['camera_open'] = 1
			self.glvar['out_ptr'] = cameraHandle
			return self.glvar['out_ptr']
   
   
	def close_camera(self,camHand):
		if self.glvar['camera_open'] == 1:
			resC = LIB.PCO_CloseCamera(camHand)
			if resC():
				print 'PCO_CloseCamera failed with error %08X ' % resC()
			else:
				print 'PCO_CloseCamera done'
				self.glvar['camera_open'] = 0
				self.glvar['out_ptr'] = []
		else:
			print 'No open camera'


	def setup_camera(self,exposure_time=50,time_stamp=1,pixelrate=1,trigger_mode=0,hor_bin=1,vert_bin=1):
		print '*******SETUP CAMERA*******'
		if self.glvar['camera_open'] == 0:
			self.open_camera()
		else:
			print 'Camera already open'
		print 'camer_open should be 1 is :',self.glvar['camera_open']
		
		self.set_exposure_time(self.glvar['out_ptr'],exposure_time)
		self.enable_timestamp(self.glvar['out_ptr'],time_stamp)
		self.set_pixelrate(self.glvar['out_ptr'],pixelrate)
		self.set_triggermode(self.glvar['out_ptr'],trigger_mode)
		self.set_spatialbinning(self.glvar['out_ptr'],hor_bin,vert_bin)
		#self.set_storagemode(self.glvar['out_ptr'],0)
		self.show_frametime(self.glvar['out_ptr'])
		self.arm_camera(self.glvar['out_ptr'])
		self.start_camera(self.glvar['out_ptr'])
		print 'CAMERA READY'


	def start_camera(self,camHand):
		act_recState = c_ushort(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1():
			print 'PCO_GetRecordingState failed %08X ' % res1
			LIB.PCO_GetErrorText(res1)
	
		if act_recState.value != 1:
			res1 = LIB.PCO_SetRecordingState(camHand,1)
			print 'RecordingState set to 1'


	def stop_camera(self,camHand):
		act_recState = c_ushort(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1():
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
		
		if res1():
			print 'PCO_GetDelayExposureTime failed'
		
		print 'Exposure time set to : ',str(time),' ms'
		print 'Delay is             : ',str(del_time.value),' ms'
		
		exp_time = c_uint(time)
		exp_base = c_ushort(2)
		
		res2 = LIB.PCO_SetDelayExposureTime(camHand,del_time,exp_time,del_base,exp_base)
		if res2():
			print 'PCO_SetDelayExposureTime failed'


	def enable_timestamp(self,camHand,Stamp):
		act_recState = c_ushort(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1():
			print 'PCO_GetRecordingState failed %08X ' % res1
	
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			if res2():
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
		if res2():
			print 'PCO_GetRecordingState failed'
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4():
				print 'PCO_SetRecordingState failed'


	def set_pixelrate(self,camHand,Rate):
		act_recState = c_ushort(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1():
			print 'PCO_GetRecordingState failed'
	
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			print 'RecordingState set to 0'
		
		cam_desc = LIB.PCO_Description(436,)		
		#print self.cam_desc.wSize, self.cam_desc.wSensorTypeDESC
		res3 = LIB.PCO_GetCameraDescription(camHand,byref(cam_desc))
		if res3():
			print 'PCO_GetCameraDescription failed with error %08X' % res4
		#bitpix = uint16(cam_desc.wDynResDESC)
		
		if Rate!=0 and Rate!= 1:
			print 'Rate must be 0 or 1'
			
		#print cam_desc.dwPixelRateDESC[0], cam_desc.dwPixelRateDESC[1]
		if cam_desc.dwPixelRateDESC[Rate]:
			res4 = LIB.PCO_SetPixelRate(camHand,cam_desc.dwPixelRateDESC[Rate])
			if res4():
				print 'PCO_SetPixelRate failed'
		
		print 'Pixelrate is  : ',cam_desc.dwPixelRateDESC[Rate]/1000000.,' MHz'
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4():
				print 'PCO_SetRecordingState failed'


	def set_triggermode(self,camHand,triggerMode):
		
		act_recState = c_ushort(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1():
			print 'PCO_GetRecordingState failed'
	
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			print 'RecordingState set to 0'
		
		if triggerMode!=0 and triggerMode!=1 and triggerMode!=2 and triggerMode!=3:
			print 'Trigger mode must be 0,1,2 or 3'
		
		act_triggerMode = c_ushort(10)
		res2a = LIB.PCO_GetTriggerMode(camHand,byref(act_triggerMode))
		if res2a():
			print 'PCO_GetTriggerMode failed with error %08X ' % res2
				
		if act_triggerMode.value != triggerMode:
			res3 = LIB.PCO_SetTriggerMode(camHand,c_ushort(triggerMode))
			if res3():
				print 'PCO_SetTriggerMode failed with error %08X ' % res3
		
		print 'old trigger mode was : ',str(act_triggerMode.value),' new mode is: ',str(triggerMode)
		
		#if triggerMode == 0:
		#acquireMode = c_ulong(1)
		#res3b = LIB.PCO_SetAcquireMode(camHand,acquireMode)
		#if res3b:
		#	print 'PCO_GetAcquireMode failed with error %08X ' % res3b
		
		act_acquireMode = c_ushort(10)
		res3a = LIB.PCO_GetAcquireMode(camHand,byref(act_acquireMode))
		if res3a():
			print 'PCO_GetAcquireMode failed with error %08X ' % res3a
		
		
		#elif triggerMode == 0:
			#acquireMode = c_ushort(0)
			#res3c = LIB.PCO_SetAcquireMode(camHand,acquireMode)
			#if res3c:
				#print 'PCO_GetAcquireMode failed with error %08X ' % res3c
		
		print 'aquire mode is : ',str(act_acquireMode.value) #,' new mode is: ',str(acquireMode.value)
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4():
				print 'PCO_SetRecordingState failed with error %08X ' % res4


	def set_spatialbinning(self,camHand,hor_bin,vert_bin):
		
		act_recState = c_ushort(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1():
			print 'PCO_GetRecordingState failed'
	
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			print 'RecordingState set to 0'
		
		#if xbin!=0 and storageMode!=1:
		#	print 'StorageMode mode must be 0 or 1'
		
		act_hor_bin = c_ushort(10)
		act_vert_bin = c_ushort(10)
		res2a = LIB.PCO_GetBinning(camHand,byref(act_hor_bin),byref(act_vert_bin))
		if res2a():
			print 'PCO_GetBinning failed with error %08X ' % res2
				
		if (act_hor_bin.value != hor_bin) or (act_vert_bin.value != vert_bin):
			res3 = LIB.PCO_SetBinning(camHand,c_ushort(hor_bin),c_ushort(vert_bin))
			if res3():
				print 'PCO_SetBinning failed with error %08X ' % res3
			
			print 'old  hor. x vert. binning  was : ',str(act_hor_bin.value),'x',str(act_vert_bin.value),' new binning is: ',str(hor_bin),'x',str(vert_bin)
		
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4():
				print 'PCO_SetRecordingState failed with error %08X ' % res4


	def show_frametime(self,camHand):
		
		dwSec = c_uint(0)
		dwNanoSec = c_uint(0)
		res1 = LIB.PCO_GetCOCRuntime(camHand,byref(dwSec),byref(dwNanoSec))
		if res1():
			print 'PCO_GetCOCRuntime failed'
		
		self.waittime_s = c_double(dwNanoSec.value)
		#print 'waittime',c_double(dwSec.value), c_double(dwNanoSec.value)
		self.waittime_s = self.waittime_s.value/1000000000.
		self.waittime_s = self.waittime_s + c_double(dwSec.value).value
		
		
		print 'one frame needs %6.6f sec, resulting in %6.3f FPS' % (self.waittime_s,1./self.waittime_s)


	def arm_camera(self,camHand):
		act_recState = c_ushort(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1():
			print 'PCO_GetRecordingState failed %08X ' % res1()
		if act_recState.value != 0:
			res2 = LIB.PCO_SetRecordingState(camHand,0)
			if res2():
				print 'PCO_SetRecordingState failed %08X ' % res2()
			else:
				print 'RecordingState set to 0'
		
		res0 = LIB.PCO_ArmCamera(camHand)
		if res0():
			print 'PCO_ArmCamera failed'
		
		if act_recState.value != 0:
			res4 = LIB.PCO_SetRecordingState(camHand,act_recState)
			if res4():
				print 'PCO_SetRecordingState failed'


	def record_images(self,image_c=1):
		
		self.image_count = image_c
		
		if self.image_count==1:
			print 'get single image'
			self.get_live_image(self.glvar['out_ptr'],1)
		elif self.image_count>0:
			#print 'get ',str(self.image_count),' images'
			self.get_live_image(self.glvar['out_ptr'],self.image_count)
		else:
			print 'image_count cannot be negative'
		self.stop_camera(self.glvar['out_ptr'])


	#def extract_timestamp(self,ima,act_align,bitpix):
		#if act_align ==0:
			#ts = numpy.double(ima[1,0:14])
		#else:
			#ts = numpy.fix(numpy.double(ima[0,0:14])/(2^(16-bitpix)))
		##pdb.set_trace()
		#ts = numpy.array(ts,dtype=int)
		##pdb.set_trace()
		
		#b = ''
		#b+=str(int(numpy.fix(ts[0]/16))) + str(ts[0]&15)
		#b+=str(int(numpy.fix(ts[1]/16))) + str(ts[1]&15)
		#b+=str(int(numpy.fix(ts[2]/16))) + str(ts[2]&15)
		#b+=str(int(numpy.fix(ts[3]/16))) + str(ts[3]&15)
		
		#b += ' '
		## year
		#b+=str(int(numpy.fix(ts[4]/16))) + str(ts[4]&15)
		#b+=str(int(numpy.fix(ts[5]/16))) + str(ts[5]&15)
		#b+='-'
		## month
		#b+=str(int(numpy.fix(ts[6]/16))) + str(ts[6]&15)
		#b+='-'
		## day
		#b+=str(int(numpy.fix(ts[7]/16))) + str(ts[7]&15)
		#b+=' '
		
		## hour
		#c=str(int(numpy.fix(ts[8]/16))) + str(ts[8]&15)
		#b+=c+':'
		#ttt = float(c)*float(60.)*float(60.)
		## min
		#c=str(int(numpy.fix(ts[9]/16))) + str(ts[9]&15)
		#b+=c+':'
		#ttt = float(c)*float(60.)
		## sec
		#c=str(int(numpy.fix(ts[10]/16))) + str(ts[10]&15)
		#b+=c+'.'
		#ttt += float(c)
		## us
		#c=str(int(numpy.fix(ts[11]/16))) + str(ts[11]&15)
		#b+=c
		##print (c), float(c)
		#ttt += float(c)/float(100.)
		#c=str(int(numpy.fix(ts[12]/16))) + str(ts[12]&15)
		#b+=c
		#ttt += float(c)/float(10000.)
		#c=str(int(numpy.fix(ts[13]/16))) + str(ts[13]&15)
		#b+=c
		#ttt += float(c)/float(1000000.)
		#print b[20:22]
		#titi = numpy.float64(b[20:22])*60.*60. + numpy.float64(b[23:25])*60. + numpy.float64(b[26:-1])
		##print b, titi
		
		#return titi


	def get_live_image(self,camHand,imacount):
		print '********GET LIVE IMAGE********'
		self.imacount = imacount
		
		# get Camera Description
		cam_desc = LIB.PCO_Description(436,)
		res1 = LIB.PCO_GetCameraDescription(camHand,byref(cam_desc))
		if res1():
			print 'PCO_GetCameraDescription failed with error %08X' % res1()
		
		# set bitalignment LSB
		bitalign = c_ushort(0)
		res2 = LIB.PCO_SetBitAlignment(camHand,bitalign)
		if res2():        
			print 'PCO_SetBitAlignment failed with error %08x' % res2()
		bitpix=c_uint16(cam_desc.wDynResDESC)
		bytepix=numpy.fix(c_double(bitpix.value+7.).value/8.)
		
		
		cam_type = LIB.PCO_CameraType(1364,)
		res5 = LIB.PCO_GetCameraType(camHand,byref(cam_type))
		if res5():
			print 'PCO_GetCamerType failed with error %08X' % res5()
		interface = cam_type.wInterfaceType
        
		act_xsize= c_ushort(0)
		act_ysize= c_ushort(0)
		max_xsize= c_ushort(0)
		max_ysize= c_ushort(0)
		# use PCO_GetSizes because this always returns accurat image size for next recording
		res8 = LIB.PCO_GetSizes(camHand,byref(act_xsize),byref(act_ysize),byref(max_xsize),byref(max_ysize))
		if res8():
			print 'PCO_GetSizes failed with error %08X' % res8()
		
		res9 = LIB.PCO_CamLinkSetImageParameters(camHand,act_xsize,act_ysize)
		if res9():
			print 'PCO_CamLinkSetImageParameters failed with error %08X' % res9()
		
		# limit allocation of memory to 1Gbyte
		self.storage_required = (c_double(self.imacount).value*c_double(act_xsize.value).value*c_double(act_ysize.value).value*bytepix)
		#if (double(imacount)*double(act_xsize.value)*double(act_ysize.value)*bytepix > 1*1024*1024*1024):
		#   imacount=c_ushort(double(1*1024*1024*1024)/(double(act_xsize.value)*double(act_ysize.value)*bytepix))
		
		print 'Number of images to grab :',str(self.imacount)
		print 'Size of images           :',str(act_xsize.value), str(act_ysize.value), bytepix
		print 'Interface Type is        :',str(interface)
		
		act_align= c_ushort(10)
		res9 = LIB.PCO_GetBitAlignment(camHand,byref(act_align))
		if res9():
			print 'PCO_GetBitAlignment failed'
		else:
			print 'Current Bit Alignment',str(act_align.value)
		
		if self.imacount ==1:
			#image_stack = ones((act_xsize.value,act_ysize.value))
			#(errorCode,image_stack) = pco_get_image_single(cameraHandle,PCO_CAM_SDK,act_xsize,act_ysize,bitpix,interface)
			self.get_image_single(camHand,act_xsize,act_ysize,bitpix,interface)
			#print 'size image array ', size(image_stack)
		else:
			#(errorCode,image_stack) = pco_get_image_multi(cameraHandle,PCO_CAM_SDK,imacount,act_xsize,act_ysize,bitpix,interface)
			self.get_image_multi(camHand,self.imacount,act_xsize,act_ysize,bitpix,interface)
		
		
		
		#self.timeStamp = numpy.zeros(self.imacount,dtype=numpy.float64)
		##print 'Timstamp data of image:'
		#if self.imacount == 1:
			#print 'Obtaining time-stamp of image'
			#self.timeStamp[0] = self.extract_timestamp(self.image_stack,bitalign.value,bitpix.value)
		#else:
			#print 'Obtaining time-stamp of image data ...'
			#for n in range(self.imacount):
				#self.timeStamp[n] = self.extract_timestamp(self.image_stack_v[n,:,:],bitalign.value,bitpix.value)


	def get_image_single(self,camHand,act_xsize,act_ysize,bitpix,interface): 
		print '********GET IMAGE SINGLE********'
		act_recState = c_ushort(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1():
			print 'PCO_GetRecordingState failed'
		
		# get the memory for the images
		imas=c_uint32(numpy.fix((c_double(bitpix.value).value+7.)/8.))
		imas= imas.value*c_uint32(act_ysize.value).value* c_uint32(act_xsize.value).value; 
		imasize=c_uint(imas)
		lineadd=0
		
		#print 'imasize',imasize.value
		
		self.image_stack=numpy.ones((act_ysize.value+lineadd,act_xsize.value),dtype=numpy.uint16)
		#print 'shape image_stack',numpy.shape(self.image_stack),sum(self.image_stack)
		
		
		sBufNr = c_short(-1)
		im_ptr = self.image_stack.ctypes.data_as(POINTER(c_ushort))
		ev_ptr = c_void_p()
		#pdb.set_trace()
		res2 = LIB.PCO_AllocateBuffer(camHand,byref(sBufNr),imasize,byref(im_ptr),byref(ev_ptr))
		if res2():
			print 'PCO_AllocateBuffer failed'
		
		if act_recState.value == 0:
			res3 = LIB.PCO_SetRecordingState(camHand,1)
			if res3():
				print 'PCO_SetRecordingState failed'
		
		print 'pco_get_image_single: ',str(act_xsize.value),'x',str(act_ysize.value)
		#pdb.set_trace()
		#print act_xsize.value,act_ysize.value,bitpix,sBufNr.value
        
		res4 = LIB.PCO_GetImageEx(camHand,c_ushort(1),c_uint(0),c_uint(0),sBufNr,act_xsize,act_ysize,c_ushort(bitpix.value))
		#res4 = PCO_CAM_SDK.PCO_GetImage(camHand,c_ushort(1),c_uint(0),c_uint(0),sBufNr) #,act_xsize,act_ysize,c_ushort(bitpix))
		if res4():
			print 'PCO_GetImageEx failed'
		else:
			print 'pco_get_image_single: GetImageEx done'
		
		#print self.image_stack 
		#pdb.set_trace()
		#res5 = PCO_CAM_SDK.PCO_GetBuffer(camHand,byref(sBufNr),byref(im_ptr),byref(ev_ptr))
		#pdb.set_trace()
		#if res5 :
		#   print 'PCO_GetBuffer failed'
		
		if act_recState.value == 0:
			print 'Stop Camera'
			res6 = LIB.PCO_SetRecordingState(camHand,0)
			if res6():
				print 'PCO_SetRecordingState failed'
		
		res7 = LIB.PCO_FreeBuffer(camHand,sBufNr)
		if res7():
			print 'PCO_FreeBuffer failed'
		
		del ev_ptr
		
		#return (res7,image_stack)


	def get_image_multi(self,camHand,imacount,act_xsize,act_ysize,bitpix,interface):
		print '********GET IMAGE MULTI********'
		if imacount<2:
			print 'Wrong image count, must be 2 or greater, return'
			return
		
		act_recState = c_ushort(10)
		res1 = LIB.PCO_GetRecordingState(camHand,byref(act_recState))
		if res1():
			print 'PCO_GetRecordingState failed'
		
		# get the memory for the images
		imas=c_uint32(numpy.fix((c_double(bitpix.value).value+7.)/8.))
		imas= imas.value*c_uint32(act_ysize.value).value* c_uint32(act_xsize.value).value; 
		imasize=c_uint(imas)
		lineadd=0
		
		#self.image_stack=ones((imacount,act_ysize.value+lineadd,act_xsize.value),dtype=uint16)
		
		self.image_stack_v=numpy.zeros((imacount,act_ysize.value+lineadd,act_xsize.value),dtype=numpy.uint16)
		#self.image_stack_2=zeros((imacount,act_ysize.value+lineadd,act_xsize.value),dtype=uint16)

		# Allocate 2 SDK buffer and set address of buffers in stack
		sBufNr_1 = c_short(-1)
		im_ptr_1 = self.image_stack_v[0,:,:].ctypes.data_as(POINTER(c_ushort))
		ev_ptr_1 = c_void_p()
		#pdb.set_trace()
		res2 = LIB.PCO_AllocateBuffer(camHand,byref(sBufNr_1),imasize,byref(im_ptr_1),byref(ev_ptr_1))
		if res2():
			print 'PCO_AllocateBuffer 1 failed'
		
		sBufNr_2 = c_short(-1)
		im_ptr_2 = self.image_stack_v[1,:,:].ctypes.data_as(POINTER(c_ushort))
		ev_ptr_2 = c_void_p()
		#pdb.set_trace()
		res3 = LIB.PCO_AllocateBuffer(camHand,byref(sBufNr_2),imasize,byref(im_ptr_2),byref(ev_ptr_2))
		if res3():
			print 'PCO_AllocateBuffer 2 failed'
			LIB.PCO_FreeBuffer(camHand,sBufNr_1)
		
		print 'bufnr1: ',str(sBufNr_1.value),' bufnr2: ',str(sBufNr_2.value)
		buflist_1 = LIB.PCO_Buflist(sBufNr_1,)
		buflist_2 = LIB.PCO_Buflist(sBufNr_2,)
		print 'bufnr1: ',str(buflist_1.sBufNr),' bufnr2: ',str(buflist_2.sBufNr)
		
		if act_recState.value == 0:
			print 'Start Camera and grab images'
			res3 = LIB.PCO_SetRecordingState(camHand,1)
			if res3():
				print 'PCO_SetRecordingState failed'
		
		#nb1 = 0
		#nb2 = 0
		res4 = LIB.PCO_AddBufferEx(camHand,c_uint(0),c_uint(0),sBufNr_1,act_xsize,act_ysize,c_ushort(bitpix.value))
		if res4():
			print 'PCO_AddBufferEx failed'
		#print 'added buffer 1-%d' % nb1
		res5 = LIB.PCO_AddBufferEx(camHand,c_uint(0),c_uint(0),sBufNr_2,act_xsize,act_ysize,c_ushort(bitpix.value))
		if res5():
			print 'PCO_AddBufferEx failed'
		#print 'added buffer 2-%d' % nb2
		
		#nstore=0
		for n in range(imacount):
			#print n
			if n%2==0:
				#print 'Wait for buffer 1 :',str(n)
				res6 = LIB.PCO_WaitforBuffer(camHand,c_int(1),byref(buflist_1),c_int(5000))
				#print 'buffer 1-%d read' % nb1
				#nb1+=1
				if res6():
					print 'PCO_WaitforBuffer 1 failed'
					break
				#print 'statusdll : %08X , statusdrv : %08X ' % (buflist_1.dwStatusDll,buflist_1.dwStatusDrv)
				if (buflist_1.dwStatusDll&int(0x0008000)) and (buflist_1.dwStatusDrv ==0 ):
					#res7 = PCO_CAM_SDK.PCO_GetBuffer(camHand,byref(sBufNr_1),byref(im_ptr_1),byref(ev_ptr_1))
					#pdb.set_trace()
					#if res7 :
					#	print 'PCO_GetBuffer failed'
					#	break
					#
					#ima_1 = copy(image_stack_1)
					buflist_1.dwStatusDll= (buflist_1.dwStatusDll & int(0xFFFF7FFF))
					if (n+2)<(imacount):
						im_ptr_1 = self.image_stack_v[n+2,:,:].ctypes.data_as(POINTER(c_ushort))
						res8 = LIB.PCO_AllocateBuffer(camHand,byref(sBufNr_1),imasize,byref(im_ptr_1),byref(ev_ptr_1))
						if res8():
							print 'PCO_AllocateBuffer 3 failed'
							break
						res9 = LIB.PCO_AddBufferEx(camHand,c_uint(0),c_uint(0),sBufNr_1,act_xsize,act_ysize,c_ushort(bitpix.value))
						#print 'added buffer 1-%d' % nb1
						if res9():
							print 'PCO_AddBufferEx failed'
							break
			else:
				#print 'Wait for buffer 2 :',str(n)
				res10 = LIB.PCO_WaitforBuffer(camHand,c_int(1),byref(buflist_2),c_int(5000))
				#print 'buffer 2-%d read' % nb2
				#nb2+=1
				if res10():
					print 'PCO_WaitforBuffer 2 failed'
					break
				#print 'statusdll : %08X , statusdrv : %08X ' % (buflist_1.dwStatusDll,buflist_1.dwStatusDrv)
				if (buflist_2.dwStatusDll&int(0x0008000)) and (buflist_2.dwStatusDrv ==0 ):
					#res11 = PCO_CAM_SDK.PCO_GetBuffer(camHand,byref(sBufNr_2),byref(im_ptr_2),byref(ev_ptr_2))
					#pdb.set_trace()
					#if res11 :
					#	print 'PCO_GetBuffer failed'
					#	break
					#ima_2 = copy(image_stack_2)
					buflist_2.dwStatusDll= (buflist_2.dwStatusDll & int(0xFFFF7FFF))
					if (n+2)<(imacount):
						im_ptr_2 = self.image_stack_v[n+2,:,:].ctypes.data_as(POINTER(c_ushort))
						res12 = LIB.PCO_AllocateBuffer(camHand,byref(sBufNr_2),imasize,byref(im_ptr_2),byref(ev_ptr_2))
						if res12():
							print 'PCO_AllocateBuffer 4 failed'
							break
						res13 = LIB.PCO_AddBufferEx(camHand,c_uint(0),c_uint(0),sBufNr_2,act_xsize,act_ysize,c_ushort(bitpix.value))
						#print 'added buffer 2-%d' % nb2
						if res13():
							print 'PCO_AddBufferEx failed'
							break
				#self.image_stack[nstore,:,:] = (ima_1 + ima_2)
				#self.image_stack[nstore,0,0:14] = ima_1[0,0:14]
				#nstore+=1
			
		if act_recState.value == 0:
			print 'Stop Camera'
			res14 = LIB.PCO_SetRecordingState(camHand,0)
			if res14():
				print 'PCO_SetRecordingState failed'
		
		res13 = LIB.PCO_CancelImages(camHand)
		if res13():
			print 'PCO_CancelImages failed'
		
		res15 = LIB.PCO_FreeBuffer(camHand,sBufNr_1)
		if res15():
			print 'PCO_FreeBuffer failed'
		res16 = LIB.PCO_FreeBuffer(camHand,sBufNr_2)
		if res16():
			print 'PCO_FreeBuffer failed'
		
		#del ev_ptr
		
		#return (res16,image_stack)


<<<<<<< HEAD

=======
	def return_single_image(self):
		return self.image_stack


	def return_images(self,tempBin=1):
		# create a mask such that time-stamps does not get averaged 
		mask = numpy.copy(self.image_stack_v[0])
		mask[:] = 1
		mask[0,0:14] = 0 
		mask = numpy.array(mask,dtype=bool)
		#
		if tempBin==2:
			for n in range(int(self.imacount)/2):
				self.image_stack_v[2*n][mask] = (self.image_stack_v[2*n]/2. + self.image_stack_v[2*n+1]/2.)[mask]
			return self.image_stack_v[::2][:int(self.imacount)/2]
		#	tmp = self.image_stack_v[::2]+self.image_stack_v[1::2]
		elif tempBin==3:
			for n in range(int(self.imacount)/3):
				self.image_stack_v[3*n][mask] = (self.image_stack_v[3*n]/3. + self.image_stack_v[3*n+1]/3. + self.image_stack_v[3*n+2]/3.)[mask]
			return self.image_stack_v[::3][:int(self.imacount)/3]
		#	tmp = self.image_stack_v[::2]+self.image_stack_v[1::2]
		elif tempBin==4:
			for n in range(int(self.imacount)/4):
				self.image_stack_v[4*n][mask] = (self.image_stack_v[4*n]/4. + self.image_stack_v[4*n+1]/4. + self.image_stack_v[4*n+2]/4. + self.image_stack_v[4*n+3]/4.)[mask]
			return self.image_stack_v[::4][:int(self.imacount)/4]
		#	tmp = self.image_stack_v[::2]+self.image_stack_v[1::2]
		elif tempBin==1:
			return self.image_stack_v
		else:
			print 'temporal Bin is not supported!'
			return self.image_stack_v


>>>>>>> 4930397f4242796ab5d8950394760f20803a7aea
