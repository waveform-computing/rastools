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

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

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
    'Programming Language :: Python :: 2.6',
    'Topic :: Multimedia :: Graphics',
    'Topic :: Scientific/Engineering',
]

entry_points = {
    'console_scripts': [
        'rasinfo    = rastools.rasinfo:main',
        'rasextract = rastools.rasextract:main',
        'rasdump    = rastools.rasdump:main',
        'rasviewer  = rastools.rasviewer:main',
    ]
}

def get_console_scripts():
    import re
    for s in entry_points['console_scripts']:
        print re.match(r'^([^= ]*) *=.*$', s).group(1)

def main():
    from rastools.main import __version__
    setup(
        name                 = 'rastools',
        version              = __version__,
        license              = 'LICENSE.txt',
        description          = 'Tools for converting scans from the SSRL to images',
        long_description     = open('README.txt').read(),
        author               = 'Dave Hughes',
        author_email         = 'dave@waveform.org.uk',
        url                  = 'http://www.waveform.org.uk/trac/rastools/',
        packages             = find_packages(exclude=['ez_setup']),
        install_requires     = ['matplotlib', 'PyQt'],
        include_package_data = True,
        platforms            = 'ALL',
        zip_safe             = False,
        entry_points         = entry_points,
        classifiers          = classifiers
    )

if __name__ == '__main__':
    main()
