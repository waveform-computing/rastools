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

"""Main module for the rasextract utility."""

import os
import sys
import logging
from collections import namedtuple

import numpy as np
import matplotlib
import matplotlib.cm
import matplotlib.image

import rastools.main

DPI = 72.0

Percentile = namedtuple('Percentile', ('low', 'high'))
Range = namedtuple('Range', ('low', 'high'))
Crop = namedtuple('Crop', ('top', 'left', 'bottom', 'right'))

class RasExtractUtility(rastools.main.Utility):
    """%prog [options] data-file [channel-file]

    This utility accepts a data file and an optional channel definition file.
    For each channel listed in the latter, an image is produced from the
    corresponding channel in the data file. Various options are provided for
    customizing the output including percentile limiting, color-mapping, and
    drawing of axes and titles.

    The available command line options are listed below.
    """

    def __init__(self):
        super(RasExtractUtility, self).__init__()
        self._image_writers = {}
        self._data_parsers = {}
        self._renderer = RasRenderer()
        self.parser.set_defaults(
            list_colormaps=False,
            list_formats=False,
            list_interpolations=False,
            show_axes=False,
            show_colorbar=False,
            show_histogram=False,
            colormap='gray',
            crop='0,0,0,0',
            percentile=None,
            range=None,
            output='{filename_root}_{channel:02d}_{channel_name}.png',
            title='',
            interpolation=None,
            empty=False,
            multi=False,
        )
        self.parser.add_option(
            '--help-colormaps', dest='list_colormaps', action='store_true',
            help='list the available colormaps')
        self.parser.add_option(
            '--help-formats', dest='list_formats', action='store_true',
            help='list the available file output formats')
        self.parser.add_option(
            '--help-interpolations', dest='list_interpolations',
            action='store_true', help='list the available interpolation '
            'algorithms')
        self.parser.add_option(
            '-a', '--axes', dest='show_axes', action='store_true',
            help='draw the coordinate axes in the output')
        self.parser.add_option(
            '-b', '--color-bar', dest='show_colorbar', action='store_true',
            help='draw a color-bar showing the range of the colormap to the '
            'right of the output')
        self.parser.add_option(
            '-H', '--histogram', dest='show_histogram', action='store_true',
            help='draw a histogram of the channel values below the output')
        self.parser.add_option(
            '-c', '--colormap', dest='colormap', action='store',
            help='the colormap to use in output (e.g. gray, jet, hot); '
            'see --help-colormaps for listing')
        self.parser.add_option(
            '-p', '--percentile', dest='percentile', action='store',
            help='clip values in the output image to the specified low,high '
            'percentile range (mutually exclusive with --range)')
        self.parser.add_option(
            '-r', '--range', dest='range', action='store',
            help='clip values in the output image to the specified low,high '
            'count range (mutually exclusive with --percentile)')
        self.parser.add_option(
            '-C', '--crop', dest='crop', action='store',
            help='crop the input data by left,top,right,bottom points')
        self.parser.add_option(
            '-i', '--interpolation', dest='interpolation', action='store',
            help='force the use of the specified interpolation algorithm; see '
            '--help-interpolation for listing')
        self.parser.add_option(
            '-t', '--title', dest='title', action='store',
            help='specify the template used to display a title at the top of '
            'the output; supports {variables} produced by rasinfo -t')
        self.parser.add_option(
            '-o', '--output', dest='output', action='store',
            help='specify the template used to generate the output filenames; '
            'supports {variables}, see --help-formats for supported file '
            'formats. Default: %default')
        self.parser.add_option(
            '-m', '--multi', dest='multi', action='store_true',
            help='if specified, produce a single output file with multiple '
            'layers or pages, one per channel (only available with certain '
            'formats)')
        self.parser.add_option(
            '-e', '--empty', dest='empty', action='store_true',
            help='if specified, include empty channels in the output (by '
            'default empty channels are ignored)')

    def main(self, options, args):
        if options.list_colormaps:
            self.list_colormaps()
            return 0
        if options.list_interpolations:
            self.list_interpolations()
            return 0
        self.load_backends()
        if options.list_formats:
            self.list_formats()
            return 0
        # Parse the input file(s)
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
            data_file = self._data_parsers[ext](
                data_file, channels_file, progress=progress)
        except KeyError:
            self.parser.error('unrecognized file extension %s' % ext)
        # Configure the renderer from the command line options
        self.parse_percentile(options)
        self.parse_range(options)
        self.parse_colormap(options)
        self.parse_crop(options)
        (   canvas_method,
            multi_class,
            default_interpolation
        ) = self.parse_output(options)
        self.parse_interpolation(options, default_interpolation)
        self.parse_multi(options, multi_class)
        self._renderer.colorbar = options.show_colorbar
        self._renderer.histogram = options.show_histogram
        self._renderer.axes = options.show_axes
        self._renderer.title = options.title
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
                **self._renderer.format_dict(data_file))
            logging.warning('Writing all channels to %s',  filename)
            output = multi_class(filename)
        try:
            for channel in data_file.channels:
                if channel.enabled:
                    if options.multi:
                        logging.warning(
                            'Writing channel %d (%s) to new page/layer',
                            channel.index, channel.name)
                    else:
                        filename = options.output.format(
                            **self._renderer.format_dict(channel))
                        logging.warning(
                            'Writing channel %d (%s) to %s',
                            channel.index, channel.name, filename)
                    figure = self._renderer.draw(
                        channel, allow_empty=options.empty)
                    if figure is not None:
                        # Finally, dump the figure to disk as whatever format
                        # the user requested
                        canvas = canvas_method.im_class(figure)
                        if options.multi:
                            output.savefig(
                                figure, title=channel.format(
                                    '{channel} - {channel_name}'))
                        else:
                            canvas_method(canvas, filename, dpi=DPI)
        finally:
            if options.multi:
                output.close()

    def load_backends(self):
        """Load the various matplotlib backends and custom extensions"""
        from rastools.parsers import PARSERS
        from rastools.image_writers import IMAGE_WRITERS
        # Re-arrange the arrays into more useful dictionaries keyed by
        # extension
        self._image_writers = dict(
            (ext, (method, interpolation, multi_class))
            for (method, exts, _, interpolation, multi_class) in IMAGE_WRITERS
            for ext in exts
        )
        self._data_parsers = dict(
            (ext, cls)
            for (cls, exts, _) in PARSERS
            for ext in exts
        )

    def list_colormaps(self):
        """Prints the list of available colormaps to stdout"""
        sys.stdout.write('The following colormaps are available:\n\n')
        sys.stdout.write('\n'.join(sorted(
            name for name in matplotlib.cm.datad
            if not name.endswith('_r')
        )))
        sys.stdout.write('\n\n')
        sys.stdout.write(
            'Append _r to any colormap name to reverse it. Previews at:\n')
        sys.stdout.write(
            'http://matplotlib.sourceforge.net/examples/pylab_examples/'
            'show_colormaps.html\n\n')

    def list_interpolations(self):
        """Prints the list of supported interpolations to stdout"""
        sys.stdout.write(
            'The following image interpolation algorithms are available:\n\n')
        sys.stdout.write('\n'.join(sorted(
            alg for alg in matplotlib.image.AxesImage._interpd
        )))
        sys.stdout.write('\n\n')

    def list_formats(self):
        """Prints the list of supported iamge formats to stdout"""
        sys.stdout.write('The following file formats are available:\n\n')
        sys.stdout.write('\n'.join(sorted(
            ext for ext in self._image_writers
        )))
        sys.stdout.write('\n\n')

    def parse_percentile(self, options):
        """Parses the --percentile option and checks its validity"""
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
                self._renderer.clip = Percentile(float(low), float(high))
            except ValueError:
                self.parser.error(
                    '%s is not a valid percentile range' % options.percentile)
            if self._renderer.clip.low > self._renderer.clip.high:
                self.parser.error('percentile range must be specified low-high')
            for i in self._renderer.clip:
                if not (0.0 <= i <= 100.0):
                    self.parser.error(
                        'percentile must be between 0 and 100 (%f '
                        'specified)' % i)

    def parse_range(self, options):
        """Parses the --range option and checks its validity"""
        if options.range:
            s = options.range
            if ',' in s:
                low, high = s.split(',', 1)
            elif '-' in s:
                low, high = s.split('-', 1)
            else:
                low, high = ('0.0', s)
            try:
                self._renderer.clip = Range(float(low), float(high))
            except ValueError:
                self.parser.error(
                    '%s is not a valid count range' % self._renderer.clip)
            if self._renderer.clip.low > self._renderer.clip.high:
                self.parser.error('count range must be specified low-high')

    def parse_crop(self, options):
        """Parses the --crop option and checks its validity"""
        try:
            left, top, right, bottom = options.crop.split(',', 4)
        except ValueError:
            self.parser.error(
                'you must specify 4 integer values for the --crop option')
        try:
            self._renderer.crop = Crop(
                int(left), int(top), int(right), int(bottom))
        except ValueError:
            self.parser.error(
                'non-integer values found in --crop value %s' % options.crop)

    def parse_colormap(self, options):
        """Checks the validity of the --colormap option"""
        if not matplotlib.cm.get_cmap(options.colormap):
            self.parser.error('color-map %s is unknown' % options.colormap)
        self._renderer.colormap = options.colormap

    def parse_output(self, options):
        """Checks the validity of the --output option"""
        ext = os.path.splitext(options.output)[1]
        try:
            (   canvas_method,
                default_interpolation,
                multi_class,
            ) = self._image_writers[ext]
        except KeyError:
            self.parser.error('unknown image format "%s"' % ext)
        return canvas_method, multi_class, default_interpolation

    def parse_interpolation(self, options, default_interpolation):
        """Checks the validity of the --interpolation option"""
        if options.interpolation is None:
            options.interpolation = default_interpolation
        if not options.interpolation in matplotlib.image.AxesImage._interpd:
            self.parser.error('interpolation algorithm %s is unknown')
        self._renderer.interpolation = options.interpolation

    def parse_multi(self, options, multi_class):
        """Checks the validity of the --multi switch"""
        if options.multi and not multi_class:
            multi_ext = [
                ext
                for (ext, (_, _, multi)) in self._image_writers.iteritems()
                if multi
            ]
            if multi_ext:
                self.parser.error(
                    'output filename must end with %s when --multi '
                    'is specified' % ','.join(multi_ext))
            else:
                self.parser.error(
                    '--multi is not supported by any registered '
                    'output formats')


