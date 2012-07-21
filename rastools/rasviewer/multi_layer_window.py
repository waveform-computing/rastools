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

"""Module implementing the multi-layer rasviewer document window"""

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


class ControlSet(object):
    def __init__(self, index, **kwargs):
        self.index = index
        self.channel_combo = kwargs['channel_combo']
        self.value_from_label = kwargs['value_from_label']
        self.value_to_label = kwargs['value_to_label']
        self.value_from_spinbox = kwargs['value_from_spinbox']
        self.value_to_spinbox = kwargs['value_to_spinbox']
        self.value_from_slider = kwargs['value_from_slider']
        self.value_to_slider = kwargs['value_to_slider']
        self.percentile_from_spinbox = kwargs['percentile_from_spinbox']
        self.percentile_to_spinbox = kwargs['percentile_to_spinbox']
        self.percentile_from_slider = kwargs['percentile_from_slider']
        self.percentile_to_slider = kwargs['percentile_to_slider']


class MultiLayerWindow(QtGui.QWidget):
    "The rasviewer document window"

    def __init__(self, data_file, channel_file=None):
        super(MultiLayerWindow, self).__init__(None)
        self.ui = None
        self.ui = uic.loadUi(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    'multi_layer_window.ui'
                )), self)
        self._current_set = None
        self._control_sets = [
            ControlSet(
                index=0,
                channel_combo=self.ui.red_channel_combo,
                value_from_label=self.ui.red_value_from_label,
                value_to_label=self.ui.red_value_to_label,
                value_from_spinbox=self.ui.red_value_from_spinbox,
                value_to_spinbox=self.ui.red_value_to_spinbox,
                value_from_slider=self.ui.red_value_from_slider,
                value_to_slider=self.ui.red_value_to_slider,
                percentile_from_spinbox=self.ui.red_percentile_from_spinbox,
                percentile_to_spinbox=self.ui.red_percentile_to_spinbox,
                percentile_from_slider=self.ui.red_percentile_from_slider,
                percentile_to_slider=self.ui.red_percentile_to_slider),
            ControlSet(
                index=1,
                channel_combo=self.ui.green_channel_combo,
                value_from_label=self.ui.green_value_from_label,
                value_to_label=self.ui.green_value_to_label,
                value_from_spinbox=self.ui.green_value_from_spinbox,
                value_to_spinbox=self.ui.green_value_to_spinbox,
                value_from_slider=self.ui.green_value_from_slider,
                value_to_slider=self.ui.green_value_to_slider,
                percentile_from_spinbox=self.ui.green_percentile_from_spinbox,
                percentile_to_spinbox=self.ui.green_percentile_to_spinbox,
                percentile_from_slider=self.ui.green_percentile_from_slider,
                percentile_to_slider=self.ui.green_percentile_to_slider),
            ControlSet(
                index=2,
                channel_combo=self.ui.blue_channel_combo,
                value_from_label=self.ui.blue_value_from_label,
                value_to_label=self.ui.blue_value_to_label,
                value_from_spinbox=self.ui.blue_value_from_spinbox,
                value_to_spinbox=self.ui.blue_value_to_spinbox,
                value_from_slider=self.ui.blue_value_from_slider,
                value_to_slider=self.ui.blue_value_to_slider,
                percentile_from_spinbox=self.ui.blue_percentile_from_spinbox,
                percentile_to_spinbox=self.ui.blue_percentile_to_spinbox,
                percentile_from_slider=self.ui.blue_percentile_from_slider,
                percentile_to_slider=self.ui.blue_percentile_to_slider)]
        self._file = None
        self._data = None
        self._data_sorted = None
        self._data_cropped = None
        self._data_normalized = None
        self._data_flat = None
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
        self.figure = Figure(figsize=(5.0, 4.0), dpi=FIGURE_DPI,
            facecolor='w', edgecolor='w')
        self.canvas = FigureCanvas(self.figure)
        self.image_axes = self.figure.add_axes((0.1, 0.1, 0.8, 0.8))
        self.histogram_axes = None
        self.title_axes = None
        self.ui.splitter.addWidget(self.canvas)
        # Fill out the combos
        for cset in self._control_sets:
            cset.channel_combo.addItem('None', None)
            for channel in self._file.channels:
                if channel.enabled:
                    if channel.name:
                        cset.channel_combo.addItem(
                            'Channel {index} - {name}'.format(
                                index=channel.index, name=channel.name),
                            channel)
                    else:
                        cset.channel_combo.addItem(
                            'Channel {index}'.format(
                                index=channel.index),
                            channel)
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
        for cset in self._control_sets:
            cset.channel_combo.currentIndexChanged.connect(self.channel_changed)
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
        self.ui.title_edit.textChanged.connect(self.invalidate_image)
        self.ui.default_title_button.clicked.connect(self.default_title_clicked)
        self.ui.clear_title_button.clicked.connect(self.clear_title_clicked)
        self.ui.title_info_button.clicked.connect(self.title_info_clicked)
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
        labels = (
            ('Red', self.window().ui.red_label),
            ('Green', self.window().ui.green_label),
            ('Blue', self.window().ui.blue_label))
        if (self.image_axes and
                (event.inaxes == self.image_axes) and
                (event.xdata is not None)):
            self.window().ui.x_label.setText('X: {0:.2f}'.format(event.xdata))
            self.window().ui.y_label.setText('Y: {0:.2f}'.format(event.ydata))
            try:
                for index, (name, label) in enumerate(labels):
                    label.setText(
                        '{name}: {value:.2f} ({norm:.2f})'.format(
                            name=name,
                            value=self.data[event.ydata, event.xdata, index],
                            norm=self.data_normalized[
                                event.ydata - self.ui.crop_top_spinbox.value(),
                                event.xdata - self.ui.crop_left_spinbox.value(),
                                index]))
            except IndexError:
                for _, label in labels:
                    label.setText('')
            self.canvas.setCursor(QtCore.Qt.CrossCursor)
        else:
            self.window().ui.x_label.setText('')
            self.window().ui.y_label.setText('')
            for _, label in labels:
                label.setText('')
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
        percentile_controls = dict(
            (control, cset)
            for cset in self._control_sets
            for control in (
                cset.percentile_from_slider,
                cset.percentile_from_spinbox,
                cset.percentile_to_slider,
                cset.percentile_to_spinbox,
            )
        )
        range_controls = dict(
            (control, cset)
            for cset in self._control_sets
            for control in (
                cset.value_from_slider,
                cset.value_from_spinbox,
                cset.value_to_slider,
                cset.value_to_spinbox,
            )
        )
        if ((old_widget not in percentile_controls) and
                (new_widget in percentile_controls)):
            self.percentile_connect(percentile_controls[new_widget])
        elif ((old_widget in percentile_controls) and
                (new_widget not in percentile_controls)):
            self.percentile_disconnect(percentile_controls[old_widget])
        if ((old_widget not in range_controls) and
                (new_widget in range_controls)):
            self.range_connect(range_controls[new_widget])
        elif ((old_widget in range_controls) and
                (new_widget not in range_controls)):
            self.range_disconnect(range_controls[old_widget])

    def percentile_connect(self, cset):
        "Connects percentile controls to event handlers"
        # See focus_changed above
        self._current_set = cset
        cset.percentile_from_slider.valueChanged.connect(
            self.percentile_from_slider_changed)
        cset.percentile_from_spinbox.valueChanged.connect(
            self.percentile_from_spinbox_changed)
        cset.percentile_to_slider.valueChanged.connect(
            self.percentile_to_slider_changed)
        cset.percentile_to_spinbox.valueChanged.connect(
            self.percentile_to_spinbox_changed)

    def percentile_disconnect(self, cset):
        "Disconnects percentile controls from event handlers"
        # See focus_changed above
        cset.percentile_from_slider.valueChanged.disconnect(
            self.percentile_from_slider_changed)
        cset.percentile_from_spinbox.valueChanged.disconnect(
            self.percentile_from_spinbox_changed)
        cset.percentile_to_slider.valueChanged.disconnect(
            self.percentile_to_slider_changed)
        cset.percentile_to_spinbox.valueChanged.disconnect(
            self.percentile_to_spinbox_changed)

    def range_connect(self, cset):
        "Connects range controls to event handlers"
        # See focus_changed above
        self._current_set = cset
        cset.value_from_slider.valueChanged.connect(
            self.value_from_slider_changed)
        cset.value_from_spinbox.valueChanged.connect(
            self.value_from_spinbox_changed)
        cset.value_to_slider.valueChanged.connect(
            self.value_to_slider_changed)
        cset.value_to_spinbox.valueChanged.connect(
            self.value_to_spinbox_changed)

    def range_disconnect(self, cset):
        "Disconnects range controls from event handlers"
        # See focus_changed above
        cset.value_from_slider.valueChanged.disconnect(
            self.value_from_slider_changed)
        cset.value_from_spinbox.valueChanged.disconnect(
            self.value_from_spinbox_changed)
        cset.value_to_slider.valueChanged.disconnect(
            self.value_to_slider_changed)
        cset.value_to_spinbox.valueChanged.disconnect(
            self.value_to_spinbox_changed)

    def percentile_from_slider_changed(self, value):
        "Handler for percentile_from_slider change event"
        self._current_set.percentile_to_spinbox.setMinimum(value / 100.0)
        self._current_set.percentile_from_spinbox.setValue(value / 100.0)
        self.invalidate_data_normalized()

    def percentile_to_slider_changed(self, value):
        "Handler for percentile_to_slider change event"
        self._current_set.percentile_from_spinbox.setMaximum(value / 100.0)
        self._current_set.percentile_to_spinbox.setValue(value / 100.0)
        self.invalidate_data_normalized()

    def percentile_from_spinbox_changed(self, value):
        "Handler for percentile_from_spinbox change event"
        self._current_set.percentile_to_spinbox.setMinimum(value)
        self._current_set.percentile_from_slider.setValue(int(value * 100.0))
        self._current_set.value_from_spinbox.setValue(
            self.data_sorted[
                (self.data_sorted.shape[0] - 1) * value / 100.0,
                self._current_set.index])
        self._current_set.value_from_slider.setValue(
            int(self._current_set.value_from_spinbox.value() * 100.0))
        self.invalidate_data_normalized()

    def percentile_to_spinbox_changed(self, value):
        "Handler for percentile_to_spinbox change event"
        self._current_set.percentile_from_spinbox.setMaximum(value)
        self._current_set.percentile_to_slider.setValue(int(value * 100.0))
        self._current_set.value_to_spinbox.setValue(
            self.data_sorted[
                (self.data_sorted.shape[0] - 1) * value / 100.0,
                self._current_set.index])
        self._current_set.value_to_slider.setValue(
            int(self._current_set.value_to_spinbox.value() * 100.0))
        self.invalidate_data_normalized()

    def value_from_slider_changed(self, value):
        "Handler for range_from_slider change event"
        cset = self._current_set
        cset.value_to_spinbox.setMinimum(value / 100.0)
        cset.value_from_spinbox.setValue(value / 100.0)
        self.invalidate_data_normalized()

    def value_to_slider_changed(self, value):
        "Handler for range_to_slider change event"
        cset = self._current_set
        cset.value_from_spinbox.setMaximum(value / 100.0)
        cset.value_to_spinbox.setValue(value / 100.0)
        self.invalidate_data_normalized()

    def value_from_spinbox_changed(self, value):
        "Handler for range_from_spinbox change event"
        cset = self._current_set
        cset.value_to_spinbox.setMinimum(value)
        cset.value_from_slider.setValue(int(value * 100.0))
        cset.percentile_from_spinbox.setValue(
            self.data_sorted[..., cset.index].searchsorted(value) * 100.0 / (self.data_sorted.shape[0] - 1))
        cset.percentile_from_slider.setValue(
            int(cset.percentile_from_spinbox.value() * 100.0))
        self.invalidate_data_normalized()

    def value_to_spinbox_changed(self, value):
        "Handler for range_to_spinbox change event"
        cset = self._current_set
        cset.value_from_spinbox.setMaximum(value)
        cset.value_to_slider.setValue(int(value * 100.0))
        cset.percentile_to_spinbox.setValue(
            self.data_sorted[..., cset.index].searchsorted(value) * 100.0 / (self.data_sorted.shape[0] - 1))
        cset.percentile_to_slider.setValue(
            int(cset.percentile_to_spinbox.value() * 100.0))
        self.invalidate_data_normalized()

    def channel_changed(self):
        "Handler for data channel change event"
        self.invalidate_data()
        self.crop_changed()

    def crop_changed(self, value=None):
        "Handler for crop_*_spinbox change event"
        self.invalidate_data_cropped()
        if self.data is not None:
            for cset in self._control_sets:
                cset.value_from_label.setText(
                    str(self.data_domain[cset.index].low))
                cset.value_to_label.setText(
                    str(self.data_domain[cset.index].high))
                cset.value_from_spinbox.setRange(
                    self.data_domain[cset.index].low,
                    self.data_domain[cset.index].high)
                cset.value_from_spinbox.setValue(self.data_sorted[
                    (self.data_sorted.shape[0] - 1) *
                    cset.percentile_from_spinbox.value() / 100.0, cset.index])
                cset.value_to_spinbox.setRange(
                    self.data_domain[cset.index].low,
                    self.data_domain[cset.index].high)
                cset.value_to_spinbox.setValue(self.data_sorted[
                    (self.data_sorted.shape[0] - 1) *
                    cset.percentile_to_spinbox.value() / 100.0, cset.index])
                cset.value_from_slider.setRange(
                    int(self.data_domain[cset.index].low * 100.0),
                    int(self.data_domain[cset.index].high * 100.0))
                cset.value_from_slider.setValue(
                    int(cset.value_from_spinbox.value() * 100.0))
                cset.value_to_slider.setRange(
                    int(self.data_domain[cset.index].low * 100.0),
                    int(self.data_domain[cset.index].high * 100.0))
                cset.value_to_slider.setValue(
                    int(cset.value_to_spinbox.value() * 100.0))
            y_size, x_size, _ = self.data_cropped.shape
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
    def red_channel(self):
        "Returns the currently selected red channel object"
        # We test self.ui here as during ui loading something
        # (connectSlotsByName) seems to iterate over all the properties
        # querying their value. As self.ui wasn't assigned at this point it led
        # to several annoying exceptions...
        if self.ui and (self.ui.red_channel_combo.currentIndex() != -1):
            return self.ui.red_channel_combo.itemData(
                self.ui.red_channel_combo.currentIndex()).toPyObject()

    @property
    def green_channel(self):
        "Returns the currently selected green channel object"
        # See note above about self.ui
        if self.ui and (self.ui.green_channel_combo.currentIndex() != -1):
            return self.ui.green_channel_combo.itemData(
                self.ui.green_channel_combo.currentIndex()).toPyObject()

    @property
    def blue_channel(self):
        "Returns the currently selected blue channel object"
        # See note above about self.ui
        if self.ui and (self.ui.blue_channel_combo.currentIndex() != -1):
            return self.ui.blue_channel_combo.itemData(
                self.ui.blue_channel_combo.currentIndex()).toPyObject()

    @property
    def data(self):
        "Returns the data of the combined channels"
        if self.ui and (self._data is None):
            self._data = np.zeros(
                (self._file.y_size, self._file.x_size, 3), np.float)
            for index, channel in enumerate((
                    self.red_channel,
                    self.green_channel,
                    self.blue_channel,
                    )):
                if channel:
                    self._data[..., index] = channel.data
        return self._data

    @property
    def data_cropped(self):
        "Returns the data after cropping"
        if (self._data_cropped is None) and (self.data is not None):
            top = self.ui.crop_top_spinbox.value()
            left = self.ui.crop_left_spinbox.value()
            bottom = self.data.shape[0] - self.ui.crop_bottom_spinbox.value()
            right = self.data.shape[1] - self.ui.crop_right_spinbox.value()
            self._data_cropped = self.data[top:bottom, left:right]
        return self._data_cropped

    @property
    def data_sorted(self):
        "Returns a flat, sorted array of the cropped data"
        if (self._data_sorted is None) and (self.data_cropped is not None):
            self._data_sorted = np.empty(
                (self.data_cropped.shape[0] * self.data_cropped.shape[1], 3))
            for index in range(3):
                self._data_sorted[..., index] = np.sort(
                    self.data_cropped[..., index], axis=None)
        return self._data_sorted

    @property
    def data_domain(self):
        "Returns a list of tuples of the value limits"
        if self.data_sorted is not None:
            return [
                Range(
                    self.data_sorted[..., index][0],
                    self.data_sorted[..., index][-1])
                for index in range(3)]

    @property
    def data_range(self):
        "Returns a list of tuples of the percentile values"
        if self.data_sorted is not None:
            return [
                Range(
                    self.ui.red_value_from_spinbox.value(),
                    self.ui.red_value_to_spinbox.value()),
                Range(
                    self.ui.green_value_from_spinbox.value(),
                    self.ui.green_value_to_spinbox.value()),
                Range(
                    self.ui.blue_value_from_spinbox.value(),
                    self.ui.blue_value_to_spinbox.value())]

    @property
    def data_normalized(self):
        "Returns the data normalized to a 0-1 range"
        if (self._data_normalized is None) and (self.data_cropped is not None):
            array = self.data_cropped.copy()
            for index in range(3):
                low, high = self.data_range[index]
                array[..., index][array[..., index] < low] = low
                array[..., index][array[..., index] > high] = high
                array[..., index] = array[..., index] - low
                if (high - low):
                    array[..., index] = array[..., index] / (high - low)
            self._data_normalized = array
        return self._data_normalized

    @property
    def data_flat(self):
        "Returns the normalized data flattened and sorted"
        if (self._data_flat is None) and (self.data_normalized is not None):
            self._data_flat = np.empty(
                (self.data_normalized.shape[0] * self.data_normalized.shape[1], 3))
            for index in range(3):
                self._data_flat[..., index] = self.data_normalized[..., index].flatten()
        return self._data_flat

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
        "Invalidate our copy of the data"
        self._data = None
        self.invalidate_data_cropped()

    def invalidate_data_cropped(self):
        "Invalidate our copy of the cropped data"
        self._data_cropped = None
        self.invalidate_data_sorted()

    def invalidate_data_sorted(self):
        "Invalidate our flat sorted version of the cropped data"
        self._data_sorted = None
        self.invalidate_data_normalized()

    def invalidate_data_normalized(self):
        "Invalidate our normalized version of the cropped data"
        self._data_normalized = None
        self.invalidate_data_flat()

    def invalidate_data_flat(self):
        "Invalidate our flattened normalized data"
        self._data_flat = None
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
        if self._file and self.data is not None:
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
            margin = (0.0, 0.75)[
                self.ui.axes_check.isChecked()
                or self.ui.histogram_check.isChecked()
                or bool(title)
            ]
            image_box = BoundingBox(
                margin,
                0.0,
                self.data_cropped.shape[0] / FIGURE_DPI,
                self.data_cropped.shape[1] / FIGURE_DPI
            )
            histogram_box = BoundingBox(
                margin,
                [0.0, margin][self.ui.histogram_check.isChecked()],
                image_box.width,
                [0.0, image_box.height * 0.8][
                    self.ui.histogram_check.isChecked()]
            )
            image_box.bottom = (
                margin + histogram_box.top
            )
            title_box = BoundingBox(
                0.0,
                [0.0, margin + image_box.top][bool(title)],
                image_box.width + (margin * 2),
                [0.0, 0.75][bool(title)]
            )
            figure_box = BoundingBox(
                0.0,
                0.0,
                image_box.width + (margin * 2),
                margin + (title_box.top if bool(title) else image_box.top)
            )
            # Draw the various image elements within bounding boxes calculated
            # from the metrics above
            image = self.draw_image(image_box.relative_to(figure_box))
            self.draw_histogram(histogram_box.relative_to(figure_box))
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
            self.data_normalized,
            origin='upper',
            extent=self.x_limits + self.y_limits,
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
            self.histogram_axes.hist(self.data_flat,
                bins=self.ui.histogram_bins_spinbox.value(),
                histtype='barstacked',
                color=('red', 'green', 'blue'))
        elif self.histogram_axes:
            self.figure.delaxes(self.histogram_axes)
            self.histogram_axes = None

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

