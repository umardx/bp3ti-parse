#!/usr/bin/python
from openpyxl import Workbook
from datetime import datetime
import datetime
import time
import pandas
import numpy
import logging
import os, os.path, sys

def toNaN(val):
	if (val == -1000):
		result = numpy.NaN
	else:
		result = val
	return result

def prtgToUnix(prtgDate):
	result = (prtgDate-25569)*86400
	return result

def unixToDate(unix):
	try:
		result = datetime.datetime.fromtimestamp(float(unix)).strftime('%Y-%m-%d %H:%M:%S')
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

def fileUPStoBlnThn(val):
	val = val.split('/')[3]
	val = val.split('_')[0]
	val0 = int(val.split('-')[0])
	val1 = int(val.split('-')[1])
	return val0, val1

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
	try:
		result = pandas.read_csv(file, usecols=["Date Time(RAW)", "ups high prec input line voltage(RAW)", "Downtime(RAW)"])
	except:
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
		if (dataUPS.Downtime[i] == 0):
			return False
			break
	return True

def semuaNull(dataPING):
	for i, _ in dataPING.iterrows():
		if (dataPING.Downtime[i] != -1000):
			return False
			break
	return True

def statusBaterai(dataUPS):
	dataUPS['Status'] = "OFF"
	dataUPS.loc[(dataUPS.Downtime == 0) & (dataUPS.VInput == 0), 'Status'] = "ON"
	dataUPS.loc[(dataUPS.Downtime == 0) & (dataUPS.VInput == -1000), 'Status'] = "Unknown"
	return dataUPS

def joinData(dataUPS, dataPING, dataUPS2, CHANGEDATE):
	if (CHANGEDATE > 0):
		result = pandas.merge(dataUPS, dataPING, on='Timestamp', how='outer')
		result.columns = ["Timestamp", "VInput", "UPSDowntime", "Status", "PINGDowntime"]
		result.loc[(result.Timestamp >= CHANGEDATE), 'VInput'] = dataUPS2.VInput
		result.loc[(result.Timestamp >= CHANGEDATE), 'UPSDowntime'] = dataUPS2.Downtime
	else:
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
	jData.loc[(jData.PINGDowntime == 0) & (jData.UPSDowntime == 0),
	'Kategori'] = "OK"

	# Kategori Link
	jData.loc[((jData.PINGDowntime > 0) & (jData.UPSDowntime == 0)) | ((jData.PINGDowntime > 0) & (jData.UPSDowntime == -1000)),
	'Kategori'] = "Link"

	# Kategori Non-Link (Ragu bisa jalan)
	#for i in xrange(2):
	jData.loc[((jData.Status.shift(-1) == "OFF") & (jData.Status == "Unknown") & (jData.PINGDowntime > 0) & (jData.UPSDowntime > 0)) | ((jData.Kategori.shift(-1) == "Non-Link") & (jData.PINGDowntime > 0) & (jData.UPSDowntime > 0)), 'Kategori'] = "Non-Link"

	# Kategori Bypass
	#for i in xrange(2):
	jData.loc[((jData.PINGDowntime == 0) & (jData.UPSDowntime > 0)) | ((jData.PINGDowntime > 0) & (jData.PINGDowntime < 100) & (jData.UPSDowntime == 100)) | ((jData.PINGDowntime > 0) & (jData.UPSDowntime > 0 ) & (jData.Kategori.shift(-1) == "Bypass")), 'Kategori'] = "Bypass"

	for i, _ in jData.iterrows():
		if (i>0):
			v = i-1
			if ((jData.UPSDowntime[i] > 0) and (jData.PINGDowntime[i] > 0)):
				if (jData.Kategori[v] == "Bypass"):
					jData.iloc[i, jData.columns.get_loc('Kategori')] = "Bypass"
				if (jData.Kategori[v] == "Non-Link"):
					jData.iloc[i, jData.columns.get_loc('Kategori')] = "Non-Link"
			if (jData.UPSDowntime[i] == -1000) or (jData.PINGDowntime[i] == -1000):
				if (jData.Kategori[v] == "Bypass"):
					jData.iloc[i, jData.columns.get_loc('Kategori')] = "Bypass"
				if (jData.Kategori[v] == "Non-Link"):
					jData.iloc[i, jData.columns.get_loc('Kategori')] = "Non-Link"

	jData.loc[jData.Kategori == "OK", 'Restitusi'] = 0
	jData.loc[((jData.Kategori == "Link") & (jData.PINGDowntime >= 0)), 'Restitusi'] = (jData.PINGDowntime*300/100)
	jData.loc[jData.Kategori == "Non-Link", 'Restitusi'] = 0
	jData.loc[((jData.Kategori == "Bypass") & (jData.PINGDowntime >= 0)), 'Restitusi'] = (jData.PINGDowntime*300/100)
	return jData

