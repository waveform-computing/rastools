# vim: set noet sw=4 ts=4:

# External utilities
PYTHON=python
PYFLAGS=
DESTDIR=/
PROJECT=rastools
BUILDIR=$(CURDIR)/debian/$(PROJECT)

# Calculate the base names of the distribution, the location of all source,
# documentation and executable script files
NAME:=$(shell $(PYTHON) $(PYFLAGS) setup.py --name)
VER:=$(shell $(PYTHON) $(PYFLAGS) setup.py --version)
PYVER:=$(shell $(PYTHON) $(PYFLAGS) -c "import sys; print 'py%d.%d' % sys.version_info[:2]")
SOURCE:=$(shell \
	$(PYTHON) $(PYFLAGS) setup.py egg_info >/dev/null 2>&1 && \
	cat $(NAME).egg-info/SOURCES.txt)

# Calculate the name of all distribution archives / installers
DIST_EGG=dist/$(NAME)-$(VER)-$(PYVER).egg
DIST_EXE=dist/$(NAME)-$(VER).win32.exe
DIST_RPM=dist/$(NAME)-$(VER)-1.src.rpm
DIST_TAR=dist/$(NAME)-$(VER).tar.gz
DIST_DEB=dist/$(NAME)_$(VER)-1~ppa1_all.deb
MAN_PAGES=docs/_build/man/rasextract.1 docs/_build/man/rasdump.1 docs/_build/man/rasinfo.1

# Default target
all:
	@echo "make source - Create source package"
	@echo "make install - Install on local system"
	@echo "make buildegg - Generate a PyPI egg package"
	@echo "make buildrpm - Generate an RedHat package"
	@echo "make builddeb - Generate a Debian package"
	@echo "make buildexe - Generate a Windows exe installer"
	@echo "make clean - Get rid of scratch and byte files"

install:
	$(PYTHON) $(PYFLAGS) setup.py install --root $(DESTDIR) $(COMPILE)

source: $(DIST_TAR)

buildexe: $(DIST_EXE)

buildegg: $(DIST_EGG)

buildrpm: $(DIST_RPM)

builddeb: $(DIST_DEB)

dist: $(DIST_EXE) $(DIST_EGG) $(DIST_RPM) $(DIST_DEB) $(DIST_TAR)

develop: tags
	$(PYTHON) $(PYFLAGS) setup.py develop

test:
	@echo "No tests currently implemented"
	#cd examples && ./runtests.sh

clean:
	$(PYTHON) $(PYFLAGS) setup.py clean
	$(MAKE) -f $(CURDIR)/debian/rules clean
	rm -fr build/ docs/_build/* $(NAME).egg-info/ tags
	find $(CURDIR) -name "*.pyc" -delete

cleanall: clean
	rm -fr dist/

tags: $(SOURCE)
	ctags -R --exclude="build/*" --languages="Python"

$(MAN_PAGES):
	make -C docs man

$(DIST_TAR): $(SOURCE)
	$(PYTHON) $(PYFLAGS) setup.py sdist $(COMPILE)

$(DIST_EGG): $(SOURCE)
	$(PYTHON) $(PYFLAGS) setup.py bdist_egg $(COMPILE)

$(DIST_EXE): $(SOURCE)
	$(PYTHON) $(PYFLAGS) setup.py bdist_wininst $(COMPILE)

$(DIST_RPM): $(SOURCE) $(MAN_PAGES)
	$(PYTHON) $(PYFLAGS) setup.py bdist_rpm $(COMPILE)
	# XXX Add man-pages to RPMs ... how?
	#$(PYTHON) $(PYFLAGS) setup.py bdist_rpm --post-install=rpm/postinstall --pre-uninstall=rpm/preuninstall $(COMPILE)

$(DIST_DEB): $(SOURCE) $(MAN_PAGES)
	# build the source package in the parent directory then rename it to
	# project_version.orig.tar.gz
	$(PYTHON) $(PYFLAGS) setup.py sdist $(COMPILE) --dist-dir=../
	rename -f 's/$(PROJECT)-(.*)\.tar\.gz/$(PROJECT)_$$1\.orig\.tar\.gz/' ../*
	dpkg-buildpackage -i -I -rfakeroot
	mkdir -p dist/
	mv ../$(NAME)_$(VER)-1~ppa1_all.deb dist/

