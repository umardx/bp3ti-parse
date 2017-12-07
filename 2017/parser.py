#!/usr/bin/python
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
from openpyxl import Workbook
from datetime import datetime
import pandas
import numpy
import logging
import os, os.path, sys

def prtgToUnix(prtgDate):
	result = (prtgDate-25569)*86400
	return result

def unixToDate(unix):
	result = datetime.fromtimestamp(unix)
	return result

def log(message):
	logging.basicConfig(
		filename="parser.err",
		level=logging.DEBUG,
		format='%(asctime)s %(levelname)s - %(message)s',
		datefmt='%m/%d/%Y %I:%M:%S %p')
	logging.info(message)

def loadCSV(file):
	result = pandas.read_csv(file)
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
		if (dataUPS.Downtime[i] != 100) and (dataUPS.Downtime[i] != -1000):
			return False
			break
	return True

def statusBaterai(dataUPS):
	dataUPS['Status'] = "OFF"
	dataUPS.loc[(dataUPS.Downtime == 0) & (dataUPS.VInput == 0), 'Status'] = "ON"
	dataUPS.loc[(dataUPS.Downtime == 0) & (dataUPS.VInput == -1000), 'Status'] = "Unknown"
	return dataUPS

def joinData(dataUPS, dataPING):
	result = pandas.merge(dataUPS, dataPING, on='Timestamp', how='outer')
	result.columns = ["Timestamp", "VInput", "UPSDowntime", "Status", "PINGDowntime"]
	return result

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
	jData.loc[(jData.PINGDowntime == 0) & (jData.UPSDowntime == 0) & (jData.VInput > 0),
	'Kategori'] = "OK"
	jData.loc[jData.Kategori == "OK", 'Restitusi'] = 0

	# Kategori Link
	jData.loc[((jData.PINGDowntime > 0) & (jData.UPSDowntime == 0)) | ((jData.PINGDowntime > 0) & (jData.UPSDowntime == -1000)),
	'Kategori'] = "Link"
	jData.loc[jData.Kategori == "Link", 'Restitusi'] = (jData.PINGDowntime*300/100)

	# Kategori Non-Link (Ragu bisa jalan)
	jData.loc[((jData.Status.shift(-1) == "OFF") & (jData.Status == "Unknown") & (jData.PINGDowntime > 0) & (jData.UPSDowntime > 0))
	| ((jData.PINGDowntime == 100) & (jData.UPSDowntime == 100))
	| ((jData.Kategori.shift(-1) == "Non-Link") & (jData.PINGDowntime > 0) & (jData.UPSDowntime > 0)),
	'Kategori'] = "Non-Link"
	jData.loc[((jData.Status.shift(-1) == "OFF") & (jData.Status == "Unknown") & (jData.PINGDowntime > 0) & (jData.UPSDowntime > 0))
	| ((jData.PINGDowntime == 100) & (jData.UPSDowntime == 100))
	| ((jData.Kategori.shift(-1) == "Non-Link") & (jData.PINGDowntime > 0) & (jData.UPSDowntime > 0)),
	'Kategori'] = "Non-Link"
	jData.loc[jData.Kategori == "Non-Link", 'Restitusi'] = 0

	# Kategori Bypass
	jData.loc[((jData.PINGDowntime == 0) & (jData.UPSDowntime > 0))
	| ((jData.PINGDowntime > 0) & (jData.PINGDowntime < 100) & (jData.UPSDowntime == 100))
	| ((jData.PINGDowntime > 0) & (jData.UPSDowntime >0 ) & (jData.Kategori.shift(-1) == "Bypass")),
	'Kategori'] = "Bypass"
	jData.loc[((jData.PINGDowntime == 0) & (jData.UPSDowntime > 0))
	| ((jData.PINGDowntime > 0) & (jData.PINGDowntime < 100) & (jData.UPSDowntime == 100))
	| ((jData.PINGDowntime > 0) & (jData.UPSDowntime >0 ) & (jData.Kategori.shift(-1) == "Bypass")),
	'Kategori'] = "Bypass"

	return jData

def hitungBulan(data_lokasi, i, fileUPS, filePING):
	# if ((data_lokasi.LOKASI[i] == "BLK DISNAKER ACEH SINGKIL")
	# 	and (fileUPS == "ISP Aplikanusa Lintasarta/ups/out/7720/2017-03-01-00-00-00_2017-04-01-00-00-00.csv")):
		print "Proccessing....."
		print "Lokasi:{}".format(data_lokasi.LOKASI[i])
		print "UPS:{} PING:{}".format(fileUPS, filePING)
		print ""
		dataUPS = loadUPS(fileUPS, data_lokasi.ISP[i])
		dataPING = loadPING(filePING)
		dataUPS = statusBaterai(dataUPS)
		jData = joinData(dataUPS, dataPING)
		if selaluMati(dataUPS):
			print "Selalu Mati"
			hitungSelaluMati(jData)
		else:
			print "Normal"
			jData = hitungNormal(jData)
			print jData
			writer = pandas.ExcelWriter('output.xlsx', index=False)
			jData.to_excel(writer,'Sheet1')
			dataUPS.to_excel(writer,'Sheet2')
			writer.save()

def iterDataBulan(data_lokasi, dirPathPING, dirPathUPS, fileListPING, fileListUPS, i):
	if (len(fileListUPS) == len(fileListPING)):
		for idx in range(0, len(fileListPING)):
			try:
				fileUPS = str(dirPathUPS + "/" + fileListUPS[idx])
				filePING = str(dirPathPING + "/" + fileListPING[idx])
				hitungBulan(data_lokasi, i, fileUPS, filePING)
			except:
				message = str("Error while read: " + data_lokasi.ISP[i] + ", Lokasi: " + data_lokasi.LOKASI[i] + ", UPS: " + fileListUPS[idx] + " or " + fileListPING[idx])
				log(message)
	else:
		message = "Jumlah fileListPING != fileListUPS"
		log(message)


def iterDataLokasi(data_lokasi):
	for i, _ in data_lokasi.iterrows():
		try:
			dirPathPING = str(data_lokasi.ISP[i] + "/ping/out/" + str(data_lokasi.PINGID[i]))
			dirPathUPS = str(data_lokasi.ISP[i] + "/ups/out/" + str(data_lokasi.UPSID[i]))
			fileListPING = os.listdir(dirPathPING)
			fileListUPS = os.listdir(dirPathUPS)
		except:
			message = str("Error while read: " + data_lokasi.ISP[i] + ", Lokasi: " + data_lokasi.LOKASI[i])
			log(message)
			continue
		iterDataBulan(data_lokasi, dirPathPING, dirPathUPS, fileListPING, fileListUPS, i)

def main():
	data_lokasi = loadCSV("data_lokasi.csv")
	iterDataLokasi(data_lokasi)

if __name__ == "__main__":
	main()