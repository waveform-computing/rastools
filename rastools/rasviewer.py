#!/usr/bin/env python

import os
import sys
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.cm
import matplotlib.image
from PyQt4 import QtCore, QtGui
from rastools.rasview_main import Ui_MainWindow
from rastools.rasview_open import Ui_OpenDialog
from rastools.rasview_mdi import Ui_MDIWindow
from rastools.parsers import PARSERS
import numpy as np

__version__ = '0.1'
FIGURE_DPI = 72.0
DEFAULT_INTERPOLATION = 'nearest'
DEFAULT_COLORMAP = 'gray'


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Connect up actions to methods
        self.ui.about_action.triggered.connect(self.about)
        self.ui.about_qt_action.triggered.connect(self.about_qt)
        self.ui.open_action.triggered.connect(self.open_file)
        self.ui.close_action.triggered.connect(self.close_file)
        self.figure_dpi = 72.0

    def open_file(self):
        d = OpenDialog(self)
        if d.exec_():
            w = self.ui.mdi_area.addSubWindow(MDIWindow(d.data_file, d.channel_file))
            w.show()

    def close_file(self):
        pass

    def about(self):
        QtGui.QMessageBox.about(self, self.tr('About rasViewer'),
            self.tr("""<b>rasViewer</b>
            <p>Version %s</p> <p>rasViewer is a visual previewer for the
            content of .RAS and .DAT files from the SSRL facility</p>
            <p>Copyright 2012 Dave Hughes &lt;dave@waveform.org.uk&gt;</p>""") % __version__)

    def about_qt(self):
        QtGui.QMessageBox.aboutQt(self, self.tr('About QT'))


class MDIWindow(QtGui.QWidget):
    def __init__(self, data_file, channel_file):
        super(MDIWindow, self).__init__(None)
        self.ui = Ui_MDIWindow()
        self.ui.setupUi(self)
        self._data = None
        self._data_sorted = None
        self._file = None
        # Open the selected file
        try:
            ext = os.path.splitext(data_file)[-1]
            if channel_file:
                files = (data_file, channel_file)
            else:
                files = (data_file,)
            for p in PARSERS:
                if ext in p.ext:
                    self._file = p(*files)
                    break
            if not self._file:
                raise ValueError(self.tr('Unrecognized file extension "%s"') % ext)
        except Exception, e:
            QtGui.QMessageBox.critical(self, self.tr('Error'), str(e))
            self.close()
            return
        # Create a figure in a tab for the file
        self.figure = Figure(figsize=(5.0, 4.0), dpi=FIGURE_DPI)
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.add_axes((0.1, 0.1, 0.8, 0.8))
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
        # Set up the event connections and a timer to handle delayed redrawing
        self.redraw_timer = QtCore.QTimer()
        self.redraw_timer.setInterval(200)
        self.redraw_timer.timeout.connect(self.redraw_timeout)
        self.ui.channel_combo.currentIndexChanged.connect(self.invalidate_data)
        self.ui.colormap_combo.currentIndexChanged.connect(self.invalidate_image)
        self.ui.interpolation_combo.currentIndexChanged.connect(self.invalidate_image)
        self.ui.percentile_from_slider.valueChanged.connect(self.percentile_from_slider_changed)
        self.ui.percentile_from_spinbox.valueChanged.connect(self.percentile_from_spinbox_changed)
        self.ui.percentile_to_slider.valueChanged.connect(self.percentile_to_slider_changed)
        self.ui.percentile_to_spinbox.valueChanged.connect(self.percentile_to_spinbox_changed)
        #self.ui.range_from_slider.valueChanged.connect(self.range_from_slider_changed)
        #self.ui.range_from_spinbox.valueChanged.connect(self.range_from_spinbox_changed)
        #self.ui.range_to_slider.valueChanged.connect(self.range_to_slider_changed)
        #self.ui.range_to_spinbox.valueChanged.connect(self.range_to_spinbox_changed)
        self.setWindowTitle(os.path.basename(data_file))
        self.invalidate_data()

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
            self._data_sorted = np.sort(self.data, None)
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
    def data_sorted(self):
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
            self.axes.clear()
            self.axes.imshow(self.data,
                vmin=self.ui.range_from_spinbox.value(),
                vmax=self.ui.range_to_spinbox.value(),
                cmap=matplotlib.cm.get_cmap(str(self.ui.colormap_combo.currentText())),
                interpolation=str(self.ui.interpolation_combo.currentText()))
            self.canvas.draw()

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
        self.invalidate_image()

    def range_to_spinbox_changed(self, value):
        self.ui.range_from_spinbox.setMaximum(value)
        self.ui.range_to_slider.setValue(int(value * 100.0))
        self.ui.percentile_to_spinbox.setValue(self.data_sorted.searchsorted(value) * 100.0 / (len(self.data_sorted) - 1))
        self.invalidate_image()


class OpenDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(OpenDialog, self).__init__(parent)
        self.ui = Ui_OpenDialog()
        self.ui.setupUi(self)
        self.ui.data_file_combo.editTextChanged.connect(self.data_file_changed)
        self.ui.data_file_button.clicked.connect(self.data_file_select)
        self.ui.channel_file_button.clicked.connect(self.channel_file_select)
        self.data_file_changed()

    @property
    def data_file(self):
        result = str(self.ui.data_file_combo.currentText())
        if result:
            return result
        else:
            return None

    @property
    def channel_file(self):
        result = str(self.ui.channel_file_combo.currentText())
        if result:
            return result
        else:
            return None

    def data_file_changed(self, value=None):
        if value is None:
            value = self.ui.data_file_combo.currentText()
        self.ui.button_box.button(QtGui.QDialogButtonBox.Ok).setEnabled(value != '')

    def data_file_select(self):
        f = QtGui.QFileDialog.getOpenFileName(self, self.tr('Select data file'), os.getcwd(),
            ';;'.join(
                '%s (%s)' % (self.tr(p.label), ' '.join('*' + e for e in p.ext))
                for p in PARSERS
            )
        )
        if f:
            os.chdir(os.path.dirname(str(f)))
            self.ui.data_file_combo.setEditText(f)

    def channel_file_select(self):
        f = QtGui.QFileDialog.getOpenFileName(self, self.tr('Select channel file'), os.getcwd(),
            self.tr('Text files (*.txt *.TXT);;All files (*)'))
        if f:
            os.chdir(os.path.dirname(str(f)))
            self.ui.channel_file_combo.setEditText(f)


def main(args=None):
    if args is None:
        args = sys.argv
    app = QtGui.QApplication(args)
    win = MainWindow()
    win.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
