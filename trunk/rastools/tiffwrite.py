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

"""This module is a dirty hack to add TIFF, GIF, and JPEG support to matplotlib
(mpl's default JEPG support comes from GDK, but that doesn't play nice with
things like Qt)"""

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
