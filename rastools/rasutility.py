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

"""Module providing a common base for ras command line utilities"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import sys
import logging

import numpy as np

try:
    # Optionally import optcomplete (for auto-completion) if it's installed
    import optcomplete
except ImportError:
    optcomplete = None

from rastools.terminal import TerminalApplication
from rastools.collections import Percentile, Range, Crop, Coord

class RasUtility(TerminalApplication):
    """Base class for ras terminal utilities.

    This class enhances the base TerminalApplication class with some facilities
    common to all the ras command line utilities - mostly to do with parsing
    command line parameters, but also including progress notifications.
    """
    status = ''
    progress = 0

    def __init__(self):
        super(RasUtility, self).__init__()
        self._data_parsers = None

    @property
    def data_parsers(self):
        "Load the available data parsers lazily"
        if self._data_parsers is None:
            from rastools.data_parsers import DATA_PARSERS
            # Re-arrange the array into a more useful dictionary keyed by
            # extension
            self._data_parsers = dict(
                (ext, (cls, desc))
                for (cls, exts, desc) in DATA_PARSERS
                for ext in exts
            )
        return self._data_parsers

    def add_range_options(self):
        "Add --percentile and --range options to the command line parser"
        self.parser.set_defaults(percentile=None, range=None)
        opt = self.parser.add_option(
            '-p', '--percentile', dest='percentile', action='store',
            help='clip values in the output to the specified low-high '
            'percentile range (mutually exclusive with --range)')
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(['low-high'])
        opt = self.parser.add_option(
            '-r', '--range', dest='range', action='store',
            help='clip values in the output to the specified low-high '
            'count range (mutually exclusive with --percentile)')
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(['low-high'])

    def parse_range_options(self, options):
        "Parses the --percentile and --range options"
        if options.percentile:
            if options.range:
                self.parser.error(
                    'you may specify one of --percentile and --range')
            s = options.percentile
            if ',' in s:
                low, high = s.split(',', 1)
            elif '-' in s:
                low, high = s.split('-', 1)
            else:
                low, high = ('0.0', s)
            try:
                result = Percentile(float(low), float(high))
            except ValueError:
                self.parser.error(
                    '%s is not a valid --percentile range' %
                    options.percentile)
            if result.low > result.high:
                self.parser.error('--percentile range must be specified '
                    'low to high')
            for i in result:
                if not (0.0 <= i <= 100.0):
                    self.parser.error(
                        '--percentile must be between 0 and 100 (%f '
                        'specified)' % i)
            return result
        elif options.range:
            s = options.range
            if ',' in s:
                low, high = s.split(',', 1)
            elif '-' in s:
                low, high = s.split('-', 1)
            else:
                low, high = ('0.0', s)
            try:
                result = Range(float(low), float(high))
            except ValueError:
                self.parser.error(
                    '%s is not a valid count range' % options.range)
            if result.low > result.high:
                self.parser.error('--range must be specified low-high')
            return result

    def add_crop_option(self):
        "Add a --crop option to the command line parser"
        self.parser.set_defaults(crop='0,0,0,0')
        opt = self.parser.add_option(
            '-c', '--crop', dest='crop', action='store',
            help='crop the input data by top,left,bottom,right points')
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(['top,left,bottom,right'])

    def parse_crop_option(self, options):
        "Parses the --crop option"
        try:
            left, top, right, bottom = options.crop.split(',', 4)
        except ValueError:
            self.parser.error(
                'you must specify 4 integer values for the --crop option')
        try:
            result = Crop(int(left), int(top), int(right), int(bottom))
        except ValueError:
            self.parser.error(
                'non-integer values found in --crop value %s' % options.crop)
        return result

    def add_empty_option(self):
        "Add a --empty option to the command line parser"
        self.parser.set_defaults(empty=False)
        self.parser.add_option(
            '-e', '--empty', dest='empty', action='store_true',
            help='if specified, include empty channels in the output (by '
            'default empty channels are ignored)')

    def parse_files(self, options, args):
        "Parse the files specified and construct a data parser"
        if len(args) == 0:
            self.parser.error('you must specify a data file')
        elif len(args) == 1:
            args = (args[0], None)
        elif len(args) > 2:
            self.parser.error('you cannot specify more than two filenames')
        data_file, channels_file = args
        if data_file == '-' and channels_file == '-':
            self.parser.error('you cannot specify stdin for both files!')
        # XXX #15: what format is stdin?
        ext = os.path.splitext(data_file)[-1]
        data_file, channels_file = (
            sys.stdin if arg == '-' else arg
            for arg in (data_file, channels_file)
        )
        if options.loglevel < logging.WARNING:
            progress = (
                self.progress_start,
                self.progress_update,
                self.progress_finish)
        else:
            progress = (None, None, None)
        try:
            parser = self.data_parsers[ext][0]
        except KeyError:
            self.parser.error('unrecognized file extension %s' % ext)
        return parser(data_file, channels_file, progress=progress)

    def progress_start(self):
        "Called at the start of a long operation to display progress"
        self.progress = 0
        self.status = 'Reading channel data %d%%' % self.progress
        sys.stderr.write(self.status)

    def progress_update(self, new_progress):
        "Called to update progress during a long operation"
        if new_progress != self.progress:
            self.progress = new_progress
            new_status = 'Reading channel data %d%%' % self.progress
            sys.stderr.write('\b' * len(self.status))
            sys.stderr.write(new_status)
            self.status = new_status

    def progress_finish(self):
        "Called to clean up the display at the end of a long operation"
        sys.stderr.write('\n')


class RasError(Exception):
    "Base class for processing errors"

class RasChannelEmptyError(RasError):
    "Error raised when an empty channel is discovered"

class RasChannelProcessor(object):
    """Base class for classes which intend to process channel data.

    This class provides the ability to perform percentile or straight range
    limiting of channel data - functionality which is common to several tools
    in the suite. The class attributes are as follows:

    crop -- A Crop instance indicating the number of pixels that should be
            cropped from each edge before data-limits are calculated
    clip -- A Percentile or Range instance indicating the type and range of
            limiting to be applied to channel data
    empty -- If False (the default), then channels which are empty, or which
            become empty after data limits are applied, will result in an
            EmptyError exception being raised during a call to process()
    """

    def __init__(self, data_size):
        self.data_size = Coord(*data_size)
        self.crop = Crop(0, 0, 0, 0)
        self.clip = None
        self.empty = False

    def process_multiple(self, red_channel, green_channel, blue_channel):
        "Combine, crop, and limit the specified channels returning the data"
        channels = (red_channel, green_channel, blue_channel)
        data = np.zeros((self.data_size.y, self.data_size.x, 3), np.float)
        for index, channel in enumerate(channels):
            if channel:
                data[..., index] = channel.data
        data = data [
            self.crop.top:data.shape[0] - self.crop.bottom,
            self.crop.left:data.shape[1] - self.crop.right]
        vsorted = np.empty((data.shape[0] * data.shape[1], 3))
        for index in range(3):
            vsorted[..., index] = np.sort(data[..., index], axis=None)
        data_domain = [
            Range(vsorted[..., index][0], vsorted[..., index][-1])
            for index in range(3)]
        if isinstance(self.clip, Percentile):
            data_range = [
                Range(
                    vsorted[min(
                        vsorted.shape[0] - 1,
                        int(vsorted.shape[0] * self.clip.low / 100.0)), index],
                    vsorted[min(
                        vsorted.shape[0] - 1,
                        int(vsorted.shape[0] * self.clip.high / 100.0)), index])
                for index in range(3)]
        elif isinstance(self.clip, Range):
            data_range = [self.clip] * 3
            for index, (channel_color, channel, channel_domain, channel_range) in enumerate(zip(
                    ('Red', 'Green', 'Blue'), channels, data_domain, data_range)):
                if channel:
                    if channel_range.low < channel_domain.low:
                        logging.warning(
                            '%s channel (%d - %s) has no values below %d',
                            channel_color, channel.index, channel.name,
                            channel_range.low)
                    if channel_range.high > channel_domain.high:
                        logging.warning(
                            '%s channel (%d - %s) has no values above %d',
                            channel_color, channel.index, channel.name,
                            channel_range.high)
                    data_range[index] = Range(
                        max(channel_range.low, channel_domain.low),
                        min(channel_range.high, channel_domain.high))
        else:
            data_range = data_domain
        for (channel_color, channel, channel_domain, channel_range) in zip(
                ('Red', 'Green', 'Blue'), channels, data_domain, data_range):
            if channel:
                if channel_range != channel_domain:
                    logging.info(
                        '%s channel (%d - %s) has new range %d-%d',
                        channel_color, channel.index, channel.name,
                        channel_range.low, channel_range.high)
                if channel_range.low >= channel_range.high:
                    logging.warning(
                        '%s channel (%d - %s) is empty',
                        channel_color, channel.index, channel.name)
        return data, data_domain, data_range

    def process_single(self, channel):
        "Crop and limit the specified channel returning the domain and range"
        # Perform any cropping requested. This must be done before calculation
        # of the data's range and percentile limiting is performed
        data = channel.data
        data = data[
            self.crop.top:data.shape[0] - self.crop.bottom,
            self.crop.left:data.shape[1] - self.crop.right]
        # Find the minimum and maximum values in the channel and clip
        # them to a percentile/range if requested
        vsorted = np.sort(data, None)
        data_domain = Range(vsorted[0], vsorted[-1])
        logging.info(
            'Channel %d (%s) has range %d-%d',
            channel.index, channel.name, data_domain.low, data_domain.high)
        if isinstance(self.clip, Percentile):
            data_range = Range(
                vsorted[min(
                    len(vsorted) - 1,
                    int(len(vsorted) * self.clip.low / 100.0))],
                vsorted[min(
                    len(vsorted) - 1,
                    int(len(vsorted) * self.clip.high / 100.0))])
            logging.info(
                '%gth percentile is %d',
                self.clip.low, data_range.low)
            logging.info(
                '%gth percentile is %d',
                self.clip.high, data_range.high)
        elif isinstance(self.clip, Range):
            data_range = self.clip
            if data_range.low < data_domain.low:
                logging.warning(
                    'Channel %d (%s) has no values below %d',
                    channel.index, channel.name, data_range.low)
            if data_range.high > data_domain.high:
                logging.warning(
                    'Channel %d (%s) has no values above %d',
                    channel.index, channel.name, data_range.high)
            data_range = Range(
                max(data_range.low, data_domain.low),
                min(data_range.high, data_domain.high))
        else:
            data_range = data_domain
        if data_range != data_domain:
            logging.info(
                'Channel %d (%s) has new range %d-%d',
                channel.index, channel.name, data_range.low, data_range.high)
        if data_range.low >= data_range.high:
            if self.empty:
                logging.warning(
                    'Channel %d (%s) is empty',
                    channel.index, channel.name)
            else:
                logging.warning(
                    'Channel %d (%s) is empty, skipping',
                    channel.index, channel.name)
                raise RasChannelEmptyError(
                    'Channel %d is empty' % channel.index)
        return data, data_domain, data_range

    def format_dict(self, **kwargs):
        "Converts the configuration for use in format substitutions"
        return dict(
            percentile_from=
                self.clip.low if isinstance(self.clip, Percentile) else None,
            percentile_to=
                self.clip.high if isinstance(self.clip, Percentile) else None,
            range_from=
                self.clip.low if isinstance(self.clip, Range) else None,
            range_to=
                self.clip.high if isinstance(self.clip, Range) else None,
            crop_left=self.crop.left,
            crop_top=self.crop.top,
            crop_right=self.crop.right,
            crop_bottom=self.crop.bottom,
            **kwargs)

