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

import os
from PyQt4 import QtCore, QtGui, uic

class OpenDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(OpenDialog, self).__init__(parent)
        self.ui = uic.loadUi(os.path.abspath(os.path.join(os.path.dirname(__file__), 'open_dialog.ui')), self)
        # Read the last-used lists
        self.settings = self.parent().settings
        self.settings.beginGroup('last_used')
        try:
            count = self.settings.beginReadArray('data_files')
            try:
                for i in range(count):
                    self.settings.setArrayIndex(i)
                    self.ui.data_file_combo.addItem(self.settings.value('path').toString())
            finally:
                self.settings.endArray()
            self.ui.data_file_combo.setEditText(self.settings.value('data_file', '').toString())
            count = self.settings.beginReadArray('channel_files')
            try:
                for i in range(count):
                    self.settings.setArrayIndex(i)
                    self.ui.channel_file_combo.addItem(self.settings.value('path').toString())
            finally:
                self.settings.endArray()
            self.ui.channel_file_combo.setEditText(self.settings.value('channel_file', '').toString())
        finally:
            self.settings.endGroup()
        # Connect up signals
        self.ui.data_file_combo.editTextChanged.connect(self.data_file_changed)
        self.ui.data_file_button.clicked.connect(self.data_file_select)
        self.ui.channel_file_button.clicked.connect(self.channel_file_select)
        self.data_file_changed()

    def accept(self):
        super(OpenDialog, self).accept()
        # When the dialog is accepted insert the current filenames at the top
        # of the combos or, if the entry already exists, move it to the top of
        # the combo list
        i = self.ui.data_file_combo.findText(self.ui.data_file_combo.currentText())
        if i == -1:
            self.ui.data_file_combo.addItem(self.ui.data_file_combo.currentText())
        else:
            self.ui.data_file_combo.insertItem(0, self.ui.data_file_combo.currentText())
            self.ui.data_file_combo.setCurrentIndex(0)
            self.ui.data_file_combo.removeItem(i + 1)
        while self.ui.data_file_combo.count() > self.ui.data_file_combo.maxCount():
            self.ui.data_file_combo.removeItem(self.ui.data_file_combo.count() - 1)
        if str(self.ui.channel_file_combo.currentText()) != '':
            i = self.ui.channel_file_combo.findText(self.ui.channel_file_combo.currentText())
            if i == -1:
                self.ui.channel_file_combo.addItem(self.ui.channel_file_combo.currentText())
            else:
                self.ui.channel_file_combo.insertItem(0, self.ui.channel_file_combo.currentText())
                self.ui.channel_file_combo.setCurrentIndex(0)
                self.ui.channel_file_combo.removeItem(i + 1)
        while self.ui.channel_file_combo.count() > self.ui.channel_file_combo.maxCount():
            self.ui.channel_file_combo.removeItem(self.ui.channel_file_combo.count() - 1)
        # Only write the last-used lists when the dialog is accepted (not when
        # cancelled or just closed)
        self.settings.beginGroup('last_used')
        try:
            self.settings.beginWriteArray('data_files', self.ui.data_file_combo.count())
            try:
                for i in range(self.ui.data_file_combo.count()):
                    self.settings.setArrayIndex(i)
                    self.settings.setValue('path', self.ui.data_file_combo.itemText(i))
            finally:
                self.settings.endArray()
            self.settings.setValue('data_file', self.ui.data_file_combo.currentText())
            self.settings.beginWriteArray('channel_files', self.ui.channel_file_combo.count())
            try:
                for i in range(self.ui.channel_file_combo.count()):
                    self.settings.setArrayIndex(i)
                    self.settings.setValue('path', self.ui.channel_file_combo.itemText(i))
            finally:
                self.settings.endArray()
            self.settings.setValue('channel_file', self.ui.channel_file_combo.currentText())
        finally:
            self.settings.endGroup()

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
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            from rastools.parsers import PARSERS
        finally:
            QtGui.QApplication.instance().restoreOverrideCursor()
        filters = ';;'.join(
            [
                str(self.tr('All data files (%s)')) % ' '.join('*' + ext for (_, exts, _) in PARSERS for ext in exts)
            ] + [
                '%s (%s)' % (self.tr(label), ' '.join('*' + ext for ext in exts))
                for (klass, exts, label) in PARSERS
            ]
        )
        f = QtGui.QFileDialog.getOpenFileName(self, self.tr('Select data file'), os.getcwd(), filters)
        if f:
            os.chdir(os.path.dirname(str(f)))
            self.ui.data_file_combo.setEditText(f)

    def channel_file_select(self):
        f = QtGui.QFileDialog.getOpenFileName(self, self.tr('Select channel file'), os.getcwd(),
            self.tr('Text files (*.txt *.TXT);;All files (*)'))
        if f:
            os.chdir(os.path.dirname(str(f)))
            self.ui.channel_file_combo.setEditText(f)

