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

import sys
mswindows = sys.platform.startswith('win')

import os
import optparse
import ConfigParser
import logging
import locale
import traceback
import glob

__version__ = '0.1'

# Use the user's default locale instead of C
locale.setlocale(locale.LC_ALL, '')

class OptionParser(optparse.OptionParser):
    # Customize error handling to raise an exception (default simply prints an
    # error and terminates execution)
    def error(self, msg):
        raise optparse.OptParseError(msg)

class Utility(object):
    # Get the default output encoding from the default locale
    encoding = locale.getdefaultlocale()[1]
    status = ''
    progress = 0

    # This class is the abstract base class for each of the command line
    # utility classes defined. It provides some basic facilities like an option
    # parser, console pretty-printing, logging and exception handling

    def __init__(self, usage=None, version=None, description=None):
        super(Utility, self).__init__()
        if usage is None:
            usage = self.__doc__.split('\n')[0]
        if version is None:
            version = '%%prog %s' % __version__
        if description is None:
            description = '\n'.join(s.strip() for s in self.__doc__.split('\n')[1:] if s)
        self.parser = OptionParser(
            usage=usage,
            version=version,
            description=description,
        )
        self.parser.set_defaults(
            debug=False,
            logfile='',
            loglevel=logging.WARNING
        )
        self.parser.add_option('-q', '--quiet', dest='loglevel', action='store_const', const=logging.ERROR,
            help="""produce less console output""")
        self.parser.add_option('-v', '--verbose', dest='loglevel', action='store_const', const=logging.INFO,
            help="""produce more console output""")
        self.parser.add_option('-l', '--log-file', dest='logfile',
            help="""log messages to the specified file""")
        self.parser.add_option('-P', '--pdb', dest='debug', action='store_true',
            help="""run under PDB (debug mode)""")

    def __call__(self, args=None):
        if args is None:
            args = sys.argv[1:]
        (options, args) = self.parser.parse_args(self.expand_args(args))
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter('%(message)s'))
        console.setLevel(options.loglevel)
        logging.getLogger().addHandler(console)
        if options.logfile:
            logfile = logging.FileHandler(options.logfile)
            logfile.setFormatter(logging.Formatter('%(asctime)s, %(levelname)s, %(message)s'))
            logfile.setLevel(logging.DEBUG)
            logging.getLogger().addHandler(logfile)
        if options.debug:
            console.setLevel(logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
        if options.debug:
            import pdb
            return pdb.runcall(self.main, options, args)
        else:
            try:
                return self.main(options, args) or 0
            except:
                return self.handle(*sys.exc_info())

    def expand_args(self, args):
        """Expands @response files and wildcards in the command line"""
        result = []
        for arg in args:
            if arg.startswith('@') and len(arg) > 1:
                arg = os.path.normcase(os.path.realpath(os.path.abspath(os.path.expanduser(arg[1:]))))
                try:
                    with open(arg, 'rU') as resp_file:
                        for resp_arg in resp_file:
                            # Only strip the line break (whitespace is significant)
                            resp_arg = resp_arg.rstrip('\n')
                            # Only perform globbing on response file values for UNIX
                            if mswindows:
                                result.append(resp_arg)
                            else:
                                result.extend(self.glob_arg(resp_arg))
                except IOError, e:
                    raise optparse.OptionValueError(str(e))
            else:
                result.append(arg)
        # Perform globbing on everything for Windows
        if mswindows:
            result = reduce(lambda a, b: a + b, [self.glob_arg(f) for f in result], [])
        return result

    def glob_arg(self, arg):
        """Performs shell-style globbing of arguments"""
        if set('*?[') & set(arg):
            args = glob.glob(os.path.normcase(os.path.realpath(os.path.abspath(os.path.expanduser(arg)))))
            if args:
                return args
        # Return the original parameter in the case where the parameter
        # contains no wildcards or globbing returns no results
        return [arg]

    def handle(self, type, value, tb):
        """Exception hook for non-debug mode."""
        if issubclass(type, (SystemExit, KeyboardInterrupt)):
            # Just ignore system exit and keyboard interrupt errors (after all,
            # they're user generated)
            return 130
        elif issubclass(type, (ValueError, IOError, ConfigParser.Error)):
            # For simple errors like IOError just output the message which
            # should be sufficient for the end user (no need to confuse them
            # with a full stack trace)
            logging.critical(str(value))
            return 1
        elif issubclass(type, (optparse.OptParseError,)):
            # For option parser errors output the error along with a message
            # indicating how the help page can be displayed
            logging.critical(str(value))
            logging.critical('Try the --help option for more information.')
            return 2
        else:
            # Otherwise, log the stack trace and the exception into the log
            # file for debugging purposes
            for line in traceback.format_exception(type, value, tb):
                for s in line.rstrip().split('\n'):
                    logging.critical(s)
            return 1

    def progress_start(self):
        self.progress = 0
        self.status = 'Reading channel data %d%%' % self.progress
        sys.stderr.write(self.status)

    def progress_update(self, new_progress):
        if new_progress != self.progress:
            self.progress = new_progress
            new_status = 'Reading channel data %d%%' % self.progress
            sys.stderr.write('\b' * len(self.status))
            sys.stderr.write(new_status)
            self.status = new_status

    def progress_finish(self):
        sys.stderr.write('\n')

    def main(self, options, args):
        pass

