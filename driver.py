import multiprocessing as mp
import numpy as np
import threading
import time

from PIL import ImageGrab

from config import *
from classes.CashGameState import CashGameState
from classes.Player import Player

# MacOS
if config['Environment']['OS'] == 'Darwin':
    import Quartz
    import applescript

# Windows (to be implemented...)
elif config['Environment']['OS'] == 'Windows':
    pass

table_windows = []  # j=0: window object, j=1: window title, j=2: hwnd


def display_game_states() -> None:
    """
    Displays all current game states to console
    """
    for key, value in game_states.items():
        log.debug(f'Game: {value.title}')
        for key2, value2 in value.players.items():
            log.debug(f'Player: {value2.__dict__}')
        log.debug('')


# uses tesseract for ocr. Parses an image to string
def ocr(img, x_scale=1, y_scale=1, config="") -> str:
    img = cv2.resize(img, None, fx=x_scale, fy=y_scale)
    return pt.image_to_string(img, config=config)


# TODO: take in a colored screenshot, then get the suit of the card based on the color of the letter.
def get_player_details(seat_crop, seat_location) -> Player:
    # Setup screenshot crops for varying info
    seat_crop_gray = cv2.cvtColor(seat_crop, cv2.COLOR_RGB2GRAY)
    player_crops = {
        'cards_both': seat_crop[0:110, 40:205],  # Note this crop is in color to check suit
        'seat_num': seat_crop_gray[130:160, 20:50],
        'stack': seat_crop_gray[125:-20, 60:230],  # TODO: fix why 1 sometimes shows up as 4...?
        'button': [],  # TODO: button moves dynamically based on spot - right/left positions have it to the left/right
        'vacant_text': seat_crop_gray[110:-15, 85:170]
    }
    player_crops['card_left'] = player_crops['cards_both'][0:-1, 0:80]
    player_crops['card_left_rank_only'] = player_crops['card_left'][0:50, 10:-30]
    player_crops['card_right'] = player_crops['cards_both'][0:-1, 85:165]
    player_crops['card_right_rank_only'] = player_crops['card_right'][0:50, 10:-30]

    # Setup default attributes
    is_vacant = True if 'vacant' in ocr(img=player_crops['vacant_text'], config="--psm 8").lower() else False
    seat_num = -1
    hand = ''
    position = ''
    stack = 0.0

    # cv2.imshow('_', player_crops['vacant_text'])
    # cv2.waitKey(0)

    if not is_vacant:
        seat_num = int(ocr(img=player_crops['seat_num'], config="--psm 10 -c tessedit_char_whitelist=123456789").strip())
        stack = float(ocr(img=player_crops['stack'], config="--psm 8 -c tessedit_char_whitelist=0123456789.").strip())

        # Only retrieve hand if we are looking at the hero
        if seat_location == 'bot_mid':
            card_left_rank_only_gray = cv2.cvtColor(player_crops['card_left_rank_only'], cv2.COLOR_RGB2GRAY)
            card_right_rank_only_gray = cv2.cvtColor(player_crops['card_right_rank_only'], cv2.COLOR_RGB2GRAY)

            card_ranks = '1234567890AKJQ'
            tesseract_cards_config = f"--psm 8 -c tessedit_char_whitelist={card_ranks}"
            card_left_str = ocr(img=card_left_rank_only_gray, config=tesseract_cards_config).strip()
            card_right_str = ocr(img=card_right_rank_only_gray, config=tesseract_cards_config).strip()

            # TODO: use https://stackoverflow.com/questions/47483951/how-to-define-a-threshold-value-to-detect-only-green-colour-objects-in-an-image
            # TODO: To check for colors to determin suit
            card_left_color = 'unknown'
            card_right_color = 'unknown'

            log.debug(np.unique(player_crops['card_left_rank_only'], axis=0, return_counts=True))

            hand = card_left_str + SUITS_BY_COLOR[card_left_color] + ' '  # left card
            hand += card_right_str + SUITS_BY_COLOR[card_right_color]  # right card

    return Player(seat_location=seat_location, seat_num=seat_num, is_hero=seat_location == 'bot_mid',
                  is_vacant=is_vacant, hand=hand, position=position, stack=stack)


