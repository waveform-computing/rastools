#!/usr/bin/env python
# vim: set et sw=4 sts=4:

import sys
import logging
import itertools
import rastools.main
import rastools.rasfile
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.cm as cm
import numpy as np

class RasExtractUtility(rastools.main.Utility):
    """%prog [options] ras-file channel-file

    This utility accepts a QSCAN RAS file and a channel definition file. For
    each channel listed in the latter, an image is produced from the
    corresponding channel in the RAS file. Various options are provided for
    customizing the output including percentile limiting, color-mapping, and
    drawing of axes and titles.

    The available command line options are listed below.
    """

    def __init__(self):
        super(RasExtractUtility, self).__init__()
        self.parser.set_defaults(
            cmap_list=False,
            show_axes=False,
            cmap='gray',
            clip=100.0,
        )
        self.parser.add_option('--help-cmap', dest='cmap_list', action='store_true',
            help="""list the available color-maps""")
        self.parser.add_option('-c', '--cmap', dest='cmap', action='store',
            help="""the color-map to use in output (e.g. gray, jet, hot)""")
        self.parser.add_option('-p', '--percentile', dest='clip', action='store',
            help="""clip values in the output image to n% of the input values""")
        self.parser.add_option('-a', '--axes', dest='show_axes', action='store_true',
            help="""display the coordinate axes in the output""")

    def main(self, options, args):
        super(RasExtractUtility, self).main(options, args)
        if options.cmap_list:
            sys.stdout.write('The following colormaps are available:\n\n')
            sys.stdout.write('\n'.join(sorted(name for name in cm.datad if not name.endswith('_r'))))
            sys.stdout.write('\n\n')
            sys.stdout.write('Append _r to any colormap name to reverse it\n\n')
            return 0
        if len(args) != 2:
            self.parser.error('you must specify a RAS file and a channel definitions file')
        # Parse the input RAS file
        if args[0] == '-':
            ras_f = rastools.rasfile.RasFileReader(sys.stdin, verbose=options.loglevel<logging.WARNING)
        else:
            ras_f = rastools.rasfile.RasFileReader(args[0], verbose=options.loglevel<logging.WARNING)
        # Parse the channels spec
        if args[1] == '-':
            if args[0] == '-':
                raise IOError('you cannot specify stdin for both files!')
            channels_f = sys.stdin
        else:
            channels_f = open(args[1], 'rU')
        channel_map = []
        for line_num, line in enumerate(channels_f):
            line = line.strip()
            # Ignore empty lines and #-prefixed comment lines
            if line and not line.startswith('#'):
                try:
                    (index, name) = line.split(None, 1)
                except ValueError:
                    self.parser.error('only one value found on line %d of channels file' % line_num + 1)
                try:
                    index = int(index)
                except ValueError:
                    self.parser.error('non-integer channel number ("%s") found on line %d of channels file' % (index, line_num + 1))
                if index < 0:
                    self.parser.error('negative channel number (%d) found on line %d of channels file' % (index, line_num + 1))
                if index >= ras_f.channel_count:
                    self.parser.error('channel number (%d) on line %d of channels file exceeds number of channels in RAS file (%d)' % (index, line_num + 1, ras_f.channel_count))
                channel_map.append((index, name, '%s_%02d_%s.png' % (ras_f.file_head, index, name)))
        channel_map.sort()
        # Check the clip level is a valid percentage
        try:
            options.clip = float(options.clip)
        except ValueError:
            self.parser.error('%s is not a valid percentile clip level' % options.clip)
        if not (0 <= options.clip <= 100.0):
            self.parser.error('percentile clip level must be between 0 and 100 (%f specified)' % options.clip)
        # Check the colormap is known
        if not cm.get_cmap(options.cmap):
            self.parser.error('color-map %s is invalid' % options.cmap)
        # Extract the specified channels
        logging.info('File contains %d channels, extracting channels %s' % (
            ras_f.channel_count,
            ','.join(str(channel) for (channel, filename) in channel_map)
        ))
        for (channel, filename) in channel_map:
            # Find the minimum and maximum values in the channel and clip them
            # to a percentile if required
            vsorted = np.sort(ras_f.channels[channel], None)
            vmin = vsorted[0]
            vmax = vsorted[-1]
            if options.clip < 100.0:
                vmax = vsorted[round(options.clip * len(vsorted) / 100.0)]
            if vmin == vmax:
                logging.warning('Channel %d is empty, skipping' % channel)
            else:
                # Generate a normalized version of the channel with floating
                # point values between 0.0 and 1.0
                logging.info('Writing channel %d to %s' % (channel, filename))
                data = np.array(ras_f.channels[channel], np.float)
                dpi = 72.0
                (width, height) = (ras_f.point_count / dpi, ras_f.raster_count / dpi)
                margins = (
                    (0.0, 1.0)[options.show_axes], # left
                    (0.0, 1.0)[options.show_axes], # bottom
                    (0.0, 1.0)[options.show_axes], # right
                    (0.0, 1.0)[options.show_axes], # top
                )
                fig = Figure(figsize=(width + margins[0] + margins[2], height + margins[1] + margins[3]), dpi=dpi)
                canvas = FigureCanvas(fig)
                ax = fig.add_axes((
                    (margins[0]) / (width + margins[0] + margins[2]),  # left
                    (margins[1]) / (height + margins[1] + margins[3]), # bottom
                    width / (width + margins[0] + margins[2]),         # width
                    height / (height + margins[1] + margins[3]),       # height
                ), frame_on=options.show_axes)
                img = ax.imshow(data, cmap=cm.get_cmap(options.cmap), vmin=vmin, vmax=vmax, interpolation='nearest')
                cb = fig.colorbar(img)
                canvas.print_figure(filename, dpi=dpi, format='png')

main = RasExtractUtility()
