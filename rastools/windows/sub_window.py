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

from rastools.collections import Crop, Coord, Range, BoundingBox
from rastools.rasviewer.progress_dialog import ProgressDialog
from rastools.rasviewer.figure_canvas import FigureCanvas


DEFAULT_COLORMAP = 'gray'
DEFAULT_INTERPOLATION = 'nearest'
FIGURE_DPI = 72.0
ZOOM_THRESHOLD = 49
REDRAW_TIMEOUT_DEFAULT = 200
REDRAW_TIMEOUT_PAN = 100


class SubWindow(QtGui.QWidget):
    "Base class for rasviewer document windows"

    cropChanged = QtCore.pyqtSignal()

    def __init__(self, ui_file, data_file, channel_file=None):
        super(SubWindow, self).__init__(None)
        self._load_interface(ui_file)
        try:
            self._load_data(data_file, channel_file)
        except (ValueError, IOError) as exc:
            QtGui.QMessageBox.critical(self, self.tr('Error'), str(exc))
            self.close()
            return
        self._config_interface()
        self._config_handlers()
        self.channel_changed()

    def _load_interface(self, ui_file):
        "Called by __init__ to load the Qt interface file"
        self.ui = None
        self.ui = uic.loadUi(
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), ui_file)),
            self)

    def _load_data(self, data_file, channel_file=None):
        "Called by __init__ to load the data file"
        self._file = None
        self._progress = 0
        self._progress_update = None
        self._progress_dialog = None
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
        self.setWindowTitle(os.path.basename(data_file))

    def _config_interface(self):
        "Called by __init__ to configure the interface elements"
        self._info_dialog = None
        self._drag_start = None
        self._pan_id = None
        self._pan_crop = None
        self._zoom_id = None
        self._zoom_rect = None
        # Create a figure in a tab for the file
        self.figure = Figure(figsize=(5.0, 5.0), dpi=FIGURE_DPI,
            facecolor='w', edgecolor='w')
        self.canvas = FigureCanvas(self.figure)
        self.image_axes = self.figure.add_axes((0.1, 0.1, 0.8, 0.8))
        self.histogram_axes = None
        self.colorbar_axes = None
        self.title_axes = None
        self.ui.splitter.addWidget(self.canvas)
        # Set up the redraw timer
        self.redraw_timer = QtCore.QTimer()
        self.redraw_timer.setInterval(REDRAW_TIMEOUT_DEFAULT)
        self.redraw_timer.timeout.connect(self.redraw_timeout)
        # Set up the limits of the crop spinners
        self.ui.crop_left_spinbox.setRange(0, self._file.x_size - 1)
        self.ui.crop_right_spinbox.setRange(0, self._file.x_size - 1)
        self.ui.crop_top_spinbox.setRange(0, self._file.y_size - 1)
        self.ui.crop_bottom_spinbox.setRange(0, self._file.y_size - 1)
        # Configure the common combos
        default = -1
        for interpolation in sorted(matplotlib.image.AxesImage._interpd):
            if interpolation == DEFAULT_INTERPOLATION:
                default = self.ui.interpolation_combo.count()
            self.ui.interpolation_combo.addItem(interpolation)
        self.ui.interpolation_combo.setCurrentIndex(default)
        if hasattr(self.ui, 'colorbar_check'):
            default = -1
            for color in sorted(matplotlib.cm.datad):
                if not color.endswith('_r'):
                    if color == DEFAULT_COLORMAP:
                        default = self.ui.colormap_combo.count()
                    self.ui.colormap_combo.addItem(color)
            self.ui.colormap_combo.setCurrentIndex(default)

    def _config_handlers(self):
        "Called by __init__ to connect events to handlers"
        # Set up common event connections
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
        self.ui.splitter.splitterMoved.connect(self.splitter_moved)
        QtGui.QApplication.instance().focusChanged.connect(self.focus_changed)
        self.canvas.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.canvas_popup)
        if hasattr(self.ui, 'colorbar_check'):
            self.ui.colorbar_check.toggled.connect(self.invalidate_image)
            self.ui.colormap_combo.currentIndexChanged.connect(self.invalidate_image)
            self.ui.reverse_check.toggled.connect(self.invalidate_image)
        self.press_id = self.canvas.mpl_connect(
            'button_press_event', self.canvas_press)
        self.release_id = self.canvas.mpl_connect(
            'button_release_event', self.canvas_release)
        self.motion_id = self.canvas.mpl_connect(
            'motion_notify_event', self.canvas_motion)

    def splitter_moved(self, pos, index):
        self.invalidate_image()

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

    def canvas_popup(self, pos):
        "Handler for canvas context menu event"
        menu = QtGui.QMenu(self)
        menu.addAction(self.window().ui.zoom_mode_action)
        menu.addAction(self.window().ui.pan_mode_action)
        menu.addSeparator()
        menu.addAction(self.window().ui.zoom_in_action)
        menu.addAction(self.window().ui.zoom_out_action)
        menu.addAction(self.window().ui.reset_zoom_action)
        menu.addSeparator()
        menu.addAction(self.window().ui.home_axes_action)
        menu.addAction(self.window().ui.reset_axes_action)
        menu.popup(self.canvas.mapToGlobal(pos))

    def canvas_motion(self, event):
        "Handler for mouse movement over graph canvas"
        raise NotImplementedError

    def canvas_press(self, event):
        "Handler for mouse press on graph canvas"
        if event.button != 1:
            return
        if event.inaxes != self.image_axes:
            return
        self._drag_start = Coord(event.x, event.y)
        if self.window().ui.zoom_mode_action.isChecked():
            self._zoom_id = self.canvas.mpl_connect(
                'motion_notify_event', self.canvas_zoom_motion)
        elif self.window().ui.pan_mode_action.isChecked():
            self._pan_id = self.canvas.mpl_connect(
                'motion_notify_event', self.canvas_pan_motion)
            self._pan_crop = Crop(
                top=self.ui.crop_top_spinbox.value(),
                left=self.ui.crop_left_spinbox.value(),
                bottom=self.ui.crop_bottom_spinbox.value(),
                right=self.ui.crop_right_spinbox.value())
            self.redraw_timer.setInterval(REDRAW_TIMEOUT_PAN)

    def canvas_pan_motion(self, event):
        "Handler for mouse movement in pan mode"
        inverse = self.image_axes.transData.inverted()
        start_x, start_y = inverse.transform_point(self._drag_start)
        end_x, end_y = inverse.transform_point((event.x, event.y))
        delta = Coord(int(start_x - end_x), int(start_y - end_y))
        if (self._pan_crop.left + delta.x >= 0) and (self._pan_crop.right - delta.x >= 0):
            self.ui.crop_left_spinbox.setValue(self._pan_crop.left + delta.x)
            self.ui.crop_right_spinbox.setValue(self._pan_crop.right - delta.x)
        if (self._pan_crop.top + delta.y >= 0) and (self._pan_crop.bottom - delta.y >= 0):
            self.ui.crop_top_spinbox.setValue(self._pan_crop.top + delta.y)
            self.ui.crop_bottom_spinbox.setValue(self._pan_crop.bottom - delta.y)

    def canvas_zoom_motion(self, event):
        "Handler for mouse movement in zoom mode"
        # Calculate the display coordinates of the selection
        box_left, box_top, box_right, box_bottom = self.image_axes.bbox.extents
        height = self.figure.bbox.height
        band_left   = max(min(self._drag_start.x, event.x), box_left)
        band_right  = min(max(self._drag_start.x, event.x), box_right)
        band_top    = max(min(self._drag_start.y, event.y), box_top)
        band_bottom = min(max(self._drag_start.y, event.y), box_bottom)
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
        if (abs(data_right - data_left) * abs(data_bottom - data_top)) > ZOOM_THRESHOLD:
            self._zoom_rect = (data_left, data_top, data_right, data_bottom)
            self.window().statusBar().showMessage(
                self.tr(
                    'Crop from ({left:.0f}, {top:.0f}) to '
                    '({right:.0f}, {bottom:.0f})').format(
                        left=data_left, top=data_top,
                        right=data_right, bottom=data_bottom))
            self.canvas.drawRectangle(rectangle)
        else:
            self._zoom_rect = None
            self.window().statusBar().clearMessage()
            self.canvas.draw()

    def canvas_release(self, event):
        "Handler for mouse release on graph canvas"
        if self._pan_id:
            self.window().statusBar().clearMessage()
            self.canvas.mpl_disconnect(self._pan_id)
            self._pan_id = None
            self.redraw_timer.setInterval(REDRAW_TIMEOUT_DEFAULT)
        if self._zoom_id:
            self.window().statusBar().clearMessage()
            self.canvas.mpl_disconnect(self._zoom_id)
            self._zoom_id = None
            if self._zoom_rect:
                (   data_left,
                    data_top,
                    data_right,
                    data_bottom,
                ) = self._zoom_rect
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

    def channel_changed(self):
        "Handler for data channel change event"
        self.invalidate_data()
        self.crop_changed()

    def crop_changed(self, value=None):
        "Handler for crop_*_spinbox change event"
        self.cropChanged.emit()

    @property
    def zoom_factor(self):
        "Returns the percentage by which zoom in/out will operate"
        factor = 0.2
        height, width = self.data_cropped.shape[:2]
        return (max(1.0, width * factor), max(1.0, height * factor))

    @property
    def can_zoom_in(self):
        "Returns True if the image can be zoomed"
        height, width = self.data_cropped.shape[:2]
        x_factor, y_factor = self.zoom_factor
        return (width - x_factor * 2) * (height - y_factor * 2) > ZOOM_THRESHOLD

    @property
    def can_zoom_out(self):
        "Returns True if the image is zoomed"
        return (
            self.ui.crop_left_spinbox.value() > 0
            or self.ui.crop_right_spinbox.value() > 0
            or self.ui.crop_top_spinbox.value() > 0
            or self.ui.crop_bottom_spinbox.value())

    def zoom_in(self):
        "Zooms the image in by a fixed amount"
        x_factor, y_factor = self.zoom_factor
        self.ui.crop_left_spinbox.setValue(
            self.ui.crop_left_spinbox.value() + x_factor)
        self.ui.crop_right_spinbox.setValue(
            self.ui.crop_right_spinbox.value() + x_factor)
        self.ui.crop_top_spinbox.setValue(
            self.ui.crop_top_spinbox.value() + y_factor)
        self.ui.crop_bottom_spinbox.setValue(
            self.ui.crop_bottom_spinbox.value() + y_factor)

    def zoom_out(self):
        "Zooms the image out by a fixed amount"
        x_factor, y_factor = self.zoom_factor
        self.ui.crop_left_spinbox.setValue(
            max(0.0, self.ui.crop_left_spinbox.value() - x_factor))
        self.ui.crop_right_spinbox.setValue(
            max(0.0, self.ui.crop_right_spinbox.value() - x_factor))
        self.ui.crop_top_spinbox.setValue(
            max(0.0, self.ui.crop_top_spinbox.value() - y_factor))
        self.ui.crop_bottom_spinbox.setValue(
            max(0.0, self.ui.crop_bottom_spinbox.value() - y_factor))

    def reset_zoom(self):
        "Handler for reset_zoom_action triggered event"
        self.ui.crop_left_spinbox.setValue(0)
        self.ui.crop_right_spinbox.setValue(0)
        self.ui.crop_top_spinbox.setValue(0)
        self.ui.crop_bottom_spinbox.setValue(0)

    def reset_axes(self):
        "Handler for the reset_axes_action triggered event"
        self.ui.scale_locked_check.setChecked(True)
        self.ui.x_scale_spinbox.setValue(1.0)
        self.ui.y_scale_spinbox.setValue(1.0)
        self.ui.offset_locked_check.setChecked(True)
        self.ui.x_offset_spinbox.setValue(0.0)
        self.ui.y_offset_spinbox.setValue(0.0)

    def home_axes(self):
        "Handler for home_axes_action triggered event"
        self.ui.scale_locked_check.setChecked(True)
        self.ui.x_scale_spinbox.setValue(1.0)
        self.ui.y_scale_spinbox.setValue(1.0)
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
        raise NotImplementedError

    def clear_title_clicked(self):
        "Handler for clear_title_button click event"
        self.ui.title_edit.clear()

    def title_info_clicked(self, items):
        "Handler for title_info_button click event"
        from rastools.rasviewer.title_info_dialog import TitleInfoDialog
        if not self._info_dialog:
            self._info_dialog = TitleInfoDialog(self)
        self._info_dialog.ui.template_list.clear()
        for key, value in sorted(self.format_dict().items()):
            if isinstance(value, type('')):
                if '\n' in value:
                    value = value.splitlines()[0].rstrip()
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        ['{{{0}}}'.format(key), value]))
            elif isinstance(value, int):
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        ['{{{0}}}'.format(key), '{0}'.format(value)]))
                if 0 < value < 10:
                    self._info_dialog.ui.template_list.addTopLevelItem(
                        QtGui.QTreeWidgetItem(
                            ['{{{0}:02d}}'.format(key), '{0:02d}'.format(value)]))
            elif isinstance(value, float):
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        ['{{{0}}}'.format(key), '{0}'.format(value)]))
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        ['{{{0}:.2f}}'.format(key), '{0:.2f}'.format(value)]))
            elif isinstance(value, dt.datetime):
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        ['{{{0}}}'.format(key), '{0}'.format(value)]))
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        ['{{{0}:%Y-%m-%d}}'.format(key),
                            '{0:%Y-%m-%d}'.format(value)]))
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        ['{{{0}:%H:%M:%S}}'.format(key),
                            '{0:%H:%M:%S}'.format(value)]))
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        ['{{{0}:%A, %d %b %Y, %H:%M:%S}}'.format(key),
                            '{0:%A, %d %b %Y, %H:%M:%S}'.format(value)]))
            else:
                self._info_dialog.ui.template_list.addTopLevelItem(
                    QtGui.QTreeWidgetItem(
                        ['{{{0}}}'.format(key), '{0}'.format(value)]))
        self._info_dialog.show()

    @property
    def data(self):
        "Returns the original data array"
        raise NotImplementedError

    @property
    def data_cropped(self):
        "Returns the data after cropping"
        raise NotImplementedError

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

    @property
    def axes_visible(self):
        "Returns True if the axes should be shown"
        return hasattr(self.ui, 'axes_check') and self.ui.axes_check.isChecked()

    @property
    def colorbar_visible(self):
        "Returns True if the colorbar should be shown"
        return hasattr(self.ui, 'colorbar_check') and self.ui.colorbar_check.isChecked()

    @property
    def histogram_visible(self):
        "Returns True if the histogram should be shown"
        return hasattr(self.ui, 'histogram_check') and self.ui.histogram_check.isChecked()

    @property
    def margin_visible(self):
        "Returns True if the image margins should be shown"
        return (
            self.axes_visible
            or self.histogram_visible
            or self.colorbar_visible
            or bool(self.image_title))

    @property
    def x_margin(self):
        "Returns the size of the left and right margins when drawing"
        return 0.75 if self.margin_visible else 0.0

    @property
    def y_margin(self):
        "Returns the size of the top and bottom margins when drawing"
        return 0.25 if self.margin_visible else 0.0

    @property
    def sep_margin(self):
        "Returns the size of the separator between image elements"
        return 0.3

    @property
    def image_title(self):
        "Returns the text of the image title after substitution"
        result = ''
        try:
            if self.ui.title_edit.toPlainText():
                result = str(self.ui.title_edit.toPlainText()).format(
                    **self.format_dict())
        except KeyError as exc:
            self.ui.title_error_label.setText(
                'Unknown template "{}"'.format(exc))
            self.ui.title_error_label.show()
        except ValueError as exc:
            self.ui.title_error_label.setText(str(exc))
            self.ui.title_error_label.show()
        else:
            self.ui.title_error_label.hide()
        return result

    @property
    def figure_box(self):
        "Returns the overall bounding box"
        return BoundingBox(
            0.0,
            0.0,
            self.figure.get_figwidth(),
            self.figure.get_figheight()
        )

    @property
    def colorbar_box(self):
        "Returns the colorbar bounding box"
        return BoundingBox(
            self.x_margin,
            self.y_margin,
            self.figure_box.width - (self.x_margin * 2),
            0.5 if self.colorbar_visible else 0.0)

    @property
    def title_box(self):
        "Returns the title bounding box"
        return BoundingBox(
            self.x_margin,
            self.figure_box.height - (self.y_margin + 1.0 if bool(self.image_title) else 0.0),
            self.figure_box.width - (self.x_margin * 2),
            1.0 if bool(self.image_title) else 0.0
        )

    @property
    def histogram_box(self):
        "Returns the histogram bounding box"
        return BoundingBox(
            self.x_margin,
            self.colorbar_box.top + (
                self.sep_margin if self.colorbar_visible else 0.0),
            self.figure_box.width - (self.x_margin * 2),
            (
                self.figure_box.height -
                (self.y_margin * 2) -
                self.colorbar_box.height -
                self.title_box.height -
                (self.sep_margin if self.colorbar_visible else 0.0) -
                (self.sep_margin if bool(self.image_title) else 0.0)
            ) / 2.0 if self.histogram_visible else 0.0
        )

    @property
    def image_box(self):
        "Returns the image bounding box"
        return BoundingBox(
            self.x_margin,
            self.histogram_box.top + (
                self.sep_margin if self.colorbar_visible or self.histogram_visible else 0.0),
            self.figure_box.width - (self.x_margin * 2),
            (
                self.figure_box.height -
                (self.y_margin * 2) -
                self.colorbar_box.height -
                self.title_box.height -
                self.histogram_box.height -
                (self.sep_margin if self.colorbar_visible else 0.0) -
                (self.sep_margin if self.histogram_visible else 0.0) -
                (self.sep_margin if bool(self.image_title) else 0.0)
            )
        )

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
            # Draw the various image elements within bounding boxes calculated
            # from the metrics above
            image = self.draw_image()
            self.draw_histogram()
            self.draw_colorbar(image)
            self.draw_title()
            self.canvas.draw()

    def draw_image(self):
        "Draws the image of the data within the specified figure"
        raise NotImplementedError

    def draw_histogram(self):
        "Draws the data's historgram within the figure"
        raise NotImplementedError

    def draw_colorbar(self, image):
        "Draws a range color-bar within the figure"
        raise NotImplementedError

    def draw_title(self):
        "Draws a title within the specified figure"
        box = self.title_box.relative_to(self.figure_box)
        if bool(self.image_title):
            if self.title_axes is None:
                self.title_axes = self.figure.add_axes(box)
            else:
                self.title_axes.clear()
                self.title_axes.set_position(box)
            self.title_axes.set_axis_off()
            # Render the title
            self.title_axes.text(0.5, 0, self.image_title,
                horizontalalignment='center', verticalalignment='baseline',
                multialignment='center', size='medium', family='sans-serif',
                transform=self.title_axes.transAxes)
        elif self.title_axes:
            self.figure.delaxes(self.title_axes)
            self.title_axes = None

    def format_dict(self):
        "Returns UI settings in a dict for use in format substitutions"
        raise NotImplementedError


