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

"""Implements a QT-based matplotlib FigureCanvas with better rubber-banding"""

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from PyQt4 import QtCore, QtGui

COMPOSITION_SUPPORTED = True

class FigureCanvas(FigureCanvasQTAgg):
    "FigureCanvas derivative with better rubber-banding"

    composition_supported = True

    def paintEvent(self, evt):
        # This version of paintEvent is a bit of a hack to work-around the
        # parent class' crappy selection of drawing mode. The parent class
        # always paints a white line, but on light images this is almost
        # impossible to see. Here we force the parent not to draw the rect,
        # then switch to difference-composition and draw it ourselves (if
        # required).
        #
        # There doesn't appear to be a (reliable) way to tell in advance if
        # difference compsition is supported so to avoid spamming the console
        # with thousands of errors we keep a track of whether the composition
        # mode is supported with a global variable
        if self.drawRect:
            self.drawRect = False
            super(FigureCanvas, self).paintEvent(evt)
            painter = QtGui.QPainter(self)
            painter.setPen(QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine))
            if self.composition_supported:
                painter.setCompositionMode(
                    QtGui.QPainter.CompositionMode_Difference)
                self.composition_supported = (painter.compositionMode() ==
                    QtGui.QPainter.CompositionMode_Difference)
            painter.drawRect(
                self.rect[0], self.rect[1], self.rect[2], self.rect[3])
            painter.end()
        else:
            super(FigureCanvas, self).paintEvent(evt)



