#!/usr/bin/env python
# vim: set et sw=4 sts=4:

import os
import sys
import logging
import struct
import datetime as dt
import numpy as np

class RasFileReader(object):
    """Parser for QSCAN RAS files"""

    # QSCAN Data File format - April '08
    #
    # The QSCAN file format consists of a binary copy of a data structure, the
    # header, followed by the data as a continuous block of unsigned 32 bit
    # integers.
    #
    # Please note that this header structure was copied from other data
    # collection programs, contains fields that are not needed and it will
    # change in the near future - I will let you know of any changes.
    #
    # At present the header, is a simple C structure defined as shown below in
    # the test program to read and print out a binary file.
    #
    # #include <stdio.h>
    # #include <stdlib.h>
    #
    # typedef struct
    # {
    #   char version[80];             /* Version number                      */
    #   int  ver_num;                 /* Not used?                           */
    #   unsigned long pid;            /* PID of data collection process      */
    #   char comment1[80];            /* Misc. comment lines                 */
    #   char comment2[80];
    #   char comment3[80];
    #   char comment4[80];
    #   char comment5[80];
    #   char comment6[80];
    #   char x_motor[40];             /* name of X motor                     */
    #   char y_motor[40];             /* Name of Y motor                     */
    #   char region[80];              /* Region file name                    */
    #   char file_head[80];           /* Data file name info.                */
    #   char file_name[80];
    #   char start_time[40];
    #   char stop_time[40];
    #   int num_chans;                /* number of channels to collect       */
    #                                 /* - sub addresses of the hex scaler   */
    #   double count_time;            /* copied from the region              */
    #   int num_sweeps;               /* number of sweeps                    */
    #   int ascii_out;                /* automatically generate ASCII file?  */
    #   int num_points;               /* copied from region - redundant?     */
    #   int num_raster;               /* copied from region - redundant?     */
    #   int pixel_point;              /* pixel per pt, for real-time display */
    #   int scan_dir;                 /* = 2 scan in + & -ve X, 1 = +ve only */
    #   int scan_type;                /* quick scan or pt to pt, 1 or 2      */
    #   int cur_x_dir;                /* cur. dir. of x for real-time plot   */
    #   int command1;                 /* Point num from collector process    */
    #   int command2;                 /* Line number, from collector         */
    #   int command3;                 /* Exit command from collector         */
    #   int command4;                 /* Commands to collector               */
    #   double offsets[6];            /* Not used at present                 */
    #   int run_num;                  /* Incremented for file name           */
    # } _header;
    #
    # int dump_file_test(char *fname)
    # {
    #   int i,k,l;
    #   FILE *fp;
    #   char buf[80];
    #   unsigned int uidata;
    #   _header header;
    #
    #   if( (fp = fopen(fname,"rb")  ) == NULL )
    #     {
    #       printf("\nFailed to open: %s",fname);
    #       return 1;
    #     }
    #
    #   fread((void *)&header,sizeof(_header),1,fp);
    #
    #   printf("\n Header Info: \n Version: %s \n Comment1: %s\n",
    #      header.version,header.comment1);
    #
    #   printf("\nLines: %d Cols: %d Channels: %d\n",
    #      header.num_raster,header.num_points,header.num_chans);
    #
    #   printf("\nHit enter to dump the data...");
    #   fgets(buf,80,stdin);
    #
    #   /* Read data in with a single fread, or point by point... */
    #
    #   for(i=0;i<header.num_raster;i++)       /* number of lines         */
    #     {
    #       for(k=0;k<header.num_points;k++)   /* points in each line     */
    #        {
    #      for(l=0;l<header.num_chans;l++)     /* data channels per point */
    #       {
    #         fread((void *)&uidata,sizeof(unsigned int),1,fp);
    #         printf("\n%d %d) %d %u",i+1,k+1,l+1,uidata);
    #       }
    #        }
    #     }
    #
    #   fclose(fp);
    #
    #   return 0;
    # }
    #
    # int main(int argc,char *argv[])
    # {
    #   if( argc != 2 )
    #    {
    #     printf("\nPlease supply a file name: ");
    #     exit(0);
    #    }
    #   dump_file_test(argv[1]);
    # }
    datetime_format = '%a %b %d %H:%M:%S %Y'
    header_struct = struct.Struct(
        '<'       # little-endian
        + '80s'   # version
        + 'i'     # ver_num
        + 'L'     # pid
        + '80s'*6 # comment1..comment6
        + '40s'   # x_motor
        + '40s'   # y_motor
        + '80s'   # region
        + '80s'   # file_head
        + '80s'   # file_name
        + '40s'   # start_time
        + '40s'   # stop_time
        + 'i'     # num_chans
        + 'i'     # XXX Not listed in spec, but it's there!
        + 'd'     # count_time
        + 'i'     # num_sweeps
        + 'i'     # ascii_out
        + 'i'     # num_points
        + 'i'     # num_raster
        + 'i'     # pixel_point
        + 'i'     # scan_dir
        + 'i'     # scan_type
        + 'i'     # cur_x_dir
        + 'i'*4   # command1..command4
        + 'd'*6   # offsets0..offsets5
        + 'i'     # run_num
        + 'i'     # XXX Not listed in spec, padding?
    )

    def __init__(self, f, verbose=False):
        """Constructor accepts a filename or file-like object"""
        super(RasFileReader, self).__init__()
        self.verbose = verbose
        if isinstance(f, basestring):
            logging.debug('Opening file %s' % f)
            self._file = open(f, 'rb')
        else:
            self._file = f
        # Parse the header
        logging.debug('Reading QSCAN RAS header')
        self.comments = [''] * 6
        self.commands = [''] * 4
        self.offsets = [0.0] * 6
        (
            self.version,
            self.version_number,
            self.pid,
            self.comments[0],
            self.comments[1],
            self.comments[2],
            self.comments[3],
            self.comments[4],
            self.comments[5],
            self.x_motor,
            self.y_motor,
            self.region,
            self.file_head,
            self.file_name,
            self.start_time,
            self.stop_time,
            self.channel_count,
            _,
            self.count_time,
            self.sweep_count,
            self.ascii_out,
            self.point_count,
            self.raster_count,
            self.pixel_point,
            self.scan_direction,
            self.scan_type,
            self.current_x_direction,
            self.commands[0],
            self.commands[1],
            self.commands[2],
            self.commands[3],
            self.offsets[0],
            self.offsets[1],
            self.offsets[2],
            self.offsets[3],
            self.offsets[4],
            self.offsets[5],
            self.run_number,
            _,
        ) = self.header_struct.unpack(self._file.read(self.header_struct.size))
        if not self.version.startswith('Raster Scan'):
            raise ValueError('This does not appear to be a QSCAN RAS file')
        if self.version_number != 1:
            raise ValueError('Cannot interpret QSCAN RAS version %d - only version 1' % self.version_number)
        # Right strip the various string fields
        strip_chars = '\t\r\n \0'
        self.version = self.version.rstrip(strip_chars)
        self.x_motor = self.x_motor.rstrip(strip_chars)
        self.y_motor = self.y_motor.rstrip(strip_chars)
        self.region = self.region.rstrip(strip_chars)
        self.file_head = self.file_head.rstrip(strip_chars)
        self.file_name = self.file_name.rstrip(strip_chars)
        # Convert comments to a simple string
        self.comments = '\n'.join(
            line.rstrip(strip_chars)
            for line in self.comments
        )
        # Convert timestamps to a sensible format
        self.start_time = dt.datetime.strptime(
            self.start_time.rstrip(strip_chars), self.datetime_format)
        self.stop_time = dt.datetime.strptime(
            self.stop_time.rstrip(strip_chars), self.datetime_format)
        self._channels = None

    @property
    def channels(self):
        if self._channels is None:
            # Initialize a list of zero-filled arrays
            self._channels = [
                np.zeros((self.raster_count, self.point_count), np.uint32)
                for channel in xrange(self.channel_count)
            ]
            # Read a line at a time and extract the specified channel
            input_struct = struct.Struct('I' * self.point_count * self.channel_count)
            if self.verbose:
                progress = 0
                status = 'Reading channel data %d%%' % progress
                sys.stderr.write(status)
            for raster in xrange(self.raster_count):
                data = input_struct.unpack(self._file.read(input_struct.size))
                for channel in xrange(self.channel_count):
                    self._channels[channel][raster] = data[channel - 1::self.channel_count]
                if self.verbose:
                    new_progress = round(raster * 100.0 / self.raster_count)
                    if new_progress != progress:
                        progress = new_progress
                        new_status = 'Reading channel data %d%%' % progress
                        sys.stderr.write('\b' * len(status))
                        sys.stderr.write(new_status)
                        status = new_status
            if self.verbose:
                sys.stderr.write('\n')
        return self._channels

