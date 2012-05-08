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

__all__ = ['DATA_WRITERS']

DATA_WRITERS = []

logging.info('Loading CSV renderer')
try:
    from rastools.csvwrite import CsvWriter, TsvWriter
except ImportError:
    # If we can't find the default CSV backend, something's seriously
    # wrong (it's built into python!)
    raise
else:
    DATA_WRITERS.extend([
        # class     extensions        description               multi-class
        (CsvWriter, ('.csv', '.CSV'), 'Comma Separated Values', None),
        (TsvWriter, ('.tsv', '.TSV'), 'Tab Separated Values',   None),
    ])

logging.info('Loading RAS support')
try:
    from rastools.raswrite import RasWriter, RasAsciiWriter, RasMultiWriter, RasAsciiMultiWriter
except ImportError:
    logging.warning('Failed to load RAS support')
else:
    DATA_WRITERS.extend([
        (RasWriter,      ('.ras', '.RAS'),     'QSCAN raster file',  RasMultiWriter),
        (RasAsciiWriter, ('.ras_a', '.RAS_A'), 'QSCAN ASCII output', RasAsciiMultiWriter),
    ])

logging.info('Loading Excel support')
try:
    from rastools.xlswrite import XlsWriter, XlsMulti
except ImportError:
    logging.warning('Failed to load Excel support')
else:
    DATA_WRITERS.extend([
        (XlsWriter, ('.xls', '.XLS'), 'Excel workbook', XlsMulti),
    ])
