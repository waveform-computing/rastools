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

"""Module implementing the file open dialog"""

from __future__ import (
    unicode_literals, print_function, absolute_import, division)

import os

from PyQt4 import QtCore, QtGui, uic


class ProgressDialog(QtGui.QDialog):
    "Implements the progress dialog"

    def __init__(self, parent=None):
        super(ProgressDialog, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = uic.loadUi(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    'progress_dialog.ui'
                )), self)
        self.cancelled = False

    def _get_task(self):
        "Getter for task property"
        return self.ui.windowTitle()
    def _set_task(self, value):
        "Setter for task property"
        self.ui.setWindowTitle(value)
    task = property(_get_task, _set_task, doc="The current task")

    def _get_progress(self):
        "Getter for progress property"
        return self.ui.progress_bar.value()
    def _set_progress(self, value):
        "Setter for progress property"
        self.ui.progress_bar.setValue(value)
        QtGui.QApplication.instance().processEvents()
    progress = property(
        _get_progress, _set_progress,
        doc="The current progress step")

    def _get_limits(self):
        "Getter for the limits property"
        return (
            self.ui.progress_bar.minimum(),
            self.ui.progress_bar.maximum()
        )
    def _set_limits(self, value):
        "Setter for the limits property"
        self.ui.progress_bar.setRange(value[0], value[1])
    limits = property(
        _get_limits, _set_limits,
        doc="Specifies the range of the progress property")

    def reject(self):
        self.cancelled = True
        # No idea why we need to call hide() here, but for some reason the
        # window doesn't close properly unless we do!
        self.hide()
        self.close()
