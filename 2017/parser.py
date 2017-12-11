#!/usr/bin/python
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
from openpyxl import Workbook
from datetime import datetime
import datetime
import time
import pandas
import numpy
import logging
import os, os.path, sys

def prtgToUnix(prtgDate):
	result = (prtgDate-25569)*86400
	return result

def unixToDate(unix):
	try:
		result = datetime.fromtimestamp(unix)
	except:
		result = numpy.NaN
	return result

def dateToUnix(date):
	try:
		result = time.mktime(datetime.datetime.strptime(date, "%d/%m/%Y").timetuple())
	except:
		result = numpy.NaN
	return result

def toINT(float):
	try:
		result = int(float)
	except:
		result = numpy.NaN
	return result

def fileUPStoBln(val):
	val = val.split('/')[3]
	val = val.split('_')[0]
	val = val.split('-')[1]
	val = int(val)
	return val

def log(message):
	logging.basicConfig(
		filename="parser.err",
		level=logging.DEBUG,
		format='%(asctime)s %(levelname)s - %(message)s',
		datefmt='%m/%d/%Y %I:%M:%S %p')
	logging.info(message)

def loadDataLokasi(file):
	result = pandas.read_csv(file)
	result['STARTDATE'] = result['STARTDATE'].map(dateToUnix)
	result['STARTDATE'] = result['STARTDATE'].fillna(-1000).astype(numpy.float64)
	result['CHANGEDATE'] = result['CHANGEDATE'].map(dateToUnix)
	result['CHANGEDATE'] = result['CHANGEDATE'].fillna(-1000).astype(numpy.float64)
	result['CHANGEUPSID'] = result['CHANGEUPSID'].fillna(-1000).astype(numpy.int64)
	return result

def loadUPS(file, ISP):
	if (ISP == "ISP Iforte Global Internet"):
		result = pandas.read_csv(file, usecols=["Date Time(RAW)", "ups high prec input line voltage(RAW)", "Downtime(RAW)"])
	else:
		result = pandas.read_csv(file, usecols=["Date Time(RAW)", "Value(RAW)", "Downtime(RAW)"])
	result.columns = ["Timestamp", "VInput", "Downtime"]
	result['Timestamp'] = result['Timestamp'].map(prtgToUnix)
	result.VInput = result.VInput.fillna(-1000)
	result.Downtime = result.Downtime.fillna(-1000)
	result = result[:-1]
	return result

def loadPING(file):
	result = pandas.read_csv(file, usecols=["Date Time(RAW)", "Downtime(RAW)"])
	result.columns = ["Timestamp", "Downtime"]
	result['Timestamp'] = result['Timestamp'].map(prtgToUnix)
	result.Downtime = result.Downtime.fillna(-1000)
	result = result[:-1]
	return result

def selaluMati(dataUPS):
	for i, _ in dataUPS.iterrows():
		if (dataUPS.Downtime[i] != 100) or (dataUPS.Downtime[i] != -1000):
			return False
			break
	return True

def statusBaterai(dataUPS):
	dataUPS['Status'] = "OFF"
	dataUPS.loc[(dataUPS.Downtime == 0) & (dataUPS.VInput == 0), 'Status'] = "ON"
	dataUPS.loc[(dataUPS.Downtime == 0) & (dataUPS.VInput == -1000), 'Status'] = "Unknown"
	return dataUPS

def joinData(dataUPS, dataPING, dataUPS2, CHANGEDATE):
	try:
		result = pandas.merge(dataUPS, dataPING, on='Timestamp', how='outer')
		result.columns = ["Timestamp", "VInput", "UPSDowntime", "Status", "PINGDowntime"]
		result.loc[(result.Timestamp >= CHANGEDATE), 'VInput'] = dataUPS2.VInput
		result.loc[(result.Timestamp >= CHANGEDATE), 'UPSDowntime'] = dataUPS2.Downtime
	except:
		result = pandas.merge(dataUPS, dataPING, on='Timestamp', how='outer')
		result.columns = ["Timestamp", "VInput", "UPSDowntime", "Status", "PINGDowntime"]
	return result

def writeToExcel(data):
	pass
	# writer = pandas.ExcelWriter('output.xlsx', index=False)
	# jData.to_excel(writer,'Sheet1')
	# dataUPS.to_excel(writer,'Sheet2')
	# writer.save()

def hitungSelaluMati(jData):
	jData['Restitusi'] = numpy.NaN
	# Kategori Bypass
	jData.loc[(jData.PINGDowntime <= 100) & (jData.PINGDowntime > 0), 'Restitusi'] = 300
	# Kategori OK
	jData.loc[(jData.PINGDowntime == 0), 'Restitusi'] = 0
	return jData

