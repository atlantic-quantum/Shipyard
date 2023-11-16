"""Logging for the shipyard
"""

# todo create CLI
# todo make logging level option in CLI

import logging

LOGGER = logging.getLogger("Compiler")
LOGGER.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
LOGGER.addHandler(ch)
