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
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import re
import sys
import logging
from operator import methodcaller

import numpy as np
import matplotlib
import matplotlib.cm
import matplotlib.image

try:
    # Optionally import optcomplete (for auto-completion) if it's installed
    import optcomplete
except ImportError:
    optcomplete = None

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
            show_grid=False,
            show_colorbar=False,
            show_histogram=False,
            bins=32,
            colormap='gray',
            output='{filename_root}_{channel:02d}_{channel_name}.png',
            title='',
            title_x='',
            title_y='',
            interpolation=None,
            layers=None,
            multi=False,
        )
        self.parser.add_option(
            '--help-colormaps', dest='list_colormaps', action='store_true',
            help='list the available colormaps')
        self.parser.add_option(
            '--help-formats', dest='list_formats', action='store_true',
            help='list the available file formats')
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
        opt = self.parser.add_option(
            '-C', '--colormap', dest='colormap', action='store',
            help='the colormap to use in output (e.g. gray, jet, hot); '
            'see --help-colormaps for listing')
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(self.list_colormaps())
        opt = self.parser.add_option(
            '-i', '--interpolation', dest='interpolation', action='store',
            help='force the use of the specified interpolation algorithm; see '
            '--help-interpolation for listing')
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(
                self.list_interpolations())
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
        opt = self.parser.add_option(
            '-o', '--output', dest='output', action='store',
            help='specify the template used to generate the output filenames; '
            'supports {variables}, see --help-formats for supported file '
            'formats. Default: %default')
        if optcomplete:
            opt.completer = optcomplete.RegexCompleter(
                re.compile('.*' + ext.replace('.', '\.'))
                for (ext, _) in self.list_output_formats()
            )
        self.parser.add_option(
            '-m', '--multi', dest='multi', action='store_true',
            help='if specified, produce a single output file with multiple '
            'layers or pages, one per channel (only available with certain '
            'formats)')
        self.parser.add_option(
            '-L', '--layers', dest='layers', action='store',
            help='store the specified channels as Red, Green, and Blue in '
            'the resulting image. Channels are comma separated and specified '
            'as 0-based numbers. Channels may be left empty')
        if optcomplete:
            self.arg_completer = optcomplete.RegexCompleter(
                re.compile('.*' + ext.replace('.', '\.'))
                for (ext, _) in self.list_input_formats()
            )

    @property
    def image_writers(self):
        "Load matplotlib backends lazily as some are expensive to load"
        if self._image_writers is None:
            from rastools.image_writers import IMAGE_WRITERS
            self._image_writers = dict(
                (ext, (cls, method, interp, multi_class, desc))
                for (cls, method, exts, desc, interp, multi_class) in IMAGE_WRITERS
                for ext in exts
            )
        return self._image_writers

    def main(self, options, args):
        if options.list_colormaps:
            self.list_colormaps()
            sys.stdout.write('The following colormaps are available:\n\n')
            sys.stdout.write('\n'.join(
                name for name in self.list_colormaps()
                if not name.endswith('_r')
            ))
            sys.stdout.write('\n\n')
            sys.stdout.write(
                'Append _r to any colormap name to reverse it. Previews at:\n')
            sys.stdout.write(
                'http://matplotlib.sourceforge.net/examples/pylab_examples/'
                'show_colormaps.html\n\n')
            return 0
        if options.list_interpolations:
            sys.stdout.write(
                'The following image interpolation algorithms are '
                'available:\n\n')
            sys.stdout.write('\n'.join(self.list_interpolations()))
            sys.stdout.write('\n\n')
            return 0
        if options.list_formats:
            sys.stdout.write('The following input formats are supported:\n\n')
            sys.stdout.write('\n'.join(
                '{0:<8} - {1}'.format(ext, desc)
                for (ext, desc) in self.list_input_formats()
            ))
            sys.stdout.write('\n\n')
            sys.stdout.write('The following output formats are supported:\n\n')
            sys.stdout.write('\n'.join(
                '{0:<8} - {1}'.format(ext, desc)
                for (ext, desc) in self.list_output_formats()
            ))
            sys.stdout.write('\n\n')
            return 0
        # Configure the renderer from the command line options
        data_file = self.parse_files(options, args)
        options.layers = self.parse_layers(options, data_file)
        if options.layers:
            if options.show_colorbar:
                self.parser.error('you may not use --color-bar with --layers')
            renderer = LayeredRenderer((data_file.x_size, data_file.y_size))
        else:
            renderer = ChannelRenderer((data_file.x_size, data_file.y_size))
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
        renderer.grid = options.show_grid
        renderer.empty = options.empty
        (   canvas_class,
            canvas_method,
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
        if options.layers:
            filename = options.output.format(
                **data_file.format_dict(
                    **renderer.format_dict()))
            logging.warning('Writing all layers to %s', filename)
            figure = renderer.draw(*options.layers)
            canvas = canvas_class(figure)
            canvas_method(canvas, filename)
        elif options.multi:
            filename = options.output.format(
                **data_file.format_dict(
                    **renderer.format_dict()))
            logging.warning('Writing all channels to %s',  filename)
            output = multi_class(filename)
            try:
                for channel in data_file.channels:
                    if channel.enabled:
                        logging.warning(
                            'Writing channel %d (%s) to new page/layer',
                            channel.index, channel.name)
                        figure = renderer.draw(channel)
                        if figure is not None:
                            canvas = canvas_class(figure)
                            output.savefig(
                                figure,
                                title='{channel} - {channel_name}'.format(
                                    **channel.format_dict()))
            finally:
                output.close()
        else:
            for channel in data_file.channels:
                if channel.enabled:
                    filename = options.output.format(
                        **channel.format_dict(
                            **renderer.format_dict()))
                    logging.warning(
                        'Writing channel %d (%s) to %s',
                        channel.index, channel.name, filename)
                    figure = renderer.draw(channel)
                    if figure is not None:
                        # Finally, dump the figure to disk as whatever format
                        # the user requested
                        canvas = canvas_class(figure)
                        canvas_method(canvas, filename)

    def list_colormaps(self):
        "List the available colormaps"
        return sorted(matplotlib.cm.datad)

    def list_interpolations(self):
        "List the supported interpolations"
        return (
            alg for alg in sorted(matplotlib.image.AxesImage._interpd)
        )

    def list_input_formats(self):
        "List the supported data formats"
        return (
            (ext, self.data_parsers[ext][-1])
            for ext in sorted(self.data_parsers.keys(),
                key=methodcaller('lower'))
        )

    def list_output_formats(self):
        "List the supported image formats"
        return (
            (ext, self.image_writers[ext][-1])
            for ext in sorted(self.image_writers.keys(),
                key=methodcaller('lower'))
        )

    def parse_layers(self, options, data_file):
        if options.layers is not None:
            try:
                red, green, blue = options.layers.split(',')
            except ValueError:
                self.parser.error(
                    '--layers must be specified with three '
                    'comma-separated channels')
            result = [red, green, blue]
            for index, channel in enumerate(result):
                if channel:
                    try:
                        channel = int(channel)
                    except ValueError:
                        self.parser.error(
                            '--layers must be specified as integer '
                            'numbers (found %s)' % channel)
                    try:
                        channel = [
                            c for c in data_file.channels
                            if c.index == channel][0]
                    except IndexError:
                        self.parser.error(
                            '--layers refers to channel %d which does '
                            'not exist in the source file' % channel)
                else:
                    channel = None
                result[index] = channel
            return result

    def parse_colormap_option(self, options):
        "Checks the validity of the --colormap option"
        if not matplotlib.cm.get_cmap(options.colormap):
            self.parser.error(
                'color-map {} is unknown'.format(options.colormap))
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
                    '{} is not a valid --resize value'.format(options.resize))
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
                    '{} is not a valid --offset'.format(options.offset))
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
                    '{} is not a valid --scale'.format(options.scale))
            if result.x == 0.0 or result.y == 0.0:
                self.parser.error('--scale multiplier cannot be 0.0')
            return result

    def parse_output_options(self, options):
        "Checks the validity of the --output and --multi options"
        ext = os.path.splitext(options.output)[1]
        try:
            (   canvas_class,
                canvas_method,
                default_interpolation,
                multi_class,
                _
            ) = self.image_writers[ext]
        except KeyError:
            self.parser.error('unknown image format "{}"'.format(ext))
        if options.multi and not multi_class:
            multi_ext = [
                ext
                for (ext, (_, _, _, multi, _)) in self.image_writers.items()
                if multi
            ]
            if multi_ext:
                self.parser.error(
                    'output filename must end with {} when --multi '
                    'is specified'.format(','.join(multi_ext)))
            else:
                self.parser.error(
                    '--multi is not supported by any registered '
                    'output formats')
        return canvas_class, canvas_method, multi_class, default_interpolation

    def parse_interpolation_option(self, options, default_interpolation):
        "Checks the validity of the --interpolation option"
        if options.interpolation is None:
            options.interpolation = default_interpolation
        if not options.interpolation in matplotlib.image.AxesImage._interpd:
            self.parser.error(
                'interpolation algorithm {} is unknown'.format(
                    options.interpolation))
        return options.interpolation


