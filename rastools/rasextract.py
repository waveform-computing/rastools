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
from collections import namedtuple

Crop = namedtuple('Crop', ('top', 'left', 'bottom', 'right'))

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
            show_colorbar=False,
            show_histogram=False,
            cmap='gray',
            crop='0,0,0,0',
            percentile=100.0,
        )
        self.parser.add_option('--help-cmap', dest='cmap_list', action='store_true',
            help="""list the available color-maps""")
        self.parser.add_option('-c', '--color-map', dest='cmap', action='store',
            help="""the color-map to use in output (e.g. gray, jet, hot)""")
        self.parser.add_option('-p', '--percentile', dest='percentile', action='store',
            help="""clip values in the output image to the specified percentile""")
        self.parser.add_option('-a', '--axes', dest='show_axes', action='store_true',
            help="""display the coordinate axes in the output""")
        self.parser.add_option('-b', '--color-bar', dest='show_colorbar', action='store_true',
            help="""draw a color-bar showing the range of the color-map to the right of the output""")
        self.parser.add_option('-H', '--histogram', dest='show_histogram', action='store_true',
            help="""draw a histogram of the channel values below the output""")
        self.parser.add_option('-C', '--crop', dest='crop', action='store',
            help="""crop the input data by top,left,bottom,right points""")

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
        # Parse the channels definition file
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
            options.percentile = float(options.percentile)
        except ValueError:
            self.parser.error('%s is not a valid percentile' % options.percentile)
        if not (0 <= options.percentile <= 100.0):
            self.parser.error('percentile must be between 0 and 100 (%f specified)' % options.percentile)
        # Check the colormap is known
        if not cm.get_cmap(options.cmap):
            self.parser.error('color-map %s is invalid' % options.cmap)
        # Check the crop values
        try:
            options.crop = options.crop.split(',', 4)
        except ValueError:
            self.parser.error('you must specify 4 integer values for the --crop option')
        try:
            options.crop = Crop(*[int(i) for i in options.crop])
        except ValueError:
            self.parser.error('non-integer values found in --crop value %s' % ','.join(options.crop))
        # Extract the specified channels
        logging.info('File contains %d channels, extracting channels %s' % (
            ras_f.channel_count,
            ','.join(str(channel) for (channel, _, _) in channel_map)
        ))
        for (channel, name, filename) in channel_map:
            # Perform any cropping requested. This must be done before
            # calculation of the data's range and percentile limiting is
            # performed for obvious reasons
            data = ras_f.channels[channel]
            data = data[
                options.crop.top:data.shape[0] - options.crop.bottom,
                options.crop.left:data.shape[1] - options.crop.right
            ]
            # Find the minimum and maximum values in the channel and clip them
            # to a percentile if required
            vsorted = np.sort(data, None)
            vmin = vsorted[0]
            vmax = vsorted[-1]
            if options.percentile < 100.0:
                vmax = vsorted[round(options.percentile * len(vsorted) / 100.0)]
            if vmin == vmax:
                logging.warning('Channel %d (%s) is empty, skipping' % (channel, name))
            else:
                logging.info('Writing channel %d (%s) to %s' % (channel, name, filename))
                # Copy the data into a floating-point array (matplotlib's image
                # module won't play with uint32 data - only uint8 or float32)
                # and crop it as necessary
                data = np.array(data, np.float)
                # Calculate the figure dimensions and margins, and construct
                # the necessary objects
                dpi = 72.0
                (img_width, img_height) = (
                    (ras_f.point_count - options.crop.left - options.crop.right) / dpi,
                    (ras_f.raster_count - options.crop.top - options.crop.bottom) / dpi
                )
                (hist_width, hist_height) = ((0.0, 0.0), (img_width, img_height))[options.show_histogram]
                (cbar_width, cbar_height) = ((0.0, 0.0), (img_width, 1.0))[options.show_colorbar]
                margin = (0.0, 1.0)[options.show_axes or options.show_colorbar or options.show_histogram]
                fig_width = img_width + margin * 2
                fig_height = img_height + hist_height + cbar_height + margin * 2
                fig = Figure(figsize=(fig_width, fig_height), dpi=dpi)
                canvas = FigureCanvas(fig)
                # Construct an axis in which to draw the channel data and draw
                # it. The imshow() call takes care of clamping values with vmin
                # and vmax and color-mapping. Interpolation is set manually to
                # 'nearest' to avoid any blurring (after all, we're sizing the
                # axis precisely to the image data so interpolation shouldn't
                # be needed)
                ax = fig.add_axes((
                    margin / fig_width,      # left
                    (margin + hist_height + cbar_height) / fig_height, # bottom
                    img_width / fig_width,   # width
                    img_height / fig_height, # height
                ), frame_on=options.show_axes)
                if not options.show_axes:
                    ax.set_axis_off()
                img = ax.imshow(data, cmap=cm.get_cmap(options.cmap), vmin=vmin, vmax=vmax, interpolation='nearest')
                # Construct an axis for the histogram, if requested
                if options.show_histogram:
                    hax = fig.add_axes((
                        margin / fig_width,               # left
                        (margin + cbar_height + hist_height * 0.1) / fig_height, # bottom
                        hist_width / fig_width,           # width
                        (hist_height * 0.8) / fig_height, # height
                    ))
                    hg = hax.hist(data.flat, 512, range=(vmin, vmax))
                # Construct an axis for the colorbar, if requested
                if options.show_colorbar:
                    cax = fig.add_axes((
                        margin / fig_width,               # left
                        (margin + cbar_height * 0.25) / fig_height, # bottom
                        cbar_width / fig_width,           # width
                        (cbar_height * 0.5) / fig_height, # height
                    ))
                    cb = fig.colorbar(img, cax=cax, orientation='horizontal')
                # Finally, dump the figure to disk as a PNG
                canvas.print_figure(filename, dpi=dpi, format='png')

main = RasExtractUtility()
