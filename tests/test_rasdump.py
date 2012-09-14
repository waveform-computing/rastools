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

"""Blackbox tests for the rasdump utility"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import csv
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

def check_dump_size(filename, dialect, exactly=None, at_least=None):
    if exactly:
        w, h = exactly
    elif at_least:
        w, h = at_least
    else:
        assert False
    with open(filename, 'r') as f:
        dump = csv.reader(f, dialect=dialect)
        for row_num, row in enumerate(dump):
            if exactly:
                assert len(row) == w
            elif at_least:
                assert len(row) >= w
        if exactly:
            assert row_num == h - 1
        elif at_least:
            assert row_num >= h - 1

def check_dump_zeros(filename, dialect):
    reader = csv.reader(open(filename, 'r'), dialect=dialect)
    assert all([float(value) == 0.0 for line in reader for value in line])

def check_dump_sequence(filename, dialect, min_value=None, max_value=None):
    last_value = 0.0
    with open(filename, 'r') as f:
        reader = csv.reader(f, dialect=dialect)
        for line in reader:
            for value in line:
                value = float(value)
                assert value >= last_value
                if min_value is not None:
                    assert value >= min_value
                if max_value is not None:
                    assert value <= max_value
                last_value = value

def check_rasdump(filename):
    formats = get_dump_formats()
    csv_formats = {
        '.csv': 'excel',
        '.tsv': 'excel-tab'}
    for fmt in formats:
        run([
            'rasdump', '--empty', '--output',
            os.path.join(THIS_PATH, 'test.{channel}%s' % fmt), filename])
        test0 = os.path.join(THIS_PATH, 'test.0%s' % fmt)
        test1 = os.path.join(THIS_PATH, 'test.1%s' % fmt)
        check_exists(test0)
        check_exists(test1)
        if fmt in csv_formats:
            dialect = csv_formats[fmt]
            check_dump_size(test0, dialect, exactly=(10, 10))
            check_dump_size(test1, dialect, exactly=(10, 10))
            check_dump_zeros(test0, dialect)
            check_dump_sequence(test1, dialect)
            run([
                'rasdump', '--range', '50-80', '--output',
                os.path.join(THIS_PATH, 'test-range.{channel}%s' % fmt),
                filename])
            test0 = os.path.join(THIS_PATH, 'test-range.0%s' % fmt)
            test1 = os.path.join(THIS_PATH, 'test-range.1%s' % fmt)
            check_not_exists(test0)
            check_exists(test1)
            check_dump_size(test1, dialect, exactly=(10, 10))
            check_dump_sequence(test1, dialect, min_value=50, max_value=80)
            run([
                'rasdump', '--percentile', '50-80', '--output',
                os.path.join(THIS_PATH, 'test-percentile.{channel}%s' % fmt),
                filename])
            test0 = os.path.join(THIS_PATH, 'test-percentile.0%s' % fmt)
            test1 = os.path.join(THIS_PATH, 'test-percentile.1%s' % fmt)
            check_not_exists(test0)
            check_exists(test1)
            check_dump_size(test1, dialect, exactly=(10, 10))
            check_dump_sequence(test1, dialect, min_value=50, max_value=80)
            run([
                'rasdump', '--crop', '1,1,1,1', '--output',
                os.path.join(THIS_PATH, 'test-crop.{channel}%s' % fmt),
                filename])
            test0 = os.path.join(THIS_PATH, 'test-crop.0%s' % fmt)
            test1 = os.path.join(THIS_PATH, 'test-crop.1%s' % fmt)
            check_not_exists(test0)
            check_exists(test1)
            check_dump_size(test1, dialect, exactly=(8, 8))
            check_dump_sequence(test1, dialect, min_value=11, max_value=88)

def setup():
    create_test_ras()
    create_test_channels()

def test_rasdump():
    check_rasdump(TEST_DAT)
    check_rasdump(TEST_RAS)

def teardown():
    delete_produced_files()

