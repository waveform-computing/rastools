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

"""Unit tests for datparse"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import numpy as np
from nose import with_setup

from rastools.datparse import DatParser
from rastools.datwrite import DatMultiWriter
from rastools.rasparse import RasParser
from rastools.raswrite import RasMultiWriter, RasAsciiMultiWriter

THIS_PATH = os.path.abspath(os.path.dirname(__file__))
TEST_DAT = os.path.join(THIS_PATH, 'test.dat')
TEST2_DAT = os.path.join(THIS_PATH, 'test2.dat')
TEST_RAS = os.path.join(THIS_PATH, 'test.ras')
TEST_CHANNELS = os.path.join(THIS_PATH, 'channels.txt')

def read_dat_file(filename):
    return DatParser(filename)

def write_dat_file(filename, data_file):
    with DatMultiWriter(filename, data_file) as f:
        for channel in data_file.channels:
            f.write_page(channel.data, channel)

def read_ras_file(filename, channels):
    return RasParser(filename, channels)

def write_ras_file(filename, data_file):
    with RasMultiWriter(filename, data_file) as f:
        for channel in data_file.channels:
            f.write_page(channel.data, channel)

def setup_pass():
    pass

def setup_ras_file():
    write_ras_file(TEST_RAS, read_dat_file(TEST_DAT))
    with open(TEST_CHANNELS, 'w') as f:
        f.write('0 Zeros\n')
        f.write('1 Sequence\n')

def teardown_ras_file():
    if os.path.exists(TEST_RAS):
        os.unlink(TEST_RAS)
    if os.path.exists(TEST_CHANNELS):
        os.unlink(TEST_CHANNELS)

def setup_dat_file():
    write_dat_file(TEST2_DAT, read_dat_file(TEST_DAT))

def teardown_dat_file():
    if os.path.exists(TEST2_DAT):
        os.unlink(TEST2_DAT)

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

def test_datparse():
    check_contents(read_dat_file(TEST_DAT))

@with_setup(setup_pass, teardown_ras_file)
def test_raswrite():
    setup_ras_file()

@with_setup(setup_ras_file, teardown_ras_file)
def test_rasparse():
    check_contents(read_ras_file(TEST_RAS, TEST_CHANNELS))

@with_setup(setup_pass, teardown_dat_file)
def test_datwrite():
    setup_dat_file()
