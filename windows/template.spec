# vim: set et sw=4 sts=4 fileencoding=utf-8 filetype=python:

import os
import sys
import glob

# Need to insert the current directory in order to import setup (because
# PyInstaller is relying on execfile...)
sys.path.insert(0, os.getcwd())
from setup import ENTRY_POINTS, PACKAGE_DATA

console_scripts = {
    entry_point.split('=')[0].rstrip()
    for entry_point in ENTRY_POINTS['console_scripts']
    }
gui_scripts = {
    entry_point.split('=')[0].rstrip()
    for entry_point in ENTRY_POINTS['gui_scripts']
    }
scripts = console_scripts | gui_scripts

analyses = {
    script: Analysis(
                scripts=[os.path.join(@NAME@, script + '.py')],
                pathex=[os.getcwd()],
                excludes=[
                    'Tkinter',
                    'wx',
                    'matplotlib.backends._wxagg',
                    'matplotlib.backends._tkagg',
                    ],
                runtime_hooks=[os.path.join('windows', 'rthook_pyqt4.py')]
                )
    for script in scripts
    }

exes = {
    script: EXE(
        PYZ(analysis.pure),
        analysis.scripts,
        exclude_binaries=1,
        name=os.path.join('build', 'pyi.' + sys.platform, script, script + '.exe'),
        debug=False,
        strip=None,
        upx=False,
        icon=os.path.join('icons', 'ico', script + '.ico') if (script in [@GUI_SCRIPTS@]) else None,
        # For some reason this doesn't work!
        #console=(script in console_scripts))
        console=(script not in [@GUI_SCRIPTS@]))
    for script, analysis in analyses.items()
    }

collect = [
    item
    for script in scripts
    for item in (
        exes[script],
        analyses[script].binaries,
        analyses[script].zipfiles,
        analyses[script].datas,
        )
    ]

data = [
    (filename, filename, 'DATA')
    for package, paths in PACKAGE_DATA.items()
    for path in paths
    for filename in glob.glob(os.path.join(*(package.split('.') + [path])))
    ]


dist = COLLECT(data, *collect, strip=None, upx=False, name='dist')
