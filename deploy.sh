#!/bin/bash
cd /var/chezbetty
source bin/activate
cd repo
bower-install
python3 setup.py install
sudo restart-apache

