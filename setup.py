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

from setuptools import setup, find_packages
from utils import description, get_version, require_python

require_python(0x020500f0)

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Environment :: Win32 (MS Windows)',
    'Environment :: X11 Applications :: Qt',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
    'Operating System :: Unix',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Multimedia :: Graphics',
    'Topic :: Scientific/Engineering',
]

entry_points = {
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
        version              = get_version('rastools/main.py'),
        description          = 'Tools for converting SSRL scans into images',
        long_description     = description('README.txt'),
        author               = 'Dave Hughes',
        author_email         = 'dave@waveform.org.uk',
        url                  = 'http://www.waveform.org.uk/trac/rastools/',
        packages             = find_packages(exclude=['distribute_setup', 'utils']),
        install_requires     = ['matplotlib'],
        extras_require       = {'XLS': ['xlwt']},
        include_package_data = True,
        platforms            = 'ALL',
        zip_safe             = False,
        entry_points         = entry_points,
        classifiers          = classifiers
    )

if __name__ == '__main__':
    main()
