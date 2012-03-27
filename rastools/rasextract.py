#!/usr/bin/env python
# vim: set et sw=4 sts=4:

import os
import sys
import logging
import itertools
import rastools.main
import rastools.rasfile
import numpy as np
import matplotlib as mpl
from collections import namedtuple

# Import various backends from matplotlib and configure the available formats
# depending on what's available

DPI = 72.0
IMAGE_FORMATS = {}
MULTI_PAGE_PDF=False

try:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
except ImportError:
    # If we can't find the default Agg backend, something's seriously wrong
    raise
else:
    IMAGE_FORMATS.update({
        # ext    canvas method                interpolation
        '.bmp':  (FigureCanvasAgg.print_bmp,  'nearest'),
        '.emf':  (FigureCanvasAgg.print_emf,  'nearest'),
        '.eps':  (FigureCanvasAgg.print_eps,  'bicubic'),
        '.pdf':  (FigureCanvasAgg.print_pdf,  'bicubic'),
        '.png':  (FigureCanvasAgg.print_png,  'nearest'),
        '.ps':   (FigureCanvasAgg.print_ps,   'bicubic'),
        '.raw':  (FigureCanvasAgg.print_raw,  'nearest'),
        '.rgb':  (FigureCanvasAgg.print_rgb,  'nearest'),
        '.rgba': (FigureCanvasAgg.print_rgba, 'nearest'),
        '.svg':  (FigureCanvasAgg.print_svg,  'bicubic'),
        '.svgz': (FigureCanvasAgg.print_svgz, 'bicubic'),
    })
try:
    from rastools.rastiff import FigureCanvasPIL
except ImportError:
    pass
else:
    IMAGE_FORMATS.update({
        # ext    canvas method                interpolation
        '.tif':  (FigureCanvasPIL.print_tif,  'nearest'),
        '.tiff': (FigureCanvasPIL.print_tif,  'nearest'),
        '.gif':  (FigureCanvasPIL.print_gif,  'nearest'),
    })
try:
    from matplotlib.backends.backend_gdk import FigureCanvasGDK
except ImportError:
    pass
else:
    IMAGE_FORMATS.update({
        # ext    canvas method                interpolation
        '.jpg':  (FigureCanvasGDK.print_jpg,  'bicubic'),
        '.jpeg': (FigureCanvasGDK.print_jpg,  'bicubic'),
    })
try:
    from matplotlib.backends.backend_pdf import FigureCanvasPdf, PdfPages
    IMAGE_FORMATS.update({
        # ext    canvas method                interpolation
        '.pdf':  (FigureCanvasPdf.print_pdf,  'bicubic'),
    })
    MULTI_PAGE_PDF=True
except ImportError:
    pass

Crop = namedtuple('Crop', ('top', 'left', 'bottom', 'right'))

