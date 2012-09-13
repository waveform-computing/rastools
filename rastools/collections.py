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

"""Module providing several common collection tuple definitions"""

from __future__ import (
    unicode_literals, print_function, absolute_import, division)

from collections import namedtuple


Percentile = namedtuple('Percentile', ('low', 'high'))
Range = namedtuple('Range', ('low', 'high'))
Crop = namedtuple('Crop', ('top', 'left', 'bottom', 'right'))
Coord = namedtuple('Coord', ('x', 'y'))


class BoundingBox(object):
    "Represents a bounding-box in a matplotlib figure"

    def __init__(self, left, bottom, width, height):
        self.left = left
        self.bottom = bottom
        self.width = width
        self.height = height

    @property
    def top(self):
        "Returns the top coordinate of the bounding box"
        return self.bottom + self.height

    @property
    def right(self):
        "Returns the right coordinate of the bounding box"
        return self.left + self.width

    def relative_to(self, container):
        "Returns the bounding-box as a proportion of container"
        return BoundingBox(
            self.left / container.width,
            self.bottom / container.height,
            self.width / container.width,
            self.height / container.height
        )

    def __len__(self):
        return 4

    def __getitem__(self, index):
        return (
            self.left,
            self.bottom,
            self.width,
            self.height,
        )[index]

    def __iter__(self):
        for i in (self.left, self.bottom, self.width, self.height):
            yield i

    def __contains__(self, value):
        return value in (self.left, self.bottom, self.width, self.height)

    def __str__(self):
        return 'BoundingBox from ({0}, {1}) to ({2}, {3})'.format(
            self.left, self.bottom, self.right, self.top)

    def __repr__(self):
        return 'BoundingBox(left={0}, bottom={1}, width={2}, height={3})'.format(
            self.left, self.bottom, self.width, self.height)
