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

import os
import sys
mswindows = sys.platform.startswith('win')
import tempfile
import subprocess
import logging
from PIL import Image
from matplotlib.backends.backend_agg import FigureCanvasAgg

GIMP_EXECUTABLE = 'gimp'

# Test launch the GIMP executable. We do this on import because without GIMP
# being available this entire module is basically useless!
try:
    p = subprocess.Popen([
        GIMP_EXECUTABLE, '-i', '-b', '(gimp-quit 0)'],
        stdin=None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        shell=False)
    # Read all the process' output but only print it if an error occurs.
    # Otherwise, we don't care about any warnings - just that GIMP launched and
    # quit successfully
    output = p.communicate()[0]
    if p.returncode != 0:
        for line in output.splitlines():
            logging.error(line.rstrip())
        raise Exception()
except:
    raise ImportError('Unable to test-launch GIMP executable "%s"' % GIMP_EXECUTABLE)


class FigureCanvasXcf(FigureCanvasAgg):
    def print_xcf(self, filename_or_obj, *args, **kwargs):
        # If filename_or_obj is a file-like object we need a temporary file for
        # GIMP's output too...
        if isinstance(filename_or_obj, basestring):
            out_temp_handle, out_temp_name = None, filename_or_obj
        else:
            out_temp_handle, out_temp_name = tempfile.mkstemp(suffix='.xcf')
        try:
            # Create a temporary file and write the "layer" to it as a PNG
            in_temp_handle, in_temp_name = tempfile.mkstemp(suffix='.png')
            try:
                FigureCanvasAgg.print_png(self, in_temp_name, *args, **kwargs)
                scheme = """\
(let*
  (
    (im (car (file-png-load RUN-NONINTERACTIVE "%(input)s" "%(input)s")))
    (layer (car (gimp-image-get-active-layer im)))
  )
  (gimp-file-save RUN-NONINTERACTIVE im layer "%(output)s" "%(output)s")
  (gimp-image-delete im)
)
""" % {'input': in_temp_name, 'output': out_temp_name}
                p = subprocess.Popen([
                    GIMP_EXECUTABLE,       # self-explanatory...
                    '-i',                  # run in non-interactive mode
                    '-b', scheme,          # run batch to generate layered XCF
                    '-b', '(gimp-quit 0)', # ensure we terminate GIMP afterward
                ], stdin=None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
                output = p.communicate()[0]
                # As with the test at the start, only log GIMP's output if an
                # error occurs - otherwise we don't care
                if p.returncode != 0:
                    for line in output.splitlines():
                        logging.error(line.rstrip())
                    raise Exception('GIMP XCF generation failed with return code %d - see above for further details' % p.returncode)
            finally:
                os.close(in_temp_handle)
                os.unlink(in_temp_name)
        finally:
            if out_temp_handle:
                os.close(out_temp_handle)
                # If we wrote the XCF to a temporary file, write its content to
                # the file-like object we were given
                # XXX What if it's a gigabyte file?!
                with open(out_temp_name, 'rb') as f:
                    filename_or_obj.write(f.read())
                os.unlink(out_temp_name)


class XcfLayers(object):
    def __init__(self, filename):
        self.filename = filename
        self.width = None
        self.height = None
        self._layers = []

    def close(self):
        try:
            # Use GIMP's batch mode with some Scheme to merge all the temporary
            # files into a single XCF image
            subst = {
                # XXX What about filenames that contain quotes?
                'layers': ' '.join('"%s"' % s for (s, _) in self._layers),
                'titles': ' '.join('"%s"' % s for (_, s) in self._layers),
                'width':  self.width,
                'height': self.height,
                'output': '"%s"' % self.filename
            }
            scheme = """\
(let*
  (
    (images '(%(layers)s))
    (titles '(%(titles)s))
    (im (car (gimp-image-new %(width)d %(height)d RGB)))
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
    (gimp-file-save RUN-NONINTERACTIVE im layer %(output)s %(output)s)
  )
  (gimp-image-delete im)
)
""" %subst
            # If the output file already exists, remove it first
            try:
                os.unlink(self.filename)
            except OSError:
                pass
            p = subprocess.Popen([
                GIMP_EXECUTABLE,       # self-explanatory...
                '-i',                  # run in non-interactive mode
                '-b', scheme,          # run batch to generate layered XCF
                '-b', '(gimp-quit 0)', # ensure we terminate GIMP afterward
            ], stdin=None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
            output = p.communicate()[0]
            # As with the test at the start, only log GIMP's output if an error
            # occurs - otherwise we don't care
            if p.returncode != 0:
                for line in output.splitlines():
                    logging.error(line.rstrip())
                raise Exception('GIMP XCF generation failed with return code %d - see above for further details' % p.returncode)
            # Check that the output file exists
            if not os.path.exists(self.filename):
                for line in output.splitlines():
                    logging.error(line.rstrip())
                raise IOError('GIMP succeeded but cannot find XCF file "%s" - see above for details' % self.filename)
        finally:
            # Remove all the temporary files we generated
            while self._layers:
                filename, name = self._layers.pop()
                os.unlink(filename)

    def savefig(self, figure, **kwargs):
        # Create a temporary file and write the "layer" to it as a PNG
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
