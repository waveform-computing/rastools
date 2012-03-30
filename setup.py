#!/usr/bin/env python
# vim: set et sw=4 sts=4:

"""Tools for dealing with RAS scans"""

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

classifiers = [
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
    'Operating System :: Unix',
    'Programming Language :: Python :: 2.6',
    'Topic :: Multimedia :: Graphics',
    'Topic :: Scientific/Engineering',
]

entry_points = {
    'console_scripts': [
        'rasinfo = rastools.rasinfo:main',
        'rasextract = rastools.rasextract:main',
        'rasdump = rastools.rasdump:main',
    ]
}

def get_console_scripts():
    import re
    for s in entry_points['console_scripts']:
        print re.match(r'^([^= ]*) ?=.*$', s).group(1)

def main():
    from rastools.main import __version__
    setup(
        name                 = 'rastools',
        version              = __version__,
        description          = 'Tools for converting RAS scans to images',
        long_description     = __doc__,
        author               = 'Dave Hughes',
        author_email         = 'dave@waveform.org.uk',
        url                  = 'http://www.waveform.org.uk/trac/rastools/',
        packages             = find_packages(exclude=['ez_setup']),
        install_requires     = ['matplotlib'],
        include_package_data = True,
        platforms            = 'ALL',
        zip_safe             = False,
        entry_points         = entry_points,
        classifiers          = classifiers
    )

if __name__ == '__main__':
    main()
