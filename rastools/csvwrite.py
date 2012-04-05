#!/usr/bin/env python
# vim: set et sw=4 sts=4:

import csv

class CsvWriter(object):
    def __init__(self, filename_or_obj, channel):
        if isinstance(filename_or_obj, basestring):
            self._file = open(filename_or_obj, 'w')
        else:
            self._file = filename_or_obj
        self._writer = csv.writer(self._file, dialect='excel')

    def write(self, data):
        for row in data:
            self._writer.writerow(row)


class TsvWriter(CsvWriter):
    def __init__(self, filename_or_obj, channel):
        super(TsvWriter, self).__init__(filename_or_obj, channel)
        self._writer = csv.writer(self._file, dialect='excel-tab')
