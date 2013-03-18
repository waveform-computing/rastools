.. -*- rst -*-

========
rastools
========

rastools is a small suite of utilities for converting data files obtained from
SSRL (Stanford Synchrotron Radiation Lightsource) scans (.RAS and .DAT files)
into images. Various simple manipulations (cropping, percentiles, histograms,
color-maps) are supported. Most tools are command line based, but a Qt-based
GUI is also included.


Installation
============

The `project homepage <http://www.waveform.org.uk/rastools/>`_ has links to
packages or instructions for all supported platforms.


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

Further information on the tools can be found in the `rastools documentation
<http://rastools.readthedocs.org/>`_.


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