def hitungBulan(data_lokasi, i, fileUPS, filePING, fileUPS2):
	dataUPS = loadUPS(fileUPS, data_lokasi.ISP[i])
	dataPING = loadPING(filePING)
	dataUPS = statusBaterai(dataUPS)
	if (data_lokasi.CHANGEDATE[i] > 0):
		dataUPS2 = loadUPS(fileUPS2, data_lokasi.ISP[i])
	else:
		dataUPS2 = ""
	jData = joinData(dataUPS, dataPING, dataUPS2, data_lokasi.CHANGEDATE[i])
	print "File: {}".format(fileUPS)
	if selaluMati(dataUPS):
		print "SELALU MATI"
		if semuaNull(dataPING):
			print "SEMUA NULL"
		jData = hitungSelaluMati(jData)
	else:
		print "NORMAL"
		jData = hitungNormal(jData)
	tahun, bulan = fileUPStoBlnThn(fileUPS)
	SUMRestitusi = jData['Restitusi'].sum()

	# if (bulan == 2):
	# 	temp_writer = pandas.ExcelWriter('DETAILS.xlsx')
	# 	jData.to_excel(temp_writer,'Sheet1', index=False)
	# 	temp_writer.save()
	SLA = (1-(SUMRestitusi/((jData['Timestamp'].iloc[-1] - jData['Timestamp'].iloc[0]))))*100
	print "SLA: {}, SUMRestitusi: {}".format(SLA, SUMRestitusi)
	return tahun, bulan, SUMRestitusi, SLA

def iterDataBulan(data_lokasi, dirPathPING, dirPathUPS, dirPathUPS2, fileListPING, fileListUPS, fileListUPS2, i):
	result = pandas.DataFrame(index=range(1,13), columns=['Tahun', 'Bulan', 'Restitusi', 'SLA'])
	if (len(fileListUPS) == len(fileListPING)):
		for idx in range(0, len(fileListPING)):
			if (data_lokasi.CHANGEDATE[i] > 0):
				fileUPS2 = str(dirPathUPS2 + "/" + fileListUPS2[idx])
			else:
				fileUPS2 = ""

			fileUPS = str(dirPathUPS + "/" + fileListUPS[idx])
			filePING = str(dirPathPING + "/" + fileListPING[idx])

			tahun, bulan, SUMRestitusi, SLA = hitungBulan(data_lokasi, i, fileUPS, filePING, fileUPS2)

			try:
				result['Tahun'].iloc[bulan-1] = tahun
				result['Bulan'].iloc[bulan-1] = bulan
				result['Restitusi'].iloc[bulan-1] = round(SUMRestitusi, 0)
				result['SLA'].iloc[bulan-1] = round(SLA, 2)
			except:
				print "bulan : {}".format(bulan)
				tahun, bulan = fileUPStoBlnThn(fileUPS)
				result['Tahun'].iloc[bulan-1] = numpy.NaN
				result['Bulan'].iloc[bulan-1] = numpy.NaN
				result['Restitusi'].iloc[bulan-1] = numpy.NaN
				result['SLA'].iloc[bulan-1] = numpy.NaN
				
				message = str("Error while read ISP: " + data_lokasi.ISP[i] + ", Lokasi: " + data_lokasi.LOKASI[i]) + ", Bulan: " + str(bulan)
				log(message)
				continue
	else:
		message = "Jumlah fileListPING != fileListUPS"
		log(message)
	return result

