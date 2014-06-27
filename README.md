chez-betty
==========

UMich version of Chez Bob

Installation
============

Application is developed using Python Pyramid. To develop against, do the following:

 1. Setup virtualenv (e.g. `virtualenv --no-site-packages --distribute -p /usr/local/bin/python3.3 chezbetty`)

 2. Install application within virtualenv. If developing, just create a symlink to your checkout. Otherwise git export or similar.

 3. run python setup.py develop to install all the dependencies of the application
