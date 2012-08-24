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

"""Plugin supporting the RAS file format as a 2D Veusz dataset"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

from veusz.plugins import (
    ImportPlugin,
    ImportDataset2D,
    FieldFilename,
    importpluginregistry,
    )

from rastools.rasparse import RasParser, Error

class ImportPluginRas(ImportPlugin):
    """A plugin supporting the QSCAN RAS format"""

    name = 'QSCAN RAS import'
    author = 'Dave Hughes <dave@waveform.org.uk>'
    description = 'Reads the 2D channels from a QSCAN RAS file'
    file_extensions = set(['.RAS', '.ras'])

    def __init__(self):
        ImportPlugin.__init__(self)
        self.fields = [
            FieldFilename('channels', descr='Channels file (optional)'),
        ]

    def getPreview(self, params):
        if params.field_results.get('channels'):
            result = """\
File contains {count} enabled channels: {names}
"""
        else:
            result = """\
File contains {count} channels: {names}
If you wish to disable/rename channels, select a channels file in the box
below and re-select the main data-file to update this display.
"""
        result += """\
Channel resolution: {x_size} by {y_size}

Comments:
{comments}

"""
        try:
            reader = RasParser(params.filename,
                params.field_results.get('channels'))
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
                    comments=reader.comments),
                True
            )
        except IOError as exc:
            return ('I/O error when opening file: {}'.format(exc), False)
        except Error as exc:
            return ('File does not appear to be a valid RAS file: {}'.format(exc), False)

    def doImport(self, params):
        reader = RasParser(params.filename,
            params.field_results.get('channels'))
        return [
            ImportDataset2D(channel.name, channel.data)
            for channel in reader.channels
            if channel.enabled
        ]

importpluginregistry.append(ImportPluginRas)
