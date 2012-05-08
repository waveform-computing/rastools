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
import time
import numpy as np
import datetime as dt
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.cm
import matplotlib.image
from PyQt4 import QtCore, QtGui, uic
from collections import namedtuple

import sys
import traceback as tb

DEFAULT_COLORMAP = 'gray'
DEFAULT_INTERPOLATION = 'nearest'
FIGURE_DPI = 72.0
COMPOSITION_SUPPORTED = True

Coord = namedtuple('Coord', ('x', 'y'))

class FigureCanvas(FigureCanvasQTAgg):
    def paintEvent(self, e):
        global COMPOSITION_SUPPORTED
        if self.drawRect:
            self.drawRect = False
            super(FigureCanvas, self).paintEvent(e)
            p = QtGui.QPainter(self)
            p.setPen(QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine))
            if COMPOSITION_SUPPORTED:
                p.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
                COMPOSITION_SUPPORTED = (p.compositionMode() == QtGui.QPainter.CompositionMode_Difference)
            p.drawRect(self.rect[0], self.rect[1], self.rect[2], self.rect[3])
            p.end()
        else:
            super(FigureCanvas, self).paintEvent(e)

class MDIWindow(QtGui.QWidget):
    def __init__(self, data_file, channel_file):
        super(MDIWindow, self).__init__(None)
        self.ui = uic.loadUi(os.path.abspath(os.path.join(os.path.dirname(__file__), 'mdi_window.ui')), self)
        self._file = None
        self._data = None
        self._data_cropped = None
        self._data_sorted = None
        self._progress = 0
        self._progress_update = None
        self._info_dialog = None
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            from rastools.parsers import PARSERS
        finally:
            QtGui.QApplication.instance().restoreOverrideCursor()
        # Open the selected file
        try:
            ext = os.path.splitext(data_file)[-1]
            if channel_file:
                files = (data_file, channel_file)
            else:
                files = (data_file,)
            parsers = dict(
                (ext, klass)
                for (klass, exts, _) in PARSERS
                for ext in exts
            )
            try:
                self._file = parsers[ext](*files, progress=(
                    self.progress_start,
                    self.progress_update,
                    self.progress_finish,
                ))
            except KeyError:
                raise ValueError(self.tr('Unrecognized file extension "%s"') % ext)
        except Exception, e:
            QtGui.QMessageBox.critical(self, self.tr('Error'), str(e))
            self.close()
            return
        # Create a figure in a tab for the file
        self.figure = Figure(figsize=(5.0, 4.0), dpi=FIGURE_DPI,
            facecolor='w', edgecolor='w')
        self.canvas = FigureCanvas(self.figure)
        self.image_axes = self.figure.add_axes((0.1, 0.1, 0.8, 0.8))
        self.histogram_axes = None
        self.colorbar_axes = None
        self.title_axes = None
        self.ui.splitter.addWidget(self.canvas)
        # Fill out the combos
        for channel in self._file.channels:
            if channel.enabled:
                if channel.name:
                    self.ui.channel_combo.addItem(unicode(self.tr('Channel %d - %s')) % (channel.index, channel.name), channel)
                else:
                    self.ui.channel_combo.addItem(unicode(self.tr('Channel %d')) % channel.index, channel)
        default = -1
        for color in sorted(matplotlib.cm.datad):
            if not color.endswith('_r'):
                if color == DEFAULT_COLORMAP:
                    default = self.ui.colormap_combo.count()
                self.ui.colormap_combo.addItem(color)
        self.ui.colormap_combo.setCurrentIndex(default)
        default = -1
        for interpolation in sorted(matplotlib.image.AxesImage._interpd):
            if interpolation == DEFAULT_INTERPOLATION:
                default = self.ui.interpolation_combo.count()
            self.ui.interpolation_combo.addItem(interpolation)
        self.ui.interpolation_combo.setCurrentIndex(default)
        # Set up the limits of the crop spinners
        self.ui.crop_left_spinbox.setRange(0, self._file.x_size - 1)
        self.ui.crop_right_spinbox.setRange(0, self._file.x_size - 1)
        self.ui.crop_top_spinbox.setRange(0, self._file.y_size - 1)
        self.ui.crop_bottom_spinbox.setRange(0, self._file.y_size - 1)
        # Set up the event connections and a timer to handle delayed redrawing
        self.redraw_timer = QtCore.QTimer()
        self.redraw_timer.setInterval(200)
        self.redraw_timer.timeout.connect(self.redraw_timeout)
        self.ui.channel_combo.currentIndexChanged.connect(self.channel_changed)
        self.ui.colormap_combo.currentIndexChanged.connect(self.invalidate_image)
        self.ui.reverse_check.toggled.connect(self.invalidate_image)
        self.ui.interpolation_combo.currentIndexChanged.connect(self.invalidate_image)
        self.ui.crop_top_spinbox.valueChanged.connect(self.crop_changed)
        self.ui.crop_left_spinbox.valueChanged.connect(self.crop_changed)
        self.ui.crop_right_spinbox.valueChanged.connect(self.crop_changed)
        self.ui.crop_bottom_spinbox.valueChanged.connect(self.crop_changed)
        self.ui.crop_reset_button.clicked.connect(self.crop_reset_clicked)
        self.ui.axes_check.toggled.connect(self.invalidate_image)
        self.ui.x_label_edit.textChanged.connect(self.invalidate_image)
        self.ui.y_label_edit.textChanged.connect(self.invalidate_image)
        self.ui.x_scale_spinbox.valueChanged.connect(self.x_scale_changed)
        self.ui.y_scale_spinbox.valueChanged.connect(self.y_scale_changed)
        self.ui.x_offset_spinbox.valueChanged.connect(self.x_offset_changed)
        self.ui.y_offset_spinbox.valueChanged.connect(self.y_offset_changed)
        self.ui.grid_check.toggled.connect(self.invalidate_image)
        self.ui.histogram_check.toggled.connect(self.invalidate_image)
        self.ui.histogram_bins_spinbox.valueChanged.connect(self.invalidate_image)
        self.ui.colorbar_check.toggled.connect(self.invalidate_image)
        self.ui.title_edit.textChanged.connect(self.invalidate_image)
        self.ui.default_title_button.clicked.connect(self.default_title_clicked)
        self.ui.clear_title_button.clicked.connect(self.clear_title_clicked)
        self.ui.title_info_button.clicked.connect(self.title_info_clicked)
        QtGui.QApplication.instance().focusChanged.connect(self.focus_changed)
        self.press_id = self.canvas.mpl_connect('button_press_event', self.canvas_press)
        self.release_id = self.canvas.mpl_connect('button_release_event', self.canvas_release)
        self.motion_id = self.canvas.mpl_connect('motion_notify_event', self.canvas_motion)
        self.zoom_id = None
        self.setWindowTitle(os.path.basename(data_file))
        self.channel_changed()

    def canvas_motion(self, event):
        if self.image_axes and (event.inaxes == self.image_axes) and (event.xdata is not None):
            self.window().ui.x_label.setText('X: %.2f' % event.xdata)
            self.window().ui.y_label.setText('Y: %.2f' % event.ydata)
            try:
                self.window().ui.value_label.setText('Value: %.2f' % self.data[event.ydata, event.xdata])
            except IndexError:
                self.window().ui.value_label.setText('')
            self.canvas.setCursor(QtCore.Qt.CrossCursor)
        else:
            self.window().ui.x_label.setText('')
            self.window().ui.y_label.setText('')
            self.window().ui.value_label.setText('')
            self.canvas.setCursor(QtCore.Qt.ArrowCursor)

    def canvas_press(self, event):
        if event.button != 1:
            return
        if event.inaxes != self.image_axes:
            return
        self.zoom_start = Coord(event.x, event.y)
        self.zoom_id = self.canvas.mpl_connect('motion_notify_event', self.canvas_zoom_motion)

    def canvas_zoom_motion(self, event):
        # Calculate the display coordinates of the selection
        box_left, box_top, box_right, box_bottom = self.image_axes.bbox.extents
        height = self.figure.bbox.height
        band_left   = max(min(self.zoom_start.x, event.x), box_left)
        band_right  = min(max(self.zoom_start.x, event.x), box_right)
        band_top    = max(min(self.zoom_start.y, event.y), box_top)
        band_bottom = min(max(self.zoom_start.y, event.y), box_bottom)
        self.canvas.drawRectangle((
            band_left,
            height - band_top,
            band_right - band_left,
            band_top - band_bottom,
        ))
        # Calculate the data coordinates of the selection. Note that top and
        # bottom and reversed by this conversion
        inverse = self.image_axes.transData.inverted()
        height = self._file.y_size
        data_left, data_bottom = inverse.transform_point((band_left, band_top))
        data_right, data_top = inverse.transform_point((band_right, band_bottom))
        self.zoom_coords = (data_left, data_top, data_right, data_bottom)
        self.window().statusBar().showMessage(
            self.tr('Crop from (%d, %d) to (%d, %d)' % (
                data_left,
                data_top,
                data_right,
                data_bottom,
            ))
        )

    def canvas_release(self, event):
        if self.zoom_id:
            self.canvas.mpl_disconnect(self.zoom_id)
            self.zoom_id = None
            (
                data_left,
                data_top,
                data_right,
                data_bottom,
            ) = self.zoom_coords
            self.ui.crop_left_spinbox.setValue(data_left)
            self.ui.crop_top_spinbox.setValue(data_top)
            self.ui.crop_right_spinbox.setValue(self._file.x_size - data_right)
            self.ui.crop_bottom_spinbox.setValue(self._file.y_size - data_bottom)
            self.window().statusBar().clearMessage()
            self.canvas.draw()

    def focus_changed(self, old_widget, new_widget):
        percentile_controls = (
            self.ui.percentile_from_slider,
            self.ui.percentile_from_spinbox,
            self.ui.percentile_to_slider,
            self.ui.percentile_to_spinbox,
        )
        range_controls = (
            self.ui.value_from_slider,
            self.ui.value_from_spinbox,
            self.ui.value_to_slider,
            self.ui.value_to_spinbox,
        )
        if (old_widget not in percentile_controls) and (new_widget in percentile_controls):
            self.percentile_connect()
        elif (old_widget in percentile_controls) and (new_widget not in percentile_controls):
            self.percentile_disconnect()
        if (old_widget not in range_controls) and (new_widget in range_controls):
            self.range_connect()
        elif (old_widget in range_controls) and (new_widget not in range_controls):
            self.range_disconnect()

    def progress_start(self):
        self._progress = 0
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        # The following test is necessary as the progress update can be called
        # before the MDI widget is attached to the main window
        if hasattr(self.window(), 'statusBar'):
            self.window().statusBar().showMessage('Loading channel data')

    def progress_update(self, progress):
        now = time.time()
        if (self._progress_update is None) or (now - self._progress_update) > 0.2:
            self._progress_update = now
            if progress != self._progress:
                if hasattr(self.window(), 'statusBar'):
                    self.window().statusBar().showMessage('Loading channel data... %d%%' % progress)
                self._progress = progress

    def progress_finish(self):
        if hasattr(self.window(), 'statusBar'):
            self.window().statusBar().clearMessage()
        QtGui.QApplication.instance().restoreOverrideCursor()

    def percentile_connect(self):
        self.ui.percentile_from_slider.valueChanged.connect(self.percentile_from_slider_changed)
        self.ui.percentile_from_spinbox.valueChanged.connect(self.percentile_from_spinbox_changed)
        self.ui.percentile_to_slider.valueChanged.connect(self.percentile_to_slider_changed)
        self.ui.percentile_to_spinbox.valueChanged.connect(self.percentile_to_spinbox_changed)

    def percentile_disconnect(self):
        self.ui.percentile_from_slider.valueChanged.disconnect(self.percentile_from_slider_changed)
        self.ui.percentile_from_spinbox.valueChanged.disconnect(self.percentile_from_spinbox_changed)
        self.ui.percentile_to_slider.valueChanged.disconnect(self.percentile_to_slider_changed)
        self.ui.percentile_to_spinbox.valueChanged.disconnect(self.percentile_to_spinbox_changed)

    def range_connect(self):
        self.ui.value_from_slider.valueChanged.connect(self.value_from_slider_changed)
        self.ui.value_from_spinbox.valueChanged.connect(self.value_from_spinbox_changed)
        self.ui.value_to_slider.valueChanged.connect(self.value_to_slider_changed)
        self.ui.value_to_spinbox.valueChanged.connect(self.value_to_spinbox_changed)

    def range_disconnect(self):
        self.ui.value_from_slider.valueChanged.disconnect(self.value_from_slider_changed)
        self.ui.value_from_spinbox.valueChanged.disconnect(self.value_from_spinbox_changed)
        self.ui.value_to_slider.valueChanged.disconnect(self.value_to_slider_changed)
        self.ui.value_to_spinbox.valueChanged.disconnect(self.value_to_spinbox_changed)

    def percentile_from_slider_changed(self, value):
        self.ui.percentile_to_spinbox.setMinimum(value / 100.0)
        self.ui.percentile_from_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def percentile_to_slider_changed(self, value):
        self.ui.percentile_from_spinbox.setMaximum(value / 100.0)
        self.ui.percentile_to_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def percentile_from_spinbox_changed(self, value):
        self.ui.percentile_to_spinbox.setMinimum(value)
        self.ui.percentile_from_slider.setValue(int(value * 100.0))
        self.ui.value_from_spinbox.setValue(self.data_sorted[(len(self.data_sorted) - 1) * value / 100.0])
        self.ui.value_from_slider.setValue(int(self.ui.value_from_spinbox.value() * 100.0))
        self.invalidate_image()

    def percentile_to_spinbox_changed(self, value):
        self.ui.percentile_from_spinbox.setMaximum(value)
        self.ui.percentile_to_slider.setValue(int(value * 100.0))
        self.ui.value_to_spinbox.setValue(self.data_sorted[(len(self.data_sorted) - 1) * value / 100.0])
        self.ui.value_to_slider.setValue(int(self.ui.value_to_spinbox.value() * 100.0))
        self.invalidate_image()

    def value_from_slider_changed(self, value):
        self.ui.value_to_spinbox.setMinimum(value / 100.0)
        self.ui.value_from_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def value_to_slider_changed(self, value):
        self.ui.value_from_spinbox.setMaximum(value / 100.0)
        self.ui.value_to_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def value_from_spinbox_changed(self, value):
        self.ui.value_to_spinbox.setMinimum(value)
        self.ui.value_from_slider.setValue(int(value * 100.0))
        self.ui.percentile_from_spinbox.setValue(self.data_sorted.searchsorted(value) * 100.0 / (len(self.data_sorted) - 1))
        self.ui.percentile_from_slider.setValue(int(self.ui.percentile_from_spinbox.value() * 100.0))
        self.invalidate_image()

    def value_to_spinbox_changed(self, value):
        self.ui.value_from_spinbox.setMaximum(value)
        self.ui.value_to_slider.setValue(int(value * 100.0))
        self.ui.percentile_to_spinbox.setValue(self.data_sorted.searchsorted(value) * 100.0 / (len(self.data_sorted) - 1))
        self.ui.percentile_to_slider.setValue(int(self.ui.percentile_to_spinbox.value() * 100.0))
        self.invalidate_image()

    def channel_changed(self):
        self.invalidate_data()
        self.crop_changed()

    def crop_changed(self, value=None):
        self.invalidate_data_cropped()
        self.ui.value_from_label.setText(str(self.data_sorted[0]))
        self.ui.value_to_label.setText(str(self.data_sorted[-1]))
        self.ui.value_from_spinbox.setRange(self.data_sorted[0], self.data_sorted[-1])
        self.ui.value_from_spinbox.setValue(self.data_sorted[(len(self.data_sorted) - 1) * self.ui.percentile_from_spinbox.value() / 100.0])
        self.ui.value_to_spinbox.setRange(self.data_sorted[0], self.data_sorted[-1])
        self.ui.value_to_spinbox.setValue(self.data_sorted[(len(self.data_sorted) - 1) * self.ui.percentile_to_spinbox.value() / 100.0])
        self.ui.value_from_slider.setRange(int(self.data_sorted[0] * 100.0), int(self.data_sorted[-1] * 100.0))
        self.ui.value_from_slider.setValue(int(self.ui.value_from_spinbox.value() * 100.0))
        self.ui.value_to_slider.setRange(int(self.data_sorted[0] * 100.0), int(self.data_sorted[-1] * 100.0))
        self.ui.value_to_slider.setValue(int(self.ui.value_to_spinbox.value() * 100.0))
        y_size, x_size = self.data_cropped.shape
        self.ui.x_size_label.setText(str(x_size))
        self.ui.y_size_label.setText(str(y_size))

    def crop_reset_clicked(self):
        self.ui.crop_left_spinbox.setValue(0)
        self.ui.crop_right_spinbox.setValue(0)
        self.ui.crop_top_spinbox.setValue(0)
        self.ui.crop_bottom_spinbox.setValue(0)

    def x_scale_changed(self, value):
        if self.ui.scale_locked_check.isChecked():
            self.ui.y_scale_spinbox.setValue(value)
        self.invalidate_image()

    def y_scale_changed(self, value):
        if self.ui.scale_locked_check.isChecked():
            self.ui.x_scale_spinbox.setValue(value)
        self.invalidate_image()

    def x_offset_changed(self, value):
        if self.ui.offset_locked_check.isChecked():
            self.ui.y_offset_spinbox.setValue(value)
        self.invalidate_image()

    def y_offset_changed(self, value):
        if self.ui.offset_locked_check.isChecked():
            self.ui.x_offset_spinbox.setValue(value)
        self.invalidate_image()

    def default_title_clicked(self):
        self.ui.title_edit.setPlainText(u"""\
Channel {channel:02d} - {channel_name}
{start_time:%A, %d %b %Y %H:%M:%S}
Percentile range: {percentile_from} to {percentile_to}
Value range: {value_from} to {value_to}""")

    def clear_title_clicked(self):
        self.ui.title_edit.clear()

    def title_info_clicked(self):
        from rastools.rasviewer.title_info_dialog import TitleInfoDialog
        if not self._info_dialog:
            self._info_dialog = TitleInfoDialog(self)
            self._info_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self._info_dialog.ui.template_list.clear()
        for key, value in sorted(self.format_dict(self.channel).iteritems()):
            if isinstance(value, basestring):
                if '\n' in value:
                    value = value.splitlines()[0].rstrip()
                self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s}' % key, value])))
            elif isinstance(value, (int, long)):
                self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s}' % key, '{}'.format(value)])))
                if 0 < value < 10:
                    self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s:02d}' % key, '{:02d}'.format(value)])))
            elif isinstance(value, float):
                self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s}' % key, '{}'.format(value)])))
                self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s:.2f}' % key, '{:.2f}'.format(value)])))
            elif isinstance(value, dt.datetime):
                self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s}' % key, '%s' % value])))
                self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s:%%Y-%%m-%%d}' % key, '{:%Y-%m-%d}'.format(value)])))
                self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s:%%H:%%M:%%S}' % key, '{:%H:%M:%S}'.format(value)])))
                self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s:%%A, %%d %%b %%Y, %%H:%%M:%%S}' % key, '{:%A, %d %b %Y, %H:%M:%S}'.format(value)])))
            else:
                self._info_dialog.ui.template_list.addTopLevelItem(QtGui.QTreeWidgetItem(QtCore.QStringList(['{%s}' % key, '{}'.format(value)])))
        self._info_dialog.show()

    @property
    def channel(self):
        if self.ui.channel_combo.currentIndex() != -1:
            return self.ui.channel_combo.itemData(
                self.ui.channel_combo.currentIndex()).toPyObject()

    @property
    def data(self):
        if self._data is None:
            self._data = np.array(self.channel.data, np.float)
        return self._data

    @property
    def data_cropped(self):
        if self._data_cropped is None:
            self._data_cropped = self.data[
                self.ui.crop_top_spinbox.value():self.data.shape[0] - self.ui.crop_bottom_spinbox.value(),
                self.ui.crop_left_spinbox.value():self.data.shape[1] - self.ui.crop_right_spinbox.value()
            ]
        return self._data_cropped

    @property
    def data_sorted(self):
        if self._data_sorted is None:
            self._data_sorted = np.sort(self.data_cropped, None)
        return self._data_sorted

    @property
    def percentile_range(self):
        return (
            self.data_sorted[(len(self.data_sorted) - 1) * self.ui.percentile_from_spinbox.value() / 100.0],
            self.data_sorted[(len(self.data_sorted) - 1) * self.ui.percentile_to_spinbox.value() / 100.0],
        )

    @property
    def data_export(self):
        result = np.array(self.channel.data, np.float)
        result = result[
            self.ui.crop_top_spinbox.value():self._data.shape[0] - self.ui.crop_bottom_spinbox.value(),
            self.ui.crop_left_spinbox.value():self._data.shape[1] - self.ui.crop_right_spinbox.value()
        ]
        s = np.sort(result, None)
        pmin = s[(len(s) - 1) * self.ui.percentile_from_spinbox.value() / 100.0]
        pmax = s[(len(s) - 1) * self.ui.percentile_to_spinbox.value() / 100.0]
        result[result < pmin] = pmin
        result[result > pmax] = pmax
        return result

    def invalidate_data(self):
        self._data = None
        self.invalidate_data_cropped()

    def invalidate_data_cropped(self):
        self._data_cropped = None
        self.invalidate_data_sorted()

    def invalidate_data_sorted(self):
        self._data_sorted = None
        self.invalidate_image()

    def invalidate_image(self):
        if self.redraw_timer.isActive():
            self.redraw_timer.stop()
        self.redraw_timer.start()

    def redraw_timeout(self):
        self.redraw_timer.stop()
        self.redraw_image()

    def redraw_image(self):
        if self.channel is not None:
            vmin = self.data_sorted[0]
            vmax = self.data_sorted[-1]
            pmin = self.ui.value_from_spinbox.value()
            pmax = self.ui.value_to_spinbox.value()
            crop_l = self.ui.crop_left_spinbox.value()
            crop_r = self.ui.crop_right_spinbox.value()
            crop_t = self.ui.crop_top_spinbox.value()
            crop_b = self.ui.crop_bottom_spinbox.value()
            offset_x = self.ui.x_offset_spinbox.value()
            offset_y = self.ui.y_offset_spinbox.value()
            scale_x = self.ui.x_scale_spinbox.value()
            scale_y = self.ui.y_scale_spinbox.value()
            label_x = unicode(self.ui.x_label_edit.text())
            label_y = unicode(self.ui.y_label_edit.text())
            img_w = self._file.x_size
            img_h = self._file.y_size
            # Generate the title text. This is done up here as we need to know
            # if there's going to be anything to render, and whether or not to
            # reserve space for it
            title = None
            try:
                if unicode(self.ui.title_edit.toPlainText()):
                    title = unicode(self.ui.title_edit.toPlainText()).format(**self.format_dict(self.channel))
            except KeyError, e:
                self.ui.title_error_label.setText(u'Unknown template "%s"' % e)
                self.ui.title_error_label.show()
            except Exception, e:
                self.ui.title_error_label.setText(unicode(e))
                self.ui.title_error_label.show()
            else:
                self.ui.title_error_label.hide()
            # Calculate the figure dimensions and margins (in inches unlike the
            # values above which are all pixel based), and construct the
            # necessary objects
            (img_width, img_height) = (img_w / FIGURE_DPI, img_h / FIGURE_DPI)
            (hist_width, hist_height) = ((0.0, 0.0), (img_width, img_height))[self.ui.histogram_check.isChecked()]
            (cbar_width, cbar_height) = ((0.0, 0.0), (img_width, 1.0))[self.ui.colorbar_check.isChecked()]
            (head_width, head_height) = ((0.0, 0.0), (img_width, 0.75))[bool(title)]
            margin = (0.0, 0.5)[
                self.ui.axes_check.isChecked()
                or self.ui.colorbar_check.isChecked()
                or self.ui.histogram_check.isChecked()
                or bool(title)]
            fig_width = img_width + margin * 2
            fig_height = img_height + hist_height + cbar_height + head_height + margin * 2
            # Position the axes in which to draw the channel data
            self.image_axes.clear()
            self.image_axes.set_position((
                margin / fig_width,      # left
                (margin + hist_height + cbar_height) / fig_height, # bottom
                img_width / fig_width,   # width
                img_height / fig_height, # height
            ))
            # Configure the x and y axes appearance
            self.image_axes.set_frame_on(
                self.ui.axes_check.isChecked()
                or self.ui.grid_check.isChecked()
            )
            self.image_axes.set_axis_on()
            if self.ui.grid_check.isChecked():
                self.image_axes.grid(color='k', linestyle='-')
            else:
                self.image_axes.grid(False)
            if self.ui.axes_check.isChecked():
                if label_x:
                    self.image_axes.set_xlabel(label_x)
                if label_y:
                    self.image_axes.set_ylabel(label_y)
            else:
                self.image_axes.set_xticklabels([])
                self.image_axes.set_yticklabels([])
            # Draw the image. This call takes care of clamping values with vmin
            # and vmax, as well as color-mapping
            img = self.image_axes.imshow(
                self.data_cropped,
                vmin=pmin, vmax=pmax,
                origin='upper',
                extent=(
                    scale_x * (offset_x + crop_l),
                    scale_x * (offset_x + img_w - crop_r),
                    scale_y * (offset_y + img_h - crop_b),
                    scale_y * (offset_y + crop_t),
                ),
                cmap=matplotlib.cm.get_cmap(
                    unicode(self.ui.colormap_combo.currentText()) +
                    ('_r' if self.ui.reverse_check.isChecked() else '')
                ),
                interpolation=unicode(self.ui.interpolation_combo.currentText())
            )
            # Construct an axis for the histogram, if requested
            if self.ui.histogram_check.isChecked():
                r = (
                    margin / fig_width,               # left
                    (margin + cbar_height) / fig_height, # bottom
                    hist_width / fig_width,           # width
                    (hist_height * 0.8) / fig_height, # height
                )
                if self.histogram_axes is None:
                    self.histogram_axes = self.figure.add_axes(r)
                else:
                    self.histogram_axes.clear()
                    self.histogram_axes.set_position(r)
                self.histogram_axes.grid(True)
                self.histogram_axes.hist(self.data_cropped.flat,
                    bins=self.ui.histogram_bins_spinbox.value(),
                    range=(pmin, pmax))
            elif self.histogram_axes:
                self.figure.delaxes(self.histogram_axes)
                self.histogram_axes = None
            # Construct an axis for the colorbar, if requested
            if self.ui.colorbar_check.isChecked():
                r = (
                    margin / fig_width,               # left
                    margin / fig_height,              # bottom
                    cbar_width / fig_width,           # width
                    (cbar_height * 0.3) / fig_height, # height
                )
                if self.colorbar_axes is None:
                    self.colorbar_axes = self.figure.add_axes(r)
                else:
                    self.colorbar_axes.clear()
                    self.colorbar_axes.set_position(r)
                self.figure.colorbar(img, cax=self.colorbar_axes,
                    orientation='horizontal',
                    extend=
                    'both' if pmin > vmin and pmax < vmax else
                    'max' if pmax < vmax else
                    'min' if pmin > vmin else
                    'neither')
            elif self.colorbar_axes:
                self.figure.delaxes(self.colorbar_axes)
                self.colorbar_axes = None
            # Construct an axis for the title, if requested
            if title:
                r = (
                    0, (margin + cbar_height + hist_height + img_height) / fig_height, # left, bottom
                    1, head_height / fig_height, # width, height
                )
                if self.title_axes is None:
                    self.title_axes = self.figure.add_axes(r)
                else:
                    self.title_axes.clear()
                    self.title_axes.set_position(r)
                self.title_axes.set_axis_off()
                # Render the title
                self.title_axes.text(0.5, 0.5, title,
                    horizontalalignment='center', verticalalignment='baseline',
                    multialignment='center', size='medium', family='sans-serif',
                    transform=self.title_axes.transAxes)
            elif self.title_axes:
                self.figure.delaxes(self.title_axes)
                self.title_axes = None
            self.canvas.draw()

    def format_dict(self, source, **kwargs):
        """Utility routine which converts the options array for use in format substitutions"""
        return source.format_dict(
            percentile_from=self.ui.percentile_from_spinbox.value(),
            percentile_to=self.ui.percentile_to_spinbox.value(),
            percentile=(self.ui.percentile_from_spinbox.value(), self.ui.percentile_to_spinbox.value()),
            value_from=self.ui.value_from_spinbox.value(),
            value_to=self.ui.value_to_spinbox.value(),
            range=(self.ui.value_from_spinbox.value(), self.ui.value_to_spinbox.value()),
            interpolation=self.interpolation_combo.currentText(),
            colormap=self.ui.colormap_combo.currentText() +
                ('_r' if self.ui.reverse_check.isChecked() else ''),
            crop_left=self.ui.crop_left_spinbox.value(),
            crop_top=self.ui.crop_top_spinbox.value(),
            crop_right=self.ui.crop_right_spinbox.value(),
            crop_bottom=self.ui.crop_bottom_spinbox.value(),
            crop=','.join(str(i) for i in (
                self.ui.crop_left_spinbox.value(),
                self.ui.crop_top_spinbox.value(),
                self.ui.crop_right_spinbox.value(),
                self.ui.crop_bottom_spinbox.value(),
            )),
            **kwargs
        )

