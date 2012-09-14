#!/usr/bin/env python
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

"""Main module for the rasdump command line utility"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import sys
import logging

from rastools.rasutility import (
    RasUtility, RasChannelEmptyError, RasChannelProcessor)


class RasDumpUtility(RasUtility):
    """%prog [options] data-file [channels-file]

    This utility accepts a data file and an optional channel definition file.
    For each channel listed in the latter (or all channels if none is
    provided), a dump is produced of the corresponding channel in the data
    file.  Various options are provided for customizing the output including
    percentile limiting, and output format.

    The available command line options are listed below.
    """

    def __init__(self):
        super(RasDumpUtility, self).__init__()
        self._data_writers = None
        self.parser.set_defaults(
            list_formats=False,
            output='{filename_root}_{channel:02d}_{channel_name}.csv',
            multi=False,
        )
        self.parser.add_option(
            '--help-formats', dest='list_formats', action='store_true',
            help='list the available file output formats')
        self.add_range_options()
        self.add_crop_option()
        self.add_empty_option()
        self.parser.add_option(
            '-o', '--output', dest='output', action='store',
            help='specify the template used to generate the output filenames; '
            'supports {variables}, see --help-formats for supported file '
            'formats. Default: %default')
        self.parser.add_option(
            '-m', '--multi', dest='multi', action='store_true',
            help='if specified, produce a single output file with multiple '
            'pages or sheets, one per channel (only available with certain '
            'formats)')

    @property
    def data_writers(self):
        "Loads data writers lazily"
        if self._data_writers is None:
            from rastools.data_writers import DATA_WRITERS
            self._data_writers = dict(
                (ext, (writer_class, multi_class, desc))
                for (writer_class, exts, desc, multi_class) in DATA_WRITERS
                for ext in exts
            )
        return self._data_writers

    def main(self, options, args):
        if options.list_formats:
            self.list_formats()
            return 0
        # Verify the various command line options
        data_file = self.parse_files(options, args)
        self.converter = RasConverter((data_file.x_size, data_file.y_size))
        self.converter.crop = self.parse_crop_option(options)
        self.converter.clip = self.parse_range_options(options)
        self.converter.empty = options.empty
        writer_class, multi_class = self.parse_output_options(options)
        # Extract the specified channels
        logging.info(
            'File contains %d channels, extracting channels %s',
            len(data_file.channels),
            ','.join(
                str(channel.index)
                for channel in data_file.channels
                if channel.enabled
            )
        )
        if options.multi:
            filename = options.output.format(
                **data_file.format_dict(
                    **self.converter.format_dict()))
            logging.warning('Writing all channels to %s', filename)
            output = multi_class(filename, data_file)
        try:
            for channel in data_file.channels:
                if channel.enabled:
                    if options.multi:
                        logging.warning(
                            'Writing channel %d (%s) to new page',
                            channel.index, channel.name)
                    else:
                        filename = options.output.format(
                            **channel.format_dict(
                                **self.converter.format_dict()))
                        logging.warning(
                            'Writing channel %d (%s) to %s',
                            channel.index, channel.name, filename)
                    data = self.converter.convert(channel)
                    if data is not None:
                        # Finally, dump the figure to disk as whatever format
                        # the user requested
                        if options.multi:
                            output.write_page(data, channel)
                        else:
                            writer_class(filename, channel).write(data)
        finally:
            if options.multi:
                output.close()

    def list_formats(self):
        "Prints the list of supported data formats to stdout"
        sys.stdout.write('The following file formats are available:\n\n')
        for ext in sorted(self.data_writers.keys()):
            sys.stdout.write('%-8s - %s\n' % (ext, self.data_writers[ext][-1]))
        sys.stdout.write('\n')

    def parse_output_options(self, options):
        "Checks the validity of the --output and --multi options"
        ext = os.path.splitext(options.output)[1]
        try:
            writer_class, multi_class, _ = self.data_writers[ext]
        except KeyError:
            self.parser.error('unknown output format "%s"' % ext)
        if options.multi and not multi_class:
            multi_ext = [
                ext for (ext, (_, multi, _)) in self.data_writers.items()
                if multi
            ]
            if multi_ext:
                self.parser.error('output filename must end with %s when '
                    '--multi is specified' % ','.join(multi_ext))
            else:
                self.parser.error('--multi is not supported by any '
                    'registered output formats')
        return (writer_class, multi_class)


class RasConverter(RasChannelProcessor):
    "Converter class for data files"

    def convert(self, channel):
        "Convert the specified channel, returning the resulting numpy array"
        try:
            data, data_domain, data_range = self.process_single(channel)
        except RasChannelEmptyError:
            return None
        # Apply the percentiles
        data[data < data_range.low] = data_range.low
        data[data > data_range.high] = data_range.high
        return data


main = RasDumpUtility()
