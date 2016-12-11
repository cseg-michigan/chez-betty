Chez Betty
==========

[![Build Status](https://travis-ci.org/um-cseg/chez-betty.svg?branch=master)](https://travis-ci.org/um-cseg/chez-betty)
[![Code Climate](https://codeclimate.com/github/um-cseg/chez-betty/badges/gpa.svg)](https://codeclimate.com/github/um-cseg/chez-betty)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/um-cseg/chez-betty/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/um-cseg/chez-betty/?branch=master)

Chez Betty is a mini, cooperative food store where users can deposit money to their account
and use it to purchase food and other items. The system is linked
to the UMich ldap server so users can swipe their M-Card to login.

UMich version is an homage to UCSD's [Chez Bob](http://chezbob.ucsd.edu/).
Chez Betty runs [here](http://chezbetty.eecs.umich.edu).

Chez Betty is written as a Python web app designed to run on a server with
a browser based user interface. It supports cash and credit card deposits. The
user interface expects a card swiper and barcode scanner to be attached to
the machine. See the list at the end of this README for products we use.
To test / demo the system without hardware, turn on "Demo mode" in the admin
interface.

Installation
------------

The Chez Betty application is developed using Python Pyramid. To get a
development environment set up, do the following:

1. Clone this repository

        git clone https://github.com/um-cseg/chez-betty.git

2. Install system dependencies:

        # Ubuntu 15.10
        sudo apt-get install postgresql postgresql-server-dev-9.4 libjpeg-dev
        # Ubuntu 16.10
        sudo apt-get install postgresql postgresql-server-dev-9.5 libjpeg-dev

1. Setup virtualenv with Python3:

        cd chez-betty

        # Python cannot decide on how it wants to do this. So
        # we have multiple iterations that we have tried.
        ## Way back:
        # virtualenv .
        ## Python3.3:
        # python3 -m venv .
        # ^ *not* pyvenv ., that installed python2 in my venv for w/e reason
        ## Newest (only do this with Python 3.4+):
        pyvenv-3.5 venv

        source venv/bin/activate

2. Install the dependencies:

        # Note, this step *must* be run before setup.py. The latter will use
        # easy_install to install requirements instead of pip, which will
        # break some packages (e.g. stripe). The argument should be the root
        # directory of the project.
        pip install -e .

2. Setup the development environment

        python setup.py develop

3. Update `development.ini` to set config information and passwords.

        cp development.ini.example development.ini
        [edit development.ini]

3. Setup the database:

        python chezbetty/initializedb.py development.ini

4. Install bower and bower-install

        # Note: Distro copies of node tend to fall behind really quickly.
        # You are better off using a copy of node/npm installed directly:
        # http://nodejs.org/
        # https://github.com/npm/npm
        sudo npm install bower bower-installer -g

5. Get all css/js dependencies

        bower-installer

4. Run the webserver:

        pserve development.ini
        # n.b. pserve will be in your path if your virtualenv is active


### LDAP

TODO: add information about how to setup LDAP connection.

### Bitcoin

TODO: add info about how to setup bitcoin/coinbase.

Usage
-----

View the client interface using

    http://127.0.0.1:6543

View the admin interface using

    http://127.0.0.1:6543/admin
    username: admin
    password: chezbettyadmin

Tools
-----

Chez Betty currently runs using:

- Intel Nuc with case - Running Ubuntu.
- [Magnetic Strip Reader](https://www.cdw.com/shop/products/MagTek-SureSwipe-Reader-USB-HID-Keyboard-Interface-magnetic-card-reader/1140626.aspx) - Acts as a keyboard input.
- [Barcode Scanner](https://www.cdw.com/shop/products/Motorola-LS2208-barcode-scanner-scanner-and-USB-cable-included/3021140.aspx) - Also keyboard input.
- [Touchscreen Monitor](http://www.amazon.com/ViewSonic-TD2220-22-Inch-LED-Lit-Display/dp/B009F1IKFC) - Acts as a mouse.
