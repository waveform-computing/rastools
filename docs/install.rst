Installation
============

rastools is distributed in several formats. The following sections detail
installation on a variety of platforms.


Pre-requisites
--------------

rastools depends primarily on matplotlib. If you wish to use the GUI you will
also need PyQt4 installed. On Linux these, and other dependencies should be
automatically handled assuming you install from a .deb package. On Windows, it
is probably simplest to install one of the pre-built Python distributions that
includes matplotlib like the `Enthought Python Distribution
<http://enthought.com/products/epd.php>`_ or `Python (x,y)
<http://code.google.com/p/pythonxy/>`_ (both of these include matplotlib and
PyQt4).

Additional optional dependencies are:

 * `xlwt <http://pypi.python.org/pypi/xlwt>`_ - required for Excel writing support

 * `GIMP <http://www.gimp.org/>`_ - required for GIMP (.xcf) writing support


Ubuntu Linux
------------

For Ubuntu Linux it is simplest to install from the PPA as follows::

    $ sudo add-apt-repository ppa://waveform/
    $ sudo apt-get update
    $ sudo apt-get install rastools


Microsoft Windows
-----------------

On Windows, first install one of the Python matplotlib distributions mentioned
above, and then use the executable installer.


Apple Mac OS X
--------------

???

