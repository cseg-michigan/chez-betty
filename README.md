Chez Betty
==========

Chez Betty is a mini, cooperative food store where users can deposit money to their account
and use it to purchase food and other items. The system is linked
to the UMich ldap server so users can swipe their M-Card to login.

UMich version is an homage to UCSD's [Chez Bob](http://chezbob.ucsd.edu/).
Chez Betty runs [here](http://chezbetty.eecs.umich.edu).

Chez Betty is written as a Python web app designed to run on a server with
a browser based user interface. It supports cash and bitcoin deposits. The
user interface expects a card swiper and barcode scanner to be attached to
the machine. See the list at the end of this README for products we use.
To test / demo the system without hardware, turn on "Demo mode" in the admin
interface.

Installation
============

The Chez Betty application is developed using Python Pyramid. To get a
development environment set up, do the following:

1. Clone this repository

        git clone https://github.com/um-cseg/chez-betty.git

1. Setup virtualenv with Python3:

        cd chez-betty
        # virtualenv .
        # Python3.3 or later:
        python3 -m venv .
        # ^ *not* pyvenv ., that installed python2 in my venv for w/e reason
        source bin/activate

2. Install the Python3 dependencies:

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


LDAP
====

TODO: add information about how to setup LDAP connection.

Bitcoin
=======

TODO: add info about how to setup bitcoin/coinbase.

Usage
=====

View the client interface using

    http://127.0.0.1:6543

View the admin interface using

    http://127.0.0.1:6543/admin

Tools
=====

Chez Betty currently runs using:

- [Beagle Bone Black](http://beagleboard.org/black) - Running Debian, LXDE, and Ice Weasel.
- [Magnetic Strip Reader](https://www.cdw.com/shop/products/MagTek-SureSwipe-Reader-USB-HID-Keyboard-Interface-magnetic-card-reader/1140626.aspx) - Acts as a keyboard input.
- [Barcode Scanner](https://www.cdw.com/shop/products/Motorola-LS2208-barcode-scanner-scanner-and-USB-cable-included/3021140.aspx) - Also keyboard input.
- [Touchscreen Monitor](http://www.amazon.com/ViewSonic-TD2220-22-Inch-LED-Lit-Display/dp/B009F1IKFC) - Acts as a mouse.
