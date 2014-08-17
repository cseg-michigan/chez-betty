#!/bin/bash
cd /var/chezbetty
source bin/activate
cd repo
bower-installer
python3 setup.py install
sudo restart-apache
