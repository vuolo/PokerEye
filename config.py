import configparser
import logging as log
from pathlib import Path
import platform
import sys


# Initialize config.ini
config = configparser.ConfigParser()
config.read('config.ini')
config['Environment']['OS'] = platform.system()
# Path(config['Paths']['table_patterns_dir'])


# Initialize logger
if config.getboolean('Debug', 'enabled'):
    log.basicConfig(
        level=log.DEBUG,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[
            log.FileHandler("logs/recent.log", mode='w'),
            log.StreamHandler(sys.stdout)
        ]
    )
