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

class TitleInfoDialog(QtGui.QDialog):
    def __init__(self, parent):
        super(TitleInfoDialog, self).__init__(parent)
        self.ui = uic.loadUi(os.path.abspath(os.path.join(os.path.dirname(__file__), 'title_info_dialog.ui')), self)
        self.ui.template_list.setHeaderLabels(['Template', 'Substitution'])
        self.ui.template_list.itemDoubleClicked.connect(self.insert_template)

    def reject(self):
        super(TitleInfoDialog, self).reject()
        self.parent()._info_dialog = None

    def insert_template(self, item, t):
        self.parent().ui.title_edit.textCursor().insertText(item.text(0))
