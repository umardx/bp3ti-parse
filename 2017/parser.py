#!/usr/bin/python
import pandas
import logging
import os, os.path, sys

def log(message):
	logging.basicConfig(
		filename="parser.log",
		level=logging.DEBUG,
		format='%(asctime)s %(levelname)s - %(message)s',
		datefmt='%m/%d/%Y %I:%M:%S %p'
		)
	logging.info(message)

def isFile(path):
	result = os.path.isfile(path)
	return result

def isDir(path):
	result = os.path.isdir(path)
	return result

def loadCSV(path):
	result = pandas.read_csv(path)
	return result

def calculateData(data_lokasi, dirPathPING, dirPathUPS, fileListPING, fileListUPS, i):
	for 

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

def main():
	data_lokasi = loadCSV("data_lokasi.csv")
	iterDataLokasi(data_lokasi)

if __name__ == "__main__":
	main()