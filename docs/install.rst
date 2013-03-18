============
Installation
============

rastools is distributed in several formats. The following sections detail
installation on a variety of platforms.


Pre-requisites
==============

Where possible, I endeavour to provide installation methods that provide all
pre-requisites automatically - see the following sections for platform specific
instructions.

If your platform is not listed (or you're simply interested in what rastools
depends on): rastools depends primarily on `matplotlib
<http://matplotlib.sourceforge.net>`_. If you wish to use the GUI you will also
need `PyQt4 <http://www.riverbankcomputing.com/software/pyqt/download>`_
installed.

Additional optional dependencies are:

 * `xlwt <http://pypi.python.org/pypi/xlwt>`_ - required for Excel writing support

 * `GIMP <http://www.gimp.org/>`_ - required for GIMP (.xcf) writing support


Ubuntu Linux
============

For Ubuntu Linux, it is simplest to install from the `PPA
<https://launchpad.net/~waveform/+archive/ppa>`_ as follows (this also ensures
you are kept up to date as new releases are made)::

    $ sudo add-apt-repository ppa://waveform/ppa
    $ sudo apt-get update
    $ sudo apt-get install rastools


Microsoft Windows
=================

On Windows it is simplest to install from the standalone MSI installation
package available from the `homepage <http://www.waveform.org.uk/rastools/>`_.
Be aware that the installation package requires administrator privileges.


Apple Mac OS X
==============

XXX To be written


Other Platforms
===============

If your platform is *not* covered by one of the sections above, rastools is
available from PyPI and can therefore be installed with the Python distribute
``pip`` tool::

   $ pip install rastools

Theoretically this should install the mandatory pre-requisites, but optional
pre-requisites require suffixes like the following::

   $ pip install "rastools[GUI,XLS]"

Please be aware that at this time, the PyQt package does not build "nicely"
under ``pip``. If it is available from your distro's package manager I strongly
recommend using that as your source of this pre-requisite.

If PyQt is not provided by your distro (or you're on some esoteric platform
without a package manager), you can try following the instructions on the
`Veusz wiki <http://barmag.net/veusz-wiki/DevStart>`_ for building PyQt (and
SIP) under a virtualenv sandbox.


Development
===========

If you wish to develop rastools, you can install the pre-requisites, construct
a virtualenv sandbox, and check out the source code from GitHub with the
following command lines::

   # Install the pre-requisites
   $ sudo apt-get install python-matplotlib python-xlwt python-qt4 python-virtualenv python-sphinx gimp make git

   # Construct and activate a sandbox with access to the packages we just
   # installed
   $ virtualenv --system-site-packages sandbox
   $ source sandbox/bin/activate

   # Check out the source code and install it in the sandbox for development and testing
   $ git clone https://github.com/waveform80/rastools.git
   $ cd rastools
   $ make develop

The above instructions assume you are on Ubuntu Linux. Please feel free to
extend this section with instructions for alternate platforms.
