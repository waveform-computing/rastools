import logging

__all__ = ['PARSERS']

PARSERS = []

logging.info('Loading RAS parser')
try:
    from rastools.rasparse import RasFileReader
except ImportError:
    logging.warning('Failed to load RAS parser')
else:
    PARSERS.extend([
        (RasFileReader, ('.ras', '.RAS'), 'QSCAN raster file'),
    ])

logging.info('Loading DAT parser')
try:
    from rastools.datparse import DatFileReader
except ImportError:
    logging.warning('Failed to load DAT parser')
else:
    PARSERS.extend([
        (DatFileReader, ('.dat', '.DAT'), "Sam's DAT file"),
    ])