class BoundingBox(object):
    """Represents a bounding-box in a matplotlib figure"""

    def __init__(self, left, bottom, width, height):
        self.left = left
        self.bottom = bottom
        self.width = width
        self.height = height

    @property
    def top(self):
        """Returns the top coordinate of the bounding box"""
        return self.bottom + self.height

    @property
    def right(self):
        """Returns the right coordinate of the bounding box"""
        return self.left + self.width

    def relative_to(self, container):
        """Returns the bounding-box as a proportion of container"""
        return BoundingBox(
            self.left / container.width,
            self.bottom / container.height,
            self.width / container.width,
            self.height / container.height
        )

    def __len__(self):
        return 4

    def __getitem__(self, index):
        return (
            self.left,
            self.bottom,
            self.width,
            self.height,
        )[index]

    def __iter__(self):
        for i in (self.left, self.bottom, self.width, self.height):
            yield i

    def __contains__(self, value):
        return value in (self.left, self.bottom, self.width, self.height)


class RasRenderer(object):
    """Renderer class for data files"""
    def __init__(self):
        self.clip = None
        self.crop = Crop(0, 0, 0, 0)
        self.colormap = 'gray'
        self.colorbar = False
        self.histogram = False
        self.histogram_bins = 32
        self.interpolation = 'nearest'
        self.grid = False
        self.axes = False
        self.title = None

    def draw(self, channel, allow_empty=False):
        """Draw the specified channel, returning the matplotlib figure"""
        # Perform any cropping requested. This must be done before calculation
        # of the data's range and percentile limiting is performed (although
        # we've pre-calculated the percentile indexes)
        data = channel.data
        data = data[
            self.crop.top:data.shape[0] - self.crop.bottom,
            self.crop.left:data.shape[1] - self.crop.right
        ]
        # Find the minimum and maximum values in the channel and clip
        # them to a percentile/range if requested
        vsorted = np.sort(data, None)
        data_domain = Range(vsorted[0], vsorted[-1])
        logging.info(
            'Channel %d (%s) has range %d-%d',
            channel.index, channel.name, data_domain.low, data_domain.high)
        if isinstance(self.clip, Percentile):
            data_range = Range(
                vsorted[(len(vsorted) - 1) * self.clip.low / 100.0],
                vsorted[(len(vsorted) - 1) * self.clip.high / 100.0]
            )
            logging.info(
                '%gth percentile is %d',
                self.clip.low, data_range.low)
            logging.info(
                '%gth percentile is %d',
                self.clip.high, data_range.high)
        elif isinstance(self.clip, Range):
            data_range = self.clip
        else:
            data_range = data_domain
        if data_range != data_domain:
            logging.info(
                'Channel %d (%s) has new range %d-%d',
                channel.index, channel.name, *data_range)
        if data_range.low < data_domain.low:
            logging.warning(
                'Channel %d (%s) has no values below %d',
                channel.index, channel.name, data_range.low)
        if data_range.high > data_domain.high:
            logging.warning(
                'Channel %d (%s) has no values above %d',
                channel.index, channel.name, data_range.high)
        if data_range.low == data_range.high:
            if allow_empty:
                logging.warning(
                    'Channel %d (%s) is empty',
                    channel.index, channel.name)
            else:
                logging.warning(
                    'Channel %d (%s) is empty, skipping',
                    channel.index, channel.name)
                return None
        # Copy the data into a floating-point array (matplotlib's
        # image module won't play with uint32 data - only uint8 or
        # float32) and crop it as necessary
        data = np.array(data, np.float)
        # Calculate the figure dimensions and margins. The layout of objects in
        # the final image is roughly as illustrated below. Objects which are
        # not selected to appear take up no space. Only the IMAGE element is
        # mandatory:
        #
        #   +-----------------+
        #   |     margin      |
        #   |                 |
        #   | m   TITLE     m |
        #   | a             a |
        #   | r   IMAGE     r |
        #   | g             g |
        #   | i  HISTOGRAM  i |
        #   | n             n |
        #   |    COLORBAR     |
        #   |                 |
        #   |     margin      |
        #   +-----------------+
        #
        # Several dimensions depend on the IMAGE dimensions, therefore these
        # are calculated first. However, the IMAGE position in turn depends on
        # the dimensions of the other figure elements, thus the IMAGE position
        # is adjusted after calculating all other dimensions
        margin = (0.0, 0.75)[
            self.axes or
            self.colorbar or
            self.histogram or
            bool(self.title)
        ]
        image_box = BoundingBox(
            margin,
            0.0,
            (channel.parent.x_size - self.crop.left - self.crop.right) / DPI,
            (channel.parent.y_size - self.crop.top - self.crop.bottom) / DPI
        )
        colorbar_box = BoundingBox(
            margin,
            [0.0, margin][self.colorbar],
            image_box.width,
            [0.0, 0.3][self.colorbar]
        )
        histogram_box = BoundingBox(
            margin,
            [0.0, margin + colorbar_box.top][self.histogram],
            image_box.width,
            [0.0, image_box.height * 0.8][self.histogram]
        )
        image_box.bottom = (
            margin + max(histogram_box.top, colorbar_box.top)
        )
        title_box = BoundingBox(
            0.0,
            [0.0, margin + image_box.top][bool(self.title)],
            image_box.width + (margin * 2),
            [0.0, 0.75][bool(self.title)]
        )
        figure_box = BoundingBox(
            0.0,
            0.0,
            image_box.width + (margin * 2),
            title_box.top if bool(self.title) else image_box.top
        )
        figure = matplotlib.figure.Figure(
            figsize=(figure_box.width, figure_box.height), dpi=DPI,
            facecolor='w', edgecolor='w')
        # Draw the various image elements within bounding boxes calculated from
        # the metrics above
        image = self.draw_image(
            data, data_range, figure, image_box.relative_to(figure_box))
        if self.histogram:
            self.draw_histogram(
                data, data_range, figure,
                histogram_box.relative_to(figure_box))
        if self.colorbar:
            self.draw_colorbar(
                image, data_domain, data_range, figure,
                colorbar_box.relative_to(figure_box))
        if bool(self.title):
            self.draw_title(
                channel, figure, title_box.relative_to(figure_box))
        return figure

    def draw_image(self, data, data_range, figure, box):
        """Draws the image of the data within the specified figure"""
        # The imshow() call takes care of clamping values with data_range and
        # color-mapping
        axes = figure.add_axes(box, frame_on=self.axes)
        if not self.axes:
            axes.set_axis_off()
        return axes.imshow(
            data, cmap=matplotlib.cm.get_cmap(self.colormap),
            vmin=data_range.low, vmax=data_range.high,
            interpolation=self.interpolation)

    def draw_histogram(self, data, data_range, figure, box):
        """Draws the data's historgram within the specified figure"""
        axes = figure.add_axes(box)
        axes.hist(data.flat, bins=self.histogram_bins, range=data_range)

    def draw_colorbar(self, image, data_domain, data_range, figure, box):
        """Draws a range color-bar within the specified figure"""
        axes = figure.add_axes(box)
        figure.colorbar(
            image, cax=axes, orientation='horizontal',
            extend=
                'both' if data_range.low > data_domain.low and
                          data_range.high < data_domain.high else
                'max' if data_range.high < data_domain.high else
                'min' if data_range.low > data_domain.low else
                'neither')

    def draw_title(self, channel, figure, box):
        """Draws a title within the specified figure"""
        axes = figure.add_axes(box)
        axes.set_axis_off()
        # The string_escape codec is used to permit new-line escapes, and
        # various options are passed-thru to the channel formatter so things
        # like percentile can be included in the title
        title = self.title.decode('string_escape').format(
            **self.format_dict(channel))
        axes.text(
            0.5, 0, title,
            horizontalalignment='center', verticalalignment='baseline',
            multialignment='center', size='medium', family='sans-serif',
            transform=axes.transAxes)

    def format_dict(self, source, **kwargs):
        """Converts the configuration for use in format substitutions"""
        return source.format_dict(
            percentile_from=
                self.clip.low if isinstance(self.clip, Percentile) else None,
            percentile_to=
                self.clip.high if isinstance(self.clip, Percentile) else None,
            range_from=
                self.clip.low if isinstance(self.clip, Range) else None,
            range_to=
                self.clip.high if isinstance(self.clip, Range) else None,
            interpolation=self.interpolation,
            colormap=self.colormap,
            crop_left=self.crop.left,
            crop_top=self.crop.top,
            crop_right=self.crop.right,
            crop_bottom=self.crop.bottom,
            **kwargs
        )


main = RasExtractUtility()
