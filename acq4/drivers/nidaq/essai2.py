# -*- coding: cp1252 -*-
import sys, time, os
import numpy as np
modPath = os.path.split(__file__)[0]
acq4Path = os.path.abspath(os.path.join(modPath, '..', '..', '..'))
utilPath = os.path.join(acq4Path, 'lib', 'util')
sys.path = [acq4Path, utilPath] + sys.path
from nidaq import LIB as lib
import acq4.util.ptime as ptime
import math
import ctypes


if sys.argv[-1] == 'mock':
    from mock import NIDAQ as n
else:
    from nidaq import NIDAQ as n


########################################################################
def AOut_taskSin():
    print "======Genere un sinus sur la sortie ao0======"

###Methode 1
##
##    while 1:
##        x=0
##        s=np.zeros(361)
##        while x < 361:
##            s[x]=x
##            data = np.sin(math.radians(np.array(s[x])))*10 #Le *10 c'est pour l'amplitude
##            n.writeAnalogSample("/Dev1/ao0",data)
##            x+=1
##
###SIgnal lent 2Hz    

    
#Methode 2#
    t = n.createTask()
    t.CreateAOVoltageChan("/Dev1/ao0", "", -10.,10., n.Val_Volts, None)#On cree le channel 
    t.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_ContSamps, 50000) #on cfg l'echantillonage pour ecrire dans le channel. 1000 est le nombre d'echantillon genere(ici)/acquiere pour ce channel(FINITE)/remplir le buffer (CONTINUOS)

    x=0
    s=np.zeros(361)
    while 1:                
        while x < 361:
            s[x]=x
            x+=1  
        data = np.sin(np.array(s) * np.pi / 180. )
        
        t.write(data)#ecris data dans le channel
        t.start()#Demarre la tache
        time.sleep(0.2)#tempo pour aquérir/génerer les echatillons/remplir le buffer
        #t.stop()#Pas de stop génère une errreur mais le signal est régulier
    

#Probleme de régularité a cause du start stop.


########################################################################

def AOut_taskRamp():
    print "======Genere une Ramp sur la sortie ao0======"

    t = n.createTask()
    t.CreateAOVoltageChan("/Dev1/ao0", "", -10.,10., n.Val_Volts, None)#On cree le channel 
    t.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_ContSamps, 50000) #on cfg l'echantillonage pour ecrire dans le channel. 1000 est le nombre d'echantillon genere(ici)/acquiere pour ce channel(FINITE)/remplir le buffer (CONTINUOS)
    while 1:        
        data = np.linspace(-np.pi, np.pi, 201) 
        t.write(data)#ecris data dans le channel
        t.start()#Demarre la tache
        time.sleep(0.2)#tempo pour aquérir/génerer les echatillons/remplir le buffer
        t.stop()#Pas de stop génère une errreur mais le signal est régulier

########################################################################
def AOut_taskDC(Volt):
    print "======Genere une tension continue sur la sortie ao0======"
    t = n.createTask()
    t.CreateAOVoltageChan("/Dev1/ao0", "", -10.,10., n.Val_Volts, None)#On cree le channel 
    t.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_ContSamps, 50000)

    data=np.zeros(1000)
    data [0:1000] = Volt
    
    t.write(data)#ecris data dans le channel
    t.start()#Demarre la tache
    time.sleep(0.2)#tempo pour aquérir/génerer les echatillons/remplir le buffer
    t.stop()#Pas de stop génère une errreur mais le signal est régulier

########################################################################
def AOut_taskSquare():
    print "======Genere un signal carré sur la sortie ao0======"
    
    t = n.createTask()
    t.CreateAOVoltageChan("/Dev1/ao0", "", -10.,10., n.Val_Volts, None)#On cree le channel 
    t.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_ContSamps, 50000)
    
    while 1:
        cpt = 1# ici cpt influe sur la fréquence celon la vitesse à la quelle il s'incremente MAX 5kHz cpt = cpt + 1
        verif_init = 0
        etat_H=0
        etat_L = 0
        data=np.zeros(1000.)    
        while cpt <1000:
            if verif_init ==0 :
                data[0:2]= 5
                verif_init = 1
                etat_H=1
            if etat_H==1:
                data[cpt:cpt+1]=0
                etat_L = 1
                etat_H= 0
            cpt = cpt +1           
            if etat_L == 1:
                data[cpt:cpt+1]=5
                etat_L = 0
                etat_H= 1
            cpt = cpt +1
        
        t.write(data)#ecris data dans le channel
        t.start()#Demarre la tache
        time.sleep(0.2)#tempo pour aquérir/génerer les echatillons/remplir le buffer
        #t.stop() 
        
        
    
#Probleme de régularité a cause du start stop....... Mais je peux controler la fréquence  en changant le vecteur data.

########################################################################
def AOut_taskPulseSquare():
    print "======Genere une impulsion sur la sortie ao0======"

    t = n.createTask()
    t.CreateAOVoltageChan("/Dev1/ao0", "", -10.,10., n.Val_Volts, None)#On cree le channel 
    t.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_FiniteSamps, 1000)

    data=np.zeros(1000.)  
    data[30:130]=5
    
    t.write(data)#ecris data dans le channel
    t.start()#Demarre la tache
    time.sleep(0.2)#tempo pour aquérir/génerer les echatillons/remplir le buffer
    t.stop() 
    

########################################################################        
    
