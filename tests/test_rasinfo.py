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

"""Blackbox tests for the rasinfo utility"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
from utils import *


def check_rasinfo(filename):
    out, err = run(['rasinfo', filename])
    assert in_output(r'^Channel count: *2$', out)
    assert in_output(r'^Channel resolution: *10 x 10$', out)
    assert in_output(r'^TEST COMMENT$', out)


def setup():
    create_test_ras()
    create_test_channels()

def test_rasinfo():
    check_rasinfo(TEST_DAT)
    check_rasinfo(TEST_RAS)

def teardown():
    delete_produced_files()
