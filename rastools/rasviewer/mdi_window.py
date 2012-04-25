import os
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.cm
import matplotlib.image
from PyQt4 import QtCore, QtGui, uic
import numpy as np
import time

DEFAULT_COLORMAP = 'gray'
DEFAULT_INTERPOLATION = 'nearest'
FIGURE_DPI = 72.0

class MDIWindow(QtGui.QWidget):
    def __init__(self, data_file, channel_file):
        super(MDIWindow, self).__init__(None)
        self.ui = uic.loadUi(os.path.abspath(os.path.join(os.path.dirname(__file__), 'mdi_window.ui')), self)
        self._data = None
        self._data_sorted = None
        self._file = None
        self._progress = 0
        self._progress_update = None
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
        self.ui.splitter.addWidget(self.canvas)
        # Fill out the combos
        for channel in self._file.channels:
            if channel.enabled:
                if channel.name:
                    self.ui.channel_combo.addItem(str(self.tr('Channel %d - %s')) % (channel.index, channel.name), channel)
                else:
                    self.ui.channel_combo.addItem(str(self.tr('Channel %d')) % channel.index, channel)
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
        self.ui.channel_combo.currentIndexChanged.connect(self.invalidate_data)
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
        QtGui.QApplication.instance().focusChanged.connect(self.focus_changed)
        self.setWindowTitle(os.path.basename(data_file))
        self.crop_changed()
        self.invalidate_data()

    def focus_changed(self, old_widget, new_widget):
        percentile_controls = (
            self.ui.percentile_from_slider,
            self.ui.percentile_from_spinbox,
            self.ui.percentile_to_slider,
            self.ui.percentile_to_spinbox,
        )
        range_controls = (
            self.ui.range_from_slider,
            self.ui.range_from_spinbox,
            self.ui.range_to_slider,
            self.ui.range_to_spinbox,
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
        self.window().statusBar().showMessage('Loading channel data')

    def progress_update(self, progress):
        now = time.time()
        if (self._progress_update is None) or (now - self._progress_update) > 0.2:
            self._progress_update = now
            if progress != self._progress:
                self.window().statusBar().showMessage('Loading channel data... %d%%' % progress)
                self._progress = progress

    def progress_finish(self):
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
        self.ui.range_from_slider.valueChanged.connect(self.range_from_slider_changed)
        self.ui.range_from_spinbox.valueChanged.connect(self.range_from_spinbox_changed)
        self.ui.range_to_slider.valueChanged.connect(self.range_to_slider_changed)
        self.ui.range_to_spinbox.valueChanged.connect(self.range_to_spinbox_changed)

    def range_disconnect(self):
        self.ui.range_from_slider.valueChanged.disconnect(self.range_from_slider_changed)
        self.ui.range_from_spinbox.valueChanged.disconnect(self.range_from_spinbox_changed)
        self.ui.range_to_slider.valueChanged.disconnect(self.range_to_slider_changed)
        self.ui.range_to_spinbox.valueChanged.disconnect(self.range_to_spinbox_changed)

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
        self.ui.range_from_spinbox.setValue(self.data_sorted[(len(self.data_sorted) - 1) * value / 100.0])
        self.ui.range_from_slider.setValue(int(self.ui.range_from_spinbox.value() * 100.0))
        self.invalidate_image()

    def percentile_to_spinbox_changed(self, value):
        self.ui.percentile_from_spinbox.setMaximum(value)
        self.ui.percentile_to_slider.setValue(int(value * 100.0))
        self.ui.range_to_spinbox.setValue(self.data_sorted[(len(self.data_sorted) - 1) * value / 100.0])
        self.ui.range_to_slider.setValue(int(self.ui.range_to_spinbox.value() * 100.0))
        self.invalidate_image()

    def range_from_slider_changed(self, value):
        self.ui.range_to_spinbox.setMinimum(value / 100.0)
        self.ui.range_from_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def range_to_slider_changed(self, value):
        self.ui.range_from_spinbox.setMaximum(value / 100.0)
        self.ui.range_to_spinbox.setValue(value / 100.0)
        self.invalidate_image()

    def range_from_spinbox_changed(self, value):
        self.ui.range_to_spinbox.setMinimum(value)
        self.ui.range_from_slider.setValue(int(value * 100.0))
        self.ui.percentile_from_spinbox.setValue(self.data_sorted.searchsorted(value) * 100.0 / (len(self.data_sorted) - 1))
        self.ui.percentile_from_slider.setValue(int(self.ui.percentile_from_spinbox.value() * 100.0))
        self.invalidate_image()

    def range_to_spinbox_changed(self, value):
        self.ui.range_from_spinbox.setMaximum(value)
        self.ui.range_to_slider.setValue(int(value * 100.0))
        self.ui.percentile_to_spinbox.setValue(self.data_sorted.searchsorted(value) * 100.0 / (len(self.data_sorted) - 1))
        self.ui.percentile_to_slider.setValue(int(self.ui.percentile_to_spinbox.value() * 100.0))
        self.invalidate_image()

    def crop_changed(self, value=None):
        self.ui.x_size_label.setText(str(self._file.x_size - self.ui.crop_left_spinbox.value() - self.ui.crop_right_spinbox.value()))
        self.ui.y_size_label.setText(str(self._file.y_size - self.ui.crop_top_spinbox.value() - self.ui.crop_bottom_spinbox.value()))
        self.invalidate_data()

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

    @property
    def channel(self):
        if self.ui.channel_combo.currentIndex() != -1:
            return self.ui.channel_combo.itemData(
                self.ui.channel_combo.currentIndex()).toPyObject()

    @property
    def data(self):
        if self._data is None:
            self._data = np.array(self.channel.data, np.float)
            self._data = self._data[
                self.ui.crop_top_spinbox.value():self._data.shape[0] - self.ui.crop_bottom_spinbox.value(),
                self.ui.crop_left_spinbox.value():self._data.shape[1] - self.ui.crop_right_spinbox.value()
            ]
            self._data_sorted = np.sort(self._data, None)
            self.ui.range_from_spinbox.setRange(self._data_sorted[0], self._data_sorted[-1])
            self.ui.range_from_spinbox.setValue(self._data_sorted[(len(self._data_sorted) - 1) * self.ui.percentile_from_spinbox.value() / 100.0])
            self.ui.range_to_spinbox.setRange(self._data_sorted[0], self._data_sorted[-1])
            self.ui.range_to_spinbox.setValue(self._data_sorted[(len(self._data_sorted) - 1) * self.ui.percentile_to_spinbox.value() / 100.0])
            self.ui.range_from_slider.setRange(int(self._data_sorted[0] * 100.0), int(self._data_sorted[-1] * 100.0))
            self.ui.range_from_slider.setValue(int(self.ui.range_from_spinbox.value() * 100.0))
            self.ui.range_to_slider.setRange(int(self._data_sorted[0] * 100.0), int(self._data_sorted[-1] * 100.0))
            self.ui.range_to_slider.setValue(int(self.ui.range_to_spinbox.value() * 100.0))
        return self._data

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

    @property
    def data_sorted(self):
        self.data
        return self._data_sorted

    def invalidate_data(self):
        self._data = None
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
            pmin = self.ui.range_from_spinbox.value()
            pmax = self.ui.range_to_spinbox.value()
            # Calculate the figure dimensions and margins, and construct the
            # necessary objects
            (img_width, img_height) = (
                (self.channel.parent.x_size - self.ui.crop_left_spinbox.value() - self.ui.crop_right_spinbox.value()) / FIGURE_DPI,
                (self.channel.parent.y_size - self.ui.crop_top_spinbox.value() - self.ui.crop_bottom_spinbox.value()) / FIGURE_DPI
            )
            (hist_width, hist_height) = ((0.0, 0.0), (img_width, img_height))[self.ui.histogram_check.isChecked()]
            (cbar_width, cbar_height) = ((0.0, 0.0), (img_width, 1.0))[self.ui.colorbar_check.isChecked()]
            (head_width, head_height) = ((0.0, 0.0), (img_width, 0.75))[False] # XXX Add title editor
            margin = (0.0, 0.5)[
                self.ui.axes_check.isChecked()
                or self.ui.colorbar_check.isChecked()
                or self.ui.histogram_check.isChecked()
                or bool(False)] # XXX Add title
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
                if unicode(self.ui.x_label_edit.text()):
                    self.image_axes.set_xlabel(self.ui.x_label_edit.text())
                if unicode(self.ui.y_label_edit.text()):
                    self.image_axes.set_ylabel(self.ui.y_label_edit.text())
            else:
                self.image_axes.set_xticklabels([])
                self.image_axes.set_yticklabels([])
            # Draw the image. This call takes care of clamping values with vmin
            # and vmax, as well as color-mapping
            img = self.image_axes.imshow(self.data, vmin=pmin, vmax=pmax,
                extent=(
                    self.ui.x_offset_spinbox.value(),
                    self.ui.x_offset_spinbox.value() + (self.ui.x_scale_spinbox.value() * (self._file.x_size - self.ui.crop_left_spinbox.value() - self.ui.crop_right_spinbox.value())),
                    self.ui.y_offset_spinbox.value() + (self.ui.y_scale_spinbox.value() * (self._file.y_size - self.ui.crop_top_spinbox.value() - self.ui.crop_bottom_spinbox.value())),
                    self.ui.y_offset_spinbox.value(),
                ),
                origin='upper',
                cmap=matplotlib.cm.get_cmap(
                    str(self.ui.colormap_combo.currentText()) +
                    ('_r' if self.ui.reverse_check.isChecked() else '')
                ),
                interpolation=str(self.ui.interpolation_combo.currentText())
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
                self.histogram_axes.hist(self.data.flat,
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
            self.canvas.draw()

