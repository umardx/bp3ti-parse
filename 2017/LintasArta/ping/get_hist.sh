#!/bin/bash

dir_out="out"
hostName="202.43.73.154"
inputSensor="sensors.csv"

username="prtguser"
password="Bp3t1OK!"

while IFS='' read -r line || [[ -n "$line" ]]; do
	if [ ${#line} -le 2 ]; then
		continue
	fi

	for i in {1..10}; do
		let "j=$i+1"
	    if [ ${#i} -eq 1 ]; then
	    	i="0$i"
	    fi
	    if [ ${#j} -eq 1 ]; then
	    	j="0$j"
	    fi

	    sensorID=$(echo $line | tr ";" "\n")
	    sDate="2017-${i}-01-00-00-00"
	    eDate="2017-${j}-01-00-00-00"
	    dirName="${dir_out}/${sensorID}"
	    filePath="${dirName}/${sDate}_${eDate}.csv"
	    [ -d $dirName ] || mkdir -p $dirName

curl --insecure -s -w "%{http_code}" -X GET "https://${hostName}/api/historicdata.csv?id=${sensorID}&avg=300&sdate=${sDate}&edate=${eDate}&username=${username}&password=${password}" \
-H "cache-control: no-cache" -o ${filePath}
echo " | SensorID: $sensorID | sDate: $sDate"
	done



done < ${inputSensor}

exit 0