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

"""Unit tests for parsers and writers"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import numpy as np

from rastools.datparse import DatParser
from rastools.datwrite import DatMultiWriter
from rastools.rasparse import RasParser
from rastools.raswrite import RasMultiWriter


THIS_PATH = os.path.abspath(os.path.dirname(__file__))
TEST_DAT = os.path.join(THIS_PATH, 'test.dat')
TEST2_DAT = os.path.join(THIS_PATH, 'test2.dat')
TEST_RAS = os.path.join(THIS_PATH, 'test.ras')
TEST2_RAS = os.path.join(THIS_PATH, 'test2.ras')
TEST_CHANNELS = os.path.join(THIS_PATH, 'channels.txt')


def read_dat_file(filename):
    return DatParser(filename)

def read_ras_file(filename, channels):
    return RasParser(filename, channels)

def write_dat_file(filename, data_file):
    with DatMultiWriter(filename, data_file) as f:
        for channel in data_file.channels:
            f.write_page(channel.data, channel)

def write_ras_file(filename, data_file):
    with RasMultiWriter(filename, data_file) as f:
        for channel in data_file.channels:
            f.write_page(channel.data, channel)

def check_contents(data_file):
    assert data_file.version == 1
    assert data_file.x_size == 10
    assert data_file.y_size == 10
    assert data_file.comments == 'TEST COMMENT'
    assert len(data_file.channels) == 2
    assert data_file.channels[0].name == 'Zeros'
    assert data_file.channels[0].index == 0
    assert data_file.channels[0].enabled
    assert (data_file.channels[0].data == np.zeros((10, 10))).all()
    assert data_file.channels[1].name == 'Sequence'
    assert data_file.channels[1].index == 1
    assert data_file.channels[1].enabled
    assert (data_file.channels[1].data == np.arange(100).reshape((10, 10))).all()


def test_dat():
    data_file = read_dat_file(TEST_DAT)
    check_contents(data_file)
    write_dat_file(TEST2_DAT, data_file)
    data_file2 = read_dat_file(TEST2_DAT)
    check_contents(data_file2)

def test_rasroundtrip():
    with open(TEST_CHANNELS, 'w') as f:
        f.write('0 Zeros\n')
        f.write('1 Sequence\n')
    write_ras_file(TEST_RAS, read_dat_file(TEST_DAT))
    data_file = read_ras_file(TEST_RAS, TEST_CHANNELS)
    check_contents(data_file)
    write_ras_file(TEST2_RAS, data_file)
    data_file2 = read_ras_file(TEST2_RAS, TEST_CHANNELS)
    check_contents(data_file2)

def teardown():
    for filename in (TEST_RAS, TEST_CHANNELS, TEST2_DAT, TEST2_RAS):
        if os.path.exists(filename):
            os.unlink(filename)
