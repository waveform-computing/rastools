=======
rasdump
=======

This utility accepts a QSCAN RAS file and an optional channel definition file.
For each channel listed in the latter, a dump is produced of the corresponding
channel in the RAS file. Various options are provided for customizing the
output including percentile limiting, and output format.

Synopsis
========

Usage::

  $ rasdump [options] data-file [channels-file]

Where *data-file* is the file containing the channel data to dump and the
optional *channel-file* defines the indices and names of the channels to dump.
If the *channel-file* is omitted all channels are extracted and channels in
.RAS files will be unnamed.

The :program:`rasdump` utility has several options:

.. program:: rasdump

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

.. option:: -P, --pdb

   run under PDB (debug mode)

.. option:: --help-formats

   list the available file output formats

.. option:: -p PERCENTILE, --percentile=PERCENTILE

   clip values in the output image to the specified low-high percentile range
   (mutually exclusive with :option:`-r`)

.. option:: -r RANGE, --range=RANGE

   clip values in the output image to the specified low-high count range
   (mutually exclusive with :option:`-p`)

.. option:: -C CROP, --crop=CROP

   crop the input data by left,top,right,bottom points

.. option:: -e, --empty

   if specified, include empty channels in the output (by default empty
   channels are ignored)

.. option:: -o OUTPUT, --output=OUTPUT

   specify the template used to generate the output filenames; supports
   {variables}, see --help-formats for supported file formats. Default:
   {filename_root}_{channel:02d}_{channel_name}.csv

.. option:: -m, --multi

   if specified, produce a single output file with multiple pages or sheets,
   one per channel (only available with certain formats)

Examples
========

Basic Usage
-----------

The most basic usage of rasdump is to specify only the RAS file from which to
dump data. This will dump data in the default CSV format, one file per channel
with no cropping and no percentile limiting. All channels (except empty ones)
will be extracted, and will be anonymous (since no channels file has been
specified to name them)::

    $ rasdump JAN12_CHINAFISH_LZ_003.RAS
    Writing channel 0 () to JAN12_CHINAFISH_LZ_00_.csv
    Channel 0 () is empty, skipping
    Writing channel 1 () to JAN12_CHINAFISH_LZ_01_.csv
    Writing channel 2 () to JAN12_CHINAFISH_LZ_02_.csv
    Writing channel 3 () to JAN12_CHINAFISH_LZ_03_.csv
    Writing channel 4 () to JAN12_CHINAFISH_LZ_04_.csv
    Writing channel 5 () to JAN12_CHINAFISH_LZ_05_.csv
    Writing channel 6 () to JAN12_CHINAFISH_LZ_06_.csv
    Writing channel 7 () to JAN12_CHINAFISH_LZ_07_.csv
    Writing channel 8 () to JAN12_CHINAFISH_LZ_08_.csv
    Writing channel 9 () to JAN12_CHINAFISH_LZ_09_.csv
    Writing channel 10 () to JAN12_CHINAFISH_LZ_10_.csv
    Writing channel 11 () to JAN12_CHINAFISH_LZ_11_.csv
    Writing channel 12 () to JAN12_CHINAFISH_LZ_12_.csv
    Writing channel 13 () to JAN12_CHINAFISH_LZ_13_.csv
    Writing channel 14 () to JAN12_CHINAFISH_LZ_14_.csv
    Writing channel 15 () to JAN12_CHINAFISH_LZ_15_.csv

Help Lists
----------

XXX To be written

Substitution Templates
----------------------

XXX To be written

Advanced Usage
--------------

XXX To be written
