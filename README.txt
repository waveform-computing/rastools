.. -*- rst -*-

========
rastools
========

rastools is a small suite of utilities for converting data files obtained from
SSRL (Stanford Synchrotron Radiation Lightsource) scans (.RAS and .DAT files)
into images. Various simple manipulations (cropping, percentiles, histograms,
color-maps) are supported. Most tools are command line based, but a Qt-based
GUI is also included.

This package is also available in .deb form from ppa://waveform/ppa


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


Tools Overview
==============

The set of tools included is:

 * ``rasinfo`` dumps information obtained from the header of the scan file to
   stdout

 * ``rasdump`` extracts channels from a scan file and dumps its data to a
   standard format like CSV or Excel

 * ``rasextract`` extracts channels from a scan file, applies any simple
   transforms specified (e.g. percentile) and writes the output as a standard
   image format (PNG, TIFF, SVG, etc.)

 * ``rasviewer`` is a Qt-based GUI for viewing the channels of one or more scan
   files. It supports all the transforms that ``rasextract`` supports and also
   allows exporting of images

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

