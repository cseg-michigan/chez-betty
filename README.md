Chez Betty
==========

UMich version of [Chez Bob](http://chezbob.ucsd.edu/).

Installation
============

The Chez Betty application is developed using Python Pyramid. To develop
against, do the following:

1. Setup virtualenv with Python3:

        cd chez-betty
        virtualenv .
        source bin/activate

2. Install the Python3 dependencies:

        python setup.py develop

3. Setup the database:

        bin/initialize_chezbetty_db development.ini

4. Run the webserver:

        bin/pserve development.ini