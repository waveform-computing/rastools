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

"""Unit tests for the rasdump utility"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
from utils import *


def get_dump_formats():
    formats, _ = run(['rasdump', '--help-formats'])
    accept = False
    result = []
    for line in formats.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if accept:
            ext = line.split()[0].lower()
            if not ext in result:
                result.append(ext)
        elif 'file formats' in line:
            accept = True
    return result

def check_rasdump(filename):
    formats = get_dump_formats()
    for fmt in formats:
        out, err = run([
            'rasdump', '-e', '-o',
            os.path.join(THIS_PATH, 'test.{channel}%s' % fmt), filename])
        test0 = os.path.join(THIS_PATH, 'test.0%s' % fmt)
        test1 = os.path.join(THIS_PATH, 'test.1%s' % fmt)
        check_exists(test0)
        check_exists(test1)


def setup():
    create_test_ras()
    create_test_channels()

def test_rasdump():
    check_rasdump(TEST_DAT)
    check_rasdump(TEST_RAS)

def teardown():
    delete_produced_files()

