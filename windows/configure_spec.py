#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# vim: set et sw=4 sts=4:

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import io
import sys
import subprocess


MY_PATH = os.path.dirname(__file__)
NAME = subprocess.check_output(['python', os.path.join(MY_PATH, '..', 'setup.py'), '--name']).strip()
VERSION = subprocess.check_output(['python', os.path.join(MY_PATH, '..', 'setup.py'), '--version']).strip()
sys.path.insert(0, os.path.join(MY_PATH, '..'))
from setup import ENTRY_POINTS


def configure_spec(
        template=os.path.join(MY_PATH, 'template.spec'),
        output=os.path.join(MY_PATH, NAME + '.spec'),
        encoding='utf-8'):
    # Open the WiX installer template
    with io.open(template, 'rb') as f:
        document = f.read().decode(encoding)
    document = document.replace('@NAME@', repr(NAME))
    document = document.replace('@GUI_SCRIPTS@', ','.join(
        repr(entry_point.split('=')[0].rstrip())
        for entry_point in ENTRY_POINTS['gui_scripts']
        ))
    with io.open(output, 'wb') as f:
        f.write(document.encode(encoding))


if __name__ == '__main__':
    configure_spec(sys.argv[1], sys.argv[2])
