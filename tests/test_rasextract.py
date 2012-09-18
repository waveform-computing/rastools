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

"""Blackbox tests for the rasextract utility"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
from PIL import Image
from utils import *


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

def check_image_size(filename, exactly=None, at_least=None):
    image = Image.open(filename)
    if exactly:
        assert image.size == exactly
    elif at_least:
        assert image.size >= at_least
    else:
        assert False

def check_image_zeros(filename):
    # Test every pixel in the image is black. We convert the image's mode to
    # RGB for the test as this saves mucking around with palettes
    image = Image.open(filename)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    assert all([pixel == (0, 0, 0) for pixel in image.getdata()])

def check_image_sequence(filename):
    # Test every pixel in the image is brighter than the prior one, or that the
    # current line of pixels is a repeat of the last one (as in the case of
    # resized images)
    last_pixel = (0, 0, 0)
    last_raster = []
    image = Image.open(filename)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    for raster in chunks(image.size[0], image.getdata()):
        raster = list(raster)
        for index, pixel in enumerate(raster):
            if pixel < last_pixel:
                # Check for repeated raster...
                if index == 0 and raster == last_raster:
                    break
                assert False
            last_pixel = pixel
        last_raster = raster

def check_image_range(filename, first, last):
    # Test that the first n and last n pixels of filename have the same color
    # due to range or percentile limiting
    image = Image.open(filename)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    data = list(image.getdata())
    assert all(pixel == data[0] for pixel in data[:first])
    assert all(pixel == data[-1] for pixel in data[-last:])

def check_rasextract(filename):
    formats = get_picture_formats()
    pil_formats = ('.bmp', '.gif', '.png', '.tif')
    multi_formats = ('.xcf', )
    for fmt in formats:
        run([
            'rasextract', '--empty', '--output',
            os.path.join(THIS_PATH, 'test.{channel}%s' % fmt), filename])
        test0 = os.path.join(THIS_PATH, 'test.0%s' % fmt)
        test1 = os.path.join(THIS_PATH, 'test.1%s' % fmt)
        check_exists(test0)
        check_exists(test1)
        if fmt in pil_formats:
            check_image_size(test0, exactly=(10, 10))
            check_image_zeros(test0)
            check_image_size(test1, exactly=(10, 10))
            # Don't test sequences with the GIF format as the dithering
            # employed by PIL when changing the image mode to palette-based
            # makes it fail (correctly)
            if not test1.endswith('.gif'):
                check_image_sequence(test1)
            run([
                'rasextract', '--resize', '2', '--output',
                os.path.join(THIS_PATH, 'test-resized.{channel}%s' % fmt), filename])
            test0 = os.path.join(THIS_PATH, 'test-resized.0%s' % fmt)
            test1 = os.path.join(THIS_PATH, 'test-resized.1%s' % fmt)
            # test0 shouldn't exist as we don't specify --empty above and
            # channel 0 is empty
            check_not_exists(test0)
            check_exists(test1)
            check_image_size(test1, exactly=(20, 20))
            run([
                'rasextract', '--crop', '1,1,1,1', '--output',
                os.path.join(THIS_PATH, 'test-crop.{channel}%s' % fmt), filename])
            test0 = os.path.join(THIS_PATH, 'test-crop.0%s' % fmt)
            test1 = os.path.join(THIS_PATH, 'test-crop.1%s' % fmt)
            check_not_exists(test0)
            check_exists(test1)
            check_image_size(test1, exactly=(8, 8))
            run([
                'rasextract', '--range', '20-80', '--output',
                os.path.join(THIS_PATH, 'test-range.{channel}%s' % fmt), filename])
            test0 = os.path.join(THIS_PATH, 'test-range.0%s' % fmt)
            test1 = os.path.join(THIS_PATH, 'test-range.1%s' % fmt)
            check_not_exists(test0)
            check_exists(test1)
            check_image_range(test1, 10, 10)
            run([
                'rasextract', '--percentile', '20-80', '--output',
                os.path.join(THIS_PATH, 'test-percentile.{channel}%s' % fmt), filename])
            test0 = os.path.join(THIS_PATH, 'test-percentile.0%s' % fmt)
            test1 = os.path.join(THIS_PATH, 'test-percentile.1%s' % fmt)
            check_not_exists(test0)
            check_exists(test1)
            check_image_range(test1, 10, 10)
        if fmt in multi_formats:
            test = os.path.join(THIS_PATH, 'test%s' % fmt)
            run(['rasextract', '--multi', '--output', test, filename])
            check_exists(test)


def setup():
    create_test_ras()
    create_test_channels()

def test_rasextract():
    check_rasextract(TEST_DAT)
    check_rasextract(TEST_RAS)

def teardown():
    delete_produced_files()
