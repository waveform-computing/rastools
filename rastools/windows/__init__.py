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

"""Package for rastools GUI elements"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import sys
import os

from PyQt4 import QtCore, QtGui, uic


def get_ui_dir():
    "Returns the directory containing the *.ui Qt window definitions"
    if getattr(sys, 'frozen', None):
        result = os.path.join(os.path.dirname(sys.executable), 'rastools', 'windows')
    else:
        result = os.path.dirname(__file__)
    result = os.path.abspath(result)
    # Check the result is a directory and that it contains at least one .ui file
    if not os.path.isdir(result):
        raise ValueError('Expected %s to be a directory' % result)
    if not any(filename.endswith('.ui') for filename in os.listdir(result)):
        raise ValueError('UI directory %s does not contain any .ui files' % result)
    return result


def get_icon(icon_id):
    "Returns an icon from the system theme or our fallback theme if required"
    return QtGui.QIcon.fromTheme(icon_id,
        QtGui.QIcon(os.path.join(
            UI_DIR, 'fallback-theme', icon_id + '.png')))


UI_DIR = get_ui_dir()

