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

"""Utility routines for unit tests"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import re
import sys
import subprocess
try:
    # XXX Py3 only
    from itertools import zip_longest
except ImportError:
    # XXX Py2 only
    from itertools import izip_longest as zip_longest


THIS_PATH = os.path.abspath(os.path.dirname(__file__))
TEST_DAT = os.path.join(THIS_PATH, 'test.dat')
TEST_RAS = os.path.join(THIS_PATH, 'test.ras')
TEST_CHANNELS = os.path.join(THIS_PATH, 'channels.txt')
try:
    ENCODING = sys.stdout.encoding
except AttributeError:
    ENCODING = None
if not ENCODING:
    ENCODING = 'UTF-8'


def chunks(n, iterable, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # chunks(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

def run(cmdline):
    process = subprocess.Popen(
        cmdline,
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False)
    out, err = process.communicate()
    out = out.decode(ENCODING)
    err = err.decode(ENCODING)
    print(out)
    print(err)
    if process.returncode != 0:
        raise ValueError(
            'Command line %s exited with code %d' % (
                ' '.join(cmdline), process.returncode))
    return out, err

def in_output(pattern, output):
    return re.search(pattern, output, flags=re.MULTILINE | re.UNICODE)

TO_DELETE = set()
def check_exists(filename, delete_later=True):
    if delete_later:
        TO_DELETE.add(filename)
    assert os.path.exists(filename)

def check_not_exists(filename, delete_later=True):
    if delete_later:
        TO_DELETE.add(filename)
    assert not os.path.exists(filename)

def delete_produced_files():
    for filename in TO_DELETE:
        if os.path.exists(filename):
            os.unlink(filename)

def create_test_ras():
    # Generate test.ras from test.dat
    run(['rasdump', '-e', '-m', '-o', TEST_RAS, TEST_DAT])
    check_exists(TEST_RAS)
    return TEST_RAS

def create_test_channels():
    # Generate channels.txt
    with open(TEST_CHANNELS, 'w') as f:
        f.write('0 Zeros\n')
        f.write('1 Sequence\n')
    check_exists(TEST_CHANNELS)
    return TEST_CHANNELS

