import os
from PyQt4 import QtCore, QtGui, uic

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = uic.loadUi(os.path.abspath(os.path.join(os.path.dirname(__file__), 'main_window.ui')), self)
        # Read configuration
        self.settings = QtCore.QSettings()
        self.settings.beginGroup('main_window')
        try:
            self.resize(self.settings.value('size', QtCore.QSize(640, 480)).toSize())
            self.move(self.settings.value('position', QtCore.QPoint(100, 100)).toPoint())
        finally:
            self.settings.endGroup()
        # Connect up signals to methods
        self.ui.mdi_area.subWindowActivated.connect(self.window_changed)
        self.ui.about_action.triggered.connect(self.about)
        self.ui.about_qt_action.triggered.connect(self.about_qt)
        self.ui.open_action.triggered.connect(self.open_file)
        self.ui.close_action.triggered.connect(self.close_file)
        self.ui.export_image_action.triggered.connect(self.export_image)
        self.ui.export_channel_action.triggered.connect(self.export_channel)

    def close(self):
        super(MainWindow, self).close()
        self.settings.beginGroup('main_window')
        self.settings.setValue('size', self.size())
        self.settings.setValue('position', self.pos())

    def open_file(self):
        from rastools.rasviewer.open_dialog import OpenDialog
        d = OpenDialog(self)
        if d.exec_():
            from rastools.rasviewer.mdi_window import MDIWindow
            w = self.ui.mdi_area.addSubWindow(MDIWindow(d.data_file, d.channel_file))
            w.show()

    def close_file(self):
        self.ui.mdi_area.currentSubWindow().close()

    def about(self):
        QtGui.QMessageBox.about(self,
            str(self.tr('About %s')) % QtGui.QApplication.instance().applicationName(),
            str(self.tr("""<b>%(application)s</b>
            <p>Version %(version)s</p>
            <p>%(application)s is a visual previewer for the content of .RAS and
            .DAT files from the SSRL facility</p>
            <p>Copyright 2012 Dave Hughes &lt;dave@waveform.org.uk&gt;</p>""")) % {
                'application': QtGui.QApplication.instance().applicationName(),
                'version':     QtGui.QApplication.instance().applicationVersion(),
            })

    def about_qt(self):
        QtGui.QMessageBox.aboutQt(self, self.tr('About QT'))

    def export_image(self):
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            from rastools.image_writers import IMAGE_WRITERS
        finally:
            QtGui.QApplication.instance().restoreOverrideCursor()
        filters = ';;'.join(
            [
                str(self.tr('All images (%s)')) % ' '.join('*' + ext for (_, exts, _, _, _) in IMAGE_WRITERS for ext in exts)
            ] + [
                '%s (%s)' % (self.tr(label), ' '.join('*' + ext for ext in exts))
                for (method, exts, label, _, _) in IMAGE_WRITERS
            ]
        )
        f = QtGui.QFileDialog.getSaveFileName(self, self.tr('Export image'), os.getcwd(), filters)
        if f:
            f = str(f)
            os.chdir(os.path.dirname(f))
            ext = os.path.splitext(f)[1]
            writers = dict(
                (ext, method)
                for (method, exts, _, _, _) in IMAGE_WRITERS
                for ext in exts
            )
            try:
                method = writers[ext]
            except KeyError:
                QtGui.QMessageBox.warning(self, self.tr('Warning'), str(self.tr('Unknown file extension "%s"')) % ext)
            canvas = method.im_class(self.ui.mdi_area.currentSubWindow().widget().figure)
            method(canvas, f, dpi=FIGURE_DPI)

    def export_channel(self):
        # XXX Add export channel implementation
        pass

    def window_changed(self, window):
        self.ui.close_action.setEnabled(window is not None)
        self.ui.export_menu.setEnabled(window is not None)
        self.ui.export_image_action.setEnabled(window is not None)
        self.ui.export_channel_action.setEnabled(window is not None)

