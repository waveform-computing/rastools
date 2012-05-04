==========
rasextract
==========

.. toctree::
   :maxdepth: 2

This utility accepts a QSCAN RAS file and an optional channel definition file.
For each channel listed in the latter, an image is produced from the
corresponding channel in the RAS file. Various options are provided for
customizing the output including percentile limiting, color-mapping, and
drawing of axes and titles. The available command line options are listed
below.

Synopsis
========

Usage: ``rasextract [options] ras-file [channel-file]``

Options:

.. program:: rasextract

.. option:: --version

   show program's version number and exit

.. option:: -h, --help

   show this help message and exit

.. option:: -q, --quiet

   produce less console output

.. option:: -v, --verbose

   produce more console output

.. option:: -l LOGFILE, --log-file=LOGFILE

   log messages to the specified file

.. option:: -D, --debug

   enables debug mode (runs under PDB)

.. option:: --help-colormaps

   list the available colormaps

.. option:: --help-formats

   list the available file output formats

.. option:: --help-interpolations

   list the available interpolation algorithms

.. option:: -a, --axes

   draw the coordinate axes in the output

.. option:: -b, --color-bar

   draw a color-bar showing the range of the color-map to the right of the
   output

.. option:: -H, --histogram

   draw a histogram of the channel values below the output

.. option:: -c CMAP, --colormap=CMAP

   the colormap to use in output (e.g. gray, jet, hot); see
   :option:`--help-colormaps` for listing

.. option:: -p PERCENTILE, --percentile=PERCENTILE

   clip values in the output image to the specified percentile

.. option:: -C CROP, --crop=CROP

   crop the input data by top,left,bottom,right points

.. option:: -i INTERPOLATION, --interpolation=INTERPOLATION

   force the use of the specified interpolation algorithm; see
   :option:`--help-interpolations` for listing

.. option:: -t TITLE, --title=TITLE

   specify the template used to display a title at the top of the output;
   supports ``{variables}`` produced by :option:`rasinfo -p`

.. option:: -o OUTPUT, --output=OUTPUT

   specify the template used to generate the output filenames; supports
   ``{variables}``, see :option:`--help-formats` for supported file formats. Default:
   ``{filename_root}_{channel:02d}_{channel_name}.png``

.. option:: -e, --empty

   if specified, empty channels in the output (by default empty channels are
   ignored)

.. option:: --one-pdf

   if specified, a single PDF file will be produced with one page per image;
   the output template must end with .pdf and must not contain channel variable
   references

.. option:: --one-xcf

   if specified, a single XCF file will be produced with one layer per image;
   the output template must end with .xcf and must not contain channel variable
   references
