# This module is a dirty hack to add GIF & TIFF support to matplotlib

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
