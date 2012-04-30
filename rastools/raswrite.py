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

import os
import sys
import struct
import numpy as np
from rastools.rasparse import RasFileReader


class RasAsciiWriter(object):
    def __init__(self, filename_or_obj, channel):
        if isinstance(filename_or_obj, basestring):
            self._file = open(filename_or_obj, 'w')
        else:
            self._file = filename_or_obj
        self._channel = channel

    def write(self, data):
        self._file.write("""\
Version:     {f.version}
Comment1:    {comments[0]}
Comment2:    {comments[1]}
Comment3:    {comments[2]}
Comment4:    {comments[3]}
Comment5:    {comments[4]}
Comment6:    {comments[5]}

Region:      {f.region}
X_Motor:     {f.x_motor}
Y_Motor:     {f.y_motor}
File Head:   {f.file_head}
Output File: {f.file_name}
Sweeps:      {f.sweep_count}
Channels:    1
Points:      {points}
Lines:       {lines}
Count Time:  {f.count_time:.6f}
Data: 

""".format({
            'f': self._channel.ras_file,
            'points': len(data[0]),
            'lines': len(data),
            'comments': self._channel.ras_file.comments.split('\n')
        }))
        for row in data:
            self._file.write(''.join(' %d\n' % value for value in row))


class RasWriter(object):
    def __init__(self, filename_or_obj, channel):
        if isinstance(filename_or_obj, basestring):
            self._file = open(filename_or_obj, 'wb')
        else:
            self._file = filename_or_obj
        self._channel = channel
        self._ras_file = channel.ras_file

    def write(self, data):
        comments = self._ras_file.comments.split('\n')
        self._file.write(RasFileReader.header_struct.pack(
            self._ras_file.version,
            RasFileReader.header_version,
            self._ras_file.pid,
            comments[0],
            comments[1],
            comments[2],
            comments[3],
            comments[4],
            comments[5],
            self._ras_file.x_motor,
            self._ras_file.y_motor,
            self._ras_file.region,
            self._ras_file.file_head,
            self._ras_file.file_name,
            self._ras_file.start_time.strftime(RasFileReader.datetime_format),
            self._ras_file.stop_time.strftime(RasFileReader.datetime_format),
            1,            # num_chans
            0,            # unknown header field
            self._ras_file.count_time,
            self._ras_file.sweep_count,
            self._ras_file.ascii_out,
            len(data[0]), # num_points
            len(data),    # num_raster
            self._ras_file.pixel_point,
            self._ras_file.scan_direction,
            self._ras_file.scan_type,
            self._ras_file.current_x_direction,
            self._ras_file.commands[0],
            self._ras_file.commands[1],
            self._ras_file.commands[2],
            self._ras_file.commands[3],
            self._ras_file.offsets[0],
            self._ras_file.offsets[1],
            self._ras_file.offsets[2],
            self._ras_file.offsets[3],
            self._ras_file.offsets[4],
            self._ras_file.offsets[5],
            self._ras_file.run_number,
        ))
        output_struct = struct.Struct('I' * len(data[0]))
        for row in data:
            self._file.write(output_struct.pack(*row))