def get_static_crop(screenshot, section):
    """
    Crops a static part of the table window
    :param screenshot: Screenshot of the table window. The format for cropping is as follows: [y1:y2, x1:x2]
    :param section: Determines the bounds to crop around
    :return: Cropped screenshot with the specified section's bounds
    """
    width = screenshot.shape[1]
    height = screenshot.shape[0]
    board_height = height - (TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1] + FOOTER_DIMENSIONS[1])

    if section == 'title_bar':
        return screenshot[0:TITLE_BAR_DIMENSIONS[1], 0:width - 1]
    elif section == 'title_bar_watermark':
        return screenshot[2:TITLE_BAR_DIMENSIONS[1] - 2, width - 1 - 155:width - 1 - 40]
    elif section == 'header':
        return screenshot[TITLE_BAR_DIMENSIONS[1]:(TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1]), 0:width - 1]
    elif section == 'footer':
        return screenshot[(height - 1 - FOOTER_DIMENSIONS[1]):height - 1, 0:width - 1]
    elif section == 'board':
        return screenshot[(TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1]):(height - 1 - FOOTER_DIMENSIONS[1]),
               0:width - 1]


def get_seat_crops(screenshot, num_seats) -> dict:
    """
    Crops the main screenshot to get each seat
    :param screenshot: Screenshot of the table window. The format for cropping is as follows: [y1:y2, x1:x2]
    :param num_seats: Number of seats available for the table
    :return: Dictionary full of cropped screenshots of each seat
    """
    board = get_static_crop(screenshot, 'board')

    if num_seats == 9:
        return {
            # 'bot_left': board[601:601 + 180, 347:347 + 255],
            'bot_mid': board[625:625 + 180, 695:695 + 255],
            # 'bot_right': board[601:601 + 180, 1043:1043 + 255]
        }


def populate_players(game_state) -> None:
    """
    Creates Player objects for each player found. For each player, sets seat_num, is_hero, and stack.
    These players are added to game_state's players dictionary.
    :param game_state: CashGameState object
    """
    # Crop current screen to hero's seat number (bot_mid is preferred seat setup in Ignition Casino's settings)
    seat_crops = get_seat_crops(game_state.screenshot, game_state.num_seats)
    for seat_location, crop in seat_crops.items():
        player = get_player_details(crop, seat_location)
        game_state.players[str(player.seat_num)] = player


def parse_blinds(title) -> tuple:
    """
    Parses the blinds from the title of the table window
    :param title: Table window title
    :return: Tuple containing floats of each blind (small blind, big blind)
    """
    if '/' in title:
        sb, bb = re.findall(STAKE_P, title)[0]
        return float(sb), float(bb)

    return 0.0, 0.0


def get_num_seats(screenshot) -> int:
    """
    Finds the number of seats from a grayscale screenshot
    Method: Check to see if all seats are found from the largest template first
    :param screenshot: Screenshot of the table window
    :return: Number of seats
    """
    # TODO: Compare the largest templates first to avoid incorrect matching
    return 9  # temp until functionality is implemented


def is_valid_screenshot(screenshot) -> bool:
    """
    Checks whether a screenshot was correctly taken of the table
    :param screenshot: Screenshot of the table window bounds
    :return: Boolean indicating whether the screenshot is actually of an Ignition Casino window.
    """
    title_bar_watermark = get_static_crop(screenshot, 'title_bar_watermark')

    # Validate screenshot matches the Ignition Casino watermark
    return np.array_equal(WATERMARK_TEMPLATE, title_bar_watermark)


