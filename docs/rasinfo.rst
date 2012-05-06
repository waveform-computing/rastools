=======
rasinfo
=======

This utility accepts a source RAS file from QSCAN. It extracts and prints the
information from the RAS file's header. If the optional channels definition
file is also specified, then channels will be named in the output as they would
be with rasextract. The available command line options are listed below.

Synopsis
========

Usage::

  $ rasinfo [options] ras-file [channels-file]

Options:

.. program:: rasinfo

.. option:: --version

   show program's version number and exit

.. option:: -h
.. option:: --help

   show a help message and exit

.. option:: -q
.. option:: --quiet

   produce less console output

.. option:: -v
.. option:: --verbose

   produce more console output

.. option:: -l LOGFILE
.. option:: --log-file=LOGFILE

   log messages to the specified file

.. option:: -D
.. option:: --debug

   enables debug mode (runs under PDB)

.. option:: -t
.. option:: --templates

   output substitution templates use with rasextract ``--title`` and ``--output``

.. option:: -r
.. option:: --ranges

   read each channel in the file and output its range of values

Examples
========

Basic Usage
-----------

The following is an example of basic usage of rasinfo, including
:option:`--ranges` switch to output channel count ranges::

    $ rasinfo -r JAN12_AMNHBIRD_HZ_004.RAS
    File name:              JAN12_AMNHBIRD_HZ_004.RAS
    Original filename:      JAN12_AMNHBIRD_HZ_004.RAS
    Original filename root: JAN12_AMNHBIRD_HZ
    Version name:           Raster Scan V.0.1
    Version number:         1
    PID:                    0
    X-Motor name:           HORZ
    Y-Motor name:           VERT
    Region filename:        TEST.RGN
    Start time:             Tuesday, 17 January 2012, 07:06:05
    Stop time:              Tuesday, 17 January 2012, 13:00:33
    Channel count:          16
    Channel resolution:     3400 x 1301
    Count time:             0.003987
    Sweep count:            1
    Produce ASCII output:   1 (Yes)
    Pixels per point:       1
    Scan direction:         2 (+ve and -ve)
    Scan type:              1 (Quick scan)
    Current X-direction:    -1
    Run number:             4
    Channel  0 range:       0-0 (empty)
    Channel  1 range:       0-2449
    Channel  2 range:       0-1159
    Channel  3 range:       0-907
    Channel  4 range:       0-944
    Channel  5 range:       0-900
    Channel  6 range:       0-1507
    Channel  7 range:       0-328
    Channel  8 range:       0-349
    Channel  9 range:       0-432
    Channel 10 range:       0-359
    Channel 11 range:       0-394
    Channel 12 range:       0-270
    Channel 13 range:       0-3989
    Channel 14 range:       0-222
    Channel 15 range:       0-1372

    Comments:
    The comment line always goes in speech marks
    like this
    and this
    line 4
    line 5
    and the final line

Substitution Templates
----------------------

The :option:`--templates` option causes rasinfo to output the same data but in
a form suitable for use as substitution templates in :option:`rasextract
--title` and :option:`rasextract --output` options::

    $ rasinfo --templates JAN12_CHINAFISH_LZ_003.RAS
    {rasfile}=JAN12_CHINAFISH_LZ_003.RAS
    {filename}=JAN12_CHINAFISH_LZ_003.RAS
    {filename_root}=JAN12_CHINAFISH_LZ
    {version_name}=Raster Scan V.0.1
    {version_number}=1
    {pid}=0
    {x_motor}=HORZ
    {y_motor}=VERT
    {region_filename}=TEST.RGN
    {start_time:%Y-%m-%d %H:%M:%S}=2012-01-17 21:34:08
    {stop_time:%Y-%m-%d %H:%M:%S}=2012-01-17 21:43:07
    {channel_count}=16
    {point_count}=240(sandbox)dave@morpheus:~/Desktop/Beamline/Beamline 6-2/data/data sorted by sample/china fish/maps/LZ/RAS files$ rasinfo --templates JAN12_CHINAFISH_LZ_003.RAS
    {rasfile}=JAN12_CHINAFISH_LZ_003.RAS
    {filename}=JAN12_CHINAFISH_LZ_003.RAS
    {filename_root}=JAN12_CHINAFISH_LZ
    {version_name}=Raster Scan V.0.1
    {version_number}=1
    {pid}=0
    {x_motor}=HORZ
    {y_motor}=VERT
    {region_filename}=TEST.RGN
    {start_time:%Y-%m-%d %H:%M:%S}=2012-01-17 21:34:08
    {stop_time:%Y-%m-%d %H:%M:%S}=2012-01-17 21:43:07
    {channel_count}=16
    {point_count}=240
    {raster_count}=301
    {count_time}=0.004690
    {sweep_count}=1
    {ascii_output}=1
    {pixels_per_point}=1
    {scan_direction}=2
    {scan_type}=1
    {current_x_direction}=-1
    {run_number}=3

    {channel:%02d}=00
    {channel_name}=
    {channel_enabled}=True

    {channel:%02d}=01
    {channel_name}=
    {channel_enabled}=True

    {channel:%02d}=02
    {channel_name}=
    {channel_enabled}=True


    {raster_count}=301
    {count_time}=0.004690
    {sweep_count}=1
    {ascii_output}=1
    {pixels_per_point}=1
    {scan_direction}=2
    {scan_type}=1
    {current_x_direction}=-1
    {run_number}=3

    {channel:%02d}=00
    {channel_name}=
    {channel_enabled}=True

    {channel:%02d}=01
    {channel_name}=
    {channel_enabled}=True

    {channel:%02d}=02
    {channel_name}=
    {channel_enabled}=True
    ...
