#!/bin/bash
# this script downloads updated versions of all the MicroPython libraries

cd src/lib
curl https://codeload.github.com/pfalcon/utemplate/tar.gz/master | tar -xz --strip=1 utemplate-master/utemplate

curl https://raw.githubusercontent.com/miguelgrinberg/microdot/main/src/microdot/__init__.py > microdot/__init__.py
curl https://raw.githubusercontent.com/miguelgrinberg/microdot/main/src/microdot/microdot.py > microdot/microdot.py
curl https://raw.githubusercontent.com/miguelgrinberg/microdot/main/src/microdot/utemplate.py > microdot/utemplate.py

curl https://raw.githubusercontent.com/peterhinch/micropython-mqtt/master/mqtt_as/mqtt_as.py > mqtt_as.py

cd ../..