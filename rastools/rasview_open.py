# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'rasview_open.ui'
#
# Created: Mon Apr 23 11:33:08 2012
#      by: PyQt4 UI code generator 4.8.5
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_OpenDialog(object):
    def setupUi(self, OpenDialog):
        OpenDialog.setObjectName(_fromUtf8("OpenDialog"))
        OpenDialog.resize(525, 117)
        OpenDialog.setWindowTitle(QtGui.QApplication.translate("OpenDialog", "Open Scan", None, QtGui.QApplication.UnicodeUTF8))
        OpenDialog.setModal(True)
        self.verticalLayout = QtGui.QVBoxLayout(OpenDialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.datafile_label = QtGui.QLabel(OpenDialog)
        self.datafile_label.setText(QtGui.QApplication.translate("OpenDialog", "Data file", None, QtGui.QApplication.UnicodeUTF8))
        self.datafile_label.setObjectName(_fromUtf8("datafile_label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.datafile_label)
        self.data_file_layout = QtGui.QHBoxLayout()
        self.data_file_layout.setObjectName(_fromUtf8("data_file_layout"))
        self.data_file_combo = QtGui.QComboBox(OpenDialog)
        self.data_file_combo.setEditable(True)
        self.data_file_combo.setMaxCount(20)
        self.data_file_combo.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.data_file_combo.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.data_file_combo.setMinimumContentsLength(12)
        self.data_file_combo.setObjectName(_fromUtf8("data_file_combo"))
        self.data_file_layout.addWidget(self.data_file_combo)
        self.data_file_button = QtGui.QPushButton(OpenDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.data_file_button.sizePolicy().hasHeightForWidth())
        self.data_file_button.setSizePolicy(sizePolicy)
        self.data_file_button.setText(QtGui.QApplication.translate("OpenDialog", "Browse...", None, QtGui.QApplication.UnicodeUTF8))
        self.data_file_button.setObjectName(_fromUtf8("data_file_button"))
        self.data_file_layout.addWidget(self.data_file_button)
        self.formLayout.setLayout(0, QtGui.QFormLayout.FieldRole, self.data_file_layout)
        self.channelfile_label = QtGui.QLabel(OpenDialog)
        self.channelfile_label.setText(QtGui.QApplication.translate("OpenDialog", "Channels file (optional)", None, QtGui.QApplication.UnicodeUTF8))
        self.channelfile_label.setObjectName(_fromUtf8("channelfile_label"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.channelfile_label)
        self.channel_file_layout = QtGui.QHBoxLayout()
        self.channel_file_layout.setObjectName(_fromUtf8("channel_file_layout"))
        self.channel_file_combo = QtGui.QComboBox(OpenDialog)
        self.channel_file_combo.setEditable(True)
        self.channel_file_combo.setMaxCount(20)
        self.channel_file_combo.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.channel_file_combo.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.channel_file_combo.setMinimumContentsLength(12)
        self.channel_file_combo.setObjectName(_fromUtf8("channel_file_combo"))
        self.channel_file_layout.addWidget(self.channel_file_combo)
        self.channel_file_button = QtGui.QPushButton(OpenDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.channel_file_button.sizePolicy().hasHeightForWidth())
        self.channel_file_button.setSizePolicy(sizePolicy)
        self.channel_file_button.setText(QtGui.QApplication.translate("OpenDialog", "Browse...", None, QtGui.QApplication.UnicodeUTF8))
        self.channel_file_button.setObjectName(_fromUtf8("channel_file_button"))
        self.channel_file_layout.addWidget(self.channel_file_button)
        self.formLayout.setLayout(1, QtGui.QFormLayout.FieldRole, self.channel_file_layout)
        self.verticalLayout.addLayout(self.formLayout)
        self.button_box = QtGui.QDialogButtonBox(OpenDialog)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.button_box.setObjectName(_fromUtf8("button_box"))
        self.verticalLayout.addWidget(self.button_box)
        self.datafile_label.setBuddy(self.data_file_combo)
        self.channelfile_label.setBuddy(self.channel_file_combo)

        self.retranslateUi(OpenDialog)
        QtCore.QObject.connect(self.button_box, QtCore.SIGNAL(_fromUtf8("accepted()")), OpenDialog.accept)
        QtCore.QObject.connect(self.button_box, QtCore.SIGNAL(_fromUtf8("rejected()")), OpenDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(OpenDialog)
        OpenDialog.setTabOrder(self.data_file_combo, self.data_file_button)
        OpenDialog.setTabOrder(self.data_file_button, self.channel_file_combo)
        OpenDialog.setTabOrder(self.channel_file_combo, self.channel_file_button)
        OpenDialog.setTabOrder(self.channel_file_button, self.button_box)

    def retranslateUi(self, OpenDialog):
        pass