class BaseRenderer(RasChannelProcessor):
    "Abstract renderer class for data files"

    def __init__(self, data_size):
        super(BaseRenderer, self).__init__(data_size)
        self.colorbar = False
        self.colormap = 'gray'
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

    @property
    def axes_extents(self):
        "Returns the extents of the axes for the image, after offsets and scaling"
        return (
            Range(
                self.axes_scales.x * (
                    self.axes_offsets.x + self.crop.left),
                self.axes_scales.x * (
                    self.axes_offsets.x + self.data_size.x - self.crop.right)
            ) +
            Range(
                self.axes_scales.y * (
                    self.axes_offsets.y + self.data_size.y - self.crop.bottom),
                self.axes_scales.y * (
                    self.axes_offsets.y + self.crop.top)
            )
        )

    @property
    def margins_visible(self):
        "Returns True if the image margins should be shown"
        return (
            self.axes
            or self.histogram
            or self.colorbar
            or bool(self.title))

    @property
    def margin(self):
        "Returns the size of the margins when drawing"
        return Coord(0.75, 0.25) if self.margins_visible else Coord(0.0, 0.0)

    @property
    def sep_margin(self):
        "Returns the size of the separator between image elements"
        return 0.3

    # The following properties calculate the figure dimensions and margins. The
    # layout of objects in the final image is roughly as illustrated below.
    # Objects which are not selected to appear take up no space. Only the IMAGE
    # element is mandatory:
    #
    #   +-----------------+
    #   |     margin.x    |
    #   |                 |
    #   | m    TITLE    m |
    #   | a             a |
    #   | r    IMAGE    r |
    #   | g             g |
    #   | i  HISTOGRAM  i |
    #   | n             n |
    #   | .  COLORBAR   . |
    #   | y             y |
    #   |     margin.x    |
    #   +-----------------+
    #
    # Positions are calculated from the bottom up, but several dimensions
    # depend on the image size. Hence, this is calculated first, then each
    # bounding box from the bottom up is calculated followed by the overall
    # figure box.

    @property
    def image_size(self):
        "Returns the size of the image in pixels after cropping and resizing"
        if isinstance(self.resize, Coord):
            return self.resize
        else:
            return Coord(
                self.resize * (self.data_size.x - self.crop.left - self.crop.right),
                self.resize * (self.data_size.y - self.crop.top - self.crop.bottom),
            )

    @property
    def colorbar_box(self):
        "Returns the colorbar bounding box"
        return BoundingBox(
            self.margin.x,
            self.margin.y,
            self.image_size.x / DPI,
            0.5 if self.colorbar else 0.0,
        )

    @property
    def histogram_box(self):
        "Returns the histogram bounding box"
        return BoundingBox(
            self.margin.x,
            self.colorbar_box.top + (
                self.sep_margin if self.colorbar else 0.0),
            self.image_size.x / DPI,
            self.image_size.y / DPI * 0.8 if self.histogram else 0.0,
        )

    @property
    def image_box(self):
        "Returns the image bounding box"
        return BoundingBox(
            self.margin.x,
            self.histogram_box.top + (
                self.sep_margin if self.colorbar or self.histogram else 0.0),
            self.image_size.x / DPI,
            self.image_size.y / DPI,
        )

    @property
    def title_box(self):
        "Returns the title bounding box"
        return BoundingBox(
            self.margin.x,
            self.image_box.top,
            self.image_box.width,
            1.0 if bool(self.title) else 0.0,
        )

    @property
    def figure_box(self):
        "Returns the overall bounding box"
        return BoundingBox(
            0.0,
            0.0,
            self.image_box.width + (self.margin.x * 2),
            self.title_box.top + self.margin.y,
        )

    def title_axes(self, figure):
        "Construct and configure a set of axes for the title"
        box = self.title_box.relative_to(self.figure_box)
        axes = figure.add_axes(box)
        axes.set_axis_off()
        return axes

    def image_axes(self, figure):
        "Construct and configure a set of axes for an image"
        axes = figure.add_axes(
            self.image_box.relative_to(self.figure_box),
            frame_on=self.axes or self.grid)
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
            axes.set_xticks([], False)
            axes.set_yticks([], False)
        return axes

    def histogram_axes(self, figure):
        "Construct and configure a set of axes for a histogram"
        return figure.add_axes(self.histogram_box.relative_to(self.figure_box))

    def colorbar_axes(self, figure):
        "Construct and configure a set of axes for the colorbar"
        return figure.add_axes(self.colorbar_box.relative_to(self.figure_box))

    def format_dict(self, **kwargs):
        "Converts the configuration for use in format substitutions"
        result = super(BaseRenderer, self).format_dict()
        result.update(
            interpolation=self.interpolation,
            colormap=self.colormap)
        return result