class RasAsciiMultiWriter(object):
    def __init__(self, filename_or_obj, ras_file):
        if isinstance(filename_or_obj, basestring):
            self._file = open(filename_or_obj, 'w')
        else:
            self._file = filename_or_obj
        self._ras_file = ras_file
        self._data = None
        self._channel = 0

    def write_page(self, data, channel):
        # We can't allocate the array until this point as we don't know the
        # size of the data after cropping until now. We allocate an array for
        # the number of channels in the source RAS file, knowing we won't be
        # passed more channels than this
        if self._data is None:
            self._data = np.zeros((len(data), len(data[0]), channel.ras_file.channel_count), np.uint32)
        self._data[..., self._channel] = data
        self._channel += 1

    def close(self):
        # Take a slice of the data which only includes the channels that got
        # written
        data = self._data[..., :self._channel]
        self._file.write("""\
Version:     {f.version}
Comment1:    {comments[0]}
Comment2:    {comments[1]}
Comment3:    {comments[2]}
Comment4:    {comments[3]}
Comment5:    {comments[4]}
Comment6:    {comments[5]}

Region:      {f.region}
X_Motor:     {f.x_motor}
Y_Motor:     {f.y_motor}
File Head:   {f.file_head}
Output File: {f.file_name}
Sweeps:      {f.sweep_count}
Channels:    {channels}
Points:      {points}
Lines:       {lines}
Count Time:  {f.count_time:.6f}
Data: 

""".format(
            f=self._ras_file,
            channels=self._channel,
            points=len(data[..., 0][0]),
            lines=len(data[..., 0]),
            comments=self._ras_file.comments.split('\n')
        ))
        for raster in xrange(len(data[..., 0])):
            self._file.write(''.join('%s\n' % ''.join(' %d' % value for value in row) for row in data[raster]))


class RasMultiWriter(object):
    def __init__(self, filename_or_obj, ras_file):
        if isinstance(filename_or_obj, basestring):
            self._file = open(filename_or_obj, 'wb')
        else:
            self._file = filename_or_obj
        self._ras_file = ras_file
        self._data = None
        self._channel = 0

    def write_page(self, data, channel):
        # We can't allocate the array until this point as we don't know the
        # size of the data after cropping until now. We allocate an array for
        # the number of channels in the source RAS file, knowing we won't be
        # passed more channels than this
        if self._data is None:
            self._data = np.zeros((len(data), len(data[0]), channel.ras_file.channel_count), np.uint32)
        self._data[..., self._channel] = data
        self._channel += 1

    def close(self):
        # Take a slice of the data which only includes the channels that got
        # written
        data = self._data[..., :self._channel]
        comments = self._ras_file.comments.split('\n')
        self._file.write(RasFileReader.header_struct.pack(
            self._ras_file.version,
            RasFileReader.header_version,
            self._ras_file.pid,
            comments[0],
            comments[1],
            comments[2],
            comments[3],
            comments[4],
            comments[5],
            self._ras_file.x_motor,
            self._ras_file.y_motor,
            self._ras_file.region,
            self._ras_file.file_head,
            self._ras_file.file_name,
            self._ras_file.start_time.strftime(RasFileReader.datetime_format),
            self._ras_file.stop_time.strftime(RasFileReader.datetime_format),
            self._channel,        # num_chans
            0,                    # unknown header field
            self._ras_file.count_time,
            self._ras_file.sweep_count,
            self._ras_file.ascii_out,
            len(data[..., 0][0]), # num_points
            len(data[..., 0]),    # num_raster
            self._ras_file.pixel_point,
            self._ras_file.scan_direction,
            self._ras_file.scan_type,
            self._ras_file.current_x_direction,
            self._ras_file.commands[0],
            self._ras_file.commands[1],
            self._ras_file.commands[2],
            self._ras_file.commands[3],
            self._ras_file.offsets[0],
            self._ras_file.offsets[1],
            self._ras_file.offsets[2],
            self._ras_file.offsets[3],
            self._ras_file.offsets[4],
            self._ras_file.offsets[5],
            self._ras_file.run_number,
        ))
        # XXX Simply flattening the array and writing everything to disk would
        # work perfectly well at this point, but for huge data files the string
        # allocation for the struct's format and the subsequent bytes array
        # produced tend to wind up hurting performance. Still, we ought to come
        # up with something more intelligent like flattening the np.array and
        # iterating through the result in, say, 1Mb chunks
        output_struct = struct.Struct('I' * len(data[..., 0][0]) * self._channel)
        for raster in xrange(len(data[..., 0])):
            self._file.write(output_struct.pack(*(i for i in data[raster].flat)))
        # XXX See the note in rasfile.py about the off-by-one error in the
        # header. This extraneous uint32 ensures that our output matches the
        # length of the original, bugs'n'all
        self._file.write(struct.pack('I', 0))