class RasExtractUtility(rastools.main.Utility):
    """%prog [options] ras-file [channel-file]

    This utility accepts a QSCAN RAS file and an optional channel definition
    file. For each channel listed in the latter, an image is produced from the
    corresponding channel in the RAS file. Various options are provided for
    customizing the output including percentile limiting, color-mapping, and
    drawing of axes and titles.

    The available command line options are listed below.
    """

    def __init__(self):
        super(RasExtractUtility, self).__init__()
        self.parser.set_defaults(
            cmap_list=False,
            fmt_list=False,
            show_axes=False,
            show_colorbar=False,
            show_histogram=False,
            cmap='gray',
            crop='0,0,0,0',
            percentile=100.0,
            output='{filename_root}_{channel:02d}_{channel_name}.png',
            title='',
            one_pdf=False,
        )
        self.parser.add_option('--help-color-maps', dest='cmap_list', action='store_true',
            help="""list the available color-maps""")
        self.parser.add_option('--help-formats', dest='fmt_list', action='store_true',
            help="""list the available file output formats""")
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
        self.parser.add_option('-o', '--output', dest='output', action='store',
            help="""specify the template used to generate the output filenames; supports {variables} produced by rasinfo -p (default is %default)""")
        self.parser.add_option('-t', '--title', dest='title', action='store',
            help="""specify the template used to display a title at the top of the output; supports {variables} produced by rasinfo -p""")
        if MULTI_PAGE_PDF:
            self.parser.add_option('--one-pdf', dest='one_pdf', action='store_true',
                help="""if specified, a single PDF file will be produced with one page per image; the output template must end with .pdf and must not contain channel variable references""")

    def main(self, options, args):
        super(RasExtractUtility, self).main(options, args)
        if options.cmap_list:
            sys.stdout.write('The following colormaps are available:\n\n')
            sys.stdout.write('\n'.join(sorted(name for name in mpl.cm.datad if not name.endswith('_r'))))
            sys.stdout.write('\n\n')
            sys.stdout.write('Append _r to any colormap name to reverse it\n\n')
            return 0
        if options.fmt_list:
            sys.stdout.write('The following file formats are available:\n\n')
            sys.stdout.write('\n'.join(sorted(ext for ext in IMAGE_FORMATS)))
            sys.stdout.write('\n\n')
            return 0
        if len(args) < 1:
            self.parser.error('you must specify a RAS file')
        if len(args) > 2:
            self.parser.error('you cannot specify more than two filenames')
        if args[0] == '-' and args[1] == '-':
            self.parser.error('you cannot specify stdin for both files!')
        # Parse the input files
        ras_f = rastools.rasfile.RasFileReader(
            sys.stdin if args[0] == '-' else args[0],
            None if len(args) < 2 else sys.stdin if args[1] == '-' else args[1],
            verbose=options.loglevel<logging.WARNING)
        # Check the clip level is a valid percentage
        try:
            options.percentile = float(options.percentile)
        except ValueError:
            self.parser.error('%s is not a valid percentile' % options.percentile)
        if not (0 <= options.percentile <= 100.0):
            self.parser.error('percentile must be between 0 and 100 (%f specified)' % options.percentile)
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
            (canvas_method, interpolation) = IMAGE_FORMATS[ext]
        except KeyError:
            self.parser.error('unknown image format "%s"' % ext)
        # Extract the specified channels
        logging.info('File contains %d channels, extracting channels %s' % (
            len(ras_f.channels),
            ','.join(str(channel.index) for channel in ras_f.channels if channel.enabled)
        ))
        if options.percentile < 100.0:
            options.vmax_index = round(
                (ras_f.raster_count - options.crop.top - options.crop.bottom) *
                (ras_f.point_count - options.crop.left - options.crop.right) *
                options.percentile / 100.0)
            logging.info('%gth percentile is at index %d' % (options.percentile, options.vmax_index))
        if options.one_pdf:
            filename = ras_f.format(options.output)
            logging.warning('Writing all images to %s' % filename)
            pdf_pages = PdfPages(filename)
        try:
            for channel in ras_f.channels:
                if channel.enabled:
                    if options.one_pdf:
                        logging.warning('Writing channel %d (%s) to new page' % (channel.index, channel.name))
                    else:
                        filename = channel.format(options.output)
                        logging.warning('Writing channel %d (%s) to %s' % (channel.index, channel.name, filename))
                    figure = self.draw_channel(channel, options, filename, interpolation)
                    # Finally, dump the figure to disk as whatever format the
                    # user requested
                    canvas = canvas_method.im_class(figure)
                    if options.one_pdf:
                        pdf_pages.savefig(figure)
                    else:
                        canvas_method(canvas, filename, dpi=DPI)
        finally:
            if options.one_pdf:
                pdf_pages.close()

    def draw_channel(self, channel, options, filename, interpolation):
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
        if options.percentile < 100.0:
            pmax = vsorted[options.vmax_index]
            logging.info('%gth percentile is %d' % (options.percentile, pmax))
            if pmax != vmax:
                vmax = pmax
                logging.info('Channel %d (%s) has new range %d-%d' % (channel.index, channel.name, vmin, vmax))
        if vmin == vmax:
            logging.warning('Channel %d (%s) is empty, skipping' % (channel.index, channel.name))
        else:
            # Copy the data into a floating-point array (matplotlib's
            # image module won't play with uint32 data - only uint8 or
            # float32) and crop it as necessary
            data = np.array(data, np.float)
            # Calculate the figure dimensions and margins, and
            # construct the necessary objects
            (img_width, img_height) = (
                (channel.ras_file.point_count - options.crop.left - options.crop.right) / DPI,
                (channel.ras_file.raster_count - options.crop.top - options.crop.bottom) / DPI
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
            # Construct an axis in which to draw the channel data and
            # draw it. The imshow() call takes care of clamping values
            # with vmin and vmax and color-mapping. Interpolation is
            # set manually to 'nearest' to avoid any blurring (after
            # all, we're sizing the axis precisely to the image data so
            # interpolation shouldn't be needed)
            ax = fig.add_axes((
                margin / fig_width,      # left
                (margin + hist_height + cbar_height) / fig_height, # bottom
                img_width / fig_width,   # width
                img_height / fig_height, # height
            ), frame_on=options.show_axes)
            if not options.show_axes:
                ax.set_axis_off()
            img = ax.imshow(data, cmap=mpl.cm.get_cmap(options.cmap), vmin=vmin, vmax=vmax,
                interpolation=interpolation)
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
                    percentile=options.percentile,
                    colormap=options.cmap,
                    crop=','.join(str(i) for i in options.crop),
                    output=filename)
                hd = hax.text(0.5, 0.5, title,
                    horizontalalignment='center', verticalalignment='baseline',
                    multialignment='center', size='medium', family='sans-serif',
                    transform=hax.transAxes)
        return fig


main = RasExtractUtility()
