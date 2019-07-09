#!/bin/bash
cd /var/chezbetty
source bin/activate
cd repo
bower-installer
python3 setup.py install
pushd chezbetty/locale && ./compile_all_translations.sh ; popd
sudo restart-apache
