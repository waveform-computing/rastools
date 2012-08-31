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

"""Parser for Sam's dat files"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import re
import logging
import datetime as dt
from collections import namedtuple
from bisect import bisect_left

import numpy as np


class Error(ValueError):
    """Base exception class"""

class DatFileError(Error):
    """Base class for errors encountered in dat file parsing"""

class SortedList(list):
    """Sorted list derivative with quicker index() method"""
    def __init__(self, source):
        super(SortedList, self).__init__(sorted(source))

    def index(self, i):
        "Locate i within the sorted list"
        result = bisect_left(self, i)
        if result >= len(self) or self[result] != i:
            raise ValueError('{0} is not in list'.format(i))
        return result


DatParseState = namedtuple('DatParseState', ('re', 'next'))

class DatParser(object):
    """Parser for Sam's dat files"""

    # We haven't got a formal definition of Sam's dat format, but it's a
    # fairly simple text based format. In lieu of any formal grammar, we just
    # use a whole load of regexes and a simple state machine to parse it. A
    # sample header is given below:
    #
    # * Abscissa points :   305
    # * Ordinate points :   287
    # * BLANK LINE
    # * Data Channels :   4
    # * Data Labels : I0	I1	I2	I0STRM	ICR	OCR...
    # * Comments: 
    # * dwell time = 100.0
    # * 
    # * 
    # * BLANK LINE
    # * Abscissa points requested :
    # * 0.3503	0.3493	0.3483	0.3473	0.3463	0.3453	0.3443	0.3433...
    # * BLANK LINE
    # * BLANK LINE
    # * Ordinate points requested :
    # * -1.3149	-1.3139	-1.3129	-1.3119	-1.3109	-1.3099	-1.3089	-1.3079...
    # * BLANK LINE
    # * BLANK LINE
    # * Energy points requested: 
    # *   10000.0
    # * BLANK LINE
    # * DATA
    # -1.3149	0.3503	1	1	1	25686	60	10	2	1	0	3	1	1...
    # -1.3149	0.3493	1	1	1	25690	57	10	86	21	0	98	92	68...
    # -1.3149	0.3483	1	1	1	25683	60	10	95	18	2	69	107	70...
    # -1.3149	0.3473	1	1	1	25679	57	10	70	16	4	87	90	65...
    # ...
    header_version = 1

    def __init__(
            self, data_file, channels_file=None, **kwargs):
        """Constructor accepts a filename or file-like object"""
        super(DatParser, self).__init__()
        self.progress_start, self.progress_update, self.progress_finish = \
            kwargs.get('progress', (None, None, None))
        if channels_file:
            logging.warning('Channels files are currently ignored')
        try:
            self._file = open(data_file, 'rU')
        except TypeError:
            self._file = data_file
        self.header = {}
        self.version = self.header_version
        self.filename = self._file.name
        self.filename_root = re.sub(r'^(.*?)[_-][0-9]+\.(dat|DAT)$', r'\1',
            os.path.split(self._file.name)[1])
        self.start_time = dt.datetime.fromtimestamp(
            os.stat(self._file.name).st_ctime
        )
        self.stop_time = self.start_time
        self.y_size = 0
        self.x_size = 0
        self.x_coords = []
        self.y_coords = []
        self.comments = ''
        self.channel_names = []
        self.channel_count = 0
        self.header['energy_points'] = 0.0
        data_line = self.read_header()
        self.header['x_from'] = self.x_coords[0]
        self.header['x_to'] = self.x_coords[-1]
        self.header['y_from'] = self.y_coords[0]
        self.header['y_to'] = self.y_coords[-1]
        self.channels = DatChannels(self, data_line)
        if not kwargs.get('delay_load', True):
            self.channels._read_data()

    def read_header(self):
        """Parses the dat header"""
        logging.debug('Reading dat header')
        ignore = re.compile(r'^\* *(BLANK LINE)?$')
        start_state = 'abs_count'
        state_table = {
            'abs_count': DatParseState(
                re.compile(r'^\* *Abscissa points *: *(\d+)$'),
                ('ord_count',)),
            'ord_count': DatParseState(
                re.compile(r'^\* *Ordinate points *: *(\d+)$'),
                ('chan_count',)),
            'chan_count': DatParseState(
                re.compile(r'^\* *Data Channels *: *(\d+)$'),
                ('chan_labels',)),
            'chan_labels': DatParseState(
                re.compile(r'^[*#] *Data Labels *: *(.*)$'),
                ('comments',)),
            'comments': DatParseState(
                re.compile(r'^\* *Comments *:'),
                ('comment_content',)),
            'comment_content': DatParseState(
                re.compile(r'^\* *(.*)$'),
                ('abs_head', 'comment_content')),
            'abs_head': DatParseState(
                re.compile(r'^\* *Abscissa points requested *:'),
                ('abs_points',)),
            'abs_points': DatParseState(
                re.compile(r'^\* *((([-+]?\d+(\.\d+)?)\s*)*)$'),
                ('ord_head',)),
            'ord_head': DatParseState(
                re.compile(r'^\* *Ordinate points requested *:'),
                ('ord_points',)),
            'ord_points': DatParseState(
                re.compile(r'^\* *((([-+]?\d+(\.\d+)?)\s*)*)$'),
                ('energy_head',)),
            'energy_head': DatParseState(
                re.compile(r'^\* *Energy points requested *:'),
                ('energy_points',)),
            'energy_points': DatParseState(
                re.compile(r'^\* *([-+]?\d+(\.\d+)?)$'),
                ('data',)),
            'data': DatParseState(
                re.compile(r'^\* *DATA'), ()),
        }
        states = [start_state]
        line_num = 0
        for line_num, line in enumerate(self._file):
            # Skip ignorable lines
            if ignore.match(line):
                logging.debug('Skipping line %d', line_num + 1)
                continue
            # Find a state which matches this non-ignorable line
            state = None
            for state in states:
                regex, new_states = state_table[state]
                match = regex.match(line)
                if match:
                    break
            if not match:
                raise DatFileError(
                    'expected %s on line %d of dat file' %
                    (state_table[states[0]][0].pattern, line_num + 1)
                )
            logging.debug('dat parser in state %s' % state)
            # If we've reached the end of the state graph, drop out of the loop
            if new_states:
                states = new_states
            else:
                break
            # Otherwise, try and find a handler for this state
            if hasattr(self, '_state_%s' % state):
                getattr(self, '_state_%s' % state)(match, line_num + 1)
        logging.debug('Reached end of dat header on line %d', line_num)
        return line_num

    def _state_abs_count(self, match, line):
        """Parse the abscissa count"""
        try:
            self.x_size = int(match.group(1))
        except ValueError:
            raise DatFileError(
                'non-integer abscissa count (%s) found on line %d' %
                (match.group(1), line)
            )

    def _state_ord_count(self, match, line):
        """Parse the ordinate count"""
        try:
            self.y_size = int(match.group(1))
        except ValueError:
            raise DatFileError(
                'non-integer ordinate count (%s) found on line %d' %
                (match.group(1), line)
            )

    def _state_chan_count(self, match, line):
        """Parse the number of channels"""
        try:
            self.channel_count = int(match.group(1))
        except ValueError:
            raise DatFileError(
                'non-integer channel count (%s) found on line %d' %
                (match.group(1), line)
            )

    def _state_chan_labels(self, match, line):
        """Parse the channel names"""
        self.channel_names = match.group(1).split()
        if len(self.channel_names) != self.channel_count:
            raise DatFileError(
                'number of channels (%d) does not match number of '
                'channel labels (%d) on line %d' %
                (self.channel_count, len(self.channel_names), line)
            )

    def _state_comments(self, match, line):
        """Parse the comment header"""
        self.comments = []

    def _state_comment_content(self, match, line):
        """Parse comment lines"""
        self.comments.append(match.group(1))

    def _state_abs_head(self, match, line):
        """Parse the abscissa coordinates header"""
        self.comments = '\n'.join(self.comments)

    def _state_abs_points(self, match, line):
        """Parse the abscissa coordinates"""
        self.x_coords = []
        for num in match.group(1).split():
            try:
                self.x_coords.append(float(num))
            except ValueError:
                raise DatFileError(
                    'non-float abscissa (%s) found on line %d' %
                    (num, line)
                )
        if len(self.x_coords) != self.x_size:
            raise DatFileError(
                'abscissa points (%d) does not match count of abscissa '
                'points requested (%d) on line %d' %
                (self.x_size, len(self.x_coords), line)
            )
        self.x_coords = SortedList(self.x_coords)

    def _state_ord_points(self, match, line):
        """Parse the ordinate coordinates"""
        self.y_coords = []
        for num in match.group(1).split():
            try:
                self.y_coords.append(float(num))
            except ValueError:
                raise DatFileError(
                    'non-float ordinate (%s) found on line %d' %
                    (num, line)
                )
        if len(self.y_coords) != self.y_size:
            raise DatFileError(
                'ordinate points (%d) does not match count of '
                'ordinate points requested (%d) on line %d' %
                (self.y_size, len(self.y_coords), line)
            )
        self.y_coords = SortedList(self.y_coords)

    def _state_energy_points(self, match, line):
        """Parse the energy points value"""
        try:
            self.header['energy_points'] = float(match.group(1))
        except ValueError:
            raise DatFileError(
                'non-float energy points requested value (%s) found '
                'on line %d' % (match.group(1), line)
            )

    def format_dict(self, **kwargs):
        """Return a dictionary suitable for the format method"""
        result = {}
        result.update(
            self.header,
            filename           = self._file.name,
            filename_root      = self.filename_root,
            version            = self.version,
            start_time         = self.start_time,
            stop_time          = self.stop_time,
            channel_count      = self.channel_count,
            x_size             = self.x_size,
            y_size             = self.y_size,
            comments           = self.comments,
            **kwargs
        )
        return result


