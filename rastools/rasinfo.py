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

"""Main module for the rasinfo utility."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import sys

from rastools.rasutility import RasUtility


class RasInfoUtility(RasUtility):
    """%prog [options] data-file [channels-file]

    This utility accepts a source RAS file from QSCAN. It extracts and prints
    the information from the RAS file's header. If the optional channels
    definition file is also specified, then channels will be named in the
    output as they would be with rasextract.

    The available command line options are listed below.
    """

    header_fields = [
        # Human-readable format
        [
            'File name:           {filename}',
            'Filename root:       {filename_root}',
            'Version number:      {version_number}',
            'Channel count:       {channel_count}',
            'Channel resolution:  {x_size} x {y_size}',
            # Ras-specific output
            'Original filename:   {filename_original}',
            'Version name:        {version_name}',
            'PID:                 {pid}',
            'X-Motor name:        {x_motor}',
            'Y-Motor name:        {y_motor}',
            'Region filename:     {region_filename}',
            'Start time:          {start_time:%A, %d %B %Y, %H:%M:%S}',
            'Stop time:           {stop_time:%A, %d %B %Y, %H:%M:%S}',
            'Count time:          {count_time}',
            'Sweep count:         {sweep_count}',
            'Write ASCII output:  {ascii_out} (0=No, 1=Yes)',
            'Pixels per point:    {pixels_per_point}',
            'Scan direction:      {scan_direction} (1=+ve only, 2=+ve and -ve)',
            'Scan type:           {scan_type} (1=Quick scan, 2=Point to point)',
            'Current X-direction: {current_x_direction}',
            'Run number:          {run_number}',
            # Dat-specific output
            'Energy points:       {energy_points}',
            'X coordinates:       {x_from:+} -> {x_to:+}',
            'Y coordinates:       {y_from:+} -> {y_to:+}',
            # Comments last even though they're common because they're
            # multi-line
            'Comments:\n\n{comments}\n',
        ],
        # Template format
        [
            # Common fields
            '{{filename}}={filename}',
            '{{filename_root}}={filename_root}',
            '{{version_number}}={version_number}',
            '{{channel_count}}={channel_count}',
            '{{x_size}}={x_size}',
            '{{y_size}}={y_size}',
            # Ras-specific fields
            '{{filename_original}}={filename_original}',
            '{{version_name}}={version_name}',
            '{{pid}}={pid}',
            '{{x_motor}}={x_motor}',
            '{{y_motor}}={y_motor}',
            '{{region_filename}}={region_filename}',
            '{{start_time:%Y-%m-%d %H:%M:%S}}={start_time:%Y-%m-%d %H:%M:%S}',
            '{{stop_time:%Y-%m-%d %H:%M:%S}}={stop_time:%Y-%m-%d %H:%M:%S}',
            '{{count_time}}={count_time}',
            '{{sweep_count}}={sweep_count}',
            '{{ascii_output}}={ascii_output}',
            '{{pixels_per_point}}={pixels_per_point}',
            '{{scan_direction}}={scan_direction}',
            '{{scan_type}}={scan_type}',
            '{{current_x_direction}}={current_x_direction}',
            '{{run_number}}={run_number}',
            # Dat-specific fields
            '{{energy_points}}={energy_points}',
            '{{x_from}}={x_from}',
            '{{x_to}}={x_to}',
            '{{y_from}}={y_from}',
            '{{y_to}}={y_to}',
            # Comments last even though they're common because they're
            # multi-line
            '{{comments}}={comments}',
        ],
    ]

    channel_fields = [
        # Human-readable format
        [
            'Channel {channel} - {channel_name}',
            '  Enabled: {channel_enabled}',
            '  Empty:   {channel_empty}',
            '  Range:   {channel_min} -> {channel_max}',
            '',
        ],
        # Template format
        [
            '{{channel:02d}}={channel:02d}',
            '{{channel_name}}={channel_name}',
            '{{channel_enabled}}={channel_enabled}',
            '{{channel_empty}}={channel_empty}',
            '{{channel_min}}={channel_min}',
            '{{channel_max}}={channel_max}',
        ],
    ]

    def __init__(self):
        super(RasInfoUtility, self).__init__()
        self.parser.set_defaults(
            templates=False,
            channels=False,
        )
        self.add_empty_option()
        self.parser.add_option(
            '-t', '--templates', dest='templates', action='store_true',
            help='output substitution templates used with rasextract '
            '--title and --output')
        self.parser.add_option(
            '-c', '--channels', dest='channels', action='store_true',
            help='output information about individual channels in '
            'addition to header details (note: this requires reading the '
            'entire file which can take some time)')

    def main(self, options, args):
        data_file = self.parse_files(options, args)
        self.query_header(options, data_file)
        if options.channels:
            for channel in data_file.channels:
                self.query_channel(options, channel)

    def query_header(self, options, data_file):
        "Dump data_file's header information to stdout"
        header_dict = data_file.format_dict()
        for s in self.header_fields[options.templates]:
            try:
                sys.stdout.write(s.format(**header_dict) + '\n')
            except KeyError:
                # Ignore KeyErrors - these will occur when attempting to
                # dump header fields which don't exist in a particular file
                # format
                pass

    def query_channel(self, options, channel):
        "Dump the channel's information to stdout"
        channel_dict = channel.format_dict()
        for s in self.channel_fields[options.templates]:
            try:
                sys.stdout.write(s.format(**channel_dict) + '\n')
            except KeyError:
                # Same as above
                pass


main = RasInfoUtility()
