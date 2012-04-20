PYUIC=pyuic4
#PYUIC=pyside-uic

all: rasview_open.py rasview_main.py

%.py: %.ui
	$(PYUIC) $< > $@
