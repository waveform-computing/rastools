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

"""Unit tests for command line utilities"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import re
import csv
import subprocess
from nose import with_setup


THIS_PATH = os.path.abspath(os.path.dirname(__file__))
TEST_DAT = os.path.join(THIS_PATH, 'test.dat')
TEST_RAS = os.path.join(THIS_PATH, 'test.ras')
TEST_CHANNELS = os.path.join(THIS_PATH, 'channels.txt')
TO_DELETE = []


def run(cmdline):
    process = subprocess.Popen(
        cmdline,
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False)
    out, err = process.communicate()
    if process.returncode != 0:
        raise ValueError(
            'Command line %s exited with code %d' % (
                ' '.join(cmdline), process.returncode))
    return out, err

def in_output(pattern, output):
    return re.search(pattern, output, flags=re.MULTILINE | re.UNICODE)

def get_picture_formats():
    formats, _ = run(['rasextract', '--help-formats'])
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
        elif 'output formats' in line:
            accept = True
    return result

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

def check_rasinfo(filename):
    out, err = run(['rasinfo', filename])
    assert in_output(r'^Channel count: *2$', out)
    assert in_output(r'^Channel resolution: *10 x 10$', out)
    assert in_output(r'^TEST COMMENT$', out)

def check_rasdump(filename):
    formats = get_dump_formats()
    for fmt in formats:
        out, err = run([
            'rasdump', '-e', '-o',
            os.path.join(THIS_PATH, 'test.{channel}%s' % fmt), filename])
        print(out)
        print(err)
        TO_DELETE.append(os.path.join(THIS_PATH, 'test.0%s' % fmt))
        TO_DELETE.append(os.path.join(THIS_PATH, 'test.1%s' % fmt))
        assert os.path.exists(os.path.join(THIS_PATH, 'test.0%s' % fmt))
        assert os.path.exists(os.path.join(THIS_PATH, 'test.1%s' % fmt))

def check_rasextract(filename):
    formats = get_picture_formats()
    pil_formats = ('.bmp', '.gif', '.png', '.tif')
    for fmt in formats:
        out, err = run([
            'rasextract', '-e', '-o',
            os.path.join(THIS_PATH, 'test.{channel}%s' % fmt), filename])
        print(out)
        print(err)
        TO_DELETE.append(os.path.join(THIS_PATH, 'test.0%s' % fmt))
        TO_DELETE.append(os.path.join(THIS_PATH, 'test.1%s' % fmt))
        assert os.path.exists(os.path.join(THIS_PATH, 'test.0%s' % fmt))
        assert os.path.exists(os.path.join(THIS_PATH, 'test.1%s' % fmt))
        if fmt in pil_formats:
            pass


def setup():
    # Generate test.ras from test.dat
    run(['rasdump', '-e', '-m', '-o', TEST_RAS, TEST_DAT])
    TO_DELETE.append(TEST_RAS)
    # Generate channels.txt
    with open(TEST_CHANNELS, 'w') as f:
        f.write('0 Zeros\n')
        f.write('1 Sequence\n')
    TO_DELETE.append(TEST_CHANNELS)

def test_rasinfo():
    check_rasinfo(TEST_DAT)
    check_rasinfo(TEST_RAS)

def test_rasdump():
    check_rasdump(TEST_DAT)
    check_rasdump(TEST_RAS)

def test_rasextract():
    check_rasextract(TEST_DAT)
    check_rasextract(TEST_RAS)

def teardown():
    for filename in TO_DELETE:
        if os.path.exists(filename):
            os.unlink(filename)
