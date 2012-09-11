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

"""Microsoft Excel writer module for rasdump and rasviewer"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import xlwt

class XlsWriter(object):
    "Single-sheet writer class for Microsoft Excel output"

    def __init__(self, filename_or_obj, channel):
        if channel.parent.x_size > 256:
            raise ValueError('Data has too many columns to fit in an Excel '
                'spreadsheet (%d)' % channel.parent.x_size)
        self._file = filename_or_obj
        self._workbook = xlwt.Workbook()
        self._worksheet = self._workbook.add_sheet(
            '{channel} - {channel_name}'.format(**channel.format_dict()))

    def write(self, data):
        "Writes channel data to the first workbook sheet"
        for row_num, row in enumerate(data):
            for col_num, cell in enumerate(row):
                self._worksheet.write(row_num, col_num, int(cell))
        self._workbook.save(self._file)

class XlsMulti(object):
    "Multi-sheet writer class for Microsoft Excel output"

    def __init__(self, filename_or_obj, data_file):
        if data_file.x_size > 256:
            raise ValueError('Data has too many columns to fit in an Excel '
                'spreadsheet (%d)' % data_file.x_size)
        self._file = filename_or_obj
        self._workbook = xlwt.Workbook()

    def write_page(self, data, channel):
        "Writes channel data to a new workbook sheet"
        sheet = self._workbook.add_sheet(
            '{channel} - {channel_name}'.format(**channel.format_dict()))
        for row_num, row in enumerate(data):
            for col_num, cell in enumerate(row):
                sheet.write(row_num, col_num, int(cell))

    def close(self):
        "Finalizes the workbook and closes the file"
        self._workbook.save(self._file)
