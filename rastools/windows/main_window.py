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
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os

from PyQt4 import QtCore, QtGui, uic

from rastools.rasviewer.open_dialog import OpenDialog
from rastools.rasviewer.single_layer_window import SingleLayerWindow
from rastools.rasviewer.multi_layer_window import MultiLayerWindow
#from rastools.rasviewer.figure_canvas import FigureCanvas


MODULE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_icon(icon_id):
    "Returns an icon from the system theme or our fallback theme if required"
    return QtGui.QIcon.fromTheme(icon_id,
        QtGui.QIcon(os.path.join(
            MODULE_DIR, 'fallback-theme', icon_id + '.png')))


class MainWindow(QtGui.QMainWindow):
    "The rasviewer main window"

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = uic.loadUi(os.path.join(MODULE_DIR, 'main_window.ui'), self)
        # Read configuration
        self.settings = QtCore.QSettings()
        self.settings.beginGroup('main_window')
        try:
            self.resize(
                self.settings.value(
                    'size', QtCore.QSize(640, 480)))
            self.move(
                self.settings.value(
                    'position', QtCore.QPoint(100, 100)))
        finally:
            self.settings.endGroup()
        # Configure status bar elements
        self.ui.x_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.x_label)
        self.ui.y_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.y_label)
        self.ui.value_label = QtGui.QLabel('')
        self.ui.red_label = self.ui.value_label
        self.statusBar().addWidget(self.ui.value_label)
        self.ui.green_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.green_label)
        self.ui.blue_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.blue_label)
        # Connect up signals to methods
        self.ui.mdi_area.subWindowActivated.connect(self.window_changed)
        self.ui.quit_action.setIcon(get_icon('application-exit'))
        self.ui.about_action.triggered.connect(self.about)
        self.ui.about_action.setIcon(get_icon('help-about'))
        self.ui.about_qt_action.triggered.connect(self.about_qt)
        self.ui.about_qt_action.setIcon(get_icon('help-about'))
        self.ui.open_action.setIcon(get_icon('document-open'))
        self.ui.open_action.triggered.connect(self.open_file)
        self.ui.close_action.setIcon(get_icon('window-close'))
        self.ui.close_action.triggered.connect(self.close_file)
        self.ui.export_image_action.setIcon(get_icon('image-x-generic'))
        self.ui.export_image_action.triggered.connect(self.export_image)
        self.ui.export_channel_action.setIcon(get_icon('text-x-generic'))
        self.ui.export_channel_action.triggered.connect(self.export_channel)
        self.ui.export_document_action.setIcon(get_icon('x-office-document'))
        self.ui.export_document_action.triggered.connect(self.export_document)
        self.ui.print_action.setIcon(get_icon('document-print'))
        self.ui.print_action.triggered.connect(self.print_file)
        self.ui.zoom_in_action.setIcon(get_icon('zoom-in'))
        self.ui.zoom_in_action.triggered.connect(self.zoom_in)
        self.ui.zoom_out_action.setIcon(get_icon('zoom-out'))
        self.ui.zoom_out_action.triggered.connect(self.zoom_out)
        self.ui.reset_zoom_action.setIcon(get_icon('zoom-original'))
        self.ui.reset_zoom_action.triggered.connect(self.reset_zoom)
        self.ui.reset_axes_action.setIcon(get_icon('reset-axes'))
        self.ui.reset_axes_action.triggered.connect(self.reset_axes)
        self.ui.home_axes_action.setIcon(get_icon('home-axes'))
        self.ui.home_axes_action.triggered.connect(self.home_axes)
        self.ui.zoom_mode_action.setIcon(get_icon('zoom-mode'))
        self.ui.zoom_mode_action.triggered.connect(self.zoom_mode)
        self.ui.pan_mode_action.setIcon(get_icon('pan-mode'))
        self.ui.pan_mode_action.triggered.connect(self.pan_mode)
        self.ui.status_bar_action.triggered.connect(self.toggle_status)
        self.ui.view_menu.aboutToShow.connect(self.update_status)

    @property
    def sub_widget(self):
        "Returns the widget shown in the current sub-window"
        if self.ui.mdi_area.currentSubWindow():
            return self.ui.mdi_area.currentSubWindow().widget()
        else:
            return None

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
                if dialog.multi_layer:
                    window = self.ui.mdi_area.addSubWindow(
                        MultiLayerWindow(dialog.data_file, dialog.channel_file))
                else:
                    window = self.ui.mdi_area.addSubWindow(
                        SingleLayerWindow(dialog.data_file, dialog.channel_file))
                window.show()
                window.widget().cropChanged.connect(self.crop_changed)
            except KeyboardInterrupt:
                if window is not None:
                    window.close()

    def close_file(self):
        "Handler for the File/Close action"
        self.ui.mdi_area.currentSubWindow().close()

    def print_file(self):
        "Handler for the File/Print action"
        # Construct a printer and a dialog to configure it
        printer = QtGui.QPrinter(QtGui.QPrinter.HighResolution)
        dialog = QtGui.QPrintDialog(printer, self)
        dialog.setOptions(
            QtGui.QAbstractPrintDialog.PrintToFile |
            QtGui.QAbstractPrintDialog.PrintShowPageSize)
        if dialog.exec_():
            QtGui.QApplication.instance().setOverrideCursor(
                QtCore.Qt.WaitCursor)
            try:
                # Save the existing image size and DPI and construct a painter
                # to draw onto the printer
                save_dpi = self.sub_widget.figure.get_dpi()
                save_size = self.sub_widget.canvas.size()
                painter = QtGui.QPainter()
                painter.begin(printer)
                try:
                    # Set the image size and DPI to the printer and call the
                    # redraw_figure() method to refresh the bounding boxes
                    self.sub_widget.figure.set_dpi(printer.resolution())
                    self.sub_widget.canvas.resize(printer.pageRect().size())
                    self.sub_widget.redraw_figure()
                    # Center the image on the page and render it
                    painter.translate(
                        printer.paperRect().x() + printer.pageRect().width() / 2,
                        printer.paperRect().y() + printer.pageRect().height() / 2)
                    painter.translate(
                        -self.sub_widget.canvas.width() / 2,
                        -self.sub_widget.canvas.height() / 2)
                    self.sub_widget.canvas.render(painter)
                finally:
                    painter.end()
                    # Restore everything we tweaked for printing
                    self.sub_widget.figure.set_dpi(save_dpi)
                    self.sub_widget.canvas.resize(save_size)
                    self.sub_widget.redraw_figure()
            finally:
                QtGui.QApplication.instance().restoreOverrideCursor()

    def zoom_in(self):
        "Handler for the View/Zoom In action"
        self.sub_widget.zoom_in()

    def zoom_out(self):
        "Handler for the View/Zoom Out action"
        self.sub_widget.zoom_out()

    def reset_zoom(self):
        "Handler for the View/Reset Zoom action"
        self.sub_widget.reset_zoom()

    def reset_axes(self):
        "Handler for the View/Reset Axes action"
        self.sub_widget.reset_axes()

    def home_axes(self):
        "Handler for the View/Home Axes action"
        self.sub_widget.home_axes()

    def zoom_mode(self):
        "Handler for the View/Zoom Mode action"
        self.ui.zoom_mode_action.setChecked(True)
        self.ui.pan_mode_action.setChecked(False)

    def pan_mode(self):
        "Handler for the View/Pan Mode action"
        self.ui.zoom_mode_action.setChecked(False)
        self.ui.pan_mode_action.setChecked(True)

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
.DAT files from the SSRL facility. Project homepage is at
<a href="http://www.waveform.org.uk/trac/rastools/">http://www.waveform.org.uk/trac/rastools/</a></p>
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
        # Build a map of filter string labels to (method, default_ext)
        filter_map = dict(
            ('{name} ({exts})'.format(
                name=self.tr(label),
                exts=' '.join('*' + ext for ext in exts)),
                (cls, method, exts[0]))
            for (cls, method, exts, label, _, _) in IMAGE_WRITERS
        )
        # Construct the filter list by prefixing the list with an "All images"
        # entry which includes all possible extensions
        filters = ';;'.join(
            [
                str(self.tr('All images ({0})')).format(
                    ' '.join(
                        '*' + ext
                        for (_, _, exts, _, _, _) in IMAGE_WRITERS
                        for ext in exts))
            ] + sorted(filter_map.keys())
        )
        # Use the new getSaveFileNameAndFilter method to retrieve both the
        # filename and the filter the user selected
        (filename, filter_) = QtGui.QFileDialog.getSaveFileNameAndFilter(
            self, self.tr('Export image'), os.getcwd(), filters)
        if filename:
            filename = str(filename)
            filter_ = str(filter_)
            os.chdir(os.path.dirname(filename))
            ext = os.path.splitext(filename)[1]
            if ext:
                # If the user has explicitly specified an extension then lookup
                # the method associated with the extension (if any)
                writers = dict(
                    (ext, (cls, method))
                    for (cls, method, exts, _, _, _) in IMAGE_WRITERS
                    for ext in exts
                )
                try:
                    cls, method = writers[ext]
                except KeyError:
                    QtGui.QMessageBox.warning(
                        self, self.tr('Warning'),
                        str(self.tr('Unknown file extension "{0}"')).format(ext))
                    return
            else:
                # Otherwise, use the filter label map we built earlier to
                # lookup the selected filter string and retrieve the default
                # extension which we append to the filename
                (cls, method, ext) = filter_map[filter_]
                filename = filename + ext
            fig = self.sub_widget.figure
            QtGui.QApplication.instance().setOverrideCursor(
                QtCore.Qt.WaitCursor)
            try:
                canvas = cls(fig)
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
        # See export_image above for commentary on this map
        filter_map = dict(
            ('{name} ({exts})'.format(
                    name=self.tr(label),
                    exts=' '.join('*' + ext for ext in exts)),
                (cls, exts[0]))
            for (cls, exts, label, _) in DATA_WRITERS
        )
        filters = ';;'.join(
            [
                str(self.tr('All data files ({0})')).format(
                    ' '.join(
                        '*' + ext
                        for (_, exts, _, _) in DATA_WRITERS
                        for ext in exts))
            ] + sorted(filter_map.keys())
        )
        (filename, filter_) = QtGui.QFileDialog.getSaveFileNameAndFilter(
            self, self.tr('Export channel'), os.getcwd(), filters)
        if filename:
            filename = str(filename)
            filter_ = str(filter_)
            os.chdir(os.path.dirname(filename))
            ext = os.path.splitext(filename)[1]
            if ext:
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
                return
            else:
                (cls, ext) = filter_map[filter_]
                filename = filename + ext
            QtGui.QApplication.instance().setOverrideCursor(
                QtCore.Qt.WaitCursor)
            try:
                data = self.sub_widget.data_cropped
                start, finish = self.sub_widget.data_range
                data[data < start] = start
                data[data > finish] = finish
                cls(filename, self.sub_widget.channel).write(data)
            finally:
                QtGui.QApplication.instance().restoreOverrideCursor()

    def export_document(self):
        "Handler for the File/Export Document action"
        # XXX Placeholder
        pass

    def crop_changed(self):
        "Called when the crop in a sub-window changes"
        self.update_actions()

    def window_changed(self, window):
        "Called when the MDI child window changes"
        self.update_actions()

    def update_actions(self):
        "Called to update the main window actions"
        self.ui.print_action.setEnabled(self.sub_widget is not None)
        self.ui.close_action.setEnabled(self.sub_widget is not None)
        self.ui.export_menu.setEnabled(self.sub_widget is not None)
        self.ui.export_image_action.setEnabled(self.sub_widget is not None)
        self.ui.export_channel_action.setEnabled(self.sub_widget is not None)
        #self.ui.export_document_action.setEnabled(self.sub_widget is not None)
        self.ui.zoom_in_action.setEnabled(self.sub_widget is not None and self.sub_widget.can_zoom_in)
        self.ui.zoom_out_action.setEnabled(self.sub_widget is not None and self.sub_widget.can_zoom_out)
        self.ui.reset_zoom_action.setEnabled(self.sub_widget is not None and self.sub_widget.can_zoom_out)
        self.ui.reset_axes_action.setEnabled(self.sub_widget is not None)
        self.ui.home_axes_action.setEnabled(self.sub_widget is not None)
        self.ui.zoom_mode_action.setEnabled(self.sub_widget is not None)
        self.ui.pan_mode_action.setEnabled(self.sub_widget is not None)