def resize_tables() -> None:
    """
    Resizes all active table windows to the same size specified in the config
    """
    dimensions = '{' + str(int(config['DEFAULT']['table_width']) // 2) + ', '
    dimensions += str(int(config['DEFAULT']['table_height']) // 2) + '}'
    applescript.tell.app("System Events", f'''tell application process "Ignition Casino Poker"
                                                set allWindows to every window
                                                repeat with aWindow in allWindows
                                                    set size of aWindow to {dimensions}
                                                end repeat
                                              end tell''')


def update_window_attributes(hwnd, opened_window) -> None:
    """
    Update window attributes using current window state
    :param hwnd: Handle to Window (window number)
    :param opened_window: Most recent state of a window found by looking through all opened windows
    """
    for i in range(0, len(table_windows)):
        if hwnd == table_windows[i][2]:
            if table_windows[i][1] != opened_window['kCGWindowName']:
                if table_windows[i][1] != 'Poker':  # Default (uninitialized) title when launching a table w/ Ignition
                    log.debug('Table game updated: {0} -> {1} [{2}]'
                              .format(table_windows[i][1], opened_window['kCGWindowName'], hwnd))
                table_windows[i][1] = opened_window['kCGWindowName']
            table_windows[i][0] = opened_window
            resize_tables()


def validate_table_windows(opened_windows) -> None:
    """
    Remove old/invalid table windows (recurs until valid)
    :param opened_windows: Array of all currently opened windows
    """
    for i in range(0, len(table_windows)):
        if not window_already_found(table_windows[i][2], opened_windows):
            log.debug('Table closed: {0} [{1}]'
                      .format(table_windows[i][1], table_windows[i][2]))
            table_windows.pop(i)
            validate_table_windows(opened_windows)
            break


def window_already_found(hwnd, windows=table_windows) -> bool:
    """
    Checks whether a hwnd is already found
    :param hwnd: Handle to Window (window number)
    :param windows: Array of windows to search through
    :return: Boolean indicating whether the window is found
    """
    # MacOS
    if config['Environment']['OS'] == 'Darwin':
        for window in windows:
            if window[2] == hwnd:
                return True

    # Windows (to be implemented...)
    elif config['Environment']['OS'] == 'Windows':
        pass

    return False


def refresh_table_windows(forever=False) -> None:
    """
    Updates table_windows (recurs until found)
    :param forever: Boolean determining whether to infinitely repeat this function
    """
    global table_windows

    # MacOS
    if config['Environment']['OS'] == 'Darwin':
        # Retrieve all active windows
        opened_windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID)
        opened_windows_formatted = []

        # Find all Ignition Casino windows
        for opened_window in opened_windows:
            if opened_window['kCGWindowOwnerName'] == 'Ignition Casino Poker':
                window_name = opened_window.get('kCGWindowName', None)
                hwnd = opened_window['kCGWindowNumber']
                opened_windows_formatted.append([opened_window, window_name, hwnd])
                if window_name is None:
                    log.error('Unable to read window titles... Ensure you have enabled Screen Recording privileges for '
                              'the IDE in System Preferences > Security & Privacy > Screen Recording')
                    sys.exit(-1)
                elif 'Poker Lobby' not in window_name:
                    if not window_already_found(hwnd):
                        # Still loading
                        if window_name == 'Poker':
                            log.debug('Loading new table... [{0}]'
                                      .format(hwnd))
                        # Unknown blinds
                        elif '/' not in window_name:
                            log.debug('Found new table ({0} [{1}]). Loading blinds...'
                                      .format(window_name, hwnd))
                        # Blinds found... load table window
                        else:
                            log.debug('Loaded new table: {0} [{1}]'
                                      .format(window_name, hwnd))
                        table_windows.append([opened_window, window_name, hwnd])
                    else:
                        update_window_attributes(hwnd, opened_window)

        # Remove invalid tables before ending
        validate_table_windows(opened_windows_formatted)

        # Recur until a table window is found...
        if len(table_windows) == 0:
            log.error('No open tables found. Searching again in {0} second{1}...'
                      .format(config.get('DEFAULT', 'window_refresh_time_seconds'),
                              '(s)' if config.get('DEFAULT', 'window_refresh_time_seconds') != '1' else ''))
            time.sleep(float(config.get('DEFAULT', 'window_refresh_time_seconds')))
            refresh_table_windows()

    # Windows (to be implemented...)
    elif config['Environment']['OS'] == 'Windows':
        pass

    if forever:
        time.sleep(float(config.get('DEFAULT', 'window_refresh_time_seconds')))
        refresh_table_windows(forever)


def capture_bounds(bbox) -> object:
    """
    Captures a screenshot of the specified bounds
    :param bbox: Bounds box tuple (x1, y1, x2, y2)
    :return: Image returned by PIL ImageGrab.grab()
    """
    screenshot = np.array(ImageGrab.grab(bbox))  # convert to array full of bgr vals
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)  # convert from bgr to rgb (for OpenCV)
    return screenshot


