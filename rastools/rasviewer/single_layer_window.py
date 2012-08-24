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

"""Module implementing the rasviewer document window"""

from __future__ import (
    unicode_literals, print_function, absolute_import, division)

import os
import time
import datetime as dt

import numpy as np
import matplotlib
from matplotlib.figure import Figure
import matplotlib.cm
import matplotlib.image
from PyQt4 import QtCore, QtGui, uic

from rastools.collections import Coord, Range, BoundingBox
from rastools.rasviewer.progress_dialog import ProgressDialog
from rastools.rasviewer.figure_canvas import FigureCanvas


DEFAULT_COLORMAP = 'gray'
DEFAULT_INTERPOLATION = 'nearest'
FIGURE_DPI = 72.0


class SingleLayerWindow(QtGui.QWidget):
    "The rasviewer document window"

    def __init__(self, data_file, channel_file=None):
        super(SingleLayerWindow, self).__init__(None)
        self.ui = None
        self.ui = uic.loadUi(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    'single_layer_window.ui'
                )), self)
        self._file = None
        self._data = None
        self._data_sorted = None
        self._data_cropped = None
        self._progress = 0
        self._progress_update = None
        self._progress_dialog = None
        self._info_dialog = None
        self._zoom_id = None
        self._zoom_start = None
        self._zoom_coords = None
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            from rastools.data_parsers import DATA_PARSERS
        finally:
            QtGui.QApplication.instance().restoreOverrideCursor()
        # Open the selected file
        ext = os.path.splitext(data_file)[-1]
        parsers = dict(
            (ext, cls)
            for (cls, exts, _) in DATA_PARSERS
            for ext in exts
        )
        try:
            try:
                parser = parsers[ext]
            except KeyError:
                raise ValueError(
                    self.tr('Unrecognized file extension "{0}"').format(ext))
            self._file = parser(
                data_file, channel_file,
                delay_load=False,
                progress=(
                    self.progress_start,
                    self.progress_update,
                    self.progress_finish,
                ))
        except (ValueError, IOError) as exc:
            QtGui.QMessageBox.critical(self, self.tr('Error'), str(exc))
            self.close()
            return
        # Create a figure in a tab for the file
        self.figure = Figure(figsize=(5.0, 5.0), dpi=FIGURE_DPI,
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
                    self.ui.channel_combo.addItem(
                        'Channel {index} - {name}'.format(
                            index=channel.index, name=channel.name),
                        channel)
                else:
                    self.ui.channel_combo.addItem(
                        'Channel {index}'.format(index=channel.index),
                        channel)
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
        self.ui.splitter.splitterMoved.connect(self.splitter_moved)
        QtGui.QApplication.instance().focusChanged.connect(self.focus_changed)
        self.canvas.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.canvas_popup)
        self.press_id = self.canvas.mpl_connect(
            'button_press_event', self.canvas_press)
        self.release_id = self.canvas.mpl_connect(
            'button_release_event', self.canvas_release)
        self.motion_id = self.canvas.mpl_connect(
            'motion_notify_event', self.canvas_motion)
        self.setWindowTitle(os.path.basename(data_file))
        self.channel_changed()

    def splitter_moved(self, pos, index):
        self.invalidate_image()

    def canvas_popup(self, pos):
        "Handler for canvas context menu event"
        menu = QtGui.QMenu(self)
        menu.addAction(self.window().ui.reset_zoom_action)
        menu.addAction(self.window().ui.reset_origin_action)
        menu.popup(self.canvas.mapToGlobal(pos))

    def progress_start(self):
        "Handler for loading progress start event"
        self._progress = 0
        self._progress_dialog = ProgressDialog(self.window())
        self._progress_dialog.show()
        self._progress_dialog.task = self.tr('Opening file')
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)

    def progress_update(self, progress):
        "Handler for loading progress update event"
        now = time.time()
        if ((self._progress_update is None) or
                (now - self._progress_update) > 0.2):
            if self._progress_dialog.cancelled:
                raise KeyboardInterrupt
            self._progress_update = now
            if progress != self._progress:
                self._progress_dialog.progress = progress
                self._progress = progress

    def progress_finish(self):
        "Handler for loading progress finished event"
        QtGui.QApplication.instance().restoreOverrideCursor()
        if self._progress_dialog is not None:
            self._progress_dialog.close()
            self._progress_dialog = None

    def canvas_motion(self, event):
        "Handler for mouse movement over graph canvas"
        if (self.image_axes and
                (event.inaxes == self.image_axes) and
                (event.xdata is not None)):
            self.window().ui.x_label.setText('X: {0:.0f}'.format(event.xdata))
            self.window().ui.y_label.setText('Y: {0:.0f}'.format(event.ydata))
            try:
                self.window().ui.value_label.setText(
                    'Value: {0:.2f}'.format(
                        float(self.data[event.ydata, event.xdata])))
            except IndexError:
                self.window().ui.value_label.setText('')
            self.canvas.setCursor(QtCore.Qt.CrossCursor)
        else:
            self.window().ui.x_label.setText('')
            self.window().ui.y_label.setText('')
            self.window().ui.value_label.setText('')
            self.canvas.setCursor(QtCore.Qt.ArrowCursor)

    def canvas_press(self, event):
        "Handler for mouse press on graph canvas"
        if event.button != 1:
            return
        if event.inaxes != self.image_axes:
            return
        self._zoom_start = Coord(event.x, event.y)
        self._zoom_id = self.canvas.mpl_connect(
            'motion_notify_event', self.canvas_zoom_motion)

    def canvas_zoom_motion(self, event):
        "Handler for mouse movement over graph canvas (after press)"
        # Calculate the display coordinates of the selection
        box_left, box_top, box_right, box_bottom = self.image_axes.bbox.extents
        height = self.figure.bbox.height
        band_left   = max(min(self._zoom_start.x, event.x), box_left)
        band_right  = min(max(self._zoom_start.x, event.x), box_right)
        band_top    = max(min(self._zoom_start.y, event.y), box_top)
        band_bottom = min(max(self._zoom_start.y, event.y), box_bottom)
        rectangle = (
            band_left,
            height - band_top,
            band_right - band_left,
            band_top - band_bottom
        )
        # Calculate the data coordinates of the selection. Note that top and
        # bottom are reversed by this conversion
        inverse = self.image_axes.transData.inverted()
        data_left, data_bottom = inverse.transform_point(
            (band_left, band_top))
        data_right, data_top = inverse.transform_point(
            (band_right, band_bottom))
        # Ignore the drag operation until the total number of data-points in
        # the selection exceeds the threshold
        threshold = 49
        if (abs(data_right - data_left) * abs(data_bottom - data_top)) > threshold:
            self._zoom_coords = (data_left, data_top, data_right, data_bottom)
            self.window().statusBar().showMessage(
                unicode(self.tr(
                    'Crop from ({left:.0f}, {top:.0f}) to '
                    '({right:.0f}, {bottom:.0f})')).format(
                        left=data_left, top=data_top,
                        right=data_right, bottom=data_bottom))
            self.canvas.drawRectangle(rectangle)
        else:
            self._zoom_coords = None
            self.window().statusBar().clearMessage()
            self.canvas.draw()

    def canvas_release(self, event):
        "Handler for mouse release on graph canvas"
        if self._zoom_id:
            self.window().statusBar().clearMessage()
            self.canvas.mpl_disconnect(self._zoom_id)
            self._zoom_id = None
            if self._zoom_coords:
                (   data_left,
                    data_top,
                    data_right,
                    data_bottom,
                ) = self._zoom_coords
                data_left = (
                    (data_left / self.ui.x_scale_spinbox.value()) -
                    self.ui.x_offset_spinbox.value())
                data_right = (
                    (data_right / self.ui.x_scale_spinbox.value()) -
                    self.ui.x_offset_spinbox.value())
                data_top = (
                    (data_top / self.ui.y_scale_spinbox.value()) -
                    self.ui.y_offset_spinbox.value())
                data_bottom = (
                    (data_bottom / self.ui.y_scale_spinbox.value()) -
                    self.ui.y_offset_spinbox.value())
                self.ui.crop_left_spinbox.setValue(data_left)
                self.ui.crop_top_spinbox.setValue(data_top)
                self.ui.crop_right_spinbox.setValue(
                    self._file.x_size - data_right)
                self.ui.crop_bottom_spinbox.setValue(
                    self._file.y_size - data_bottom)
                self.canvas.draw()

    def focus_changed(self, old_widget, new_widget):
        "Handler for control focus changed event"
        # The percentile and range controls are mutually dependent; the value
        # of the percentile depends on the value of the range, and vice versa.
        # This would obviously cause infinite recursion if both sets of
        # handlers were connected all the time. Hence, when user focus changes
        # we connect the handlers for the controls the user is focused and and
        # disconnect the others.
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
        if ((old_widget not in percentile_controls) and
                (new_widget in percentile_controls)):
            self.percentile_connect()
        elif ((old_widget in percentile_controls) and
                (new_widget not in percentile_controls)):
            self.percentile_disconnect()
        if ((old_widget not in range_controls) and
                (new_widget in range_controls)):
            self.range_connect()
        elif ((old_widget in range_controls) and
                (new_widget not in range_controls)):
            self.range_disconnect()

    def percentile_connect(self):
        "Connects percentile controls to event handlers"
        # See focus_changed above
        self.ui.percentile_from_slider.valueChanged.connect(
            self.percentile_from_slider_changed)
        self.ui.percentile_from_spinbox.valueChanged.connect(
            self.percentile_from_spinbox_changed)
        self.ui.percentile_to_slider.valueChanged.connect(
            self.percentile_to_slider_changed)
        self.ui.percentile_to_spinbox.valueChanged.connect(
            self.percentile_to_spinbox_changed)

    def percentile_disconnect(self):
        "Disconnects percentile controls from event handlers"
        # See focus_changed above
        self.ui.percentile_from_slider.valueChanged.disconnect(
            self.percentile_from_slider_changed)
        self.ui.percentile_from_spinbox.valueChanged.disconnect(
            self.percentile_from_spinbox_changed)
        self.ui.percentile_to_slider.valueChanged.disconnect(
            self.percentile_to_slider_changed)
        self.ui.percentile_to_spinbox.valueChanged.disconnect(
            self.percentile_to_spinbox_changed)

    def range_connect(self):
        "Connects range controls to event handlers"
        # See focus_changed above
        self.ui.value_from_slider.valueChanged.connect(
            self.value_from_slider_changed)
        self.ui.value_from_spinbox.valueChanged.connect(
            self.value_from_spinbox_changed)
        self.ui.value_to_slider.valueChanged.connect(
            self.value_to_slider_changed)
        self.ui.value_to_spinbox.valueChanged.connect(
            self.value_to_spinbox_changed)

    def range_disconnect(self):
        "Disconnects range controls from event handlers"
        # See focus_changed above
        self.ui.value_from_slider.valueChanged.disconnect(
            self.value_from_slider_changed)
        self.ui.value_from_spinbox.valueChanged.disconnect(
            self.value_from_spinbox_changed)
        self.ui.value_to_slider.valueChanged.disconnect(
            self.value_to_slider_changed)
        self.ui.value_to_spinbox.valueChanged.disconnect(
            self.value_to_spinbox_changed)

    def percentile_from_slider_changed(self, value):
        "Handler for percentile_from_slider change event"
        self.ui.percentile_to_spinbox.setMinimum(value / 100.0)
        self.ui.percentile_from_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def percentile_to_slider_changed(self, value):
        "Handler for percentile_to_slider change event"
        self.ui.percentile_from_spinbox.setMaximum(value / 100.0)
        self.ui.percentile_to_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def percentile_from_spinbox_changed(self, value):
        "Handler for percentile_from_spinbox change event"
        self.ui.percentile_to_spinbox.setMinimum(value)
        self.ui.percentile_from_slider.setValue(int(value * 100.0))
        self.ui.value_from_spinbox.setValue(
            self.data_sorted[(len(self.data_sorted) - 1) * value / 100.0])
        self.ui.value_from_slider.setValue(
            int(self.ui.value_from_spinbox.value() * 100.0))
        self.invalidate_image()

    def percentile_to_spinbox_changed(self, value):
        "Handler for percentile_to_spinbox change event"
        self.ui.percentile_from_spinbox.setMaximum(value)
        self.ui.percentile_to_slider.setValue(int(value * 100.0))
        self.ui.value_to_spinbox.setValue(
            self.data_sorted[(len(self.data_sorted) - 1) * value / 100.0])
        self.ui.value_to_slider.setValue(
            int(self.ui.value_to_spinbox.value() * 100.0))
        self.invalidate_image()

    def value_from_slider_changed(self, value):
        "Handler for range_from_slider change event"
        self.ui.value_to_spinbox.setMinimum(value / 100.0)
        self.ui.value_from_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def value_to_slider_changed(self, value):
        "Handler for range_to_slider change event"
        self.ui.value_from_spinbox.setMaximum(value / 100.0)
        self.ui.value_to_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def value_from_spinbox_changed(self, value):
        "Handler for range_from_spinbox change event"
        self.ui.value_to_spinbox.setMinimum(value)
        self.ui.value_from_slider.setValue(int(value * 100.0))
        self.ui.percentile_from_spinbox.setValue(
            self.data_sorted.searchsorted(value) * 100.0 /
            (len(self.data_sorted) - 1))
        self.ui.percentile_from_slider.setValue(
            int(self.ui.percentile_from_spinbox.value() * 100.0))
        self.invalidate_image()

    def value_to_spinbox_changed(self, value):
        "Handler for range_to_spinbox change event"
        self.ui.value_from_spinbox.setMaximum(value)
        self.ui.value_to_slider.setValue(int(value * 100.0))
        self.ui.percentile_to_spinbox.setValue(
            self.data_sorted.searchsorted(value) * 100.0 /
            (len(self.data_sorted) - 1))
        self.ui.percentile_to_slider.setValue(
            int(self.ui.percentile_to_spinbox.value() * 100.0))
        self.invalidate_image()

    def channel_changed(self):
        "Handler for data channel change event"
        self.invalidate_data()
        self.crop_changed()

    def crop_changed(self, value=None):
        "Handler for crop_*_spinbox change event"
        self.invalidate_data_cropped()
        if self.channel is not None:
            self.ui.value_from_label.setText(str(self.data_domain.low))
            self.ui.value_to_label.setText(str(self.data_domain.high))
            self.ui.value_from_spinbox.setRange(
                self.data_domain.low,
                self.data_domain.high)
            self.ui.value_from_spinbox.setValue(
                self.data_sorted[
                    (len(self.data_sorted) - 1) *
                    self.ui.percentile_from_spinbox.value() / 100.0])
            self.ui.value_to_spinbox.setRange(
                self.data_domain.low,
                self.data_domain.high)
            self.ui.value_to_spinbox.setValue(
                self.data_sorted[
                    (len(self.data_sorted) - 1) *
                    self.ui.percentile_to_spinbox.value() / 100.0])
            self.ui.value_from_slider.setRange(
                int(self.data_sorted[0] * 100.0),
                int(self.data_sorted[-1] * 100.0))
            self.ui.value_from_slider.setValue(
                int(self.ui.value_from_spinbox.value() * 100.0))
            self.ui.value_to_slider.setRange(
                int(self.data_sorted[0] * 100.0),
                int(self.data_sorted[-1] * 100.0))
            self.ui.value_to_slider.setValue(
                int(self.ui.value_to_spinbox.value() * 100.0))
            y_size, x_size = self.data_cropped.shape
            self.ui.x_size_label.setText(str(x_size))
            self.ui.y_size_label.setText(str(y_size))

    def reset_zoom(self):
        "Handler for reset_zoom_action triggered event"
        self.ui.crop_left_spinbox.setValue(0)
        self.ui.crop_right_spinbox.setValue(0)
        self.ui.crop_top_spinbox.setValue(0)
        self.ui.crop_bottom_spinbox.setValue(0)

    def reset_origin(self):
        "Handler for reset_origin_action triggered event"
        self.ui.offset_locked_check.setChecked(False)
        self.ui.x_offset_spinbox.setValue(-self.ui.crop_left_spinbox.value())
        self.ui.y_offset_spinbox.setValue(-self.ui.crop_top_spinbox.value())

    def x_scale_changed(self, value):
        "Handler for x_scale_spinbox change event"
        if self.ui.scale_locked_check.isChecked():
            self.ui.y_scale_spinbox.setValue(value)
        self.invalidate_image()

    def y_scale_changed(self, value):
        "Handler for y_scale_spinbox change event"
        if self.ui.scale_locked_check.isChecked():
            self.ui.x_scale_spinbox.setValue(value)
        self.invalidate_image()

    def x_offset_changed(self, value):
        "Handler for x_offset_spinbox change event"
        if self.ui.offset_locked_check.isChecked():
            self.ui.y_offset_spinbox.setValue(value)
        self.invalidate_image()

    def y_offset_changed(self, value):
        "Handler for x_offset_spinbox change event"
        if self.ui.offset_locked_check.isChecked():
            self.ui.x_offset_spinbox.setValue(value)
        self.invalidate_image()

    def default_title_clicked(self):
        "Handler for default_title_button click event"
        self.ui.title_edit.setPlainText("""\
Channel {channel:02d} - {channel_name}
{start_time:%A, %d %b %Y %H:%M:%S}
Percentile range: {percentile_from} to {percentile_to}
Value range: {range_from} to {range_to}""")

    def clear_title_clicked(self):
        "Handler for clear_title_button click event"
        self.ui.title_edit.clear()

    def title_info_clicked(self):
        "Handler for title_info_button click event"
        from rastools.rasviewer.title_info_dialog import TitleInfoDialog
        if not self._info_dialog:
            self._info_dialog = TitleInfoDialog(self)
        self._info_dialog.ui.template_list.clear()
        for key, value in sorted(self.format_dict(self.channel).iteritems()):
            if isinstance(value, basestring):
                if '\n' in value:
                    value = value.splitlines()[0].rstrip()
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        QtCore.QStringList([
                            '{{{0}}}'.format(key),
                            value
                        ])))
            elif isinstance(value, (int, long)):
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        QtCore.QStringList([
                            '{{{0}}}'.format(key),
                            '{0}'.format(value)
                        ])))
                if 0 < value < 10:
                    self._info_dialog.ui.template_list.addTopLevelItem(
                        QtGui.QTreeWidgetItem(
                            QtCore.QStringList([
                                '{{{0}:02d}}'.format(key),
                                '{0:02d}'.format(value)
                            ])))
            elif isinstance(value, float):
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        QtCore.QStringList([
                            '{{{0}}}'.format(key),
                            '{0}'.format(value)
                        ])))
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        QtCore.QStringList([
                            '{{{0}:.2f}}'.format(key),
                            '{0:.2f}'.format(value)
                        ])))
            elif isinstance(value, dt.datetime):
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        QtCore.QStringList([
                            '{{{0}}}'.format(key),
                            '{0}'.format(value)
                        ])))
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        QtCore.QStringList([
                            '{{{0}:%Y-%m-%d}}'.format(key),
                            '{0:%Y-%m-%d}'.format(value)
                        ])))
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        QtCore.QStringList([
                            '{{{0}:%H:%M:%S}}'.format(key),
                            '{0:%H:%M:%S}'.format(value)
                        ])))
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        QtCore.QStringList([
                            '{{{0}:%A, %d %b %Y, %H:%M:%S}}'.format(key),
                            '{0:%A, %d %b %Y, %H:%M:%S}'.format(value)
                        ])))
            else:
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        QtCore.QStringList([
                            '{{{0}}}'.format(key),
                            '{0}'.format(value)
                        ])))
        self._info_dialog.show()

    @property
    def channel(self):
        "Returns the currently selected channel object"
        # We test self.ui here as during ui loading something
        # (connectSlotsByName) seems to iterate over all the properties
        # querying their value. As self.ui wasn't assigned at this point it led
        # to several annoying exceptions...
        if self.ui and (self.ui.channel_combo.currentIndex() != -1):
            return self.ui.channel_combo.itemData(
                self.ui.channel_combo.currentIndex()).toPyObject()

    @property
    def data(self):
        "Returns the data of the currently selected channel"
        if (self._data is None) and (self.channel is not None):
            self._data = self.channel.data.copy()
        return self._data

    @property
    def data_cropped(self):
        "Returns the data of the selected channel after cropping"
        if (self._data_cropped is None) and (self.data is not None):
            top = self.ui.crop_top_spinbox.value()
            left = self.ui.crop_left_spinbox.value()
            bottom = self.data.shape[0] - self.ui.crop_bottom_spinbox.value()
            right = self.data.shape[1] - self.ui.crop_right_spinbox.value()
            self._data_cropped = self.data[top:bottom, left:right]
        return self._data_cropped

    @property
    def data_sorted(self):
        "Returns a flat, sorted array of the cropped channel data"
        if (self._data_sorted is None) and (self.data_cropped is not None):
            self._data_sorted = np.sort(self.data_cropped, None)
        return self._data_sorted

    @property
    def data_domain(self):
        "Returns a tuple of the value limits for the current channel"
        if self.data_sorted is not None:
            return Range(self.data_sorted[0], self.data_sorted[-1])

    @property
    def data_range(self):
        "Returns a tuple of the percentile values for the current channel"
        if self.data_sorted is not None:
            return Range(
                self.ui.value_from_spinbox.value(),
                self.ui.value_to_spinbox.value())

    @property
    def x_limits(self):
        "Returns a tuple of the X-axis limits after scaling and offset"
        if self.data_cropped is not None:
            return Range(
                (self.ui.x_scale_spinbox.value() or 1.0) * (
                    self.ui.x_offset_spinbox.value() +
                    self.ui.crop_left_spinbox.value()),
                (self.ui.x_scale_spinbox.value() or 1.0) * (
                    self.ui.x_offset_spinbox.value() +
                    self._file.x_size - self.ui.crop_right_spinbox.value())
            )

    @property
    def y_limits(self):
        "Returns a tuple of the Y-axis limits after scaling and offset"
        if self.data_cropped is not None:
            return Range(
                (self.ui.y_scale_spinbox.value() or 1.0) * (
                    self.ui.y_offset_spinbox.value() +
                    self._file.y_size - self.ui.crop_bottom_spinbox.value()),
                (self.ui.y_scale_spinbox.value() or 1.0) * (
                    self.ui.y_offset_spinbox.value() +
                    self.ui.crop_top_spinbox.value())
            )

    def invalidate_data(self):
        "Invalidate our copy of the channel data"
        self._data = None
        self.invalidate_data_cropped()

    def invalidate_data_cropped(self):
        "Invalidate our copy of the cropped channel data"
        self._data_cropped = None
        self.invalidate_data_sorted()

    def invalidate_data_sorted(self):
        "Invalidate our flat sorted version of the cropped channel data"
        self._data_sorted = None
        self.invalidate_image()

    def invalidate_image(self):
        "Invalidate the image"
        # Actually, this method doesn't immediately invalidate the image (as
        # this results in a horribly sluggish UI), but starts a timer which
        # causes a redraw after no invalidations have occurred for a period
        # (see __init__ for the duration)
        if self.redraw_timer.isActive():
            self.redraw_timer.stop()
        self.redraw_timer.start()

    def redraw_timeout(self):
        "Handler for the redraw_timer's timeout event"
        self.redraw_timer.stop()
        self.redraw_figure()

    def redraw_figure(self):
        "Called to redraw the channel image"
        # The following tests ensure we don't try and draw anything while we're
        # still loading the file
        if self._file and self.channel is not None:
            # Generate the title text. This is done up here as we need to know
            # if there's going to be anything to render, and whether or not to
            # reserve space for it
            title = None
            try:
                if unicode(self.ui.title_edit.toPlainText()):
                    title = unicode(self.ui.title_edit.toPlainText()).format(
                        **self.format_dict(self.channel))
            except KeyError as exc:
                self.ui.title_error_label.setText(
                    'Unknown template "{}"'.format(exc))
                self.ui.title_error_label.show()
            except ValueError as exc:
                self.ui.title_error_label.setText(unicode(exc))
                self.ui.title_error_label.show()
            else:
                self.ui.title_error_label.hide()
            # Calculate the figure dimensions and margins. See RasRenderer.draw
            # in the rastools.rasextract module for more information about this
            # stuff...
            margin_visible = (
                self.ui.axes_check.isChecked()
                or self.ui.colorbar_check.isChecked()
                or self.ui.histogram_check.isChecked()
                or bool(title)
            )
            xmargin = 0.75 if margin_visible else 0.0
            ymargin = 0.25 if margin_visible else 0.0
            separator = 0.3
            figure_box = BoundingBox(
                0.0,
                0.0,
                self.figure.get_figwidth(),
                self.figure.get_figheight()
            )
            colorbar_box = BoundingBox(
                xmargin,
                ymargin,
                figure_box.width - (xmargin * 2),
                0.5 if self.ui.colorbar_check.isChecked() else 0.0
            )
            title_box = BoundingBox(
                xmargin,
                figure_box.height - (ymargin + 1.0 if bool(title) else 0.0),
                figure_box.width - (xmargin * 2),
                1.0 if bool(title) else 0.0
            )
            histogram_box = BoundingBox(
                xmargin,
                colorbar_box.top + (
                    separator if self.ui.colorbar_check.isChecked() else 0.0),
                figure_box.width - (xmargin * 2),
                (
                    figure_box.height -
                    (ymargin * 2) -
                    colorbar_box.height -
                    title_box.height -
                    (separator if self.colorbar_check.isChecked() else 0.0) -
                    (separator if bool(title) else 0.0)
                ) / 2.0 if self.histogram_check.isChecked() else 0.0
            )
            image_box = BoundingBox(
                xmargin,
                histogram_box.top + (
                    separator if self.ui.colorbar_check.isChecked()
                    or self.ui.histogram_check.isChecked() else 0.0),
                figure_box.width - (xmargin * 2),
                (
                    figure_box.height -
                    (ymargin * 2) -
                    colorbar_box.height -
                    title_box.height -
                    histogram_box.height -
                    (
                        separator if self.colorbar_check.isChecked()
                        or self.histogram_check.isChecked() else 0.0) -
                    (separator if bool(title) else 0.0)
                )
            )
            # Draw the various image elements within bounding boxes calculated
            # from the metrics above
            image = self.draw_image(image_box.relative_to(figure_box))
            self.draw_histogram(histogram_box.relative_to(figure_box))
            self.draw_colorbar(image, colorbar_box.relative_to(figure_box))
            self.draw_title(title, title_box.relative_to(figure_box))
            self.canvas.draw()

    def draw_image(self, box):
        "Draws the image of the data within the specified figure"
        # Position the axes in which to draw the channel data
        self.image_axes.clear()
        self.image_axes.set_position(box)
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
            if unicode(self.ui.x_label_edit.text()):
                self.image_axes.set_xlabel(unicode(self.ui.x_label_edit.text()))
            if unicode(self.ui.y_label_edit.text()):
                self.image_axes.set_ylabel(unicode(self.ui.y_label_edit.text()))
        else:
            self.image_axes.set_xticklabels([])
            self.image_axes.set_yticklabels([])
        # The imshow() call takes care of clamping values with data_range and
        # color-mapping
        return self.image_axes.imshow(
            self.data_cropped,
            vmin=self.data_range.low, vmax=self.data_range.high,
            origin='upper',
            extent=self.x_limits + self.y_limits,
            cmap=matplotlib.cm.get_cmap(
                unicode(self.ui.colormap_combo.currentText()) +
                ('_r' if self.ui.reverse_check.isChecked() else '')
            ),
            interpolation=unicode(self.ui.interpolation_combo.currentText()))

    def draw_histogram(self, box):
        "Draws the data's historgram within the figure"
        if self.ui.histogram_check.isChecked():
            if self.histogram_axes is None:
                self.histogram_axes = self.figure.add_axes(box)
            else:
                self.histogram_axes.clear()
                self.histogram_axes.set_position(box)
            self.histogram_axes.grid(True)
            self.histogram_axes.hist(self.data_cropped.flat,
                bins=self.ui.histogram_bins_spinbox.value(),
                range=self.data_range)
        elif self.histogram_axes:
            self.figure.delaxes(self.histogram_axes)
            self.histogram_axes = None

    def draw_colorbar(self, image, box):
        "Draws a range color-bar within the figure"
        if self.ui.colorbar_check.isChecked():
            if self.colorbar_axes is None:
                self.colorbar_axes = self.figure.add_axes(box)
            else:
                self.colorbar_axes.clear()
                self.colorbar_axes.set_position(box)
            self.figure.colorbar(
                image, cax=self.colorbar_axes,
                orientation='horizontal',
                extend=
                'both' if self.data_range.low > self.data_domain.low and
                          self.data_range.high < self.data_domain.high else
                'max' if self.data_range.high < self.data_domain.high else
                'min' if self.data_range.low > self.data_domain.low else
                'neither')
        elif self.colorbar_axes:
            self.figure.delaxes(self.colorbar_axes)
            self.colorbar_axes = None

    def draw_title(self, title, box):
        "Draws a title within the specified figure"
        if bool(title):
            if self.title_axes is None:
                self.title_axes = self.figure.add_axes(box)
            else:
                self.title_axes.clear()
                self.title_axes.set_position(box)
            self.title_axes.set_axis_off()
            # Render the title
            self.title_axes.text(0.5, 0, title,
                horizontalalignment='center', verticalalignment='baseline',
                multialignment='center', size='medium', family='sans-serif',
                transform=self.title_axes.transAxes)
        elif self.title_axes:
            self.figure.delaxes(self.title_axes)
            self.title_axes = None

    def format_dict(self, source, **kwargs):
        "Returns UI settings in a dict for use in format substitutions"
        return source.format_dict(
            percentile_from=self.ui.percentile_from_spinbox.value(),
            percentile_to=self.ui.percentile_to_spinbox.value(),
            range_from=self.ui.value_from_spinbox.value(),
            range_to=self.ui.value_to_spinbox.value(),
            interpolation=self.interpolation_combo.currentText(),
            colormap=self.ui.colormap_combo.currentText() +
                ('_r' if self.ui.reverse_check.isChecked() else ''),
            crop_left=self.ui.crop_left_spinbox.value(),
            crop_top=self.ui.crop_top_spinbox.value(),
            crop_right=self.ui.crop_right_spinbox.value(),
            crop_bottom=self.ui.crop_bottom_spinbox.value(),
            **kwargs
        )

