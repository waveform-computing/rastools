#!/usr/bin/env python
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

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
from setuptools import setup, find_packages
from utils import description, get_version, require_python

HERE = os.path.abspath(os.path.dirname(__file__))

# Workaround <http://bugs.python.org/issue10945>
import codecs
try:
    codecs.lookup('mbcs')
except LookupError:
    ascii = codecs.lookup('ascii')
    func = lambda name, enc=ascii: {True: enc}.get(name=='mbcs')
    codecs.register(func)

require_python(0x020600f0)

REQUIRES = [
    # For some bizarre reason, matplotlib doesn't "require" numpy in its
    # setup.py. The ordering below is also necessary to ensure numpy gets
    # picked up first ... yes, it's backwards ...
    'matplotlib',
    'numpy',
    ]

EXTRA_REQUIRES = {
    'XLS':        ['xlwt'],
    'completion': ['optcomplete'],
    'GUI':        ['pyqt'],
    }

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Environment :: Win32 (MS Windows)',
    'Environment :: X11 Applications :: Qt',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
    'Operating System :: Unix',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Multimedia :: Graphics',
    'Topic :: Scientific/Engineering',
    ]

ENTRY_POINTS = {
    'console_scripts': [
        'rasinfo = rastools.rasinfo:main',
        'rasextract = rastools.rasextract:main',
        'rasdump = rastools.rasdump:main',
    ],
    'gui_scripts': [
        'rasviewer = rastools.rasviewer:main',
    ]
    }


def main():
    setup(
        name                 = 'rastools',
        version              = get_version(os.path.join(HERE, 'rastools/__init__.py')),
        description          = 'Tools for converting SSRL scans into images',
        long_description     = description(os.path.join(HERE, 'README.txt')),
        classifiers          = CLASSIFIERS,
        author               = 'Dave Hughes',
        author_email         = 'dave@waveform.org.uk',
        url                  = 'http://www.waveform.org.uk/trac/rastools/',
        keywords             = 'science synchrotron',
        packages             = find_packages(exclude=['distribute_setup', 'utils']),
        include_package_data = True,
        platforms            = 'ALL',
        install_requires     = REQUIRES,
        extras_require       = EXTRA_REQUIRES,
        zip_safe             = False,
        test_suite           = 'rastools',
        entry_points         = ENTRY_POINTS,
    )

if __name__ == '__main__':
    main()