def grab_screenshots(table_id=None) -> dict:
    """
    Grabs screenshots of all open table windows
    :param table_id: HWND (window number) of the table. Optional parameter to grab a single table screenshot
    :return: Object full of screenshots represented as rgb val numpy arrays
    """
    ret = {}
    for table_window in table_windows:
        if table_id and table_id != table_window[2]:  # allow for specific screenshots of a table by id
            continue
        hwnd = table_window[2]
        title = table_window[1]
        bbox_raw = table_window[0]['kCGWindowBounds']  # bounds box
        bbox = (
            bbox_raw['X'] * 2,  # x1
            bbox_raw['Y'] * 2,  # y1
            bbox_raw['X'] * 2 + bbox_raw['Width'] * 2,  # x2
            bbox_raw['Y'] * 2 + bbox_raw['Height'] * 2  # y2
        )

        # TODO: add multi display support
        while True:
            screenshot = capture_bounds(bbox)
            if is_valid_screenshot(screenshot):
                break
            # Halt until a valid screenshot is found
            time.sleep(float(config.get('DEFAULT', 'screenshot_refresh_time_seconds')))

        # Update return dict
        ret[f'{str(title)} {str(hwnd)}'] = screenshot

    return None if len(ret) == 0 else ret


def setup_tables() -> dict:
    """
    Begins background refresh for grabbing table screenshots
    :return: Table screenshots from the grab_screenshots() function
    """
    # Initial table refresh (hangs until found)
    refresh_table_windows()

    # Begin background refresh for table windows
    threading.Thread(target=refresh_table_windows, args=(True,)).start()

    return grab_screenshots()


def update_screenshots(forever=False) -> None:
    """
    Updates screenshot of each game_state
    """
    screenshots = grab_screenshots()
    if screenshots:
        for title, screenshot in screenshots.items():
            table_id = re.findall(TABLE_ID_P, title)[0]
            game_states[table_id].set_screenshot(screenshot)

    if forever:
        # Display all current game states if debugging
        if config.getboolean('Debug', 'enabled'):
            display_game_states()

        time.sleep(float(config.get('DEFAULT', 'screenshot_refresh_time_seconds')))
        update_screenshots(forever)


def init() -> None:
    """
    Called on startup. Responsible for initialization of game_state objects
    """
    screenshots = setup_tables()

    # Update game_states for each screenshot
    for title, screenshot in screenshots.items():
        num_seats = get_num_seats(screenshot)
        table_id = re.findall(TABLE_ID_P, title)[0]
        blinds = parse_blinds(title)
        game_states[table_id] = CashGameState(num_seats=num_seats, table_id=table_id, sb=blinds[0], bb=blinds[1],
                                              title=title, screenshot=screenshots[title])

    # Setup each Player objects in each game state
    for game_state in game_states.values():
        populate_players(game_state)

    # Begin background refresh for table screenshots
    threading.Thread(target=update_screenshots, args=(True,)).start()


if __name__ == '__main__':
    # TODO: use mp.Pool(num_seats) later (not in this func) to parse player chip stacks using mp with tesseract
    mp.set_start_method('spawn')
    game_states = {}
    init()
