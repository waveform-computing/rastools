# vim: set et sw=4 sts=4 fileencoding=utf-8 filetype=python:

import os
import sys

# Need to insert the current directory in order to import setup (because
# PyInstaller is relying on execfile...)
sys.path.insert(0, os.getcwd())
from setup import ENTRY_POINTS

console_scripts = {
    entry_point.split('=')[0].rstrip()
    for entry_point in ENTRY_POINTS['console_scripts']
    }
gui_scripts = {
    entry_point.split('=')[0].rstrip()
    for entry_point in ENTRY_POINTS['gui_scripts']
    }
scripts = console_scripts | gui_scripts

def is_gui(script):
    return script in gui_scripts

analyses = {
    script: Analysis(
                scripts=[os.path.join('rastools', script + '.py')],
                pathex=[os.getcwd()],
                excludes=[
                    'Tkinter',
                    'wx',
                    'matplotlib.backends._wxagg',
                    'matplotlib.backends._tkagg',
                    ],
                runtime_hooks=['rthook_pyqt4.py']
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
        upx=True,
        icon=os.path.join('..', 'icons', 'ico', script + '.ico') if is_gui(script) else None,
        # For some reason this doesn't work!
        #console=(script in console_scripts))
        console=not is_gui(script))
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

dist = COLLECT(*collect, strip=None, upx=True, name='dist')