def AIn_task():
    print "======Lis ce qu'il y a en entrée ai0======"

    t = n.createTask()
    t.CreateAIVoltageChan("/Dev1/ai0", "", n.Val_RSE, -1., 1., n.Val_Volts, None)
    t.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_FiniteSamps, 1000)#on cfg l'echantillonage pour ecrire dans le channel ici le 1000 est le nombre d'echantillon genere/acquiere(ici) pour ce channel
    t.start()
    data = t.read()
    t.stop()
    
    return data

########################################################################
def Count_RE():
    print "======Compte le nombre de front montant sur Ctr0(PFI8) A besoin d'une clock sur PFI7 pour fonctionner et génère une impulsion sur ao0======"

    t1 = n.createTask()
    t1.CreateCICountEdgesChan("/Dev1/ctr0", "", n.Val_Rising, 0, n.Val_CountUp)
    t1.CfgSampClkTiming("/Dev1/PFI7", 1500000.0, n.Val_Rising, n.Val_FiniteSamps, 1000)
    t2 = n.createTask()
    t2.CreateAOVoltageChan("/Dev1/ao0", "", -10.,10., n.Val_Volts, None)#On cree le channel 
    t2.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_FiniteSamps, 1000)

    pulse=np.zeros(1000.)
    pulse[0:1000]=5
    data = (ctypes.c_ulong*1000)()
    data2 = (ctypes.c_long*1)()
    
    t2.write(pulse)#ecris data dans le channel
    t1.start()
    t2.start()
    t1.ReadCounterU32(n.Val_Auto,1.0,data,1000,data2,None)
    t1.stop()
    t2.stop()
    
    return data

#Cette fonction prend 1000 échantillion d'un signal. Une fois ces echantillon pris, elle compte le nombre de front montant qu'il ya dans un échantillon puis range cette valeur dans un  puis fait la meme chose avec le deuxième en faisant la somme a chaque fois. !
#SI le signal clock_sampling à la meme fréqunce que le signal qui genere les front montant alors il y aura 1 front montant par échantillion.

########################################################################
def countPhotonTaskTest():
    #    Note: An external sample clock must be used. Counters do not
    #          have an internal sample clock available. You can use the
    #          Gen Dig Pulse Train-Continuous example to generate a pulse
    #          train on another counter and connect it to the Sample
    #          Clock Source you are using in this example.
    
    tPulses = n.createTask()
    tPulses.CreateCOPulseChanFreq("Dev1/ctr1","",n.Val_Hz,n.Val_Low,0.0,10000.,0.50)
    tPulses.CfgImplicitTiming(n.Val_ContSamps,1000)
    
    tCount = n.createTask()
    tCount.CreateCICountEdgesChan("/Dev1/ctr0", "", n.Val_Rising, 0, n.Val_CountUp)
    tCount.CfgSampClkTiming("/Dev1/ctr1InternalOutput", 10000., n.Val_Rising, n.Val_FiniteSamps, 1000)
    
    tPulses.start()
    tCount.start()
    counts = tCount.read()
    #t.ReadCounterU32(n.Val_Auto,10.0,data,1000,data2,None)
    #counts = t.read()
    
    tPulses.stop()
    tCount.stop()

    return counts

########################################################################
def countPhotonTaskAnalogOutputTest():
    #    Note: An external sample clock must be used. Counters do not
    #          have an internal sample clock available. You can use the
    #          Gen Dig Pulse Train-Continuous example to generate a pulse
    #          train on another counter and connect it to the Sample
    #          Clock Source you are using in this example.
    
    task = n.createTask()
    task.CreateAOVoltageChan("/Dev1/ao0", "", -10., 10., n.Val_Volts, None)
    task.CfgSampClkTiming(None, 100.0, n.Val_Rising, n.Val_FiniteSamps, 300)
    #tPulses = n.createTask()
    #tPulses.CreateCOPulseChanFreq("Dev1/ctr1","",n.Val_Hz,n.Val_Low,0.0,10000.,0.50)
    #tPulses.CfgImplicitTiming(n.Val_ContSamps,1000)
    
    tCount = n.createTask()
    tCount.CreateCICountEdgesChan("/Dev1/ctr0", "", n.Val_Rising, 0, n.Val_CountUp)
    tCount.CfgSampClkTiming("/Dev1/ao/SampleClock", 100.0, n.Val_Rising, n.Val_FiniteSamps, 300)
    
    data = np.zeros((200,), dtype=np.float64)
    data[40:50] = 5.0
    task.write(data)
    #task.start()
    
    #task.stop()
    
    #tPulses.start()
    tCount.start()
    task.start()
    time.sleep(5)
    counts = tCount.read()
    #t.ReadCounterU32(n.Val_Auto,10.0,data,1000,data2,None)

    
    #tPulses.stop()
    tCount.stop()
    task.stop()

    return counts
      
########################################################################
st = n.createSuperTask()
def superTaskTest():
    print "::::::::::::::::::  SuperTask  Test  :::::::::::::::::::::"

    st.addChannel('/Dev1/ctr0','ci')
   
    st.addChannel('/Dev1/ao0', 'ao')

    ao = np.zeros((1000,), dtype=np.float64)
    ao[400:500] = 5.0

    st.setWaveform('/Dev1/ao0', ao)

    st.configureClocks(rate=1000, nPts=1000)

    data = st.run()
    for k in data:
        if k[1] in ["ai","di","ci"]:
            print "****Input****", k
        else:
            print "****Output****", k
        print data[k]['data']
    return data


    

data = superTaskTest()



