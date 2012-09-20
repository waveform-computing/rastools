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

"""Writer for QSCAN RAS format files"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import struct

import numpy as np

from rastools.rasparse import RasParser


DEFAULT_X_MOTOR          = 'HORZ'
DEFAULT_Y_MOTOR          = 'VERT'
DEFAULT_REGION_FILENAME  = ''
DEFAULT_SWEEP_COUNT      = 1
DEFAULT_COUNT_TIME       = 0
DEFAULT_PIXELS_PER_POINT = 1
DEFAULT_SCAN_DIRECTION   = 2
DEFAULT_SCAN_TYPE        = 1
DEFAULT_X_DIRECTION      = -1

RAS_ASCII_HEADER = """\
Version:     {version_string}
Comment1:    {comments[0]}
Comment2:    {comments[1]}
Comment3:    {comments[2]}
Comment4:    {comments[3]}
Comment5:    {comments[4]}
Comment6:    {comments[5]}

Region:      {region_filename}
X_Motor:     {x_motor}
Y_Motor:     {y_motor}
File Head:   {filename_root}
Output File: {filename_original}
Sweeps:      {sweep_count}
Channels:    {channel_count}
Points:      {x_size}
Lines:       {y_size}
Count Time:  {count_time:.6f}
Data: 

"""

class RasAsciiWriter(object):
    "Single channel writer for the ASCII variant of the QSCAN RAS format"

    def __init__(self, filename_or_obj, channel):
        try:
            self._file = open(filename_or_obj, 'w')
        except TypeError:
            self._file = filename_or_obj
        self._data_file = channel.parent
        self._channel = channel

    def write(self, data):
        "Write the specified data to the output file"
        data_file = self._data_file
        self._file.write(RAS_ASCII_HEADER.format(
            version_string=RasParser.header_string,
            x_size=len(data[0]),
            y_size=len(data),
            channel_count=1,
            comments=data_file.comments.split('\n') + [''] * 6,
            filename_root=data_file.filename_root,
            region_filename=data_file.header.get('region_filename', ''),
            x_motor=data_file.header.get('x_motor', DEFAULT_X_MOTOR),
            y_motor=data_file.header.get('y_motor', DEFAULT_Y_MOTOR),
            filename_original=data_file.header.get(
                'filename_original', data_file.filename),
            sweep_count=data_file.header.get(
                'sweep_count', DEFAULT_SWEEP_COUNT),
            count_time=data_file.header.get('count_time', DEFAULT_COUNT_TIME),
        ))
        for row in data:
            self._file.write(''.join(' %d\n' % value for value in row))
        self._file.close()


class RasWriter(object):
    "Single channel writer for the default binary QSCAN RAS format"

    def __init__(self, filename_or_obj, channel):
        try:
            self._file = open(filename_or_obj, 'wb')
        except TypeError:
            self._file = filename_or_obj
        self._data_file = channel.parent
        self._channel = channel

    def write(self, data):
        "Write the specified data to the output file"
        data_file = self._data_file
        comments = data_file.comments.split('\n') + [''] * 6
        def b(s):
            return s.encode(RasParser.char_encoding)
        self._file.write(RasParser.header_struct.pack(
            b(RasParser.header_string),
            RasParser.header_version,
            data_file.header.get('pid', 0),
            b(comments[0]),
            b(comments[1]),
            b(comments[2]),
            b(comments[3]),
            b(comments[4]),
            b(comments[5]),
            b(data_file.header.get('x_motor', DEFAULT_X_MOTOR)),
            b(data_file.header.get('y_motor', DEFAULT_Y_MOTOR)),
            b(data_file.header.get('region_filename', DEFAULT_REGION_FILENAME)),
            b(data_file.filename_root),
            b(data_file.header.get('filename_original', data_file.filename)),
            b(data_file.start_time.strftime(RasParser.datetime_format)),
            b(data_file.stop_time.strftime(RasParser.datetime_format)),
            1,            # num_chans
            0,            # unknown header field
            data_file.header.get('count_time', DEFAULT_COUNT_TIME),
            data_file.header.get('sweep_count', DEFAULT_SWEEP_COUNT),
            data_file.header.get('ascii_output', 0),
            len(data[0]), # num_points
            len(data),    # num_raster
            data_file.header.get('pixels_per_point', DEFAULT_PIXELS_PER_POINT),
            data_file.header.get('scan_direction', DEFAULT_SCAN_DIRECTION),
            data_file.header.get('scan_type', DEFAULT_SCAN_TYPE),
            data_file.header.get('current_x_direction', DEFAULT_X_DIRECTION),
            len(data),    # command 1
            len(data[0]), # command 2
            0,            # command 3
            0,            # command 4
            0.0,          # offset 1
            0.0,          # offset 2
            0.0,          # offset 3
            0.0,          # offset 4
            0.0,          # offset 5
            0.0,          # offset 6
            data_file.header.get('run_number', 1),
        ))
        output_struct = struct.Struct(str('I' * len(data[0])))
        for row in data:
            self._file.write(output_struct.pack(*(int(i) for i in row)))
        self._file.close()


class RasAsciiMultiWriter(object):
    "Multi channel writer for the ASCII variant of the QSCAN RAS format"

    def __init__(self, filename_or_obj, data_file):
        if isinstance(filename_or_obj, str):
            self._file = open(filename_or_obj, 'w')
        else:
            self._file = filename_or_obj
        self._data_file = data_file
        self._data = None

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        self.close()

    def write_page(self, data, channel):
        "Write the channel to the output file"
        if self._data is None:
            self._data = np.dstack((data,))
        else:
            self._data = np.dstack((self._data, data))

    def close(self):
        "Finalize and close the output file"
        # Take a slice of the data which only includes the channels that got
        # written
        data_file = self._data_file
        self._file.write(RAS_ASCII_HEADER.format(
            version_string=RasParser.header_string,
            x_size=len(self._data[..., 0][0]),
            y_size=len(self._data[..., 0]),
            channel_count=len(self._data[0, 0]),
            comments=data_file.comments.split('\n') + [''] * 6,
            region_filename=data_file.header.get('region_filename', ''),
            x_motor=data_file.header.get('x_motor', DEFAULT_X_MOTOR),
            y_motor=data_file.header.get('y_motor', DEFAULT_Y_MOTOR),
            filename_root=data_file.filename_root,
            filename_original=data_file.header.get(
                'filename_original', data_file.filename),
            sweep_count=data_file.header.get(
                'sweep_count', DEFAULT_SWEEP_COUNT),
            count_time=data_file.header.get('count_time', DEFAULT_COUNT_TIME),
        ))
        for raster in range(len(self._data[..., 0])):
            self._file.write(
                ''.join(
                    ''.join(
                        ' %d' % value
                        for value in row
                    ) + '\n'
                    for row in self._data[raster]
                )
            )
        self._file.close()


class RasMultiWriter(object):
    "Multi channel writer for the default binary QSCAN RAS format"
    
    def __init__(self, filename_or_obj, data_file):
        try:
            self._file = open(filename_or_obj, 'wb')
        except TypeError:
            self._file = filename_or_obj
        self._data_file = data_file
        self._data = None

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        self.close()

    def write_page(self, data, channel):
        "Write the channel to the output file"
        if self._data is None:
            self._data = np.dstack((data,))
        else:
            self._data = np.dstack((self._data, data))

    def close(self):
        "Finalize and close the output file"
        data_file = self._data_file
        comments = data_file.comments.split('\n') + [''] * 6
        def b(s):
            return s.encode(RasParser.char_encoding)
        self._file.write(RasParser.header_struct.pack(
            b(RasParser.header_string),
            RasParser.header_version,
            data_file.header.get('pid', 0),
            b(comments[0]),
            b(comments[1]),
            b(comments[2]),
            b(comments[3]),
            b(comments[4]),
            b(comments[5]),
            b(data_file.header.get('x_motor', 'HORZ')),
            b(data_file.header.get('y_motor', 'VERT')),
            b(data_file.header.get('region_filename', '')),
            b(data_file.filename_root),
            b(data_file.header.get('filename_original', data_file.filename)),
            b(data_file.start_time.strftime(RasParser.datetime_format)),
            b(data_file.stop_time.strftime(RasParser.datetime_format)),
            len(self._data[0, 0]),      # num_chans
            0,            # unknown header field
            data_file.header.get('count_time', 0.0),
            data_file.header.get('sweep_count', 1),
            data_file.header.get('ascii_output', 0),
            len(self._data[..., 0][0]), # num_points
            len(self._data[..., 0]),    # num_raster
            data_file.header.get('pixels_per_point', 1),
            data_file.header.get('scan_direction', 2),
            data_file.header.get('scan_type', 1),
            data_file.header.get('current_x_direction', -1),
            len(self._data[..., 0][0]), # command 1
            len(self._data[..., 0]),    # command 2
            0,            # command 3
            0,            # command 4
            0.0,          # offset 1
            0.0,          # offset 2
            0.0,          # offset 3
            0.0,          # offset 4
            0.0,          # offset 5
            0.0,          # offset 6
            data_file.header.get('run_number', 1),
        ))
        output_struct = struct.Struct(
            str('I' * len(self._data[..., 0][0]) * len(self._data[0, 0])))
        for raster in range(len(self._data[..., 0])):
            self._file.write(
                output_struct.pack(*(int(i) for i in self._data[raster].flat)))
        # XXX See the note in rasparse.py about the off-by-one error in the
        # header. This extraneous uint32 ensures that our output matches the
        # length of the original, bugs'n'all
        self._file.write(struct.pack('I', 0))
        self._file.close()
