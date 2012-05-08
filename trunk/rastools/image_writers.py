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

import logging
import matplotlib

__all__ = ['IMAGE_WRITERS']

IMAGE_WRITERS = []

logging.info('Loading PNG support')
try:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
except ImportError:
    # If we can't find the default Agg backend, something's seriously wrong
    raise
else:
    IMAGE_WRITERS.extend([
        # canvas method              exts                description             interpolation  multi-class
        (FigureCanvasAgg.print_bmp,  ('.bmp', '.BMP'),   'Windows bitmap',       'nearest',     None),
        (FigureCanvasAgg.print_png,  ('.png', '.PNG'),   'PNG image',            'nearest',     None),
    ])

logging.info('Loading SVG support')
try:
    from matplotlib.backends.backend_svg import FigureCanvasSVG
except ImportError:
    logging.warning('Failed to load Cairo support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasSVG.print_svg,  ('.svg', '.SVG'),   'SVG image',            'lanczos',     None),
        (FigureCanvasSVG.print_svgz, ('.svgz', '.SVGZ'), 'Compressed SVG image', 'lanczos',     None),
    ])

logging.info('Loading TIFF, GIF, JPEG support')
try:
    from rastools.tiffwrite import FigureCanvasPIL
except ImportError:
    logging.warning('Failed to load TIFF support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasPIL.print_tif, ('.tif', '.tiff', '.TIF', '.TIFF'), 'TIFF image', 'nearest', None),
        (FigureCanvasPIL.print_gif, ('.gif', '.GIF'),                   'GIF image',  'nearest', None),
        (FigureCanvasPIL.print_jpg, ('.jpg', '.jpeg', '.JPG', '.JPEG'), 'JPEG image', 'lanczos', None),
    ])

logging.info('Loading PostScript support')
try:
    from matplotlib.backends.backend_ps import FigureCanvasPS
except ImportError:
    logging.warning('Failed to load PostScript support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasPS.print_eps, ('.eps', '.EPS'), 'Encapsulated PostScript image', 'lanczos', None),
        (FigureCanvasPS.print_ps,  ('.ps', '.PS'),   'PostScript document',           'lanczos', None),
    ])

logging.info('Loading PDF support')
try:
    from matplotlib.backends.backend_pdf import FigureCanvasPdf, PdfPages
except ImportError:
    logging.warning('Failed to load PDF support')
else:
    matplotlib.rc('pdf', use14corefonts=True, compression=True)
    IMAGE_WRITERS.extend([
        (FigureCanvasPdf.print_pdf, ('.pdf', '.PDF'), 'Portable Document Format', 'lanczos', PdfPages),
    ])

logging.info('Loading GIMP support')
try:
    from rastools.xcfwrite import FigureCanvasXcf, XcfLayers
except ImportError:
    logging.warning('Failed to load GIMP support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasXcf.print_xcf, ('.xcf', '.XCF'), 'GIMP XCF image', 'nearest', XcfLayers),
    ])
