import logging

__all__ = ['DATA_WRITERS']

DATA_WRITERS = []

logging.info('Loading CSV renderer')
try:
    from rastools.csvwrite import CsvWriter, TsvWriter
except ImportError:
    # If we can't find the default CSV backend, something's seriously
    # wrong (it's built into python!)
    raise
else:
    DATA_WRITERS.extend([
        # class     extensions        description               multi-class
        (CsvWriter, ('.csv', '.CSV'), 'Comma Separated Values', None),
        (TsvWriter, ('.tsv', '.TSV'), 'Tab Separated Values',   None),
    ])

logging.info('Loading RAS support')
try:
    from rastools.raswrite import RasWriter, RasAsciiWriter, RasMultiWriter, RasAsciiMultiWriter
except ImportError:
    logging.warning('Failed to load RAS support')
else:
    DATA_WRITERS.extend([
        (RasWriter,      ('.ras', '.RAS'),     'QSCAN raster file',  RasMultiWriter),
        (RasAsciiWriter, ('.ras_a', '.RAS_A'), 'QSCAN ASCII output', RasAsciiMultiWriter),
    ])

logging.info('Loading Excel support')
try:
    from rastools.xlswrite import XlsWriter, XlsMulti
except ImportError:
    logging.warning('Failed to load Excel support')
else:
    DATA_WRITERS.extend([
        (XlsWriter, ('.xls', '.XLS'), 'Excel workbook', XlsMulti),
    ])
