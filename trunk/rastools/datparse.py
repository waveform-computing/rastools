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
import re
import logging
import datetime as dt
import numpy as np
from itertools import izip
from collections import namedtuple

class Error(ValueError):
    """Base exception class"""

class DatFileError(Error):
    """Base class for errors encountered in DAT file parsing"""


DatParseState = namedtuple('DatParseState', ('re', 'next'))

class DatFileReader(object):
    """Parser for Sam's .dat files"""

    # We haven't got a formal definition of Sam's .dat format, but it's a
    # fairly simple text based format. In lieu of any formal grammar, we just
    # use a whole load of regexes and a simple state machine to parse it. A
    # sample header is given below:
    #
    # * Abscissa points :   305
    # * Ordinate points :   287
    # * BLANK LINE
    # * Data Channels :   22
    # * Data Labels : I0	I1	I2	I0STRM	I1STRM	TK	Fe	Cu	Zn	Si	P	S	Cl	K	Ca	Ti	Unk1	Unk2	Mn	Scatter	ICR	OCR	
    # * Comments: 
    # * dwell time = 100.0
    # * 
    # * 
    # * BLANK LINE
    # * Abscissa points requested :
    # * 0.3503	0.3493	0.3483	0.3473	0.3463	0.3453	0.3443	0.3433	0.3423	0.3413...
    # * BLANK LINE
    # * BLANK LINE
    # * Ordinate points requested :
    # * -1.3149	-1.3139	-1.3129	-1.3119	-1.3109	-1.3099	-1.3089	-1.3079	-1.3069	-1.3059...
    # * BLANK LINE
    # * BLANK LINE
    # * Energy points requested: 
    # *   10000.0
    # * BLANK LINE
    # * DATA
    # -1.3149	0.3503	1	1	1	25686	60	10	2	1	0	3	1	1	4	4	204	0	0	0	2	5	381	278	
    # -1.3149	0.3493	1	1	1	25690	57	10	86	21	0	98	92	68	80	222	6586	5	9	6	19	170	12862	9312	
    # -1.3149	0.3483	1	1	1	25683	60	10	95	18	2	69	107	70	70	189	6910	11	6	7	12	200	13221	9673	
    # -1.3149	0.3473	1	1	1	25679	57	10	70	16	4	87	90	65	84	181	6600	7	6	10	11	196	12614	9314	
    # ...
    header_version = 1
    header_ignore = re.compile(r'^\* *(BLANK LINE)?$')
    header_start = 'ABS_COUNT'
    header_states = {
        # STATE                REGEX                                              NEXT STATES
        'ABS_COUNT':          (re.compile(r'^\* *Abscissa points *: *(\d+)$'),   ('ORD_COUNT',)),
        'ORD_COUNT':          (re.compile(r'^\* *Ordinate points *: *(\d+)$'),   ('CHAN_COUNT',)),
        'CHAN_COUNT':         (re.compile(r'^\* *Data Channels *: *(\d+)$'),     ('CHAN_LABELS',)),
        'CHAN_LABELS':        (re.compile(r'^[*#] *Data Labels *: *(.*)$'),      ('COMMENTS',)),
        'COMMENTS':           (re.compile(r'^\* *Comments *:'),                  ('COMMENT_CONTENT',)),
        'COMMENT_CONTENT':    (re.compile(r'^\* *(.*)$'),                        ('ABS_POINTS_HEAD', 'COMMENT_CONTENT')),
        'ABS_POINTS_HEAD':    (re.compile(r'^\* *Abscissa points requested *:'), ('ABS_POINTS',)),
        'ABS_POINTS':         (re.compile(r'^\* *((([-+]?\d+(\.\d+)?)\s*)*)$'),  ('ORD_POINTS_HEAD',)),
        'ORD_POINTS_HEAD':    (re.compile(r'^\* *Ordinate points requested *:'), ('ORD_POINTS',)),
        'ORD_POINTS':         (re.compile(r'^\* *((([-+]?\d+(\.\d+)?)\s*)*)$'),  ('ENERGY_POINTS_HEAD',)),
        'ENERGY_POINTS_HEAD': (re.compile(r'^\* *Energy points requested *:'),   ('ENERGY_POINTS',)),
        'ENERGY_POINTS':      (re.compile(r'^\* *([-+]?\d+(\.\d+)?)$'),          ('DATA',)),
        'DATA':               (re.compile(r'^\* *DATA'),                         ()),
    }

    def __init__(self, *args, **kwargs):
        """Constructor accepts a filename or file-like object"""
        super(DatFileReader, self).__init__()
        (
            self.progress_start,
            self.progress_update,
            self.progress_finish,
        ) = kwargs.get('progress', (None, None, None))
        dat_file, = args
        if isinstance(dat_file, basestring):
            logging.debug('Opening DAT file %s' % dat_file)
            self._file = open(dat_file, 'rU')
        else:
            logging.debug('Opening DAT file %s' % dat_file.name)
            self._file = dat_file
        self.filename_root = re.sub(r'^(.*?)[0-9_-]+\.(dat|DAT)$', r'\1', os.path.split(self._file.name)[1])
        self.start_time = dt.datetime.fromtimestamp(os.stat(self._file.name).st_ctime)
        self.stop_time = self.start_time
        # Parse the header
        logging.debug('Reading DAT header')
        self.version_number = self.header_version
        states = [self.header_start]
        for line_num, line in enumerate(self._file):
            if self.header_ignore.match(line):
                logging.debug('Skipping blank line %d' % (line_num + 1))
                continue
            for state in states:
                regex, new_states = self.header_states[state]
                match = regex.match(line)
                if match:
                    break
            if not match:
                raise DatFileError('expected %s on line %d of DAT file' % (self.header_states[states[0]][0].pattern, line_num + 1))
            logging.debug('DAT parser in state %s' % state)
            if new_states:
                states = new_states
            else:
                break
            if state == 'ABS_COUNT':
                try:
                    self.x_size = int(match.group(1))
                except ValueError:
                    raise DatFileError('non-integer abscissa count (%s) found on line %d' % (match.group(1), line_num + 1))
            elif state == 'ORD_COUNT':
                try:
                    self.y_size = int(match.group(1))
                except ValueError:
                    raise DatFileError('non-integer ordinate count (%s) found on line %d' % (match.group(1), line_num + 1))
            elif state == 'CHAN_COUNT':
                try:
                    self.channel_count = int(match.group(1))
                except ValueError:
                    raise DatFileError('non-integer channel count (%s) found on line %d' % (match.group(1), line_num + 1))
            elif state == 'CHAN_LABELS':
                labels = match.group(1).split()
                if len(labels) != self.channel_count:
                    raise DatFileError('number of channels (%d) does not match number of channel labels (%d) on line %d' % (self.channel_count, len(self.channels), line_num + 1))
            elif state == 'COMMENTS':
                self.comments = []
            elif state == 'COMMENT_CONTENT':
                self.comments.append(match.group(1))
            elif state == 'ABS_POINTS_HEAD':
                self.comments = '\n'.join(self.comments)
            elif state == 'ABS_POINTS':
                self.x_coords = []
                for n in match.group(1).split():
                    try:
                        self.x_coords.append(float(n))
                    except ValueError:
                        raise DatFileError('non-float abscissa (%s) found on line %d' % (n, line_num + 1))
                if len(self.x_coords) != self.x_size:
                    raise DatFileError('abscissa points (%d) does not match count of abscissa points requested (%d) on line %d' % (self.x_size, len(self.x_coords), line_num + 1))
                # XXX guarantee sorting of x_coords and y_coords? See note further down...
            elif state == 'ORD_POINTS':
                self.y_coords = []
                for n in match.group(1).split():
                    try:
                        self.y_coords.append(float(n))
                    except ValueError:
                        raise DatFileError('non-float ordinate (%s) found on line %d' % (n, line_num + 1))
                if len(self.y_coords) != self.y_size:
                    raise DatFileError('ordinate points (%d) does not match count of ordinate points requested (%d) on line %d' % (self.y_size, len(self.y_coords), line_num + 1))
            elif state == 'ENERGY_POINTS':
                try:
                    self.energy_points = float(match.group(1))
                except ValueError:
                    raise DatFileError('non-float energy points requested value (%s) found on line %d' % (n, line_num + 1))
        logging.debug('Reached end of DAT header on line %d' % line_num)
        self.channels = DatChannels(self, line_num, labels)

    def format_dict(self, **kwargs):
        return dict(
            filename           = self._file.name,
            filename_root      = self.filename_root,
            version_number     = self.version_number,
            channel_count      = self.channel_count,
            x_size             = self.x_size,
            y_size             = self.y_size,
            start_time         = self.start_time,
            stop_time          = self.stop_time,
            comments           = self.comments,
            **kwargs
        )


