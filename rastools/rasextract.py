#!/usr/bin/env python
# vim: set et sw=4 sts=4:

import os
import sys
import logging
import rastools.main
import numpy as np
import matplotlib as mpl
import matplotlib.cm
import matplotlib.image
from collections import namedtuple
from rastools.parsers import PARSERS

DPI = 72.0
IMAGE_FORMATS = {}

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
        self.parser.set_defaults(
            list_colormaps=False,
            list_formats=False,
            list_interpolations=False,
            show_axes=False,
            show_colorbar=False,
            show_histogram=False,
            cmap='gray',
            crop='0,0,0,0',
            percentile=None,
            range=None,
            output='{filename_root}_{channel:02d}_{channel_name}.png',
            title='',
            interpolation=None,
            empty=False,
            multi=False,
        )
        self.parser.add_option('--help-colormaps', dest='list_colormaps', action='store_true',
            help="""list the available colormaps""")
        self.parser.add_option('--help-formats', dest='list_formats', action='store_true',
            help="""list the available file output formats""")
        self.parser.add_option('--help-interpolations', dest='list_interpolations', action='store_true',
            help="""list the available interpolation algorithms""")
        self.parser.add_option('-a', '--axes', dest='show_axes', action='store_true',
            help="""draw the coordinate axes in the output""")
        self.parser.add_option('-b', '--color-bar', dest='show_colorbar', action='store_true',
            help="""draw a color-bar showing the range of the colormap to the right of the output""")
        self.parser.add_option('-H', '--histogram', dest='show_histogram', action='store_true',
            help="""draw a histogram of the channel values below the output""")
        self.parser.add_option('-c', '--colormap', dest='cmap', action='store',
            help="""the colormap to use in output (e.g. gray, jet, hot); see --help-colormaps for listing""")
        self.parser.add_option('-p', '--percentile', dest='percentile', action='store',
            help="""clip values in the output image to the specified low,high percentile range (mutually exclusive with --range)""")
        self.parser.add_option('-r', '--range', dest='range', action='store',
            help="""clip values in the output image to the specified low,high count range (mutually exclusive with --percentile)""")
        self.parser.add_option('-C', '--crop', dest='crop', action='store',
            help="""crop the input data by top,left,bottom,right points""")
        self.parser.add_option('-i', '--interpolation', dest='interpolation', action='store',
            help="""force the use of the specified interpolation algorithm; see --help-interpolation for listing""")
        self.parser.add_option('-t', '--title', dest='title', action='store',
            help="""specify the template used to display a title at the top of the output; supports {variables} produced by rasinfo -p""")
        self.parser.add_option('-o', '--output', dest='output', action='store',
            help="""specify the template used to generate the output filenames; supports {variables}, see --help-formats for supported file formats. Default: %default""")
        self.parser.add_option('-m', '--multi', dest='multi', action='store_true',
            help="""if specified, produce a single output file with multiple layers or pages, one per channel (only available with certain formats)""")
        self.parser.add_option('-e', '--empty', dest='empty', action='store_true',
            help="""if specified, include empty channels in the output (by default empty channels are ignored)""")

    def main(self, options, args):
        super(RasExtractUtility, self).main(options, args)
        if options.list_colormaps:
            sys.stdout.write('The following colormaps are available:\n\n')
            sys.stdout.write('\n'.join(sorted(name for name in mpl.cm.datad if not name.endswith('_r'))))
            sys.stdout.write('\n\n')
            sys.stdout.write('Append _r to any colormap name to reverse it. Previews at:\n')
            sys.stdout.write('http://matplotlib.sourceforge.net/examples/pylab_examples/show_colormaps.html\n\n')
            return 0
        self.load_backends()
        if options.list_formats:
            sys.stdout.write('The following file formats are available:\n\n')
            sys.stdout.write('\n'.join(sorted(ext for ext in IMAGE_FORMATS)))
            sys.stdout.write('\n\n')
            return 0
        if options.list_interpolations:
            sys.stdout.write('The following image interpolation algorithms are available:\n\n')
            sys.stdout.write('\n'.join(sorted(alg for alg in mpl.image.AxesImage._interpd)))
            sys.stdout.write('\n\n')
            return 0
        if len(args) < 1:
            self.parser.error('you must specify a data file')
        if len(args) > 2:
            self.parser.error('you cannot specify more than two filenames')
        if args[0] == '-' and args[1] == '-':
            self.parser.error('you cannot specify stdin for both files!')
        # Parse the input file(s)
        ext = os.path.splitext(args[0])[-1]
        files = (sys.stdin if arg == '-' else arg for arg in args)
        f = None
        for p in PARSERS:
            if ext in p.ext:
                f = p(*files, verbose=options.loglevel<logging.WARNING)
                break
        if not f:
            self.parser.error('unrecognized file extension %s' % ext)
        # Check the percentile range is valid
        if options.percentile:
            if options.range:
                self.parser.error('cannot specify both --percentile and --range')
            s = options.percentile
            if ',' in s:
                s = s.split(',', 1)
            else:
                s = ('0.0', s)
            try:
                options.percentile = tuple(float(n) for n in s)
            except ValueError:
                self.parser.error('%s is not a valid percentile range' % options.percentile)
            for n in options.percentile:
                if not (0.0 <= n <= 100.0):
                    self.parser.error('percentile must be between 0 and 100 (%f specified)' % n)
        # Check the range is valid
        if options.range:
            s = options.range
            if ',' in s:
                s = s.split(',', 1)
            else:
                s = ('0.0', s)
            try:
                options.range = tuple(float(n) for n in s)
            except ValueError:
                self.parser.error('%s is not a valid count range' % options.range)
            if options.range[0] > options.range[1]:
                self.parser.error('count range must be specified low,high')
        # Check the colormap is known
        if not mpl.cm.get_cmap(options.cmap):
            self.parser.error('color-map %s is unknown' % options.cmap)
        # Check the crop values
        try:
            top, left, bottom, right = options.crop.split(',', 4)
        except ValueError:
            self.parser.error('you must specify 4 integer values for the --crop option')
        try:
            options.crop = Crop(int(top), int(left), int(bottom), int(right))
        except ValueError:
            self.parser.error('non-integer values found in --crop value %s' % options.crop)
        # Check the requested file format is known
        ext = os.path.splitext(options.output)[1].lower()
        try:
            (canvas_method, interpolation, multi_class) = IMAGE_FORMATS[ext]
        except KeyError:
            self.parser.error('unknown image format "%s"' % ext)
        # Check the requested interpolation is valid
        if options.interpolation is None:
            options.interpolation = interpolation
        if not options.interpolation in mpl.image.AxesImage._interpd:
            self.parser.error('interpolation algorithm %s is unknown')
        # Check special format switches
        if options.multi and not multi_class:
            multi_ext = [ext for (ext, (_, _, multi)) in IMAGE_FORMATS.iteritems() if multi]
            if multi_ext:
                self.parser.error('output filename must end with %s when --multi is specified' % ','.join(multi_ext))
            else:
                self.parser.error('--multi is not supported by any registered output formats')
        # Calculate the percentile indices (these will be the same for every
        # channel as every channel has the same dimensions in a RAS file)
        if options.percentile:
            options.percentile_indexes = tuple(
                ((f.y_size - options.crop.top - options.crop.bottom) *
                (f.x_size - options.crop.left - options.crop.right) - 1) *
                n / 100.0
                for n in options.percentile
            )
            for n, i in zip(options.percentile, options.percentile_indexes):
                logging.info('%gth percentile is at index %d' % (n, i))
        # Extract the specified channels
        logging.info('File contains %d channels, extracting channels %s' % (
            len(f.channels),
            ','.join(str(channel.index) for channel in f.channels if channel.enabled)
        ))
        if options.multi:
            filename = f.format(options.output, **self.format_options(options))
            logging.warning('Writing all channels to %s' % filename)
            output = multi_class(filename)
        try:
            for channel in f.channels:
                if channel.enabled:
                    if options.multi:
                        logging.warning('Writing channel %d (%s) to new page/layer' % (channel.index, channel.name))
                    else:
                        filename = channel.format(options.output, **self.format_options(options))
                        logging.warning('Writing channel %d (%s) to %s' % (channel.index, channel.name, filename))
                    figure = self.draw_channel(channel, options, filename)
                    if figure is not None:
                        # Finally, dump the figure to disk as whatever format
                        # the user requested
                        canvas = canvas_method.im_class(figure)
                        if options.multi:
                            output.savefig(figure, title=channel.format('{channel} - {channel_name}'))
                        else:
                            canvas_method(canvas, filename, dpi=DPI)
        finally:
            if options.multi:
                output.close()

    def draw_channel(self, channel, options, filename):
        """Draw the specified channel, returning the resulting matplotlib figure"""
        # Perform any cropping requested. This must be done before
        # calculation of the data's range and percentile limiting is
        # performed for obvious reasons
        data = channel.data
        data = data[
            options.crop.top:data.shape[0] - options.crop.bottom,
            options.crop.left:data.shape[1] - options.crop.right
        ]
        # Find the minimum and maximum values in the channel and clip
        # them to a percentile if required
        vsorted = np.sort(data, None)
        vmin = vsorted[0]
        vmax = vsorted[-1]
        logging.info('Channel %d (%s) has range %d-%d' % (channel.index, channel.name, vmin, vmax))
        if options.percentile:
            pmin = vsorted[options.percentile_indexes[0]]
            pmax = vsorted[options.percentile_indexes[1]]
            logging.info('%gth percentile is %d' % (options.percentile[0], pmin))
            logging.info('%gth percentile is %d' % (options.percentile[1], pmax))
        elif options.range:
            pmin, pmax = options.range
        else:
            pmin = vmin
            pmax = vmax
        if pmin != vmin or pmax != vmax:
            logging.info('Channel %d (%s) has new range %d-%d' % (channel.index, channel.name, pmin, pmax))
        if pmin < vmin:
            logging.warning('Channel %d (%s) has no values below %d' % (channel.index, channel.name, vmin))
        if pmax > vmax:
            logging.warning('Channel %d (%s) has no values above %d' % (channel.index, channel.name, vmax))
        if pmin == pmax:
            if options.empty:
                logging.warning('Channel %d (%s) is empty' % (channel.index, channel.name))
            else:
                logging.warning('Channel %d (%s) is empty, skipping' % (channel.index, channel.name))
                return None
        # Copy the data into a floating-point array (matplotlib's
        # image module won't play with uint32 data - only uint8 or
        # float32) and crop it as necessary
        data = np.array(data, np.float)
        # Calculate the figure dimensions and margins, and construct the
        # necessary objects
        (img_width, img_height) = (
            (channel.parent.x_size - options.crop.left - options.crop.right) / DPI,
            (channel.parent.y_size - options.crop.top - options.crop.bottom) / DPI
        )
        (hist_width, hist_height) = ((0.0, 0.0), (img_width, img_height))[options.show_histogram]
        (cbar_width, cbar_height) = ((0.0, 0.0), (img_width, 1.0))[options.show_colorbar]
        (head_width, head_height) = ((0.0, 0.0), (img_width, 0.75))[bool(options.title)]
        margin = (0.0, 0.75)[
            options.show_axes
            or options.show_colorbar
            or options.show_histogram
            or bool(options.title)]
        fig_width = img_width + margin * 2
        fig_height = img_height + hist_height + cbar_height + head_height + margin * 2
        fig = mpl.figure.Figure(figsize=(fig_width, fig_height), dpi=DPI,
            facecolor='w', edgecolor='w')
        # Construct an axis in which to draw the channel data and draw it. The
        # imshow() call takes care of clamping values with vmin and vmax and
        # color-mapping
        ax = fig.add_axes((
            margin / fig_width,      # left
            (margin + hist_height + cbar_height) / fig_height, # bottom
            img_width / fig_width,   # width
            img_height / fig_height, # height
        ), frame_on=options.show_axes)
        if not options.show_axes:
            ax.set_axis_off()
        img = ax.imshow(data, cmap=mpl.cm.get_cmap(options.cmap), vmin=pmin, vmax=pmax,
            interpolation=options.interpolation)
        # Construct an axis for the histogram, if requested
        if options.show_histogram:
            hax = fig.add_axes((
                margin / fig_width,               # left
                (margin + cbar_height) / fig_height, # bottom
                hist_width / fig_width,           # width
                (hist_height * 0.8) / fig_height, # height
            ))
            hg = hax.hist(data.flat, bins=32, range=(pmin, pmax))
        # Construct an axis for the colorbar, if requested
        if options.show_colorbar:
            cax = fig.add_axes((
                margin / fig_width,                # left
                margin / fig_height,               # bottom
                cbar_width / fig_width,            # width
                (cbar_height * 0.3) / fig_height, # height
            ))
            cb = fig.colorbar(img, cax=cax, orientation='horizontal',
                extend=
                'both' if pmin > vmin and pmax < vmax else
                'max' if pmax < vmax else
                'min' if pmin > vmin else
                'neither')
        # Construct an axis for the title, if requested
        if options.title:
            hax = fig.add_axes((
                0, (margin + cbar_height + hist_height + img_height) / fig_height, # left, bottom
                1, head_height / fig_height, # width, height
            ))
            hax.set_axis_off()
            # Render the title. The string_escape codec is used to
            # permit new-line escapes, and various options are
            # passed-thru to the channel formatter so things like
            # percentile can be included in the title
            title = channel.format(options.title.decode('string_escape'),
                output=filename, **self.format_options(options))
            hd = hax.text(0.5, 0.5, title,
                horizontalalignment='center', verticalalignment='baseline',
                multialignment='center', size='medium', family='sans-serif',
                transform=hax.transAxes)
        return fig

    def format_options(self, options):
        """Utility routine which converts the options array for use in format substitutions"""
        return dict(
            percentile=options.percentile,
            range=options.range,
            interpolation=options.interpolation,
            colormap=options.cmap,
            crop=','.join(str(i) for i in options.crop),
        )

    def load_backends(self):
        """Load the various matplotlib backends and custom extensions"""
        logging.info('Loading standard graphics renderer')
        try:
            global FigureCanvasAgg
            from matplotlib.backends.backend_agg import FigureCanvasAgg
        except ImportError:
            # If we can't find the default Agg backend, something's seriously wrong
            raise
        else:
            IMAGE_FORMATS.update({
                # ext    canvas method                interpolation  multi-class
                '.bmp':  (FigureCanvasAgg.print_bmp,  'nearest',     None),
                '.png':  (FigureCanvasAgg.print_png,  'nearest',     None),
            })

        logging.info('Loading SVG support')
        try:
            global FigureCanvasSVG
            from matplotlib.backends.backend_svg import FigureCanvasSVG
        except ImportError:
            logging.warning('Failed to load Cairo support')
        else:
            IMAGE_FORMATS.update({
                # ext    canvas method                interpolation  multi-class
                '.svg':  (FigureCanvasSVG.print_svg,  'lanczos',     None),
                '.svgz': (FigureCanvasSVG.print_svgz, 'lanczos',     None),
            })

        logging.info('Loading JPEG support')
        try:
            global FigureCanvasGDK
            from matplotlib.backends.backend_gdk import FigureCanvasGDK
        except ImportError:
            logging.warning('Failed to load JPEG support')
        else:
            IMAGE_FORMATS.update({
                # ext    canvas method                interpolation  multi-class
                '.jpg':  (FigureCanvasGDK.print_jpg,  'lanczos',     None),
                '.jpeg': (FigureCanvasGDK.print_jpg,  'lanczos',     None),
            })

        logging.info('Loading TIFF support')
        try:
            global FigureCanvasPIL
            from rastools.tiffwrite import FigureCanvasPIL
        except ImportError:
            logging.warning('Failed to load TIFF support')
        else:
            IMAGE_FORMATS.update({
                # ext    canvas method                interpolation  multi-class
                '.tif':  (FigureCanvasPIL.print_tif,  'nearest',     None),
                '.tiff': (FigureCanvasPIL.print_tif,  'nearest',     None),
                '.gif':  (FigureCanvasPIL.print_gif,  'nearest',     None),
            })

        logging.info('Loading PostScript support')
        try:
            global FigureCanvasPS
            from matplotlib.backends.backend_ps import FigureCanvasPS
        except ImportError:
            logging.warning('Failed to load PostScript support')
        else:
            IMAGE_FORMATS.update({
                # ext    canvas method                interpolation  multi-class
                '.eps':  (FigureCanvasPS.print_eps,  'lanczos',      None),
                '.ps':   (FigureCanvasPS.print_ps,   'lanczos',      None),
            })

        logging.info('Loading PDF support')
        try:
            global FigureCanvasPdf, PdfPages
            from matplotlib.backends.backend_pdf import FigureCanvasPdf, PdfPages
        except ImportError:
            logging.warning('Failed to load PDF support')
        else:
            mpl.rc('pdf', use14corefonts=True, compression=True)
            IMAGE_FORMATS.update({
                # ext    canvas method                interpolation  multi-class
                '.pdf':  (FigureCanvasPdf.print_pdf,  'lanczos',     PdfPages),
            })

        logging.info('Loading GIMP support')
        try:
            global FigureCanvasXcf, XcfLayers
            from rastools.xcfwrite import FigureCanvasXcf, XcfLayers
        except ImportError:
            logging.warning('Failed to load GIMP support')
        else:
            IMAGE_FORMATS.update({
                # ext    canvas method                interpolation  multi-class
                '.xcf':  (FigureCanvasXcf.print_xcf,  'nearest',     XcfLayers),
            })


main = RasExtractUtility()