class LayeredRenderer(BaseRenderer):
    "Renderer implementation for multi-layered images"

    def draw(self, red_channel, green_channel, blue_channel):
        "Draw the specified channels as a single image, returning the matplotlib figure"
        assert not self.colorbar
        data, data_domain, data_range = self.process_multiple(
            red_channel, green_channel, blue_channel)
        # Copy the data into a floating-point array (matplotlib's image module
        # won't play with uint32 data - only uint8 or float32) and normalize it
        # to values between 0.0 and 1.0
        data = np.array(data, np.float)
        for index in range(3):
            low, high = data_range[index]
            data[..., index] = data[..., index] - low
            if (high - low):
                data[..., index] = data[..., index] / (high - low)
        figure = matplotlib.figure.Figure(
            figsize=(self.figure_box.width, self.figure_box.height), dpi=DPI,
            facecolor='w', edgecolor='w')
        # Draw the various image elements within bounding boxes calculated from
        # the metrics above
        image = self.draw_image(data, data_range, figure)
        if self.histogram:
            self.draw_histogram(data, data_range, figure)
        if bool(self.title):
            self.draw_title(channel, figure)
        return figure

    def draw_image(self, data, data_range, figure):
        "Draws the image of the data within the specified figure"
        axes = self.image_axes(figure)
        # Clamp all data to values between 0.0 and 1.0 (operate on a copy to
        # ensure we don't mess with the original array which is needed for a
        # histogram)
        data = data.copy()
        data[data < 0.0] = 0.0
        data[data > 1.0] = 1.0
        # The imshow() call takes care of clamping values with data_range and
        # color-mapping
        return axes.imshow(
            data,
            origin='upper',
            extent=self.axes_extents,
            interpolation=self.interpolation)

    def draw_histogram(self, data, data_range, figure):
        "Draws the data's historgram within the specified figure"
        axes = self.histogram_axes(figure)
        data_flat = np.empty((data.shape[0] * data.shape[1], 3))
        for index in range(3):
            data_flat[..., index] = data[..., index].flatten()
        axes.hist(
            data_flat,
            bins=self.histogram_bins,
            histtype='barstacked',
            color=('red', 'green', 'blue'),
            range=(0.0, 1.0))

    def draw_title(self, channels, figure):
        "Draws a title within the specified figure"
        axes = self.title_axes(figure)
        # The string_escape codec is used to permit new-line escapes, and
        # various options are passed-thru to the channel formatter so things
        # like percentile can be included in the title
        title_dict = self.format_dict()
        for prefix, channel in zip(('red', 'green', 'blue'), channels):
            if channel:
                for name, value in channel.format_dict():
                    title_dict[prefix + '_' + name] = value
        title = self.title.decode('string_escape').format(**title_dict)
        axes.text(
            0.5, 0, title,
            horizontalalignment='center', verticalalignment='baseline',
            multialignment='center', size='medium', family='sans-serif',
            transform=axes.transAxes)


