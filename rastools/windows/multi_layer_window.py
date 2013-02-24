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


class ControlSet(object):
    def __init__(self, index, prefix, **kwargs):
        self.index = index
        self.prefix = prefix
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
        self.percentile_from_button = kwargs['percentile_from_button']
        self.percentile_to_button = kwargs['percentile_to_button']


class MultiLayerWindow(SubWindow):
    "Document window for the multi-layer view"

    def __init__(self, data_file, channel_file=None):
        self._data = None
        self._data_sorted = None
        self._data_cropped = None
        self._data_normalized = None
        self._data_flat = None
        super(MultiLayerWindow, self).__init__(
            'multi_layer_window.ui', data_file, channel_file)

    def _config_interface(self):
        self._current_set = None
        self._control_sets = [
            ControlSet(
                index=0,
                prefix='red',
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
                percentile_to_slider=self.ui.red_percentile_to_slider,
                percentile_from_button=self.ui.red_percentile_from_button,
                percentile_to_button=self.ui.red_percentile_to_button),
            ControlSet(
                index=1,
                prefix='green',
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
                percentile_to_slider=self.ui.green_percentile_to_slider,
                percentile_from_button=self.ui.green_percentile_from_button,
                percentile_to_button=self.ui.green_percentile_to_button),
            ControlSet(
                index=2,
                prefix='blue',
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
                percentile_to_slider=self.ui.blue_percentile_to_slider,
                percentile_from_button=self.ui.blue_percentile_from_button,
                percentile_to_button=self.ui.blue_percentile_to_button)]
        super(MultiLayerWindow, self)._config_interface()
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

    def _config_handlers(self):
        super(MultiLayerWindow, self)._config_handlers()
        # Set up the event connections and a timer to handle delayed redrawing
        for cset in self._control_sets:
            cset.channel_combo.currentIndexChanged.connect(self.channel_changed)
            cset.percentile_from_button.clicked.connect(self.percentile_from_clicked)
            cset.percentile_to_button.clicked.connect(self.percentile_to_clicked)

    def canvas_motion(self, event):
        "Handler for mouse movement over graph canvas"
        labels = (
            ('Red', self.window().ui.red_label),
            ('Green', self.window().ui.green_label),
            ('Blue', self.window().ui.blue_label))
        if (self.image_axes and
                (event.inaxes == self.image_axes) and
                (event.xdata is not None)):
            self.window().ui.x_label.setText(
                'X: {0:d}'.format(int(event.xdata)))
            self.window().ui.y_label.setText(
                'Y: {0:d}'.format(int(event.ydata)))
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
                min(
                    self.data_sorted.shape[0] - 1,
                    int(self.data_sorted.shape[0] * value / 100.0)),
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
                min(
                    self.data_sorted.shape[0] - 1,
                    int(self.data_sorted.shape[0] * value / 100.0)),
                self._current_set.index])
        self._current_set.value_to_slider.setValue(
            int(self._current_set.value_to_spinbox.value() * 100.0))
        self.invalidate_data_normalized()

    def percentile_from_clicked(self):
        "Handler for Percentile From Set button"
        cset_save = self._current_set
        try:
            value = cset_save.percentile_from_spinbox.value()
            for cset in self._control_sets:
                self._current_set = cset
                cset.percentile_from_spinbox.setValue(value)
                self.percentile_from_spinbox_changed(value)
        finally:
            self._current_set = cset_save

    def percentile_to_clicked(self):
        "Handler for Percentile To Set button"
        cset_save = self._current_set
        try:
            value = cset_save.percentile_to_spinbox.value()
            for cset in self._control_sets:
                self._current_set = cset
                cset.percentile_to_spinbox.setValue(value)
                self.percentile_to_spinbox_changed(value)
        finally:
            self._current_set = cset_save

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
            ((self.data_sorted[..., cset.index].searchsorted(value) + 1) * 100.0 /
            self.data_sorted.shape[0]) - 1)
        cset.percentile_from_slider.setValue(
            int(cset.percentile_from_spinbox.value() * 100.0))
        self.invalidate_data_normalized()

    def value_to_spinbox_changed(self, value):
        "Handler for range_to_spinbox change event"
        cset = self._current_set
        cset.value_from_spinbox.setMaximum(value)
        cset.value_to_slider.setValue(int(value * 100.0))
        cset.percentile_to_spinbox.setValue(
            ((self.data_sorted[..., cset.index].searchsorted(value) + 1) * 100.0 /
            self.data_sorted.shape[0]) - 1)
        cset.percentile_to_slider.setValue(
            int(cset.percentile_to_spinbox.value() * 100.0))
        self.invalidate_data_normalized()

    def crop_changed(self, value=None):
        "Handler for crop_*_spinbox change event"
        super(MultiLayerWindow, self).crop_changed(value)
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
                    min(
                        self.data_sorted.shape[0] - 1,
                        int(self.data_sorted.shape[0] *
                            cset.percentile_from_spinbox.value() / 100.0)),
                    cset.index])
                cset.value_to_spinbox.setRange(
                    self.data_domain[cset.index].low,
                    self.data_domain[cset.index].high)
                cset.value_to_spinbox.setValue(self.data_sorted[
                    min(
                        self.data_sorted.shape[0] - 1,
                        int(self.data_sorted.shape[0] *
                            cset.percentile_to_spinbox.value() / 100.0)),
                    cset.index])
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

    def default_title_clicked(self):
        "Handler for default_title_button click event"
        title = 'Multi-Layered Image'
        for channel, cset in zip(self.channels, self._control_sets):
            if channel:
                title += '\n{prefix}: {{{prefix}_channel:02d}} - {{{prefix}_channel_name}}'.format(prefix=cset.prefix)
        self.ui.title_edit.setPlainText(title)

    @property
    def red_channel(self):
        "Returns the currently selected red channel object"
        # We test self.ui here as during ui loading something
        # (connectSlotsByName) seems to iterate over all the properties
        # querying their value. As self.ui wasn't assigned at this point it led
        # to several annoying exceptions...
        if self.ui and (self.ui.red_channel_combo.currentIndex() != -1):
            return self.ui.red_channel_combo.itemData(
                self.ui.red_channel_combo.currentIndex())

    @property
    def green_channel(self):
        "Returns the currently selected green channel object"
        # See note above about self.ui
        if self.ui and (self.ui.green_channel_combo.currentIndex() != -1):
            return self.ui.green_channel_combo.itemData(
                self.ui.green_channel_combo.currentIndex())

    @property
    def blue_channel(self):
        "Returns the currently selected blue channel object"
        # See note above about self.ui
        if self.ui and (self.ui.blue_channel_combo.currentIndex() != -1):
            return self.ui.blue_channel_combo.itemData(
                self.ui.blue_channel_combo.currentIndex())

    @property
    def channels(self):
        "Returns the selected channels as a three-tuple"
        return (self.red_channel, self.green_channel, self.blue_channel)

    @property
    def data(self):
        "Returns the data of the combined channels"
        if self.ui and (self._data is None):
            self._data = np.zeros(
                (self._file.y_size, self._file.x_size, 3), np.float)
            for index, channel in enumerate(self.channels):
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
        # Here we tweak values outside the normalized 0.0 and 1.0 range just
        # before drawing. This is not done in data_normalized as otherwise
        # histograms derived from the flattened version of the data wind up
        # with clumps of data at the extremes of the range when percentiles are
        # applied
        data = self.data_normalized.copy()
        data[data < 0.0] = 0.0
        data[data > 1.0] = 1.0
        return self.image_axes.imshow(
            data,
            origin='upper',
            extent=self.x_limits + self.y_limits,
            interpolation=self.ui.interpolation_combo.currentText())

    def draw_histogram(self):
        "Draws the data's historgram within the figure"
        box = self.histogram_box.relative_to(self.figure_box)
        if self.ui.histogram_check.isChecked():
            if self.histogram_axes is None:
                self.histogram_axes = self.figure.add_axes(box)
            else:
                self.histogram_axes.clear()
                self.histogram_axes.set_position(box)
            self.histogram_axes.grid(True)
            self.histogram_axes.hist(
                self.data_flat,
                bins=self.ui.histogram_bins_spinbox.value(),
                histtype='barstacked',
                color=('red', 'green', 'blue'),
                range=(0.0, 1.0))
        elif self.histogram_axes:
            self.figure.delaxes(self.histogram_axes)
            self.histogram_axes = None

    def draw_colorbar(self, image):
        pass

    def format_dict(self):
        "Returns UI settings in a dict for use in format substitutions"
        result = dict(
            interpolation=self.interpolation_combo.currentText(),
            crop_left=self.ui.crop_left_spinbox.value(),
            crop_top=self.ui.crop_top_spinbox.value(),
            crop_right=self.ui.crop_right_spinbox.value(),
            crop_bottom=self.ui.crop_bottom_spinbox.value())
        for channel, cset in zip(self.channels, self._control_sets):
            if channel:
                for name, value in channel.format_dict().items():
                    result[cset.prefix + '_' + name] = value
        return result

