============
Installation
============

rastools is distributed in several formats. The following sections detail
installation on a variety of platforms.


Download
========

You can find pre-built binary packages for several platforms available from
the `rastools development site
<http://www.waveform.org.uk/trac/rastools/wiki/Download>`_. Installations
instructions for specific platforms are included in the sections below.

If your platform is *not* covered by one of the sections below, rastools is
also available from PyPI and can therefore be installed with the ``pip`` or
``easy_install`` tools::

   $ pip install rastools

   $ easy_install rastools


Pre-requisites
==============

rastools depends primarily on `matplotlib
<http://matplotlib.sourceforge.net>`_. If you wish to use the GUI you will also
need `PyQt4 <http://www.riverbankcomputing.com/software/pyqt/download>`_
installed. On Linux these, and other dependencies should be automatically
handled assuming you install from a .deb package. On Windows, it is probably
simplest to install one of the pre-built Python distributions that includes
matplotlib like the `Enthought Python Distribution
<http://enthought.com/products/epd.php>`_ or `Python (x,y)
<http://code.google.com/p/pythonxy/>`_ (both of these include matplotlib and
PyQt4).

Additional optional dependencies are:

 * `xlwt <http://pypi.python.org/pypi/xlwt>`_ - required for Excel writing support

 * `GIMP <http://www.gimp.org/>`_ - required for GIMP (.xcf) writing support


Ubuntu Linux
============

For Ubuntu Linux it is simplest to install from the PPA as follows::

    $ sudo add-apt-repository ppa://waveform/ppa
    $ sudo apt-get update
    $ sudo apt-get install rastools

Development
-----------

If you wish to develop rastools, you can install the pre-requisites, construct
a virtualenv sandbox, and check out the source code from subversion with the
following command lines::

   # Install the pre-requisites
   $ sudo apt-get install python-matplotlib python-xlwt python-qt4 python-virtualenv python-sphinx gimp make subversion

   # Construct and activate a sandbox with access to the packages we just
   # installed
   $ virtualenv --system-site-packages sandbox
   $ source sandbox/bin/activate

   # Check out the source code and install it in the sandbox for development and testing
   $ svn co http://www.waveform.org.uk/svn/rastools/trunk rastools
   $ cd rastools
   $ make develop


Microsoft Windows
=================

On Windows, first install one of the Python matplotlib distributions mentioned
above, and then use the executable installer.


Apple Mac OS X
==============

XXX To be written

