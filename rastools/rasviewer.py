#!/usr/bin/env python

import os
import sys
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt4 import QtCore, QtGui
from rastools.rasview_main import Ui_MainWindow
from rastools.rasview_open import Ui_OpenDialog
from rastools.rasparse import RasFileReader
from rastools.datparse import DatFileReader

__version__ = '0.1'


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Connect up actions to methods
        self.ui.about_action.triggered.connect(self.about)
        self.ui.about_qt_action.triggered.connect(self.about_qt)
        self.ui.open_action.triggered.connect(self.open)
        ## Create a test figure
        #self.dpi = 100.0
        #self.fig = Figure(figsize=(5.0, 4.0), dpi=self.dpi)
        #self.canvas = FigureCanvas(self.fig)
        #self.ui.plot_layout.addWidget(self.canvas)
        ## Draw a plot
        #ax = self.fig.add_subplot(111)
        #ax.plot([0, 1])

    def open(self):
        d = OpenDialog(self)
        if d.exec_():
            try:
                ext = os.path.splitext(d.data_file)[-1]
                if d.channel_file:
                    files = (d.data_file, d.channel_file)
                else:
                    files = (d.data_file,)
                f = None
                for cls in (RasFileReader, DatFileReader):
                    if ext in cls.ext:
                        f = cls(*files)
                        break
                if not f:
                    raise ValueError('Unrecognized file extension "%s"' % ext)
            except Exception, e:
                QtGui.QMessageBox.critical(self, 'Error', str(e))
                raise

    def about(self):
        QtGui.QMessageBox.about(self, 'About rasViewer',
            """<b>rasViewer</b>
            <p>Version %s</p> <p>rasViewer is a visual previewer for the
            content of .RAS and .DAT files from the SSRL facility</p>
            <p>Copyright 2012 Dave Hughes &lt;dave@waveform.org.uk&gt;</p>""" % __version__)

    def about_qt(self):
        QtGui.QMessageBox.aboutQt(self, 'About QT')


class OpenDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(OpenDialog, self).__init__(parent)
        self.ui = Ui_OpenDialog()
        self.ui.setupUi(self)
        self.ui.data_file_combo.editTextChanged.connect(self.data_file_changed)
        self.data_file_changed()

    @property
    def data_file(self):
        result = str(self.ui.data_file_combo.currentText())
        if result:
            return result
        else:
            return None

    @property
    def channel_file(self):
        result = str(self.ui.channel_file_combo.currentText())
        if result:
            return result
        else:
            return None

    def data_file_changed(self, value=None):
        if value is None:
            value = self.ui.data_file_combo.currentText()
        self.ui.button_box.button(QtGui.QDialogButtonBox.Ok).setEnabled(value != '')


def main(args=None):
    if args is None:
        args = sys.argv
    app = QtGui.QApplication(args)
    win = MainWindow()
    win.show()
    return app.exec_()

if __name__ == '__main__':
    main(sys.argv)
