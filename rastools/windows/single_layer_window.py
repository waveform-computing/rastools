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
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

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
from rastools.rasviewer.sub_window import SubWindow


class SingleLayerWindow(SubWindow):
    "Document window for the single-layer view"

    def __init__(self, data_file, channel_file=None):
        self._data = None
        self._data_sorted = None
        self._data_cropped = None
        super(SingleLayerWindow, self).__init__(
            'single_layer_window.ui', data_file, channel_file)

    def _config_interface(self):
        super(SingleLayerWindow, self)._config_interface()
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

    def _config_handlers(self):
        super(SingleLayerWindow, self)._config_handlers()
        # Set up the event connections and a timer to handle delayed redrawing
        self.ui.channel_combo.currentIndexChanged.connect(self.channel_changed)

    def canvas_motion(self, event):
        "Handler for mouse movement over graph canvas"
        if (self.image_axes and
                (event.inaxes == self.image_axes) and
                (event.xdata is not None)):
            self.window().ui.x_label.setText(
                'X: {0:d}'.format(int(event.xdata)))
            self.window().ui.y_label.setText(
                'Y: {0:d}'.format(int(event.ydata)))
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
            self.data_sorted[
                min(
                    len(self.data_sorted) - 1,
                    int(len(self.data_sorted) * value / 100.0))])
        self.ui.value_from_slider.setValue(
            int(self.ui.value_from_spinbox.value() * 100.0))
        self.invalidate_image()

    def percentile_to_spinbox_changed(self, value):
        "Handler for percentile_to_spinbox change event"
        self.ui.percentile_from_spinbox.setMaximum(value)
        self.ui.percentile_to_slider.setValue(int(value * 100.0))
        self.ui.value_to_spinbox.setValue(
            self.data_sorted[
                min(
                    len(self.data_sorted) - 1,
                    int(len(self.data_sorted) * value / 100.0))])
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
            ((self.data_sorted.searchsorted(value) + 1) * 100.0 /
            len(self.data_sorted)) - 1)
        self.ui.percentile_from_slider.setValue(
            int(self.ui.percentile_from_spinbox.value() * 100.0))
        self.invalidate_image()

    def value_to_spinbox_changed(self, value):
        "Handler for range_to_spinbox change event"
        self.ui.value_from_spinbox.setMaximum(value)
        self.ui.value_to_slider.setValue(int(value * 100.0))
        self.ui.percentile_to_spinbox.setValue(
            ((self.data_sorted.searchsorted(value) + 1) * 100.0 /
            len(self.data_sorted)) - 1)
        self.ui.percentile_to_slider.setValue(
            int(self.ui.percentile_to_spinbox.value() * 100.0))
        self.invalidate_image()

    def crop_changed(self, value=None):
        "Handler for crop_*_spinbox change event"
        super(SingleLayerWindow, self).crop_changed(value)
        self.invalidate_data_cropped()
        if self.data is not None:
            self.ui.value_from_label.setText(str(self.data_domain.low))
            self.ui.value_to_label.setText(str(self.data_domain.high))
            self.ui.value_from_spinbox.setRange(
                self.data_domain.low,
                self.data_domain.high)
            self.ui.value_from_spinbox.setValue(
                self.data_sorted[
                    min(
                        len(self.data_sorted) - 1,
                        int(len(self.data_sorted) *
                            self.ui.percentile_from_spinbox.value() / 100.0))])
            self.ui.value_to_spinbox.setRange(
                self.data_domain.low,
                self.data_domain.high)
            self.ui.value_to_spinbox.setValue(
                self.data_sorted[
                    min(
                        len(self.data_sorted) - 1,
                        int(len(self.data_sorted) *
                            self.ui.percentile_to_spinbox.value() / 100.0))])
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

    def default_title_clicked(self):
        "Handler for default_title_button click event"
        self.ui.title_edit.setPlainText("""\
Channel {channel:02d} - {channel_name}
{start_time:%A, %d %b %Y %H:%M:%S}
Percentile range: {percentile_from} to {percentile_to}
Value range: {range_from} to {range_to}""")

    @property
    def channel(self):
        "Returns the currently selected channel object"
        # We test self.ui here as during ui loading something
        # (connectSlotsByName) seems to iterate over all the properties
        # querying their value. As self.ui wasn't assigned at this point it led
        # to several annoying exceptions...
        if self.ui and (self.ui.channel_combo.currentIndex() != -1):
            return self.ui.channel_combo.itemData(
                self.ui.channel_combo.currentIndex())

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
    def margin_visible(self):
        "Returns True if the image margins should be shown"
        return (
            super(SingleLayerWindow, self).margin_visible or
            self.ui.colorbar_check.isChecked()
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

    def draw_image(self):
        "Draws the image of the data within the specified figure"
        # Position the axes in which to draw the channel data
        self.image_axes.clear()
        self.image_axes.set_position(
            self.image_box.relative_to(self.figure_box))
        # Configure the x and y axes appearance
        self.image_axes.set_frame_on(
            self.axes_visible or self.ui.grid_check.isChecked())
        self.image_axes.set_axis_on()
        if self.ui.grid_check.isChecked():
            self.image_axes.grid(color='k', linestyle='-')
        else:
            self.image_axes.grid(False)
        if self.axes_visible:
            if self.ui.x_label_edit.text():
                self.image_axes.set_xlabel(self.ui.x_label_edit.text())
            if self.ui.y_label_edit.text():
                self.image_axes.set_ylabel(self.ui.y_label_edit.text())
        else:
            self.image_axes.set_xticks([], False)
            self.image_axes.set_yticks([], False)
        # The imshow() call takes care of clamping values with data_range and
        # color-mapping
        return self.image_axes.imshow(
            self.data_cropped,
            vmin=self.data_range.low, vmax=self.data_range.high,
            origin='upper',
            extent=self.x_limits + self.y_limits,
            cmap=matplotlib.cm.get_cmap(
                self.ui.colormap_combo.currentText() +
                ('_r' if self.ui.reverse_check.isChecked() else '')
            ),
            interpolation=self.ui.interpolation_combo.currentText())

    def draw_histogram(self):
        "Draws the data's historgram within the figure"
        box = self.histogram_box.relative_to(self.figure_box)
        if self.histogram_visible:
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

    def draw_colorbar(self, image):
        "Draws a range color-bar within the figure"
        box = self.colorbar_box.relative_to(self.figure_box)
        if self.colorbar_visible:
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

    def format_dict(self):
        "Returns UI settings in a dict for use in format substitutions"
        return self.channel.format_dict(
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
        )

