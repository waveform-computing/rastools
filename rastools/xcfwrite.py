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

"""This module uses GIMP's batch mode to support multi-layered XCF output"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import tempfile
import subprocess
import logging

# XXX Find a python 3 compatible imaging library?
from PIL import Image
from matplotlib.backends.backend_agg import FigureCanvasAgg

GIMP_EXECUTABLE = 'gimp'

# A simple GIMP script to generate a .xcf file from a single input image.
# Substitutions:
#
#   {input} -- double-quoted input filename
#   {output} -- double-quoted output filename
SINGLE_LAYER_SCRIPT = """
(let*
  (
    (im (car (file-png-load RUN-NONINTERACTIVE {input} {input})))
    (layer (car (gimp-image-get-active-layer im)))
  )
  (gimp-file-save RUN-NONINTERACTIVE im layer {output} {output})
  (gimp-image-delete im)
)
"""

# A more complex GIMP script to generate a multi-layer .xcf file from a list of
# input images. Substitutions:
#
#   {layers} -- a space-separated list of quoted input filenames
#   {titles} -- a space-separated list of quoted layer titles
#   {width} -- the width of the output image in pixels
#   {height} -- the height of the output image in pixels
#   {output} -- the output filename
MULTI_LAYER_SCRIPT = """
(let*
  (
    (images '({layers}))
    (titles '({titles}))
    (im (car (gimp-image-new {width} {height} RGB)))
  )
  (gimp-image-undo-disable im)
  (while (not (null? images))
    (let*
      (
        (image (car images))
        (title (car titles))
        (layer (car (gimp-file-load-layer RUN-NONINTERACTIVE im image)))
      )
      (gimp-drawable-set-name layer title)
      (gimp-image-add-layer im layer 0)
    )
    (set! images (cdr images))
    (set! titles (cdr titles))
  )
  (gimp-image-undo-enable im)
  (let*
    (
      (layer (car (gimp-image-get-active-layer im)))
    )
    (gimp-file-save RUN-NONINTERACTIVE im layer {output} {output})
  )
  (gimp-image-delete im)
)
"""

# http://stackoverflow.com/questions/11301138/how-to-check-if-variable-is-string-with-python-2-and-3-compatibility
try:
    # XXX Py2 only
    basestring
    def is_string(s):
        "Tests whether s is a string in Python 2"
        return isinstance(s, basestring)
except NameError:
    # XXX Py3 only
    def is_string(s):
        "Tests whether s is a string in Python 3"
        return isinstance(s, str)

def quote_string(s):
    "Quotes a string for use in a GIMP script"
    return '"%s"' % s.replace(r'"', r'\"')

def run_gimp_script(script=None):
    "Launches the provided scheme script with GIMP"
    cmdline = [GIMP_EXECUTABLE, '-i']
    if script:
        cmdline.extend(['-b', script])
    # Ensure GIMP always quits
    cmdline.extend(['-b', '(gimp-quit 0)'])
    process = subprocess.Popen(
        cmdline,
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False)
    # Read all the process' output but only print it if an error occurs.
    # Otherwise, we don't care about any warnings - just that GIMP launched and
    # quit successfully
    output = process.communicate()[0]
    if process.returncode != 0:
        for line in output.splitlines():
            logging.error(line.rstrip())
        raise Exception('GIMP script failed with return code %d - see '
            'above for further details' % process.returncode)

# We used to test-launch the GIMP executable here, but this was causing severe
# slow-downs on startup of various tools. Now instead we simply attempt to
# locate the executable and test the permissions would potentially allow us to
# execute it
if not any(
        True for path in os.environ['PATH'].split(os.pathsep)
        if os.path.exists(os.path.join(path, GIMP_EXECUTABLE))
        and os.access(os.path.join(path, GIMP_EXECUTABLE), os.X_OK)
    ):
    raise ImportError('Unable to find GIMP executable "{}" in PATH'.format(
        GIMP_EXECUTABLE))


class FigureCanvasXcf(FigureCanvasAgg):
    """A matplotlib canvas capable of writing GIMP images"""

    def print_xcf(self, filename_or_obj, *args, **kwargs):
        "Writes the figure to a GIMP XCF image file"
        # If filename_or_obj is a file-like object we need a temporary file for
        # GIMP's output too...
        if is_string(filename_or_obj):
            out_temp_handle, out_temp_name = None, filename_or_obj
        else:
            out_temp_handle, out_temp_name = tempfile.mkstemp(suffix='.xcf')
        try:
            # Create a temporary file and write the "layer" to it as a PNG
            in_temp_handle, in_temp_name = tempfile.mkstemp(suffix='.png')
            try:
                FigureCanvasAgg.print_png(self, in_temp_name, *args, **kwargs)
                run_gimp_script(
                    SINGLE_LAYER_SCRIPT.format(
                        input=quote_string(in_temp_name),
                        output=quote_string(out_temp_name)))
            finally:
                os.close(in_temp_handle)
                os.unlink(in_temp_name)
        finally:
            if out_temp_handle:
                os.close(out_temp_handle)
                # If we wrote the XCF to a temporary file, write its content to
                # the file-like object we were given (the copy is chunked as
                # XCF files can get pretty big)
                with open(out_temp_name, 'rb') as source:
                    for chunk in iter(lambda: source.read(131072), ''):
                        filename_or_obj.write(chunk)
                os.unlink(out_temp_name)


class XcfLayers(object):
    """Multi-writer class capable of producing layered GIMP images"""

    def __init__(self, filename):
        self.filename = filename
        self.width = None
        self.height = None
        self._layers = []

    def savefig(self, figure, **kwargs):
        "Saves a figure to a temporary file"
        temp_handle, temp_name = tempfile.mkstemp(suffix='.png')
        try:
            self._layers.append((temp_name, kwargs.get('title')))
            canvas = FigureCanvasAgg(figure)
            canvas.print_png(temp_name)
            # If we haven't yet figured out our width and height, do it now by
            # reading the image we just generated
            if self.width is None:
                img = Image.open(temp_name, 'r')
                self.width, self.height = img.size
        finally:
            os.close(temp_handle)

    def close(self):
        "Combines the written figuers into a multi-layer GIMP file"
        try:
            # If the output file already exists, remove it first to avoid GIMP
            # complaining
            try:
                os.unlink(self.filename)
            except OSError:
                pass
            run_gimp_script(
                MULTI_LAYER_SCRIPT.format(
                    layers=' '.join(
                        quote_string(s) for (s, _) in self._layers),
                    titles=' '.join(
                        quote_string(s) for (_, s) in self._layers),
                    width=self.width,
                    height=self.height,
                    output=quote_string(self.filename)))
        finally:
            # Remove all the temporary files we generated
            while self._layers:
                os.unlink(self._layers.pop()[0])