def hitungNormal(jData):
	jData['Kategori'] = numpy.NaN
	jData['Restitusi'] = numpy.NaN
	
	# Kategori OK
	jData.loc[(jData.PINGDowntime == 0) & (jData.UPSDowntime == 0),
	'Kategori'] = "OK"
	jData.loc[jData.Kategori == "OK", 'Restitusi'] = 0

	# Kategori Link
	jData.loc[((jData.PINGDowntime > 0) & (jData.UPSDowntime == 0)) | ((jData.PINGDowntime > 0) & (jData.UPSDowntime == -1000)),
	'Kategori'] = "Link"
	jData.loc[jData.Kategori == "Link", 'Restitusi'] = (jData.PINGDowntime*300/100)

	# Kategori Non-Link (Ragu bisa jalan)
	for i in xrange(2):
		jData.loc[((jData.Status.shift(-1) == "OFF") & (jData.Status == "Unknown") & (jData.PINGDowntime > 0) & (jData.UPSDowntime > 0)) | ((jData.PINGDowntime == 100) & (jData.UPSDowntime == 100)) | ((jData.Kategori.shift(-1) == "Non-Link") & (jData.PINGDowntime > 0) & (jData.UPSDowntime > 0)), 'Kategori'] = "Non-Link"

	jData.loc[jData.Kategori == "Non-Link", 'Restitusi'] = 0

	# Kategori Bypass
	for i in xrange(2):
		jData.loc[((jData.PINGDowntime == 0) & (jData.UPSDowntime > 0)) | ((jData.PINGDowntime > 0) & (jData.PINGDowntime < 100) & (jData.UPSDowntime == 100)) | ((jData.PINGDowntime > 0) & (jData.UPSDowntime > 0 ) & (jData.Kategori.shift(-1) == "Bypass")), 'Kategori'] = "Bypass"

	jData.loc[jData.Kategori == "Bypass", 'Restitusi'] = (jData.PINGDowntime*300/100)
	return jData

def hitungBulan(data_lokasi, i, fileUPS, filePING, fileUPS2):
	if ((data_lokasi.LOKASI[i] == "SMP NEGERI 1 KUALA BATEE")):
		if (data_lokasi.CHANGEDATE[i] > 0):
			dataUPS2 = loadUPS(fileUPS2, data_lokasi.ISP[i])
		dataUPS = loadUPS(fileUPS, data_lokasi.ISP[i])
		dataPING = loadPING(filePING)
		dataUPS = statusBaterai(dataUPS)
		jData = joinData(dataUPS, dataPING, dataUPS2, data_lokasi.CHANGEDATE[i])
		print "File: {}".format(fileUPS)
		if selaluMati(dataUPS):
			print "SELALU MATI"
			jData = hitungSelaluMati(jData)
		else:
			print "NORMAL"
			jData = hitungNormal(jData)
		bulan = fileUPStoBln(fileUPS)
		SUMRestitusi = jData['Restitusi'].sum()
		SLA = (1-(SUMRestitusi/(jData['Timestamp'].iloc[-1] - jData['Timestamp'].iloc[0])))*100
		writeToExcel(jData)
		return bulan, SUMRestitusi, SLA

def iterDataBulan(data_lokasi, dirPathPING, dirPathUPS, dirPathUPS2, fileListPING, fileListUPS, fileListUPS2, i):
	result = pandas.DataFrame(index=range(1,13), columns=['Restitusi', 'SLA'])
	if (len(fileListUPS) == len(fileListPING)):
		for idx in range(0, len(fileListPING)):
			try:
				if (data_lokasi.CHANGEDATE[i] > 0):
					fileUPS2 = str(dirPathUPS2 + "/" + fileListUPS2[idx])
				fileUPS = str(dirPathUPS + "/" + fileListUPS[idx])
				filePING = str(dirPathPING + "/" + fileListPING[idx])
				bulan, SUMRestitusi, SLA = hitungBulan(data_lokasi, i, fileUPS, filePING, fileUPS2)
				result['Restitusi'].iloc[bulan-1] = SUMRestitusi
				result['SLA'].iloc[bulan-1] = SLA
			except:
				message = str("Error2 while read: " + data_lokasi.ISP[i] + ", Lokasi: " + data_lokasi.LOKASI[i] + ", UPS: " + fileListUPS[idx] + " or " + fileListPING[idx])
				log(message)
	else:
		message = "Jumlah fileListPING != fileListUPS"
		log(message)
	return result

def iterDataLokasi(data_lokasi):
	for i, _ in data_lokasi.iterrows():
		try:
			if (data_lokasi.CHANGEDATE[i] > 0):
				dirPathUPS2 = str(data_lokasi.ISP[i] + "/ups/" + str(data_lokasi.CHANGEUPSID[i]))
				fileListUPS2 = os.listdir(dirPathUPS2)
			dirPathPING = str(data_lokasi.ISP[i] + "/ping/" + str(data_lokasi.PINGID[i]))
			dirPathUPS = str(data_lokasi.ISP[i] + "/ups/" + str(data_lokasi.UPSID[i]))
			fileListPING = os.listdir(dirPathPING)
			fileListUPS = os.listdir(dirPathUPS)
			DATA = iterDataBulan(data_lokasi, dirPathPING, dirPathUPS, dirPathUPS2, fileListPING, fileListUPS, fileListUPS2, i)
			print DATA
		except:
			message = str("Error1 while read (Data Not Exists): " + data_lokasi.ISP[i] + ", Lokasi: " + data_lokasi.LOKASI[i])
			log(message)
			continue
def main():
	data_lokasi = loadDataLokasi("data_lokasi.csv")
	iterDataLokasi(data_lokasi)

if __name__ == "__main__":
	main()