class DatChannels(object):
    """Container for the channels in a dat file"""
    def __init__(self, parent, data_line):
        super(DatChannels, self).__init__()
        self.parent = parent
        self._done_data = False
        self._data_line = data_line
        self._items = [
            DatChannel(self, i, name)
            for (i, name) in enumerate(self.parent.channel_names)
        ]

    def _read_data(self):
        """Read the channel data from a dat file"""
        # XXX Parse optional channels file
        if not self._done_data:
            self._done_data = True
            logging.debug('Allocating channel array')
            data = np.zeros((self.parent.y_size, self.parent.x_size,
                self.parent.channel_count), np.float)
            if self.parent.progress_start:
                self.parent.progress_start()
            try:
                for line_num, line in enumerate(self.parent._file):
                    try:
                        line = [float(n) for n in line.split()]
                    except ValueError:
                        raise DatFileError(
                            'non-float value found on line %d' %
                            (line_num + self._data_line)
                        )
                    try:
                        y = self.parent.y_coords.index(line[0])
                    except ValueError:
                        raise DatFileError(
                            'invalid ordinate %f found on line %d' %
                            (line[0], line_num + self._data_line)
                        )
                    try:
                        x = self.parent.x_coords.index(line[1])
                    except ValueError:
                        raise DatFileError(
                            'invalid abscissa %f found on line %d' %
                            (line[1], line_num + self._data_line)
                        )
                    line = line[2:]
                    if len(line) != len(self):
                        raise DatFileError(
                            'incorrect number of channel values (%d) found '
                            'on line %d' %
                            (len(line), line_num + self._data_line)
                        )
                    data[y, x] = line
                    if self.parent.progress_update:
                        self.parent.progress_update(
                            round(line_num * 100.0 /
                            (self.parent.x_size * self.parent.y_size))
                        )
            finally:
                if self.parent.progress_finish:
                    self.parent.progress_finish()
            logging.debug('Slicing channel array into channels')
            for channel in self:
                channel._data = data[..., channel.index]

    def __len__(self):
        return self.parent.channel_count

    def __getitem__(self, index):
        return self._items[index]

    def __iter__(self):
        for channel in self._items:
            yield channel

    def __contains__(self, obj):
        return obj in self._items


class DatChannel(object):
    """Represents a channel of data in a dat file"""
    def __init__(self, channels, index, name, enabled=True):
        self._channels = channels
        self._index = index
        self.name = name if name else 'I{0}'.format(index)
        self.enabled = enabled
        self._data = None

    @property
    def parent(self):
        """Returns the object representing the dat file"""
        return self._channels.parent

    @property
    def index(self):
        """Returns the index of this channel in the channel list"""
        return self._index

    @property
    def data(self):
        """Returns the channel data as a numpy array"""
        self._channels._read_data()
        return self._data

    def format_dict(self, **kwargs):
        """Return a dictionary suitable for the format method"""
        return self.parent.format_dict(
            channel         = self.index,
            channel_name    = self.name,
            channel_enabled = self.enabled,
            channel_min     = self.data.min(),
            channel_max     = self.data.max(),
            channel_empty   = self.data.min() == self.data.max(),
            **kwargs
        )

