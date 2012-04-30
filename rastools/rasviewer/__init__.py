#!/usr/bin/env python
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

import sys
import logging
from PyQt4 import QtCore, QtGui, uic
from rastools.main import __version__

def excepthook(type, value, tb):
    # XXX Need to expand this to display a complete stack trace and add an
    # e-mail option for bug reports
    QtGui.QMessageBox.critical(
        QtGui.QApplication.instance().activeWindow(),
        QtGui.QApplication.instance().desktop().tr('Error'),
        str(value))

def main(args=None):
    if args is None:
        args = sys.argv
    app = QtGui.QApplication(args)
    app.setApplicationName('rasviewer')
    app.setApplicationVersion(__version__)
    app.setOrganizationName('Waveform')
    app.setOrganizationDomain('waveform.org.uk')
    app.setOverrideCursor(QtCore.Qt.WaitCursor)
    try:
        from rastools.rasviewer.main_window import MainWindow
    finally:
        app.restoreOverrideCursor()
    win = MainWindow()
    win.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
