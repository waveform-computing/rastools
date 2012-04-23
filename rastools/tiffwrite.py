# This module is a dirty hack to add TIFF, GIF, and JPEG support to matplotlib
# (mpl's default JEPG support comes from GDK, but that doesn't play nice with
# things like Qt)

from matplotlib.backends.backend_agg import FigureCanvasAgg
from PIL import Image
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# If PIL's available, define a sub-class of Agg which can handle conversion
# to odd formats like TIFF
class FigureCanvasPIL(FigureCanvasAgg):
    def print_tif(self, filename_or_obj, *args, **kwargs):
        png = StringIO()
        FigureCanvasAgg.print_png(self, png, *args, **kwargs)
        png.seek(0) # rewind
        # Convert the PNG to a TIFF (uncompressed)
        im = Image.open(png)
        im.save(filename_or_obj, 'TIFF')

    def print_gif(self, filename_or_obj, *args, **kwargs):
        png = StringIO()
        FigureCanvasAgg.print_png(self, png, *args, **kwargs)
        png.seek(0) # rewind
        # Convert the PNG to a GIF87a
        im = Image.open(png)
        im.save(filename_or_obj, 'GIF')

    def print_jpg(self, filename_or_obj, *args, **kwargs):
        png = StringIO()
        FigureCanvasAgg.print_png(self, png, *args, **kwargs)
        png.seek(0) # rewind
        # Convert the PNG to a JPEG
        im = Image.open(png)
        im.save(filename_or_obj, 'JPEG',
            quality=kwargs.get('quality', 75),
            optimize=kwargs.get('optimize', True))
