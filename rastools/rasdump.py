#!/usr/bin/env python
# vim: set et sw=4 sts=4:

import os
import sys
import logging
import rastools.main
import rastools.rasfile
import numpy as np
from collections import namedtuple

OUTPUT_FORMATS = {}

Crop = namedtuple('Crop', ('top', 'left', 'bottom', 'right'))

class RasDumpUtility(rastools.main.Utility):
    """%prog [options] ras-file [channels-file]

    This utility accepts a QSCAN RAS file and an optional channel definition
    file. For each channel listed in the latter (or all channels if none is
    provided), a dump is produced of the corresponding channel in the RAS file.
    Various options are provided for customizing the output including
    percentile limiting, and output format.

    The available command line options are listed below.
    """

    def __init__(self):
        super(RasDumpUtility, self).__init__()
        self.parser.set_defaults(
            list_formats=False,
            crop='0,0,0,0',
            percentile=100.0,
            output='{filename_root}_{channel:02d}_{channel_name}.csv',
            empty=False,
            multi=False,
        )
        self.parser.add_option('--help-formats', dest='list_formats', action='store_true',
            help="""list the available file output formats""")
        self.parser.add_option('-p', '--percentile', dest='percentile', action='store',
            help="""clip values in the output image to the specified percentile""")
        self.parser.add_option('-C', '--crop', dest='crop', action='store',
            help="""crop the input data by top,left,bottom,right points""")
        self.parser.add_option('-o', '--output', dest='output', action='store',
            help="""specify the template used to generate the output filenames; supports {variables}, see --help-formats for supported file formats. Default: %default""")
        self.parser.add_option('-m', '--multi', dest='multi', action='store_true',
            help="""if specified, produce a single output file with multiple pages or sheets, one per channel (only available with certain formats)""")
        self.parser.add_option('-e', '--empty', dest='empty', action='store_true',
            help="""if specified, empty channels in the output (by default empty channels are ignored)""")

    def main(self, options, args):
        super(RasDumpUtility, self).main(options, args)
        self.load_backends()
        if options.list_formats:
            sys.stdout.write('The following file formats are available:\n\n')
            sys.stdout.write('\n'.join(sorted(ext for ext in OUTPUT_FORMATS)))
            sys.stdout.write('\n\n')
            return 0
        if len(args) < 1:
            self.parser.error('you must specify a RAS file')
        if len(args) > 2:
            self.parser.error('you cannot specify more than two filenames')
        if args[0] == '-' and args[1] == '-':
            self.parser.error('you cannot specify stdin for both files!')
        # Parse the input files
        ras_f = rastools.rasfile.RasFileReader(
            sys.stdin if args[0] == '-' else args[0],
            None if len(args) < 2 else sys.stdin if args[1] == '-' else args[1],
            verbose=options.loglevel<logging.WARNING)
        # Check the clip level is a valid percentage
        try:
            options.percentile = float(options.percentile)
        except ValueError:
            self.parser.error('%s is not a valid percentile' % options.percentile)
        if not (0 <= options.percentile <= 100.0):
            self.parser.error('percentile must be between 0 and 100 (%f specified)' % options.percentile)
        # Check the crop values
        try:
            top, left, bottom, right = options.crop.split(',', 4)
        except ValueError:
            self.parser.error('you must specify 4 integer values for the --crop option')
        try:
            options.crop = Crop(int(top), int(left), int(bottom), int(right))
        except ValueError:
            self.parser.error('non-integer values found in --crop value %s' % options.crop)
        # Check the requested file format is known
        ext = os.path.splitext(options.output)[1].lower()
        try:
            (writer_class, multi_class) = OUTPUT_FORMATS[ext]
        except KeyError:
            self.parser.error('unknown output format "%s"' % ext)
        # Check special format switches
        if options.multi and not multi_class:
            multi_ext = [ext for (ext, (cls, multi)) in OUTPUT_FORMATS.iteritems() if multi]
            if multi_ext:
                self.parser.error('output filename must end with %s when --multi is specified' % ','.join(multi_ext))
            else:
                self.parser.error('--multi is not supported by any registered output formats')
        # Calculate the percentile index (this will be the same for every
        # channel as every channel has the same dimensions in a RAS file)
        if options.percentile < 100.0:
            options.vmax_index = round(
                (ras_f.raster_count - options.crop.top - options.crop.bottom) *
                (ras_f.point_count - options.crop.left - options.crop.right) *
                options.percentile / 100.0)
            logging.info('%gth percentile is at index %d' % (options.percentile, options.vmax_index))
        # Extract the specified channels
        logging.info('File contains %d channels, extracting channels %s' % (
            len(ras_f.channels),
            ','.join(str(channel.index) for channel in ras_f.channels if channel.enabled)
        ))
        if options.multi:
            filename = ras_f.format(options.output, **self.format_options(options))
            logging.warning('Writing all channels to %s' % filename)
            output = multi_class(filename, ras_f)
        try:
            for channel in ras_f.channels:
                if channel.enabled:
                    if options.multi:
                        logging.warning('Writing channel %d (%s) to new page' % (channel.index, channel.name))
                    else:
                        filename = channel.format(options.output, **self.format_options(options))
                        logging.warning('Writing channel %d (%s) to %s' % (channel.index, channel.name, filename))
                    data = self.dump_channel(channel, options)
                    if data is not None:
                        # Finally, dump the figure to disk as whatever format
                        # the user requested
                        if options.multi:
                            output.write_page(data, channel)
                        else:
                            writer_class(filename, channel).write(data)
        finally:
            if options.multi:
                output.close()

    def dump_channel(self, channel, options):
        """Dump the specified channel, returning the resulting numpy array"""
        # Perform any cropping requested. This must be done before
        # calculation of the data's range and percentile limiting is
        # performed for obvious reasons
        data = channel.data
        data = data[
            options.crop.top:data.shape[0] - options.crop.bottom,
            options.crop.left:data.shape[1] - options.crop.right
        ]
        # Find the minimum and maximum values in the channel and clip
        # them to a percentile if required
        vsorted = np.sort(data, None)
        vmin = vsorted[0]
        vmax = vsorted[-1]
        logging.info('Channel %d (%s) has range %d-%d' % (channel.index, channel.name, vmin, vmax))
        if options.percentile < 100.0:
            pmax = vsorted[options.vmax_index]
            logging.info('%gth percentile is %d' % (options.percentile, pmax))
            if pmax != vmax:
                logging.info('Channel %d (%s) has new range %d-%d' % (channel.index, channel.name, vmin, pmax))
        else:
            pmax = vmax
        # No minimum for the percentile (yet...)
        pmin = 0
        if pmin == pmax:
            if options.empty:
                logging.warning('Channel %d (%s) is empty' % (channel.index, channel.name))
            else:
                logging.warning('Channel %d (%s) is empty, skipping' % (channel.index, channel.name))
                return None
        # Apply the percentiles
        data[data < pmin] = pmin
        data[data > pmax] = pmax
        return data

    def format_options(self, options):
        """Utility routine which converts the options array for use in format substitutions"""
        return dict(
            percentile=options.percentile,
            crop=','.join(str(i) for i in options.crop),
        )

    def load_backends(self):
        """Load the various matplotlib backends and custom extensions"""
        logging.info('Loading CSV renderer')
        try:
            global CsvWriter
            from rastools.rascsv import CsvWriter, TsvWriter
        except ImportError:
            # If we can't find the default CSV backend, something's seriously
            # wrong (it's built into python!)
            raise
        else:
            OUTPUT_FORMATS.update({
                # ext    writer-class  multi-class
                '.csv':  (CsvWriter,   None),
                '.tsv':  (TsvWriter,   None),
            })

        logging.info('Loading RAS support')
        try:
            global RasWriter, RasAsciiWriter, RasMultiWriter, RasAsciiMultiWriter
            from rastools.rasras import RasWriter, RasAsciiWriter, RasMultiWriter, RasAsciiMultiWriter
        except ImportError:
            logging.warning('Failed to load RAS support')
        else:
            OUTPUT_FORMATS.update({
                # ext     writer-class     multi-class
                '.ras':   (RasWriter,      RasMultiWriter),
                '.ras_a': (RasAsciiWriter, RasAsciiMultiWriter),
            })

        logging.info('Loading Excel support')
        try:
            global XlsWriter, XlWorkbook
            from rastools.rasxls import XlsWriter, XlsMulti
        except ImportError:
            logging.warning('Failed to load Excel support')
        else:
            OUTPUT_FORMATS.update({
                # ext    writer-class  multi-class
                '.xls':  (XlsWriter,   XlsMulti),
            })


main = RasDumpUtility()
