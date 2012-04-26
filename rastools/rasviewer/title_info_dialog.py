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