class ChannelRenderer(BaseRenderer):
    "Renderer implementation for single-channel images"

    def draw(self, channel):
        "Draw the specified channel, returning the matplotlib figure"
        try:
            data, data_domain, data_range = self.process_single(channel)
        except RasChannelEmptyError:
            return None
        # Copy the data into a floating-point array (matplotlib's image module
        # won't play with uint32 data - only uint8 or float32)
        data = np.array(data, np.float)
        figure = matplotlib.figure.Figure(
            figsize=(self.figure_box.width, self.figure_box.height), dpi=DPI,
            facecolor='w', edgecolor='w')
        # Draw the various image elements within bounding boxes calculated from
        # the metrics above
        image = self.draw_image(data, data_range, figure)
        if self.histogram:
            self.draw_histogram(data, data_range, figure)
        if self.colorbar:
            self.draw_colorbar(image, data_domain, data_range, figure)
        if bool(self.title):
            self.draw_title(channel, figure)
        return figure

    def draw_image(self, data, data_range, figure):
        "Draws the image of the data within the specified figure"
        axes = self.image_axes(figure)
        # The imshow() call takes care of clamping values with data_range and
        # color-mapping
        return axes.imshow(
            data, cmap=matplotlib.cm.get_cmap(self.colormap),
            origin='upper', extent=self.axes_extents,
            vmin=data_range.low, vmax=data_range.high,
            interpolation=self.interpolation)

    def draw_histogram(self, data, data_range, figure):
        "Draws the data's historgram within the specified figure"
        axes = self.histogram_axes(figure)
        axes.hist(data.flat, bins=self.histogram_bins, range=data_range)

    def draw_colorbar(self, image, data_domain, data_range, figure):
        "Draws a range color-bar within the specified figure"
        axes = self.colorbar_axes(figure)
        figure.colorbar(
            image, cax=axes, orientation='horizontal',
            extend=
                'both' if data_range.low > data_domain.low and
                          data_range.high < data_domain.high else
                'max' if data_range.high < data_domain.high else
                'min' if data_range.low > data_domain.low else
                'neither')

    def draw_title(self, channel, figure):
        "Draws a title within the specified figure"
        axes = self.title_axes(figure)
        # The string_escape codec is used to permit new-line escapes, and
        # various options are passed-thru to the channel formatter so things
        # like percentile can be included in the title
        title = self.title.decode('string_escape').format(
            **channel.format_dict(**self.format_dict()))
        axes.text(
            0.5, 0, title,
            horizontalalignment='center', verticalalignment='baseline',
            multialignment='center', size='medium', family='sans-serif',
            transform=axes.transAxes)


main = RasExtractUtility()
