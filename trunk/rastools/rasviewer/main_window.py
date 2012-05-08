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

import os
from PyQt4 import QtCore, QtGui, uic

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = uic.loadUi(os.path.abspath(os.path.join(os.path.dirname(__file__), 'main_window.ui')), self)
        # Read configuration
        self.settings = QtCore.QSettings()
        self.settings.beginGroup('main_window')
        try:
            self.resize(self.settings.value('size', QtCore.QSize(640, 480)).toSize())
            self.move(self.settings.value('position', QtCore.QPoint(100, 100)).toPoint())
        finally:
            self.settings.endGroup()
        # Configure status bar elements
        self.ui.x_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.x_label)
        self.ui.y_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.y_label)
        self.ui.value_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.value_label)
        # Connect up signals to methods
        self.ui.mdi_area.subWindowActivated.connect(self.window_changed)
        self.ui.about_action.triggered.connect(self.about)
        self.ui.about_qt_action.triggered.connect(self.about_qt)
        self.ui.open_action.triggered.connect(self.open_file)
        self.ui.close_action.triggered.connect(self.close_file)
        self.ui.export_image_action.triggered.connect(self.export_image)
        self.ui.export_channel_action.triggered.connect(self.export_channel)
        self.ui.export_document_action.triggered.connect(self.export_document)

    def close(self):
        super(MainWindow, self).close()
        self.settings.beginGroup('main_window')
        try:
            self.settings.setValue('size', self.size())
            self.settings.setValue('position', self.pos())
        finally:
            self.settings.endGroup()

    def open_file(self):
        from rastools.rasviewer.open_dialog import OpenDialog
        d = OpenDialog(self)
        if d.exec_():
            from rastools.rasviewer.mdi_window import MDIWindow
            w = self.ui.mdi_area.addSubWindow(MDIWindow(d.data_file, d.channel_file))
            w.show()

    def close_file(self):
        self.ui.mdi_area.currentSubWindow().close()

    def about(self):
        QtGui.QMessageBox.about(self,
            str(self.tr('About %s')) % QtGui.QApplication.instance().applicationName(),
            str(self.tr("""<b>%(application)s</b>
            <p>Version %(version)s</p>
            <p>%(application)s is a visual previewer for the content of .RAS and
            .DAT files from the SSRL facility</p>
            <p>Copyright 2012 Dave Hughes &lt;dave@waveform.org.uk&gt;</p>""")) % {
                'application': QtGui.QApplication.instance().applicationName(),
                'version':     QtGui.QApplication.instance().applicationVersion(),
            })

    def about_qt(self):
        QtGui.QMessageBox.aboutQt(self, self.tr('About QT'))

    def export_image(self):
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            from rastools.image_writers import IMAGE_WRITERS
        finally:
            QtGui.QApplication.instance().restoreOverrideCursor()
        filters = ';;'.join(
            [
                str(self.tr('All images (%s)')) % ' '.join('*' + ext for (_, exts, _, _, _) in IMAGE_WRITERS for ext in exts)
            ] + [
                '%s (%s)' % (self.tr(label), ' '.join('*' + ext for ext in exts))
                for (_, exts, label, _, _) in IMAGE_WRITERS
            ]
        )
        filename = QtGui.QFileDialog.getSaveFileName(self, self.tr('Export image'), os.getcwd(), filters)
        if filename:
            filename = str(filename)
            os.chdir(os.path.dirname(filename))
            ext = os.path.splitext(filename)[1]
            writers = dict(
                (ext, method)
                for (method, exts, _, _, _) in IMAGE_WRITERS
                for ext in exts
            )
            try:
                method = writers[ext]
            except KeyError:
                QtGui.QMessageBox.warning(self, self.tr('Warning'), str(self.tr('Unknown file extension "%s"')) % ext)
            fig = self.ui.mdi_area.currentSubWindow().widget().figure
            QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                canvas = method.im_class(fig)
                method(canvas, filename, dpi=fig.dpi)
            finally:
                QtGui.QApplication.instance().restoreOverrideCursor()

    def export_channel(self):
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            from rastools.data_writers import DATA_WRITERS
        finally:
            QtGui.QApplication.instance().restoreOverrideCursor()
        filters = ';;'.join(
            [
                str(self.tr('All data files (%s)')) % ' '.join('*' + ext for (_, exts, _, _) in DATA_WRITERS for ext in exts)
            ] + [
                '%s (%s)' % (self.tr(label), ' '.join('*' + ext for ext in exts))
                for (_, exts, label, _) in DATA_WRITERS
            ]
        )
        filename = QtGui.QFileDialog.getSaveFileName(self, self.tr('Export channel'), os.getcwd(), filters)
        if filename:
            filename = str(filename)
            os.chdir(os.path.dirname(filename))
            ext = os.path.splitext(filename)[1]
            writers = dict(
                (ext, klass)
                for (klass, exts, _, _) in DATA_WRITERS
                for ext in exts
            )
            try:
                klass = writers[ext]
            except KeyError:
                QtGui.QMessageBox.warning(self, self.tr('Warning'), str(self.tr('Unknown file extension "%s"')) % ext)
            mdi_window = self.ui.mdi_area.currentSubWindow().widget()
            QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                data = mdi_window.data_cropped
                start, finish = mdi_window.percentile_range
                data[data < start] = start
                data[data > finish] = finish
                klass(filename, mdi_window.channel).write(data)
            finally:
                QtGui.QApplication.instance().restoreOverrideCursor()

    def export_document(self):
        # XXX Placeholder
        pass

    def window_changed(self, window):
        self.ui.close_action.setEnabled(window is not None)
        self.ui.export_menu.setEnabled(window is not None)
        self.ui.export_image_action.setEnabled(window is not None)
        self.ui.export_channel_action.setEnabled(window is not None)
        self.ui.export_document_action.setEnabled(window is not None)

