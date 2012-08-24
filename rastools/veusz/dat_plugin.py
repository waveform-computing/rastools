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

"""Plugin supporting Sam's DAT file format as a 2D Veusz dataset"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

from veusz.plugins import (
    ImportPlugin,
    ImportDataset2D,
    importpluginregistry,
    )

from rastools.datparse import DatParser, Error

class ImportPluginDat(ImportPlugin):
    """A plugin supporting Sam's dat format"""

    name = "Sam's DAT import"
    author = 'Dave Hughes <dave@waveform.org.uk>'
    description = 'Reads the 2D channels from a dat file'
    file_extensions = set(['.DAT', '.dat'])

    def __init__(self):
        ImportPlugin.__init__(self)
        self.fields = []

    def getPreview(self, params):
        result = """\
File contains {count} channels: {names}
Channel resolution: {x_size} by {y_size}

Comments:
{comments}

"""
        try:
            reader = DatParser(params.filename)
            return (
                result.format(
                    count=sum(
                        1 for channel in reader.channels
                        if channel.enabled),
                    names=','.join(
                        channel.name for channel in reader.channels
                        if channel.enabled),
                    x_size=reader.x_size,
                    y_size=reader.y_size,
                    comments=reader.comments,
                ),
                True
            )
        except IOError as exc:
            return ('I/O error when opening file: {}'.format(exc), False)
        except Error as exc:
            return ('File does not appear to be a valid DAT file: {}'.format(exc), False)

    def doImport(self, params):
        reader = DatParser(params.filename)
        return [
            ImportDataset2D(channel.name, channel.data)
            for channel in reader.channels
        ]

importpluginregistry.append(ImportPluginDat)

