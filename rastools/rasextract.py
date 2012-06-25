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

from __future__ import (
    unicode_literals, print_function, absolute_import, division)

import os
import sys
import logging

import numpy as np
import matplotlib
import matplotlib.cm
import matplotlib.image

from rastools.rasutility import (
    RasUtility, RasChannelEmptyError, RasChannelProcessor)
from rastools.collections import BoundingBox, Coord, Range


DPI = 72.0

class RasExtractUtility(RasUtility):
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
        self._image_writers = None
        self.parser.set_defaults(
            list_colormaps=False,
            list_formats=False,
            list_interpolations=False,
            resize='1.0',
            show_axes=False,
            axes_offset='0.0,0.0',
            axes_scale='1.0,1.0',
            show_colorbar=False,
            show_histogram=False,
            bins=32,
            colormap='gray',
            output='{filename_root}_{channel:02d}_{channel_name}.png',
            grid=False,
            title='',
            title_x='',
            title_y='',
            interpolation=None,
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
        self.add_range_options()
        self.add_crop_option()
        self.add_empty_option()
        self.parser.add_option(
            '-a', '--axes', dest='show_axes', action='store_true',
            help='draw the coordinate axes in the output')
        self.parser.add_option(
            '-b', '--color-bar', dest='show_colorbar', action='store_true',
            help='draw a color-bar showing the range of the colormap to the '
            'right of the output')
        self.parser.add_option(
            '-g', '--grid', dest='show_grid', action='store_true',
            help='draw grid-lines overlayed on top of the image')
        self.parser.add_option(
            '-R', '--resize', dest='resize', action='store',
            help='resize the image; if specified as a single number it is '
            'considered a multiplier for the original dimensions, otherwise '
            'two comma-separated numbers are expected which will be treated '
            'as new X,Y dimensions')
        self.parser.add_option(
            '-H', '--histogram', dest='show_histogram', action='store_true',
            help='draw a histogram of the channel values below the output')
        self.parser.add_option(
            '--histogram-bins', dest='bins', action='store',
            help='specify the number of bins to use when constructing the '
            'histogram (default=%default)')
        self.parser.add_option(
            '-C', '--colormap', dest='colormap', action='store',
            help='the colormap to use in output (e.g. gray, jet, hot); '
            'see --help-colormaps for listing')
        self.parser.add_option(
            '-i', '--interpolation', dest='interpolation', action='store',
            help='force the use of the specified interpolation algorithm; see '
            '--help-interpolation for listing')
        self.parser.add_option(
            '-O', '--offset', dest='axes_offset', action='store',
            help='specify the X,Y offset of the coordinates displayed on the '
            'axes; if one value is specified it is used for both axes')
        self.parser.add_option(
            '-S', '--scale', dest='axes_scale', action='store',
            help='specify X,Y multipliers to apply to the post-offset axes '
            'coordinates; if one value is specified it is used for both axes')
        self.parser.add_option(
            '-t', '--title', dest='title', action='store',
            help='specify the template used to display a title at the top of '
            'the output; supports {variables} produced by rasinfo -t')
        self.parser.add_option(
            '--x-title', dest='title_x', action='store',
            help='specify the title for the X-axis; implies --axes')
        self.parser.add_option(
            '--y-title', dest='title_y', action='store',
            help='specify the title for the Y-axis; imples --axes')
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

    @property
    def image_writers(self):
        "Load matplotlib backends lazily as some are expensive to load"
        if self._image_writers is None:
            from rastools.image_writers import IMAGE_WRITERS
            self._image_writers = dict(
                (ext, (method, interp, multi_class, desc))
                for (method, exts, desc, interp, multi_class) in IMAGE_WRITERS
                for ext in exts
            )
        return self._image_writers

    def main(self, options, args):
        if options.list_colormaps:
            self.list_colormaps()
            return 0
        if options.list_interpolations:
            self.list_interpolations()
            return 0
        if options.list_formats:
            self.list_formats()
            return 0
        # Configure the renderer from the command line options
        data_file = self.parse_files(options, args)
        renderer = RasRenderer()
        renderer.colormap = self.parse_colormap_option(options)
        renderer.crop = self.parse_crop_option(options)
        renderer.clip = self.parse_range_options(options)
        renderer.resize = self.parse_resize_option(options)
        renderer.colorbar = options.show_colorbar
        renderer.histogram = options.show_histogram
        renderer.histogram_bins = options.bins
        renderer.title = options.title
        renderer.axes = options.show_axes or options.title_x or options.title_y
        renderer.axes_offsets = self.parse_axes_offset_option(options)
        renderer.axes_scales = self.parse_axes_scale_option(options)
        renderer.axes_titles = Coord(options.title_x, options.title_y)
        renderer.grid = options.grid
        renderer.empty = options.empty
        (   canvas_method,
            multi_class,
            default_interpolation
        ) = self.parse_output_options(options)
        renderer.interpolation = self.parse_interpolation_option(
            options, default_interpolation)
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
                **renderer.format_dict(data_file))
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
                            **renderer.format_dict(channel))
                        logging.warning(
                            'Writing channel %d (%s) to %s',
                            channel.index, channel.name, filename)
                    figure = renderer.draw(channel)
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

    def list_colormaps(self):
        "Prints the list of available colormaps to stdout"
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
        "Prints the list of supported interpolations to stdout"
        sys.stdout.write(
            'The following image interpolation algorithms are available:\n\n')
        sys.stdout.write('\n'.join(sorted(
            alg for alg in matplotlib.image.AxesImage._interpd
        )))
        sys.stdout.write('\n\n')

    def list_formats(self):
        "Prints the list of supported image formats to stdout"
        sys.stdout.write('The following file formats are available:\n\n')
        for ext in sorted(self.image_writers.iterkeys()):
            sys.stdout.write('%-8s - %s\n' % (ext, self.image_writers[ext][-1]))
        sys.stdout.write('\n')

    def parse_colormap_option(self, options):
        "Checks the validity of the --colormap option"
        if not matplotlib.cm.get_cmap(options.colormap):
            self.parser.error('color-map %s is unknown' % options.colormap)
        return options.colormap

    def parse_resize_option(self, options):
        "Checks the validity of the --offset option"
        if options.resize:
            s = options.resize
            try:
                if not (',' in s or 'x' in s):
                    result = float(s)
                    if result == 0.0:
                        self.parser.error('--resize multiplier cannot be 0.0')
                else:
                    if ',' in s:
                        x, y = s.split(',', 1)
                    else:
                        x, y = s.split('x', 1)
                    result = Coord(float(x), float(y))
            except ValueError:
                self.parser.error(
                    '%s is not a valid --resize setting' % options.resize)
            return result

    def parse_axes_offset_option(self, options):
        "Checks the validity of the --offset option"
        if options.axes_offset:
            s = options.axes_offset
            if ',' in s:
                x, y = s.split(',', 1)
            elif '-' in s:
                x, y = s.split('-', 1)
            else:
                x, y = s, s
            try:
                result = Coord(float(x), float(y))
            except ValueError:
                self.parser.error(
                    '%s is not a valid --offset setting' % options.offset)
            return result

    def parse_axes_scale_option(self, options):
        "Checks the validity of the --scale option"
        if options.axes_scale:
            s = options.axes_scale
            if ',' in s:
                x, y = s.split(',', 1)
            elif '-' in s:
                x, y = s.split('-', 1)
            else:
                x, y = s, s
            try:
                result = Coord(float(x), float(y))
            except ValueError:
                self.parser.error(
                    '%s is not a valid --scale setting' % options.scale)
            if result.x == 0.0 or result.y == 0.0:
                self.parser.error('--scale multiplier cannot be 0.0')
            return result

    def parse_output_options(self, options):
        "Checks the validity of the --output and --multi options"
        ext = os.path.splitext(options.output)[1]
        try:
            (   canvas_method,
                default_interpolation,
                multi_class,
                _
            ) = self.image_writers[ext]
        except KeyError:
            self.parser.error('unknown image format "%s"' % ext)
        if options.multi and not multi_class:
            multi_ext = [
                ext
                for (ext, (_, _, multi, _)) in self.image_writers.iteritems()
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
        return canvas_method, multi_class, default_interpolation

    def parse_interpolation_option(self, options, default_interpolation):
        "Checks the validity of the --interpolation option"
        if options.interpolation is None:
            options.interpolation = default_interpolation
        if not options.interpolation in matplotlib.image.AxesImage._interpd:
            self.parser.error('interpolation algorithm %s is unknown')
        return options.interpolation


class RasRenderer(RasChannelProcessor):
    "Renderer class for data files"

    def __init__(self):
        super(RasRenderer, self).__init__()
        self.colormap = 'gray'
        self.colorbar = False
        self.histogram = False
        self.histogram_bins = 32
        self.interpolation = 'nearest'
        self.grid = False
        self.axes = False
        self.title = None
        self.axes_titles = Coord(None, None)
        self.axes_offsets = Coord(0.0, 0.0)
        self.axes_scales = Coord(1.0, 1.0)
        self.resize = 1.0

    def draw(self, channel):
        "Draw the specified channel, returning the matplotlib figure"
        try:
            data, data_domain, data_range = self.process(channel)
        except RasChannelEmptyError:
            return None
        # Copy the data into a floating-point array (matplotlib's image module
        # won't play with uint32 data - only uint8 or float32) and crop it as
        # necessary
        data = np.array(data, np.float)
        # Calculate the figure dimensions and margins. The layout of objects in
        # the final image is roughly as illustrated below. Objects which are
        # not selected to appear take up no space. Only the IMAGE element is
        # mandatory:
        #
        #   +-----------------+
        #   |     margin      |
        #   |                 |
        #   | m    TITLE    m |
        #   | a             a |
        #   | r    IMAGE    r |
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
        if isinstance(self.resize, Coord):
            image_box = BoundingBox(
                margin,
                0.0,
                self.resize.x / DPI,
                self.resize.y / DPI
            )
        else:
            image_box = BoundingBox(
                margin,
                0.0,
                self.resize / DPI * (
                    channel.parent.x_size - self.crop.left - self.crop.right),
                self.resize / DPI * (
                    channel.parent.y_size - self.crop.top - self.crop.bottom)
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
            margin + (title_box.top if bool(self.title) else image_box.top)
        )
        figure = matplotlib.figure.Figure(
            figsize=(figure_box.width, figure_box.height), dpi=DPI,
            facecolor='w', edgecolor='w')
        # Figure out the axis extents
        extent = Coord(
            Range(
                self.axes_scales.x * (
                    self.axes_offsets.x + self.crop.left),
                self.axes_scales.x * (
                    self.axes_offsets.x + channel.parent.x_size - self.crop.right)
            ),
            Range(
                self.axes_scales.y * (
                    self.axes_offsets.y + channel.parent.y_size - self.crop.bottom),
                self.axes_scales.y * (
                    self.axes_offsets.y + self.crop.top)
            )
        )
        # Draw the various image elements within bounding boxes calculated from
        # the metrics above
        image = self.draw_image(
            data, data_range, extent, figure,
            image_box.relative_to(figure_box))
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

    def draw_image(self, data, data_range, extent, figure, box):
        "Draws the image of the data within the specified figure"
        axes = figure.add_axes(box, frame_on=self.axes or self.grid)
        # Configure the x and y axes appearance
        if self.grid:
            axes.grid(color='k', linestyle='-')
        else:
            axes.grid(False)
        if self.axes:
            if self.axes_titles.x:
                axes.set_xlabel(self.axes_titles.x.decode('string_escape'))
            if self.axes_titles.y:
                axes.set_ylabel(self.axes_titles.y.decode('string_escape'))
        else:
            axes.set_xticklabels([])
            axes.set_yticklabels([])
        # The imshow() call takes care of clamping values with data_range and
        # color-mapping
        return axes.imshow(
            data, cmap=matplotlib.cm.get_cmap(self.colormap),
            origin='upper', extent=extent.x + extent.y,
            vmin=data_range.low, vmax=data_range.high,
            interpolation=self.interpolation)

    def draw_histogram(self, data, data_range, figure, box):
        "Draws the data's historgram within the specified figure"
        axes = figure.add_axes(box)
        axes.hist(data.flat, bins=self.histogram_bins, range=data_range)

    def draw_colorbar(self, image, data_domain, data_range, figure, box):
        "Draws a range color-bar within the specified figure"
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
        "Draws a title within the specified figure"
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
        "Converts the configuration for use in format substitutions"
        return super(RasRenderer, self).format_dict(
            source,
            interpolation=self.interpolation,
            colormap=self.colormap,
            **kwargs
        )


main = RasExtractUtility()
