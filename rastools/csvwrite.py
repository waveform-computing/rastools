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

"""CSV/TSV writer module for rasdump and rasviewer"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import sys
import csv

class CsvWriter(object):
    "CSV writer class for rasdump"

    def __init__(self, filename_or_obj, channel):
        try:
            if sys.hexversion >= 0x03000000:
                # XXX Py3 only
                self._file = open(filename_or_obj, mode='w', newline='')
            else:
                # XXX Py2 only
                self._file = open(filename_or_obj, mode='wb')
        except TypeError:
            self._file = filename_or_obj
        self._writer = csv.writer(self._file, dialect='excel')

    def write(self, data):
        "Writes channel data as CSV"
        for row in data:
            self._writer.writerow(row)


class TsvWriter(CsvWriter):
    "Tab-separated writer class for rasdump"

    def __init__(self, filename_or_obj, channel):
        super(TsvWriter, self).__init__(filename_or_obj, channel)
        self._writer = csv.writer(self._file, dialect='excel-tab')
