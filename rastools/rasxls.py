#!/usr/bin/env python
# vim: set et sw=4 sts=4:

import xlwt

class XlsWriter(object):
    def __init__(self, filename_or_obj, channel):
        self._file = filename_or_obj
        self._workbook = xlwt.Workbook()
        self._worksheet = self._workbook.add_sheet(channel.format('{channel} - {channel_name}'))

    def write(self, data):
        for r, row in enumerate(data):
            for c, cell in enumerate(row):
                self._worksheet.write(r, c, int(cell))
        self._workbook.save(self._file)

class XlsMulti(object):
    def __init__(self, filename_or_obj, ras_file):
        self._file = filename_or_obj
        self._workbook = xlwt.Workbook()

    def write_page(self, data, channel):
        ws = self._workbook.add_sheet(channel.format('{channel} - {channel_name}'))
        for r, row in enumerate(data):
            for c, cell in enumerate(row):
                ws.write(r, c, int(cell))

    def close(self):
        self._workbook.save(self._file)
