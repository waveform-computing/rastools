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

"""Centralized loader for image-writing modules"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

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
        # canvas class, method, exts, description, default interpolation, multi-class
        (FigureCanvasAgg, FigureCanvasAgg.print_png, ('.png', '.PNG'),
            'PNG - Portable Network Graphics', 'nearest', None),
    ])

logging.info('Loading SVG support')
try:
    from matplotlib.backends.backend_svg import FigureCanvasSVG
except ImportError:
    logging.warning('Failed to load Cairo support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasSVG, FigureCanvasSVG.print_svg, ('.svg', '.SVG'),
            'SVG - Scalable Vector Graphics', 'lanczos', None),
        (FigureCanvasSVG, FigureCanvasSVG.print_svgz, ('.svgz', '.SVGZ'),
            'SVGZ - Compressed Scalable Vector Graphics', 'lanczos', None),
    ])

logging.info('Loading TIFF, GIF, JPEG support')
try:
    from rastools.tiffwrite import FigureCanvasPIL
except ImportError:
    logging.warning('Failed to load TIFF support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasPIL, FigureCanvasPIL.print_bmp,
            ('.bmp', '.BMP'),
            'BMP - Windows Bitmap Format', 'nearest', None),
        (FigureCanvasPIL, FigureCanvasPIL.print_tif,
            ('.tif', '.tiff', '.TIF', '.TIFF'),
            'TIFF - Tagged Image File Format', 'nearest', None),
        (FigureCanvasPIL, FigureCanvasPIL.print_gif,
            ('.gif', '.GIF'),
            'GIF - CompuServe Graphics Interchange Format', 'nearest', None),
        (FigureCanvasPIL, FigureCanvasPIL.print_jpg,
            ('.jpg', '.jpeg', '.JPG', '.JPEG'),
            'JPEG - Joint Photographic Experts Group', 'lanczos', None),
    ])

logging.info('Loading PostScript support')
try:
    from matplotlib.backends.backend_ps import FigureCanvasPS
except ImportError:
    logging.warning('Failed to load PostScript support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasPS, FigureCanvasPS.print_eps, ('.eps', '.EPS'),
            'EPS - Encapsulated PostScript', 'lanczos', None),
        (FigureCanvasPS, FigureCanvasPS.print_ps, ('.ps', '.PS'),
            'PS - PostScript document', 'lanczos', None),
    ])

logging.info('Loading PDF support')
try:
    from matplotlib.backends.backend_pdf import FigureCanvasPdf, PdfPages
except ImportError:
    logging.warning('Failed to load PDF support')
else:
    matplotlib.rc('pdf', use14corefonts=True, compression=True)
    IMAGE_WRITERS.extend([
        (FigureCanvasPdf, FigureCanvasPdf.print_pdf, ('.pdf', '.PDF'),
            'PDF - Adobe Portable Document Format', 'lanczos', PdfPages),
    ])

logging.info('Loading GIMP support')
try:
    from rastools.xcfwrite import FigureCanvasXcf, XcfLayers
except ImportError:
    logging.warning('Failed to load GIMP support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasXcf, FigureCanvasXcf.print_xcf, ('.xcf', '.XCF'),
            'XCF - GIMP native format', 'nearest', XcfLayers),
    ])
