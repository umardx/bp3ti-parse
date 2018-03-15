# bp3ti-parse

## Install the dependencies
```
pip install openpyxl pandas numpy
```

Put files on `./2017/ISP Iforte Global Internet/` or `./{year}/{ISP}/{file}`
Run `get.sh` on `./{year}/{ISP}/` instead to get bulk csv from PRTG server.
Don't forget to add list of sensor_id line by line to `sensors.csv` file.
and then just run these command:
```
python parser.py
```
