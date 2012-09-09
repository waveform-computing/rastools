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

"""Writer for Sam's dat files"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import numpy as np


DEFAULT_ENERGY_POINTS = 10000.0

DAT_HEADER = """\
* Abscissa points : {x_size:5d}
* Ordinate points : {y_size:5d}
* BLANK LINE
* Data Channels : {channel_count:4d}
# Data Labels : {channel_names}
* Comments: 
{comments}* BLANK LINE
* Abscissa points requested :
* {x_coords}
* BLANK LINE
* BLANK LINE
* Ordinate points requested :
* {y_coords}
* BLANK LINE
* BLANK LINE
* Energy points requested: 
* {energy_points:9.1f}
* BLANK LINE
* DATA
"""


class DatWriter(object):
    "Single channel writer for Sam's dat format"

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
        # XXX Is there any way of getting the real coords in the case of a
        # cropped .dat file? If so, define it here...
        x_coords = list(range(len(data[0])))
        y_coords = list(range(len(data)))
        self._file.write(DAT_HEADER.format(
            x_size=len(data[0]),
            y_size=len(data),
            channel_count=1,
            channel_names=self._channel.name,
            comments=''.join(
                '* %s\n' % line for line in data_file.comments.split('\n')),
            x_coords='\t'.join('%.4f' % i for i in x_coords),
            y_coords='\t'.join('%.4f' % i for i in y_coords),
            energy_points=data_file.header.get(
                'energy_points', DEFAULT_ENERGY_POINTS),
        ))
        for y, row in enumerate(data):
            for x, value in enumerate(row):
                self._file.write(
                    '%.4f\t%.4f\t%.1f\n' % (y_coords[y], x_coords[x], value))
        self._file.close()

class DatMultiWriter(object):
    "Multi channel writer for Sam's dat format"

    def __init__(self, filename_or_obj, data_file):
        try:
            self._file = open(filename_or_obj, 'w')
        except TypeError:
            self._file = filename_or_obj
        self._data_file = data_file
        self._data = None
        self._names = []

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
        self._names.append(channel.name)

    def close(self):
        "Finalize and close the output file"
        data_file = self._data_file
        # XXX Is there any way of getting the real coords in the case of a
        # cropped .dat file? If so, define it here...
        x_coords = list(range(len(self._data[..., 0][0])))
        y_coords = list(range(len(self._data[..., 0])))
        self._file.write(DAT_HEADER.format(
            x_size=len(self._data[..., 0][0]),
            y_size=len(self._data[..., 0]),
            channel_count=len(self._data[0, 0]),
            channel_names=''.join('%s\t' % s for s in self._names),
            comments=''.join(
                '* %s\n' % line for line in data_file.comments.split('\n')),
            x_coords='\t'.join('%.4f' % i for i in x_coords),
            y_coords='\t'.join('%.4f' % i for i in y_coords),
            energy_points=data_file.header.get(
                'energy_points', DEFAULT_ENERGY_POINTS),
        ))
        for y, row in enumerate(self._data):
            for x, values in enumerate(row):
                self._file.write(
                    '%.4f\t%.4f\t%s\n' % (
                        y_coords[y],
                        x_coords[x],
                        ''.join('%.1f\t' % value for value in values)
                    )
                )
        self._file.close()
