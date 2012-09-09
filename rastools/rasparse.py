# vim: set et sw=4 sts=4:

# Copyright 2012 Dave Hughes.
#
# This file is part of rastools.
#
# rastools is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# rastools is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# rastools.  If not, see <http://www.gnu.org/licenses/>.

"""Parser for QSCAN RAS files"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import logging
import struct
import datetime as dt

import numpy as np


class Error(ValueError):
    """Base exception class"""

class RasFileError(Error):
    """Base class for errors encountered in RAS file parsing"""

class ChannelFileError(Error):
    """Base class for errors encountered in channel file parsing"""


class RasParser(object):
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
    char_encoding = 'ascii'
    header_version = 1
    header_string = 'Raster Scan V.0.1'
    header_struct = struct.Struct(str(
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
        + 'i'     # not listed in spec, but it's there!
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
    ))

    def __init__(
            self, data_file, channels_file=None, **kwargs):
        """Constructor accepts a filename or file-like object"""
        super(RasParser, self).__init__()
        (   self.progress_start,
            self.progress_update,
            self.progress_finish,
        ) = kwargs.get('progress', (None, None, None))
        try:
            self._file = open(data_file, 'rb')
        except TypeError:
            self._file = data_file
        # Parse the header
        logging.debug('Reading QSCAN RAS header')
        self.header = {}
        self.comments = [''] * 6
        self.header['commands'] = [0] * 4
        self.header['offsets'] = [0.0] * 6
        (   self.header['version_string'],
            self.version,
            self.header['pid'],
            self.comments[0],
            self.comments[1],
            self.comments[2],
            self.comments[3],
            self.comments[4],
            self.comments[5],
            self.header['x_motor'],
            self.header['y_motor'],
            self.header['region_filename'],
            self.filename_root,
            self.header['filename_original'],
            self.start_time,
            self.stop_time,
            self.channel_count,
            _,
            self.header['count_time'],
            self.header['sweep_count'],
            self.header['ascii_out'],
            self.x_size,
            self.y_size,
            self.header['pixels_per_point'],
            self.header['scan_direction'],
            self.header['scan_type'],
            self.header['current_x_direction'],
            self.header['commands'][0],
            self.header['commands'][1],
            self.header['commands'][2],
            self.header['commands'][3],
            self.header['offsets'][0],
            self.header['offsets'][1],
            self.header['offsets'][2],
            self.header['offsets'][3],
            self.header['offsets'][4],
            self.header['offsets'][5],
            self.header['run_number'],
        ) = self.header_struct.unpack(self._file.read(self.header_struct.size))
        # XXX There's a nasty off-by-one error here. The header actually
        # contains one more int32 which appears to always be zero. By not
        # reading it, we mistake it for the first value in the first channel.
        # The result is that all channel numbers get pushed along by one (0
        # becomes 1, 1 becomes 2, etc. and the last becomes 0), and skip
        # reading one value at the end. However, this is also what the original
        # software does so I'm loathe to do different despite it being an
        # obvious bug. Anyway, one should avoid using the first channel of data
        # in a RAS file as its first value will definitely be incorrect
        if not self.header['version_string'].startswith(b'Raster Scan'):
            raise RasFileError('This does not appear to be a QSCAN RAS file')
        if self.version != self.header_version:
            raise RasFileError(
                'Cannot interpret QSCAN RAS version %d - only '
                'version %d' % (self.version, self.header_version))
        # Right strip the various string fields
        strip_chars = '\t\r\n \0'
        self.filename = self._file.name
        self.filename_root = self.filename_root.decode(
                self.char_encoding).rstrip(strip_chars)
        for field in (
                'version_string',
                'x_motor',
                'y_motor',
                'region_filename',
                'filename_original'):
            self.header[field] = self.header[field].decode(
                    self.char_encoding).rstrip(strip_chars)
        # Convert comments to a simple string
        self.comments = [
            line.decode(self.char_encoding).rstrip(strip_chars)
            for line in self.comments]
        self.comments = '\n'.join(line for line in self.comments if line)
        # Convert timestamps to a sensible format
        self.start_time = dt.datetime.strptime(
            self.start_time.decode(
                self.char_encoding).rstrip(strip_chars), self.datetime_format)
        self.stop_time = dt.datetime.strptime(
            self.stop_time.decode(
                self.char_encoding).rstrip(strip_chars), self.datetime_format)
        self.channels = RasChannels(self, channels_file)
        if not kwargs.get('delay_load', True):
            self.channels._read_data()

    def format_dict(self, **kwargs):
        """Returns a dictionary suitable for use with the format method.

        This method returns a dictionary containing information extracted from
        the RAS file header, with the intention that it be used in with the
        string format() method. Any keyword arguments specified in the call are
        added to the dictionary that is returned (allowing, for example, a
        channel object to enhance the dictionary with channel-specific
        information).
        """
        result = {}
        result.update(
            self.header,
            filename      = self._file.name,
            filename_root = self.filename_root,
            version       = self.version,
            start_time    = self.start_time,
            stop_time     = self.stop_time,
            channel_count = self.channel_count,
            x_size        = self.x_size,
            y_size        = self.y_size,
            comments      = self.comments,
            **kwargs
        )
        return result


class RasChannels(object):
    """Represents a sequence of channels in a RAS file"""

    def __init__(self, parent, channels_file):
        super(RasChannels, self).__init__()
        self.parent = parent
        self._done_data = False
        # All channels are initially created unnamed and enabled
        self._items = [
            RasChannel(self, index, '')
            for index in range(self.parent.channel_count)
        ]
        if channels_file:
            # If a channels file is provided, disable all the channels and
            # enable only those found within the file
            for channel in self:
                channel.enabled = False
            # Parse the channels file
            try:
                self._file = open(channels_file, 'rb')
            except TypeError:
                self._file = channels_file
            logging.debug('Parsing channels file')
            for line_num, line in enumerate(self._file):
                line = line.decode('utf-8').strip()
                # Ignore empty lines and #-prefixed comment lines
                if line and not line.startswith('#'):
                    try:
                        (index, name) = line.split(None, 1)
                    except ValueError:
                        raise ChannelFileError(
                            'only one value found on line %d' % line_num + 1)
                    try:
                        index = int(index)
                    except ValueError:
                        raise ChannelFileError(
                            'non-integer channel number ("%s") found on '
                            'line %d' % (index, line_num + 1))
                    if index < 0:
                        raise ChannelFileError(
                            'negative channel number (%d) found on line '
                            '%d' % (index, line_num + 1))
                    if index >= len(self):
                        raise ChannelFileError(
                            'channel number (%d) on line %d exceeds number '
                            'of channels in RAS file (%d)' % (
                                index, line_num + 1, len(self)))
                    if self[index].enabled:
                        raise ChannelFileError(
                            'channel %d has been specified twice; second '
                            'instance on line %d' % (index, line_num + 1))
                    self[index].name = name
                    self[index].enabled = True

    def _read_data(self):
        """Reads channel data from the source file."""
        # This method is called when channel data is first accessed to read the
        # data from the source file (in other words, channel data is loaded
        # lazily - this is because some applications like rasinfo only require
        # header information and extracting the channel data is a lengthy
        # operation).
        if not self._done_data:
            self._done_data = True
            # Read all data in one go and chop it into the required channels
            if self.parent.progress_start:
                self.parent.progress_start()
            try:
                data = np.fromfile(
                    self.parent._file, dtype=np.uint32,
                    count=self.parent.x_size * self.parent.y_size * len(self))
                for channel in self:
                    channel._data = data[channel.index::len(self)].reshape(
                        (self.parent.y_size, self.parent.x_size))
                if self.parent.progress_update:
                    self.parent.progress_update(
                        round(channel.index * 100.0 / len(self)))
            finally:
                if self.parent.progress_finish:
                    self.parent.progress_finish()

    def __len__(self):
        return self.parent.channel_count

    def __getitem__(self, index):
        return self._items[index]

    def __iter__(self):
        for channel in self._items:
            yield channel

    def __contains__(self, obj):
        return obj in self._items


class RasChannel(object):
    """Container for a channel of data in a RAS file"""

    def __init__(self, channels, index, name, enabled=True):
        self._channels = channels
        self._data = None
        self._index = index
        self.name = name if name else 'I{0}'.format(index)
        self.enabled = enabled

    @property
    def index(self):
        """Returns the index of the channel in the RAS file"""
        return self._index

    @property
    def data(self):
        """Returns the channel data as a numpy array"""
        self._channels._read_data()
        return self._data

    @property
    def parent(self):
        """Returns the RAS file object that contains this channel"""
        return self._channels.parent

    def format_dict(self, **kwargs):
        """Returns a dictionary suitable for use with the format method.

        This method returns a dictionary containing information extracted from
        the RAS file channel, with the intention that it be used in with the
        string format() method. Any keyword arguments specified in the call are
        added to the dictionary that is returned.
        """
        return self.parent.format_dict(
            channel         = self.index,
            channel_name    = self.name,
            channel_enabled = self.enabled,
            channel_min     = self.data.min(),
            channel_max     = self.data.max(),
            channel_empty   = self.data.min() == self.data.max(),
            **kwargs
        )
