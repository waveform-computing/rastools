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

"""Module implementing the rasviewer main window"""

from __future__ import (
    unicode_literals, print_function, absolute_import, division)

import os

from PyQt4 import QtCore, QtGui, uic

from rastools.rasviewer.open_dialog import OpenDialog
from rastools.rasviewer.mdi_window import MDIWindow


class MainWindow(QtGui.QMainWindow):
    "The rasviewer main window"

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = uic.loadUi(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    'main_window.ui'
                )), self)
        # Read configuration
        self.settings = QtCore.QSettings()
        self.settings.beginGroup('main_window')
        try:
            self.resize(
                self.settings.value(
                    'size', QtCore.QSize(640, 480)).toSize())
            self.move(
                self.settings.value(
                    'position', QtCore.QPoint(100, 100)).toPoint())
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
        self.ui.reset_zoom_action.triggered.connect(self.reset_zoom)
        self.ui.reset_origin_action.triggered.connect(self.reset_origin)
        self.ui.status_bar_action.triggered.connect(self.toggle_status)
        self.ui.view_menu.aboutToShow.connect(self.update_status)

    def close(self):
        "Called when the window is closed"
        super(MainWindow, self).close()
        self.settings.beginGroup('main_window')
        try:
            self.settings.setValue('size', self.size())
            self.settings.setValue('position', self.pos())
        finally:
            self.settings.endGroup()

    def open_file(self):
        "Handler for the File/Open action"
        dialog = OpenDialog(self)
        if dialog.exec_():
            window = None
            try:
                window = self.ui.mdi_area.addSubWindow(
                    MDIWindow(dialog.data_file, dialog.channel_file))
                window.show()
            except KeyboardInterrupt:
                if window is not None:
                    window.close()

    def close_file(self):
        "Handler for the File/Close action"
        self.ui.mdi_area.currentSubWindow().close()

    def reset_zoom(self):
        "Handler for the View/Reset Zoom action"
        self.ui.mdi_area.currentSubWindow().widget().reset_zoom()

    def reset_origin(self):
        "Handler for the View/Reset Origin action"
        self.ui.mdi_area.currentSubWindow().widget().reset_origin()
        pass

    def update_status(self):
        "Called to update the status_bar_action check state"
        self.ui.status_bar_action.setChecked(self.statusBar().isVisible())

    def toggle_status(self):
        "Handler for the View/Status Bar action"
        if self.statusBar().isVisible():
            self.statusBar().hide()
        else:
            self.statusBar().show()

    def about(self):
        "Handler for the Help/About action"
        QtGui.QMessageBox.about(self,
            str(self.tr('About {}')).format(
                QtGui.QApplication.instance().applicationName()),
            str(self.tr("""\
<b>{application}</b>
<p>Version {version}</p>
<p>{application} is a visual previewer for the content of .RAS and
.DAT files from the SSRL facility</p>
<p>Copyright 2012 Dave Hughes &lt;dave@waveform.org.uk&gt;</p>""")).format(
                application=QtGui.QApplication.instance().applicationName(),
                version=QtGui.QApplication.instance().applicationVersion(),
            ))

    def about_qt(self):
        "Handler for the Help/About Qt action"
        QtGui.QMessageBox.aboutQt(self, self.tr('About QT'))

    def export_image(self):
        "Handler for the File/Export Image action"
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            from rastools.image_writers import IMAGE_WRITERS
        finally:
            QtGui.QApplication.instance().restoreOverrideCursor()
        filters = ';;'.join(
            [
                str(self.tr('All images ({0})')).format(
                    ' '.join(
                        '*' + ext
                        for (_, exts, _, _, _) in IMAGE_WRITERS
                        for ext in exts))
            ] + [
                '{name} ({exts})'.format(
                    name=self.tr(label),
                    exts=' '.join('*' + ext for ext in exts))
                for (_, exts, label, _, _) in IMAGE_WRITERS
            ]
        )
        filename = QtGui.QFileDialog.getSaveFileName(
            self, self.tr('Export image'), os.getcwd(), filters)
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
                QtGui.QMessageBox.warning(
                    self, self.tr('Warning'),
                    str(self.tr('Unknown file extension "{0}"')).format(ext))
            else:
                fig = self.ui.mdi_area.currentSubWindow().widget().figure
                QtGui.QApplication.instance().setOverrideCursor(
                    QtCore.Qt.WaitCursor)
                try:
                    canvas = method.im_class(fig)
                    method(canvas, filename, dpi=fig.dpi)
                finally:
                    QtGui.QApplication.instance().restoreOverrideCursor()

    def export_channel(self):
        "Handler for the File/Export Channel action"
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            from rastools.data_writers import DATA_WRITERS
        finally:
            QtGui.QApplication.instance().restoreOverrideCursor()
        filters = ';;'.join(
            [
                str(self.tr('All data files ({0})')).format(
                    ' '.join(
                        '*' + ext
                        for (_, exts, _, _) in DATA_WRITERS
                        for ext in exts))
            ] + [
                '{name} ({exts})'.format(
                    name=self.tr(label),
                    exts=' '.join('*' + ext for ext in exts))
                for (_, exts, label, _) in DATA_WRITERS
            ]
        )
        filename = QtGui.QFileDialog.getSaveFileName(
            self, self.tr('Export channel'), os.getcwd(), filters)
        if filename:
            filename = str(filename)
            os.chdir(os.path.dirname(filename))
            ext = os.path.splitext(filename)[1]
            writers = dict(
                (ext, cls)
                for (cls, exts, _, _) in DATA_WRITERS
                for ext in exts
            )
            try:
                cls = writers[ext]
            except KeyError:
                QtGui.QMessageBox.warning(
                    self, self.tr('Warning'),
                    str(self.tr('Unknown file extension "{0}"')).format(ext))
            else:
                mdi_window = self.ui.mdi_area.currentSubWindow().widget()
                QtGui.QApplication.instance().setOverrideCursor(
                    QtCore.Qt.WaitCursor)
                try:
                    data = mdi_window.data_cropped
                    start, finish = mdi_window.percentile_range
                    data[data < start] = start
                    data[data > finish] = finish
                    cls(filename, mdi_window.channel).write(data)
                finally:
                    QtGui.QApplication.instance().restoreOverrideCursor()

    def export_document(self):
        "Handler for the File/Export Document action"
        # XXX Placeholder
        pass

    def window_changed(self, window):
        "Called when the MDI child window changes"
        self.ui.close_action.setEnabled(window is not None)
        self.ui.export_menu.setEnabled(window is not None)
        self.ui.export_image_action.setEnabled(window is not None)
        self.ui.export_channel_action.setEnabled(window is not None)
        self.ui.export_document_action.setEnabled(window is not None)
        self.ui.reset_zoom_action.setEnabled(window is not None)
        self.ui.reset_origin_action.setEnabled(window is not None)