class DatChannels(object):
    def __init__(self, parent, data_line, channel_names):
        super(DatChannels, self).__init__()
        self.parent = parent
        self._read_channels = False
        self._data_line = data_line
        self._items = [
            DatChannel(self, i, name)
            for (i, name) in enumerate(channel_names)
        ]

    def read_channels(self):
        if not self._read_channels:
            self._read_channels = True
            logging.debug('Allocating channel array')
            data = np.zeros((self.parent.y_size, self.parent.x_size, self.parent.channel_count), np.float)
            if self.parent.progress_start:
                self.parent.progress_start()
            try:
                for line_num, line in enumerate(self.parent._file):
                    try:
                        line = [float(n) for n in line.split()]
                    except ValueError:
                        raise DatFileError('non-float value found on line %d' % (line_num + self._data_line))
                    # XXX if x_coords and y_coords are guaranteed sorted ... bisect?
                    try:
                        y = self.parent.y_coords.index(line[0])
                    except ValueError:
                        raise DatFileError('invalid ordinate %f found on line %d' % (line[0], line_num + self._data_line))
                    try:
                        x = self.parent.x_coords.index(line[1])
                    except ValueError:
                        raise DatFileError('invalid abscissa %f found on line %d' % (line[1], line_num + self._data_line))
                    line = line[2:]
                    if len(line) != len(self):
                        raise DatFileError('incorrect number of channel values (%d) found on line %d' % (len(line), line_num + self._data_line))
                    data[y, x] = line
                    if self.parent.progress_update:
                        self.parent.progress_update(round(line_num * 100.0 / (self.parent.x_size * self.parent.y_size)))
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
    def __init__(self, channels, index, name, enabled=True):
        self._channels = channels
        self._index = index
        self.name = name
        self.enabled = enabled
        self._data = None

    @property
    def parent(self):
        return self._channels.parent

    @property
    def index(self):
        return self._index

    @property
    def data(self):
        self._channels.read_channels()
        return self._data

    def format_dict(self, **kwargs):
        return self.parent.format_dict(
            channel         = self.index,
            channel_name    = self.name,
            channel_enabled = self.enabled,
            channel_min     = self.data.min(),
            channel_max     = self.data.max(),
            **kwargs
        )

