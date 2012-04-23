# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'rasview_main.ui'
#
# Created: Mon Apr 23 11:28:44 2012
#      by: PyQt4 UI code generator 4.8.5
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(640, 480)
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.mdi_area = QtGui.QMdiArea(self.centralwidget)
        self.mdi_area.setViewMode(QtGui.QMdiArea.TabbedView)
        self.mdi_area.setObjectName(_fromUtf8("mdi_area"))
        self.verticalLayout.addWidget(self.mdi_area)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menu_bar = QtGui.QMenuBar(MainWindow)
        self.menu_bar.setGeometry(QtCore.QRect(0, 0, 640, 25))
        self.menu_bar.setObjectName(_fromUtf8("menu_bar"))
        self.file_menu = QtGui.QMenu(self.menu_bar)
        self.file_menu.setTitle(QtGui.QApplication.translate("MainWindow", "&File", None, QtGui.QApplication.UnicodeUTF8))
        self.file_menu.setObjectName(_fromUtf8("file_menu"))
        self.export_menu = QtGui.QMenu(self.file_menu)
        self.export_menu.setEnabled(False)
        self.export_menu.setTitle(QtGui.QApplication.translate("MainWindow", "&Export", None, QtGui.QApplication.UnicodeUTF8))
        self.export_menu.setObjectName(_fromUtf8("export_menu"))
        self.help_menu = QtGui.QMenu(self.menu_bar)
        self.help_menu.setTitle(QtGui.QApplication.translate("MainWindow", "&Help", None, QtGui.QApplication.UnicodeUTF8))
        self.help_menu.setObjectName(_fromUtf8("help_menu"))
        MainWindow.setMenuBar(self.menu_bar)
        self.status_bar = QtGui.QStatusBar(MainWindow)
        self.status_bar.setObjectName(_fromUtf8("status_bar"))
        MainWindow.setStatusBar(self.status_bar)
        self.tool_bar = QtGui.QToolBar(MainWindow)
        self.tool_bar.setWindowTitle(QtGui.QApplication.translate("MainWindow", "toolBar", None, QtGui.QApplication.UnicodeUTF8))
        self.tool_bar.setObjectName(_fromUtf8("tool_bar"))
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.tool_bar)
        self.open_action = QtGui.QAction(MainWindow)
        self.open_action.setText(QtGui.QApplication.translate("MainWindow", "&Open...", None, QtGui.QApplication.UnicodeUTF8))
        self.open_action.setToolTip(QtGui.QApplication.translate("MainWindow", "Open a data file", None, QtGui.QApplication.UnicodeUTF8))
        self.open_action.setStatusTip(QtGui.QApplication.translate("MainWindow", "Open a data file", None, QtGui.QApplication.UnicodeUTF8))
        self.open_action.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+O", None, QtGui.QApplication.UnicodeUTF8))
        self.open_action.setObjectName(_fromUtf8("open_action"))
        self.close_action = QtGui.QAction(MainWindow)
        self.close_action.setEnabled(False)
        self.close_action.setText(QtGui.QApplication.translate("MainWindow", "&Close", None, QtGui.QApplication.UnicodeUTF8))
        self.close_action.setToolTip(QtGui.QApplication.translate("MainWindow", "Close the currently selected data file", None, QtGui.QApplication.UnicodeUTF8))
        self.close_action.setStatusTip(QtGui.QApplication.translate("MainWindow", "Close the currently selected data file", None, QtGui.QApplication.UnicodeUTF8))
        self.close_action.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+W", None, QtGui.QApplication.UnicodeUTF8))
        self.close_action.setShortcutContext(QtCore.Qt.WidgetShortcut)
        self.close_action.setObjectName(_fromUtf8("close_action"))
        self.quit_action = QtGui.QAction(MainWindow)
        self.quit_action.setText(QtGui.QApplication.translate("MainWindow", "&Quit", None, QtGui.QApplication.UnicodeUTF8))
        self.quit_action.setToolTip(QtGui.QApplication.translate("MainWindow", "Quit the application", None, QtGui.QApplication.UnicodeUTF8))
        self.quit_action.setStatusTip(QtGui.QApplication.translate("MainWindow", "Quit the application", None, QtGui.QApplication.UnicodeUTF8))
        self.quit_action.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+Q", None, QtGui.QApplication.UnicodeUTF8))
        self.quit_action.setMenuRole(QtGui.QAction.QuitRole)
        self.quit_action.setObjectName(_fromUtf8("quit_action"))
        self.about_action = QtGui.QAction(MainWindow)
        self.about_action.setText(QtGui.QApplication.translate("MainWindow", "&About rasViewer", None, QtGui.QApplication.UnicodeUTF8))
        self.about_action.setMenuRole(QtGui.QAction.AboutRole)
        self.about_action.setObjectName(_fromUtf8("about_action"))
        self.about_qt_action = QtGui.QAction(MainWindow)
        self.about_qt_action.setText(QtGui.QApplication.translate("MainWindow", "About QT", None, QtGui.QApplication.UnicodeUTF8))
        self.about_qt_action.setMenuRole(QtGui.QAction.AboutQtRole)
        self.about_qt_action.setObjectName(_fromUtf8("about_qt_action"))
        self.export_image_action = QtGui.QAction(MainWindow)
        self.export_image_action.setEnabled(False)
        self.export_image_action.setText(QtGui.QApplication.translate("MainWindow", "&Image...", None, QtGui.QApplication.UnicodeUTF8))
        self.export_image_action.setObjectName(_fromUtf8("export_image_action"))
        self.export_channel_action = QtGui.QAction(MainWindow)
        self.export_channel_action.setEnabled(False)
        self.export_channel_action.setText(QtGui.QApplication.translate("MainWindow", "&Channel...", None, QtGui.QApplication.UnicodeUTF8))
        self.export_channel_action.setObjectName(_fromUtf8("export_channel_action"))
        self.export_menu.addAction(self.export_image_action)
        self.export_menu.addAction(self.export_channel_action)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.close_action)
        self.file_menu.addAction(self.export_menu.menuAction())
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.quit_action)
        self.help_menu.addAction(self.about_action)
        self.help_menu.addAction(self.about_qt_action)
        self.menu_bar.addAction(self.file_menu.menuAction())
        self.menu_bar.addAction(self.help_menu.menuAction())
        self.tool_bar.addAction(self.open_action)
        self.tool_bar.addAction(self.close_action)
        self.tool_bar.addSeparator()
        self.tool_bar.addAction(self.quit_action)

        self.retranslateUi(MainWindow)
        QtCore.QObject.connect(self.quit_action, QtCore.SIGNAL(_fromUtf8("triggered()")), MainWindow.close)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        pass

