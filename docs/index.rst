========
Welcome!
========

Tools for converting scans from the SSRL to images.

rastools is a small suite of utilities for converting data files obtained from
SSRL (Stanford Synchrotron Radiation Lightsource) scans (.RAS and .DAT files)
into images. Various simple manipulations (cropping, percentiles, histograms,
color-maps) are supported. Most tools are command line based, but a Qt-based
GUI is also included.

Tools Overview
==============

The set of tools included is:

.. toctree::
   :maxdepth: 2

   rasdump
   rasextract
   rasinfo
   rasviewer

Further information on the tools can be found at the `rastools wiki
<http://www.waveform.org.uk/trac/rastools/wiki>`_.


License
=======

This file is part of rastools.

rastools is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

rastools is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
rastools.  If not, see <http://www.gnu.org/licenses/>.


Pre-requisites
==============

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


Installation
============

rastools is distributed in several formats. The following sections detail
installation on a variety of platforms.


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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

