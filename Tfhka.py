# -*- coding: iso-8859-1 -*-

from .ReportData import ReportData
from .S1PrinterData import S1PrinterData
from .S2PrinterData import S2PrinterData
from .S3PrinterData import S3PrinterData
from .S4PrinterData import S4PrinterData
from .S5PrinterData import S5PrinterData
from .S6PrinterData import S6PrinterData
from .S7PrinterData import S7PrinterData
from .S8EPrinterData import S8EPrinterData
from .S8PPrinterData import S8PPrinterData
from .AcumuladosX import AcumuladosX
from functools import reduce

import serial
import operator
import time
import datetime

import sys
import glob
import os


class Port:
  def __init__(self):
      self.portName = "COM4"
      self.baudRate = 9600
      self.dataBits = serial.EIGHTBITS
      self.stopBits = serial.STOPBITS_ONE
      self.parity = serial.PARITY_EVEN
      self.readBufferSize = 256
      self.writeBufferSize = 256
      self.readTimeOut = 1.5
      self.writeTimeOut = 5

class TfVeIfPython:
  def __init__(self):
      self.bandera = False
      self.mdepura = False
      self.status = ''
      self.envio = ''
      self.error = ''
      self.Port = Port()
    
class Tfhka(TfVeIfPython):      
#Funcion ABRIR
  def OpenFpctrl(self, p):
    if not self.bandera:
      try:
        self.ser=serial.Serial(port=p, baudrate=self.Port.baudRate, bytesize=self.Port.dataBits, parity=self.Port.parity, stopbits=self.Port.stopBits, timeout=self.Port.readTimeOut, writeTimeout=self.Port.writeTimeOut, xonxoff=0, rtscts=0)##Find out what are xonxoff, and rtscts for
        #print "baudrate", self.Port.baudRate
        self.bandera=True
        return True
      except (serial.portNotOpenError, serial.SerialTimeoutException):
        self.bandera=False
        self.envio = "Impresora no conectada o error accediendo al puerto" + str(p)
        return False

#Funcion CERRAR
  def CloseFpctrl(self):
    if self.bandera:
      self.ser.close()
      self.bandera=False
      return self.bandera

