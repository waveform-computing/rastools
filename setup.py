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
    # XXX Alright! I give in! Distutils and all its myriad extensions (py2exe,
    # py2app, et al.) are all too shit to handle unicode with barfing all over
    # the floor, so out goes the following line...
    #unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
from setuptools import setup, find_packages
from utils import description, get_version, require_python

# Attempt to import platform specific build packages; py2exe for Windows,
# py2app for Mac. Leave placeholders in the case of failed imports so that we
# can later test what got imported successfully
try:
    import py2exe
    py2app = None
except ImportError:
    py2exe = None
    try:
        import py2app
    except:
        py2app = None


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


OPTIONS = {}
EXTRA_OPTIONS = {}

if py2exe:
    MSVCRT_PATH = r'..\redist'
    import sys
    import matplotlib
    from glob import glob
    # Hack to permit py2exe to find MSVCP90.dll
    sys.path.append(MSVCRT_PATH)
    OPTIONS['py2exe'] = {
        'compressed': True,
        # Tell py2exe not to try and import the Py3k specific stuff from PyQt4
        'excludes': [
            'PyQt4.uic.port_v3',
            ],
        }
    EXTRA_OPTIONS = {
        # py2exe needs a bit of help figuring out what things to include for
        # MSVCRT and where to stick matplotlib's stuff...
        'data_files': [
            ('Microsoft.VC90.CRT', glob(os.path.join(MSVCRT_PATH, '*')))
            ] + matplotlib.get_py2exe_datafiles(),
        # We fill out the console and GUI entry points below. No idea why
        # py2exe can't just use the setuptools entry points...
        'console': [],
        'windows': [],
        }
    for entry_point_group, target_key in [
            ('console_scripts', 'console'),
            ('gui_scripts',     'windows'),
            ]:
        for entry_point in ENTRY_POINTS[entry_point_group]:
            # Extract module/package name from the entry point
            entry_point = entry_point.split('=', 1)[1].strip().split(':', 1)[0]
            # Convert the module/package name to a file path
            entry_point = os.path.join(HERE, entry_point.replace('.', os.path.sep))
            if os.path.isdir(entry_point):
                entry_point = os.path.join(entry_point, '__init__.py')
            else:
                entry_point += '.py'
            EXTRA_OPTIONS[target_key].append(entry_point)

if py2app:
    # Mac specific build options
    OPTIONS['py2app'] = {}


def main():
    setup(
        name                 = 'rastools',
        version              = get_version(os.path.join(HERE, 'rastools', '__init__.py')),
        description          = 'Tools for converting SSRL scans into images',
        long_description     = description(os.path.join(HERE, 'README.rst')),
        classifiers          = CLASSIFIERS,
        author               = 'Dave Hughes',
        author_email         = 'dave@waveform.org.uk',
        url                  = 'https://github.com/waveform80/rastools',
        keywords             = 'science synchrotron',
        packages             = ['rastools', 'rastools.rasviewer'],
        package_data         = {'rastools.rasviewer': ['*.ui']},
        platforms            = 'ALL',
        install_requires     = REQUIRES,
        extras_require       = EXTRA_REQUIRES,
        zip_safe             = False,
        test_suite           = 'rastools',
        entry_points         = ENTRY_POINTS,
        options              = OPTIONS,
        **EXTRA_OPTIONS
        )

if __name__ == '__main__':
    main()
