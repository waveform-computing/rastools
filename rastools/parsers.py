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

__all__ = ['PARSERS']

PARSERS = []

logging.info('Loading RAS parser')
try:
    from rastools.rasparse import RasFileReader
except ImportError:
    logging.warning('Failed to load RAS parser')
else:
    PARSERS.extend([
        (RasFileReader, ('.ras', '.RAS'), 'QSCAN raster file'),
    ])

logging.info('Loading DAT parser')
try:
    from rastools.datparse import DatFileReader
except ImportError:
    logging.warning('Failed to load DAT parser')
else:
    PARSERS.extend([
        (DatFileReader, ('.dat', '.DAT'), "Sam's DAT file"),
    ])

