import configparser
import cv2
import logging as log
import platform
import pytesseract as pt
import re
import sys

from pathlib import Path

# Update recursion depth (limit) to prevent background refresh threads reaching max recursion depth
sys.setrecursionlimit(10 ** 6)

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

    # Disable PIL debug logging (when ImageGrab.grab() is called)
    log.getLogger('PIL').setLevel(log.INFO)

# GLOBALS ==============================================================================================================

WATERMARK_TEMPLATE = cv2.imread(config['Paths']['templates_dir'] + '/watermark.bmp')

# (width, height), -1 means the dimension is infinitely dynamic
TITLE_BAR_DIMENSIONS = [-1, 50]
HEADER_DIMENSIONS = [-1, 80]
FOOTER_DIMENSIONS = [-1, 270]

# Regex patterns
TABLE_ID_P = re.compile(r" (\d*?)$")
# STAKE_P = re.compile(r"^\$(.*?)\/\$(.*?) ")  # this pattern only works for games using real $ (not play money)
STAKE_P = re.compile(r"^(.*?)\/(.*?) ")
# TODO: update template below to allow for play money (used in tournament/sit & go games), also add check w/out cents
MONEY_P = re.compile("^\$(\d*?\.\d\d)$")  # this pattern only works for games using real $ (not play money)

# Card suits
SUITS_BY_COLOR = {
    'red': 'h',
    'blue': 'd',
    'green': 'c',
    'black': 's',
    'unknown': 'u'
}