#Funcion MANIPULA
  def _HandleCTSRTS(self):
    try:
      self.ser.setRTS(True)
      lpri=1
      while not self.ser.getCTS():
        time.sleep(lpri/10)
        lpri=lpri+1
        if lpri>20:
          self.ser.setRTS(False)
          return False
      return True
    except serial.SerialException:
      return False

  def SendCmd(self,cmd):
    if cmd == "I0X" or cmd == "I1X" or cmd == "I1Z":
      self.trama = self._States_Report(cmd,4)
      return self.trama
    if cmd == "I0Z":
      self.trama = self._States_Report(cmd,9)
      return self.trama
    else:
      try:
        self.ser.flushInput()
        self.ser.flushOutput()
        if self._HandleCTSRTS():
          msj=self._AssembleQueryToSend(cmd)
          self._write(msj)
          rt=self._read(1)
          if rt==chr(0x06):
            self.envio = "Status: 00  Error: 00"
            rt=True
          else:
            self.envio = "Status: 00  Error: 89"
            rt=False
        else:
          self._GetStatusError(0, 128);
          self.envio = "Error... CTS in False"
          rt=False
        self.ser.setRTS(False)
      except serial.SerialException:
        rt=False
      return rt

  def SendCmdFile(self, f):
    for linea in f:
       if (linea!=""):
          #print linea
          self.SendCmd(linea)

  def _QueryCmd(self,cmd):
      try:
         self.ser.flushInput()
         self.ser.flushOutput()
         if self._HandleCTSRTS():
            msj=self._AssembleQueryToSend(cmd)
            self._write(msj)
            rt=True
         else:
            self._GetStatusError(0, 128);
            self.envio = "Error... CTS in False"
            rt=False
            self.ser.setRTS(False)
      except serial.SerialException:
         rt=False
      return rt

  def _FetchRow(self):
    while True:
      time.sleep(1)
      bytes = self.ser.inWaiting()
      if bytes>=1:
        msj=self._read(bytes)
        linea=msj[1:-1]
        lrc=chr(self._Lrc(linea))
        if lrc==msj[-1]:
          self.ser.flushInput()
          self.ser.flushOutput()
          return msj
        else:
          break
      else:
        break
    return None

  def _FetchRow_Report(self, r):
    while True:
      time.sleep(r)
      bytes = self.ser.inWaiting()
      if bytes>0:
        msj=self._read(bytes)
        linea=msj
        lrc=chr(self._Lrc(linea))
        if lrc==msj:
          self.ser.flushInput()
          self.ser.flushOutput()
          return msj
        else:
          return msj
          break
      else:
        break
    return None

  def ReadFpStatus(self):
    if self._HandleCTSRTS():
      msj=chr(0x05)
      self._write(msj)
      time.sleep(0.05)
      r=self._read(5)
      if len(r)==5:
        if ord(r[1])^ord(r[2])^0x03 == ord(r[4]):
          return self._GetStatusError(ord(r[1]), ord(r[2]))
        else:
          return self._GetStatusError(0, 144)
      else:
        return self._GetStatusError(0, 114)
    else:
      return self._GetStatusError(0, 128)

  def _write(self,msj):
    if self.mdepura:
      print ('<<< '+self._Debug(msj))
    self.ser.write(msj)

  def _read(self,bytes):
    msj = self.ser.read(bytes)
    if self.mdepura:
      print ('>>>'+ self._Debug(msj))
    return msj

  def _AssembleQueryToSend(self, linea):
    lrc = self._Lrc(linea + chr(0x03))
    previo = chr(0x02) + linea + chr(0x03) + chr(lrc)
    # Convertir previo a bytes con ISO-8859-15
    previo_bytes = previo.encode('iso-8859-15')
    return previo_bytes

  def _Lrc(self, linea):
    if not linea:  # Verifica si linea está vacía
        return 0  # O el valor inicial adecuado según tu lógica
    
    return reduce(operator.xor, map(ord, linea))

  def _Debug(self,linea):
    if linea!=None:
      if len(linea)==0:
        return 'null'
      if len(linea)>3:
        lrc=linea[-1]
        linea=linea[0:-1]
        adic=' LRC('+str(ord(lrc))+')'
      else:
        adic=''
      linea=linea.replace('STX',chr(0x02),1)
      linea=linea.replace('ENQ',chr(0x05),1)
      linea=linea.replace('ETX',chr(0x03),1)
      linea=linea.replace('EOT',chr(0x04),1)
      linea=linea.replace('ACK',chr(0x06),1)
      linea=linea.replace('NAK',chr(0x15),1)
      linea=linea.replace('ETB',chr(0x17),1)
      linea_byte = linea.encode('iso-8859-15')
      adic_byte = adic.encode('iso-8859-15')
    return linea_byte+adic_byte

  def _States(self, cmd):
    #print cmd
    self._QueryCmd(cmd)
    while True:
      trama=self._FetchRow()
      #print "La trama es", trama, "hasta aca"
      if trama==None:
        break
      return trama

  def _States_Report(self, cmd, r):
    #print cmd
    ret = r
    self._QueryCmd(cmd)
    while True:
      trama=self._FetchRow_Report(ret)
      #print "La trama es", trama, "hasta aca"
      if trama==None:
        break
      return trama

  def _UploadDataReport(self, cmd):
    try:
        self.ser.flushInput()
        self.ser.flushOutput()
        
        if self._HandleCTSRTS():
            msj = self._AssembleQueryToSend(cmd)
            self._write(msj)
            rt = self._read(1)
            ra = chr(0x05)
            ra_bytes = ra.encode('iso-8859-15')
            while rt == ra_bytes:
                time.sleep(0.05)
                self._write(self._Debug('ACK'))  # Envía ACK de debug
                
                time.sleep(0.05)
                msj = self._FetchRow()  # Intenta obtener datos de fila (¿esto es necesario?)
                
                return msj  # Devuelve msj si se recibe ACK correctamente
            
            # Si no se recibe ACK o rt no es chr(0x05)
            self._GetStatusError(0, 128)
            self.envio = "Error... CTS in False"
            self.ser.setRTS(False)
    except serial.SerialException:
        rt = None
    
    return rt  # Devuelve rt al finalizar la función

  def _ReadFiscalMemoryByNumber(self, cmd):
    msj=""
    arreglodemsj=[]
    counter=0
    try:
      self.ser.flushInput()
      self.ser.flushOutput()
      if self._HandleCTSRTS():
         m=""
         msj=self._AssembleQueryToSend(cmd)
         self._write(msj)
         rt=self._read(1)
         while True:
            while msj!= chr(0x04):
               time.sleep(0.5)
               msj=self._Debug('ACK')
               self._write(msj)
               time.sleep(0.5)
               msj=self._FetchRow_Report(1.3)
               if(msj==None):
                 counter+=1
               else:
                 arreglodemsj.append(msj)
            return arreglodemsj
      else:
         self._GetStatusError(0, 128)
         self.envio = "Error... CTS in False"
         m=None
         self.ser.setRTS(False)
    except serial.SerialException:
       m=None
    return m

  def _ReadFiscalMemoryByDate(self, cmd):
    msj=""
    arreglodemsj=[]
    counter=0
    try:
      self.ser.flushInput()
      self.ser.flushOutput()
      if self._HandleCTSRTS():
         m=""
         msj=self._AssembleQueryToSend(cmd)
         self._write(msj)
         rt=self._read(1)
         while True:
            while msj!= chr(0x04):
               time.sleep(0.5)
               msj=self._Debug('ACK')
               self._write(msj)
               time.sleep(0.5)
               msj=self._FetchRow_Report(1.5)
               if(msj==None):
                 counter+=1
               else:
                 arreglodemsj.append(msj)
            return arreglodemsj
      else:
         self._GetStatusError(0, 128)
         self.envio = "Error... CTS in False"
         m=None
         self.ser.setRTS(False)
    except serial.SerialException:
       m=None
    return m

  def _GetStatusError(self,st,er):
    st_aux = st
    st = st & ~0x04

    if   (st & 0x6A) == 0x6A: #En modo fiscal, carga completa de la memoria fiscal y emisi�n de documentos no fiscales
      self.status='En modo fiscal, carga completa de la memoria fiscal y emisi�n de documentos no fiscales'
      status = "12"
    elif (st & 0x69) == 0x69: #En modo fiscal, carga completa de la memoria fiscal y emisi�n de documentos  fiscales
      self.status='En modo fiscal, carga completa de la memoria fiscal y emisi�n de documentos  fiscales'
      status = "11"
    elif (st & 0x68) == 0x68: #En modo fiscal, carga completa de la memoria fiscal y en espera
      self.status='En modo fiscal, carga completa de la memoria fiscal y en espera'
      status = "10"
    elif (st & 0x72) == 0x72: #En modo fiscal, cercana carga completa de la memoria fiscal y en emisi�n de documentos no fiscales
      self.status='En modo fiscal, cercana carga completa de la memoria fiscal y en emisi�n de documentos no fiscales'
      status = "9 "
    elif (st & 0x71) == 0x71: #En modo fiscal, cercana carga completa de la memoria fiscal y en emisi�n de documentos no fiscales
      self.status='En modo fiscal, cercana carga completa de la memoria fiscal y en emisi�n de documentos no fiscales'
      status = "8 "
    elif (st & 0x70) == 0x70: #En modo fiscal, cercana carga completa de la memoria fiscal y en espera
      self.status='En modo fiscal, cercana carga completa de la memoria fiscal y en espera'
      status = "7 "
    elif (st & 0x62) == 0x62: #En modo fiscal y en emisi�n de documentos no fiscales
      self.status='En modo fiscal y en emisi�n de documentos no fiscales'
      status = "6 "
    elif (st & 0x61) == 0x61: #En modo fiscal y en emisi�n de documentos fiscales
      self.status='En modo fiscal y en emisi�n de documentos fiscales'
      status = "5 "
    elif (st & 0x60) == 0x60: #En modo fiscal y en espera
      self.status='En modo fiscal y en espera'
      status = "4 "
    elif (st & 0x42) == 0x42: #En modo prueba y en emisi�n de documentos no fiscales
      self.status='En modo prueba y en emisi�n de documentos no fiscales'
      status = "3 "
    elif (st & 0x41) == 0x41: #En modo prueba y en emisi�n de documentos fiscales
      self.status='En modo prueba y en emisi�n de documentos fiscales'
      status = "2 "
    elif (st & 0x40) == 0x40: #En modo prueba y en espera
      self.status='En modo prueba y en espera'
      status = "1 "
    elif (st & 0x00) == 0x00: #Status Desconocido
      self.status='Status Desconocido'
      status = "0 "

    if   (er & 0x6C) == 0x6C: #Memoria Fiscal llena
      self.error = 'Memoria Fiscal llena'
      error = "108"
    elif (er & 0x64) == 0x64: #Error en memoria fiscal
      self.error = 'Error en memoria fiscal'
      error = "100"
    elif (er & 0x60) == 0x60: #Error Fiscal
      self.error = 'Error Fiscal'
      error = "96 "
    elif (er & 0x5C) == 0x5C: #Comando Invalido
      self.error = 'Comando Invalido'
      error = "92 "
    elif (er & 0x58) == 0x58: # No hay asignadas  directivas
      self.error = 'No hay asignadas  directivas'
      error = "88 "
    elif (er & 0x54) == 0x54: #Tasa Invalida
      self.error = 'Tasa Invalida'
      error = "84 "
    elif (er & 0x50) == 0x50: #Comando Invalido/Valor Invalido
      self.error = 'Comando Invalido/Valor Invalido'
      error = "80 "
    elif (er & 0x43) == 0x43: #Fin en la entrega de papel y error mec�nico
      self.error = 'Fin en la entrega de papel y error mec�nico'
      error = "3  "
    elif (er & 0x42) == 0x42: #Error de indole mecanico en la entrega de papel
      self.error = 'Error de indole mecanico en la entrega de papel'
      error = "2  "
    elif (er & 0x41) == 0x41: #Fin en la entrega de papel
      self.error = 'Fin en la entrega de papel'
      error = "1  "
    elif (er & 0x40) == 0x40: #Sin error
      self.error = 'Sin error'
      error = "0  "

    if (st_aux & 0x04) == 0x04: #Buffer Completo
      self.error = ''
      error = "112 "
    elif er == 128:     # Error en la comunicacion
      self.error = 'CTS en falso'
      error = "128 "
    elif er == 137:     # No hay respuesta
      self.error = 'No hay respuesta'
      error = "137 "
    elif er == 144:     # Error LRC
      self.error = 'Error LRC'
      error = "144 "
    elif er == 114:
      self.error = 'Impresora no responde o ocupada'
      error = "114 "
    return status+"   " +error+"   " +self.error

  def GetS1PrinterData(self):
    self.trama=self._States("S1")
    #print self.trama
    self.S1PrinterData = S1PrinterData(self.trama)
    #print self.S1PrinterData
    return self.S1PrinterData

  def GetS2PrinterData(self):
    self.trama=self._States("S2")
    #print self.trama
    self.S2PrinterData= S2PrinterData(self.trama)
    return self.S2PrinterData

  def GetS3PrinterData(self):
    self.trama=self._States("S3")
    #print self.trama
    self.S3PrinterData= S3PrinterData(self.trama)
    return self.S3PrinterData
  
  def GetS4PrinterData(self):
    self.trama=self._States("S4")
    #print self.trama
    self.S4PrinterData= S4PrinterData(self.trama)
    return self.S4PrinterData
  
  def GetS5PrinterData(self):
    self.trama=self._States("S5")
    #print self.trama
    self.S5PrinterData= S5PrinterData(self.trama)
    return self.S5PrinterData
  
  def GetS6PrinterData(self):
    self.trama=self._States("S6")
    #print self.trama
    self.S6PrinterData= S6PrinterData(self.trama)
    return self.S6PrinterData
  
  def GetS7PrinterData(self):
    self.trama=self._States("S7")
    #print self.trama
    self.S7PrinterData= S7PrinterData(self.trama)
    return self.S7PrinterData

  def GetS8EPrinterData(self):
    self.trama=self._States("S8E")
    #print self.trama
    self.S8EPrinterData= S8EPrinterData(self.trama)
    return self.S8EPrinterData
  
  def GetS8PPrinterData(self):
    self.trama=self._States("S8P")
    #print self.trama
    self.S8PPrinterData= S8PPrinterData(self.trama)
    return self.S8PPrinterData
  
  def GetXReport(self):
    self.trama=self._UploadDataReport("U0X")
    #print self.trama
    self.XReport=ReportData(self.trama)
    return self.XReport

  def GetX2Report(self):
    self.trama=self._UploadDataReport("U1X")
    #print self.trama
    self.XReport=ReportData(self.trama)
    return self.XReport

  def GetX4Report(self):
    self.trama=self._UploadDataReport("U0X4")
    #print self.trama
    self.XReport=AcumuladosX(self.trama)
    return self.XReport

  def GetX5Report(self):
    self.trama=self._UploadDataReport("U0X5")
    #print self.trama
    self.XReport=AcumuladosX(self.trama)
    return self.XReport

  def GetX7Report(self):
    self.trama=self._UploadDataReport("U0X7")
    #print self.trama
    self.XReport=AcumuladosX(self.trama)
    return self.XReport

  def GetZReport(self, *items): #(self, mode, startParam, endParam): #(self, startDate, endDate):
    if(len(items)>0):
      mode=items[0]
      startParam=items[1]
      endParam=items[2]
      if (type(startParam)==datetime.date and type(endParam)==datetime.date):
        starString=startParam.strftime("%d%m%y")
        endString=endParam.strftime("%d%m%y")
        cmd="U2"+mode+starString+endString
        self.trama=self._ReadFiscalMemoryByDate(cmd)
      else:
        starString = str(startParam)
        while (len(starString) < 6):
          starString = "0" + starString
        endString = str(endParam)
        while (len(endString) < 6):
          endString = "0" + endString
        cmd="U3"+mode+starString+endString
        self.trama=self._ReadFiscalMemoryByNumber(cmd)
      self.ReportData=[]
      i=0
      for report in self.trama[0:-1]:
        self.Z=ReportData(report)        
        self.ReportData.append(self.Z)
        i+=1
    else:
      self.trama=self._UploadDataReport("U0Z")
      self.ReportData=ReportData(self.trama)       
    return self.ReportData
  
  def PrintXReport(self):
    self.trama = self._States_Report("I0X",4)
    return self.trama
    
  def PrintZReport(self, *items): #(self, mode, startParam, endParam):
    if(len(items)>0):
      mode=items[0]
      startParam=items[1]
      endParam=items[2]

      rep=False

      if (type(startParam)==datetime.date and type(endParam)==datetime.date): #if(type(startParam)==int and (type(endParam)==int)):
        starString=startParam.strftime("%d%m%y")
        endString=endParam.strftime("%d%m%y")
        cmd="I2"+mode+starString+endString
        rep = self.SendCmd("I2" + mode + starString + endString)
      else:
        starString = str(startParam)
        while (len(starString) < 6):
          starString = "0" + starString
        endString = str(endParam)
        while (len(endString) < 6):
          endString = "0" + endString
        rep = self.SendCmd("I3" + mode + starString + endString)
        if (rep==False):
          if (starString > endString):
            estado = "The original number can not be greater than the final number" #raise(Estado)
    else:
      self.trama = self._States_Report("I0Z",9)
      return self.trama