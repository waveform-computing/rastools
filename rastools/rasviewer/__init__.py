#!/usr/bin/env python

import sys
from PyQt4 import QtCore, QtGui, uic
from rastools.rasviewer.main_window import MainWindow

__version__ = '0.1'

WIN = None

def excepthook(type, value, tb):
    # XXX Need to expand this to display a complete stack trace and add an
    # e-mail option for bug reports
    QtGui.QMessageBox.critical(
        QtGui.QApplication.instance().activeWindow(),
        QtGui.QApplication.instance().desktop().tr('Error'), str(value))

def main(args=None):
    sys.excepthook = excepthook
    global WIN
    if args is None:
        args = sys.argv
    app = QtGui.QApplication(args)
    app.setApplicationName('rasviewer')
    app.setApplicationVersion(__version__)
    app.setOrganizationName('Waveform')
    app.setOrganizationDomain('waveform.org.uk')
    WIN = MainWindow()
    WIN.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