def iterDataLokasi(data_lokasi):
	result = data_lokasi
	for col in range(1,13):
		_Restitusi = "Restitusi_Bulan_"
		_Restitusi += str(col)
		_SLA = "SLA_Bulan_"
		_SLA += str(col)
		result[_Restitusi] = numpy.NaN
		result[_SLA] = numpy.NaN

	for i, _ in data_lokasi.iterrows():
		# if data_lokasi.LOKASI[i] == "SMP KOUH":
		try:
			if (data_lokasi.CHANGEDATE[i] > 0):
				dirPathUPS2 = str(data_lokasi.ISP[i] + "/ups/" + str(data_lokasi.CHANGEUPSID[i]))
				fileListUPS2 = os.listdir(dirPathUPS2)
			else:
				dirPathUPS2 = ""
				fileListUPS2 = [""]

			dirPathPING = str(data_lokasi.ISP[i] + "/ping/" + str(data_lokasi.PINGID[i]))
			dirPathUPS = str(data_lokasi.ISP[i] + "/ups/" + str(data_lokasi.UPSID[i]))
			fileListPING = os.listdir(dirPathPING)
			fileListUPS = os.listdir(dirPathUPS)

			# Tabel Restitusi | SLA untuk 12 bulan
			DATA = iterDataBulan(data_lokasi, dirPathPING, dirPathUPS, dirPathUPS2, fileListPING, fileListUPS, fileListUPS2, i)
			
			if (data_lokasi.STARTDATE[i] > 0):
				_tahun = int(datetime.datetime.fromtimestamp(float(data_lokasi.STARTDATE[i])).strftime('%Y'))
				_bulan = int(datetime.datetime.fromtimestamp(float(data_lokasi.STARTDATE[i])).strftime('%m'))
				DATA.loc[(DATA.Tahun == _tahun) & (DATA.Bulan < _bulan), 'Restitusi'] = numpy.NaN
				DATA.loc[(DATA.Tahun == _tahun) & (DATA.Bulan < _bulan), 'SLA'] = numpy.NaN

			for col in range(1,13):
				_Restitusi = "Restitusi_Bulan_"
				_Restitusi += str(col)
				_SLA = "SLA_Bulan_"
				_SLA += str(col)
				result.loc[i, _Restitusi] = DATA.Restitusi[col]
				result.loc[i, _SLA] = DATA.SLA[col]
		except:
			message = str("Error while read (Data Not Exists - SKIP): " + data_lokasi.ISP[i] + ", Lokasi: " + data_lokasi.LOKASI[i])
			log(message)
			continue
	return result

def main():
	data_lokasi = loadDataLokasi("data_lokasi.csv")
	hasil = iterDataLokasi(data_lokasi)
	hasil['STARTDATE'] = hasil['STARTDATE'].map(unixToDate)
	hasil['STARTDATE'] = hasil['STARTDATE'].map(toNaN)
	hasil['CHANGEDATE'] = hasil['CHANGEDATE'].map(unixToDate)
	hasil['CHANGEDATE'] = hasil['CHANGEDATE'].map(toNaN)
	hasil['CHANGEUPSID'] = hasil['CHANGEUPSID'].map(toNaN)

	writer = pandas.ExcelWriter('OUT.xlsx')
	hasil.to_excel(writer,'Sheet1', index=False)
	writer.save()

if __name__ == "__main__":
	main()