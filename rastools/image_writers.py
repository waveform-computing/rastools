import logging
import matplotlib

__all__ = ['IMAGE_WRITERS']

IMAGE_WRITERS = []

logging.info('Loading standard graphics renderer')
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

logging.info('Loading JPEG support')
try:
    from matplotlib.backends.backend_gdk import FigureCanvasGDK
except ImportError:
    logging.warning('Failed to load JPEG support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasGDK.print_jpg, ('.jpg', '.jpeg', '.JPG', '.JPEG'), 'JPEG image', 'lanczos', None),
    ])

logging.info('Loading TIFF support')
try:
    from rastools.tiffwrite import FigureCanvasPIL
except ImportError:
    logging.warning('Failed to load TIFF support')
else:
    IMAGE_WRITERS.extend([
        (FigureCanvasPIL.print_tif, ('.tif', '.tiff', '.TIF', '.TIFF'), 'TIFF image', 'nearest', None),
        (FigureCanvasPIL.print_gif, ('.gif', '.GIF'),                   'GIF image',  'nearest', None),
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
