#!/usr/bin/env python
# vim: set et sw=4 sts=4:

import sys
import logging
import rastools.main
import rastools.rasfile

class RasInfoUtility(rastools.main.Utility):
    """%prog [options] ras-file [channels-file]

    This utility accepts a source RAS file from QSCAN. It extracts and prints
    the information from the RAS file's header. If the optional channels
    definition file is also specified, then channels will be named in the
    output as they would be with rasextract.

    The available command line options are listed below.
    """

    def __init__(self):
        super(RasInfoUtility, self).__init__()
        self.parser.set_defaults(
            program=False,
            ranges=False,
        )
        self.parser.add_option('-p', '--program', dest='program', action='store_true',
            help="""produce output suitable for programmatic use""")
        self.parser.add_option('-r', '--ranges', dest='ranges', action='store_true',
            help="""read each channel in the file and output its range of values""")

    def main(self, options, args):
        super(RasInfoUtility, self).main(options, args)
        if len(args) < 1:
            self.parser.error('you must specify a RAS file')
        if len(args) > 2:
            self.parser.error('you cannot specify more than two filenames')
        if args[0] == '-' and args[1] == '-':
            self.parser.error('you cannot specify stdin for both files!')
        f = rastools.rasfile.RasFileReader(
            sys.stdin if args[0] == '-' else args[0],
            None if len(args) < 2 else sys.stdin if args[1] == '-' else args[1],
            verbose=options.loglevel<logging.WARNING)
        if options.program:
            sys.stdout.write('{rasfile}=%s\n' % args[0])
            sys.stdout.write('{filename}=%s\n' % f.file_name)
            sys.stdout.write('{filename_root}=%s\n' % f.file_head)
            sys.stdout.write('{version_name}=%s\n' % f.version)
            sys.stdout.write('{version_number}=%d\n' % f.version_number)
            sys.stdout.write('{pid}=%d\n' % f.pid)
            sys.stdout.write('{x_motor}=%s\n' % f.x_motor)
            sys.stdout.write('{y_motor}=%s\n' % f.y_motor)
            sys.stdout.write('{region_filename}=%s\n' % f.region)
            sys.stdout.write('{start_time:%%Y-%%m-%%d %%H:%%M:%%S}=%s\n' % f.start_time.strftime('%Y-%m-%d %H:%M:%S'))
            sys.stdout.write('{stop_time:%%Y-%%m-%%d %%H:%%M:%%S}=%s\n' % f.stop_time.strftime('%Y-%m-%d %H:%M:%S'))
            sys.stdout.write('{channel_count}=%d\n' % f.channel_count)
            sys.stdout.write('{point_count}=%d\n' % f.point_count)
            sys.stdout.write('{raster_count}=%d\n' % f.raster_count)
            sys.stdout.write('{count_time}=%f\n' % f.count_time)
            sys.stdout.write('{sweep_count}=%d\n' % f.sweep_count)
            sys.stdout.write('{ascii_output}=%d\n' % f.ascii_out)
            sys.stdout.write('{pixels_per_point}=%d\n' % f.pixel_point)
            sys.stdout.write('{scan_direction}=%d\n' % f.scan_direction)
            sys.stdout.write('{scan_type}=%d\n' % f.scan_type)
            sys.stdout.write('{current_x_direction}=%d\n' % f.current_x_direction)
            sys.stdout.write('{run_number}=%d\n' % f.run_number)
            sys.stdout.write('\n')
            for channel in f.channels:
                sys.stdout.write('{channel:%%02d}=%02d\n' % channel.index)
                sys.stdout.write('{channel_name}=%s\n' % channel.name)
                sys.stdout.write('{channel_enabled}=%s\n' % channel.enabled)
                if options.ranges:
                    sys.stdout.write('{channel_min}=%d\n' % channel.data.min())
                    sys.stdout.write('{channel_max}=%d\n' % channel.data.max())
                sys.stdout.write('\n')
            sys.stdout.write('{comments}=%s\n' % f.comments)
            sys.stdout.write('\n')
        else:
            sys.stdout.write('File name:              %s\n' % (args[0] if args[0] != '-' else '<stdin>'))
            sys.stdout.write('Original filename:      %s\n' % f.file_name)
            sys.stdout.write('Original filename root: %s\n' % f.file_head)
            sys.stdout.write('Version name:           %s\n' % f.version)
            sys.stdout.write('Version number:         %d\n' % f.version_number)
            sys.stdout.write('PID:                    %d\n' % f.pid)
            sys.stdout.write('X-Motor name:           %s\n' % f.x_motor)
            sys.stdout.write('Y-Motor name:           %s\n' % f.y_motor)
            sys.stdout.write('Region filename:        %s\n' % f.region)
            sys.stdout.write('Start time:             %s\n' % f.start_time.strftime('%A, %d %B %Y, %H:%M:%S'))
            sys.stdout.write('Stop time:              %s\n' % f.stop_time.strftime('%A, %d %B %Y, %H:%M:%S'))
            sys.stdout.write('Channel count:          %d\n' % f.channel_count)
            sys.stdout.write('Channel resolution:     %d x %d\n' % (f.point_count, f.raster_count))
            sys.stdout.write('Count time:             %f\n' % f.count_time)
            sys.stdout.write('Sweep count:            %d\n' % f.sweep_count)
            sys.stdout.write('Produce ASCII output:   %d (%s)\n' % (f.ascii_out, ('No', 'Yes')[bool(f.ascii_out)]))
            sys.stdout.write('Pixels per point:       %d\n' % f.pixel_point)
            sys.stdout.write('Scan direction:         %d (%s)\n' % (f.scan_direction, {1: '+ve only', 2: '+ve and -ve'}[f.scan_direction]))
            sys.stdout.write('Scan type:              %d (%s)\n' % (f.scan_type, {1: 'Quick scan', 2: 'Point to point'}[f.scan_type]))
            sys.stdout.write('Current X-direction:    %d\n' % f.current_x_direction)
            sys.stdout.write('Run number:             %d\n' % f.run_number)
            for channel in f.channels:
                name = '' if not channel.name else (' (%s)' % channel.name)
                if options.ranges:
                    sys.stdout.write('Channel %2d%s:%s%s, Range=%d-%d%s\n' % (
                        channel.index,
                        name,
                        ' ' * (13 - len(name)),
                        ('Disabled', 'Enabled')[channel.enabled],
                        channel.data.min(),
                        channel.data.max(),
                        ('', ' (empty)')[channel.data.min() == channel.data.max()],
                    ))
                else:
                    sys.stdout.write('Channel %2d%s:%s%s\n' % (
                        channel.index,
                        name,
                        ' ' * (13 - len(name)),
                        ('Disabled', 'Enabled')[channel.enabled],
                    ))
            sys.stdout.write('\n')
            sys.stdout.write('Comments:\n')
            sys.stdout.write(f.comments)
            sys.stdout.write('\n')
            sys.stdout.write('\n')

main = RasInfoUtility()
