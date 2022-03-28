import numpy as np
import threading
import time
import tkinter as tk
from tkinter import font

from PIL import ImageGrab

from config import *
from classes.CashGameState import CashGameState
from classes.Player import Player
from libraries.pokertude import pokertude  # Modified to work silently with our software, returning useful dictionaries

# MacOS
if config.get('Environment', 'OS') == 'Darwin':
    import Quartz
    import applescript

# Windows (to be implemented...)
elif config.get('Environment', 'OS') == 'Windows':
    pass

table_windows = []  # j=0: window object, j=1: window title, j=2: hwnd

# TODO calculations:
# 1. Wining percentages
# 2. EV (EV = (W% * $W) – (L% * $L))


def convert_cards_to_abbr(cards_str, convert_ten=False) -> str:
    cards_using_abbr = cards_str
    i_offset = 0
    for i in range(len(cards_str)):
        if cards_using_abbr[i] in SUIT_ABBR_MAP:
            if convert_ten and cards_using_abbr[i] == 'T':
                cards_using_abbr = list(cards_using_abbr)
                cards_using_abbr[i] = '1'
                cards_using_abbr.insert(i + 1, '0')
                cards_using_abbr = ''.join(cards_using_abbr)
                i_offset = 1
            cards_using_abbr = list(cards_using_abbr)
            cards_using_abbr[i + i_offset] = SUIT_ABBR_MAP[cards_using_abbr[i + i_offset]]
            cards_using_abbr = ''.join(cards_using_abbr)
    return cards_using_abbr


def calc_statistics(game_state):
    game_hash = game_state.get_hash()

    # Base case to prevent overlapping calculations/repeating calculations
    if game_state.calculations['is_calculating'] or game_hash == game_state.calculations['last_calc_hash']:
        return

    # Initialize analyzer
    analyzer = pokertude.Analyzer()
    game_state.calculations['is_calculating'] = True
    game_state.calculations['last_calc_hash'] = game_hash

    # Get players
    hero = None
    num_active_opponents = 0  # TODO: get accurate number of current opponents from screenshot
    for player in game_state.players.values():
        if player.is_hero:
            hero = player
        if player.is_active:  # TODO: get accurate number of current opponents from screenshot (update .is_active)
            num_active_opponents += 1

    # Pre-Flop
    if game_state.board.count('[]') == 5:
        if hero.hand.count('[]') == 2:
            game_state.calculations['is_calculating'] = False
            return
        h1, h2 = pokertude.parse_cards(convert_cards_to_abbr(hero.hand, convert_ten=True))
        analyzer.set_hole_cards(h1, h2)
        analyzer.set_num_opponents(num_active_opponents)
        game_state.calculations['odds'] = analyzer.analyze()
    # Flop
    elif game_state.board.count('[]') == 2:
        cards = convert_cards_to_abbr(' '.join(game_state.board.split()[:3]), convert_ten=True)
        c1, c2, c3 = pokertude.parse_cards(cards)
        for c in [c1, c2, c3]:
            analyzer.community_card(c)
        analyzer.set_num_opponents(num_active_opponents)
        game_state.calculations['odds'] = analyzer.analyze()
    # Turn
    elif game_state.board.count('[]') == 1:
        turn_card = pokertude.parse_card(convert_cards_to_abbr(game_state.board.split()[3], convert_ten=True))
        analyzer.community_card(turn_card)
        analyzer.set_num_opponents(num_active_opponents)
        game_state.calculations['odds'] = analyzer.analyze()
    # River
    elif game_state.board.count('[]') == 0:
        river_card = pokertude.parse_card(convert_cards_to_abbr(game_state.board.split()[4], convert_ten=True))
        analyzer.community_card(river_card)
        analyzer.set_num_opponents(num_active_opponents)
        game_state.calculations['odds'] = analyzer.analyze()

    game_state.calculations['is_calculating'] = False
    log.debug(game_state.calculations)


def format_currency(num, symbol='$') -> str:
    return '$' + format(num, ',.2f')


def show_gfx():
    gfx.deiconify()


def hide_gfx():
    gfx.withdraw()


def update_gfx():
    # Hide gfx if no game_states are found
    if len(game_states.values()) == 0:
        hide_gfx()

    # Display formatted gfx for each game_state
    for game_state in game_states.values():
        if not grab_screenshots(game_state.table_id):
            hide_gfx()
            break
        show_gfx()
        gfx_width = 200
        geometry_str = '{0}x{1}+{2}+{3}'.format(gfx_width, int(game_state.bbox['Height']),
                                                int(game_state.bbox['X']) - gfx_width, int(game_state.bbox['Y']))
        gfx.geometry(geometry_str)

        # Update displayed data for game_state
        # Prevent incorrectly displaying an empty board after the flop
        if game_state.pot == 0.0:
            board_label.config(text=game_state.board)
        elif game_state.board.count('[]') != 5:
            board_label.config(text=game_state.board)

        pot_label.config(text=format_currency(game_state.pot))

        # TODO: display other player information
        for seat_num, player in game_state.players.items():
            bb_str = str(int(player.stack // game_state.bb)) if game_state.bb else "?"
            stack_str = f'{format_currency(player.stack)} (~{bb_str} BB) '
            hero_stack_label.config(text=stack_str)
            hero_hand_label.config(text=player.hand)
            break

        # TODO: add gfx support for more than 1 table
        break

    gfx.after(int(1000 * float(config.get('DEFAULT', 'gfx_update_time_seconds'))), update_gfx)  # convert to ms


def init_gfx():
    """
    Initializes hidden gfx windows
    """
    global gfx, board_label, pot_label, hero_stack_label, hero_hand_label
    width = int(config.get('DEFAULT', 'table_window_width')) // 2
    gfx = tk.Tk()
    gfx.wm_overrideredirect(True)
    gfx.geometry(f"{width}x{100}+{20}+{700}")
    gfx.configure(bg='black')

    # Header label
    header_label = tk.Label(text='PokerEye', font=("Arial Black", 18), fg='yellow', bg='black')
    header_label.place(x=55, y=5)

    # Board labels
    board_label = tk.Label(text='[] [] [] [] []', font=("Courier", 20), fg='cyan', bg='black')
    board_label.place(x=13, y=40)
    pot_label = tk.Label(font=("Arial", 16), fg='cyan', bg='black')
    pot_label.place(x=70, y=71)

    # Hero labels
    hero_header_label = tk.Label(text='Stats', font=("Arial Black", 18), fg='yellow', bg='black')
    hero_header_label.place(x=10, y=90)
    hero_stack_label = tk.Label(font=("Arial", 16), fg='yellow', bg='black')
    hero_stack_label.place(x=10, y=120)
    hero_hand_label = tk.Label(text='[] []', font=("Courier", 20), fg='yellow', bg='black')
    hero_hand_label.place(x=10, y=145)

    # Begin main gfx update loop
    update_gfx()
    gfx.mainloop()


def update_board(game_state: object) -> None:
    """
    Reads the board from the screenshot and stores it in the game_state
    :param game_state: CashGameState object
    """
    table = get_static_crop(game_state.screenshot, 'table')
    board_crops = {'full': table[365:365 + 165, 500:500 + (110 * 5) + (22 * 4)]}
    board_crops['card_1'] = board_crops['full'][0:-1, 0:110]
    board_crops['card_2'] = board_crops['full'][0:-1, 110 + 22:(110 * 2) + 22]
    board_crops['card_3'] = board_crops['full'][0:-1, (110 * 2) + (22 * 2):(110 * 3) + (22 * 2)]
    board_crops['card_4'] = board_crops['full'][0:-1, (110 * 3) + (22 * 3):(110 * 4) + (22 * 3)]
    board_crops['card_5'] = board_crops['full'][0:-1, (110 * 4) + (22 * 4):-1]
    board_crops['pot'] = table[260:260 + 53, 620:620 + 400]

    pot_crop_gray = cv2.cvtColor(board_crops['pot'], cv2.COLOR_RGB2GRAY)
    pot_str = ocr(img=pot_crop_gray, config='--psm 7').strip().replace(',', '').replace(' ', '')
    pot_str = '.'.join(re.findall(POT_P, pot_str))
    # Fix incorrect decimal points in place of commas
    if pot_str.count('.') > 1:
        pot_str = pot_str.replace('.', '', pot_str.count('.') - 1)
    game_state.set_pot(float(pot_str) if pot_str else 0.0)

    cards = []  # 5 max cards on the board
    for card_num in range(1, 6):
        card = parse_card(board_crops['card_' + str(card_num)], 'large')
        if card:
            cards.append(card)

    board = ''
    for card_num in range(1, 6):
        if card_num > len(cards):
            board += '[] '  # hidden cards
        else:
            board += cards[card_num - 1] + ' '

    board.strip()
    game_state.set_board(board)


def refresh_game_states(forever=False) -> None:
    """
    Update players in each game state
    """
    screenshots = grab_screenshots()

    # Update game_states for each screenshot
    if screenshots:
        for title, screenshot in screenshots.items():
            num_seats = get_num_seats(screenshot[0])
            table_id = re.findall(TABLE_ID_P, title)[0]
            blinds = parse_blinds(title)
            game_states[table_id] = CashGameState(num_seats=num_seats, table_id=table_id, sb=blinds[0], bb=blinds[1],
                                                  title=title, screenshot=screenshot[0], bbox=screenshot[1])

    # Populate players for each game state
    for game_state in game_states.values():
        populate_players(game_state)
        update_board(game_state)
        calc_statistics(game_state)

    # Display all current game states if debugging
    if config.getboolean('Debug', 'enabled') and config.getboolean('Debug', 'display_game_states_to_terminal'):
        display_game_states()

    if forever:
        time.sleep(float(config.get('DEFAULT', 'game_state_refresh_time_seconds')))
        refresh_game_states(forever)


# TODO: display statistics
def display_game_states() -> None:
    """
    Displays all current game states to console
    """
    for table_id, game_state in game_states.items():
        log.debug(f'### Table {game_state.table_id}: {game_state.title.replace(game_state.table_id, "")}')
        if not grab_screenshots(game_state.table_id):
            log.debug(' | ')
            log.debug(' | Unable to view the table window... Ensure the full table window visible.')
            log.debug(' | \n')
            continue
        log.debug(' | ')
        log.debug(' | Board ' + f'(${game_state.pot}):')
        log.debug(' | ' + game_state.board)
        log.debug(' | ')
        log.debug(' | Players:')
        for seat_num, player in game_state.players.items():
            log.debug(f' | Player {seat_num}: {player.__dict__}')
        log.debug(' | \n')


def ocr(img, x_scale=1, y_scale=1, config="") -> str:
    """
    Uses tesseract for ocr. Parses an image to string
    :param img: Image to parse
    :param x_scale: Image scale in the x direction
    :param y_scale: Image scale in the y direction
    :param config: Config to use for the ocr call (ex: --psm 10 -c tessedit_char_whitelist=123456789)
    :return: The parsed string from the image
    """
    img = cv2.resize(img, None, fx=x_scale, fy=y_scale)
    return pt.image_to_string(img, config=config)


def get_card_suit(card_crop) -> str:
    """
    Searches for card suit colors by RGB to determine card suit
    :param card_crop: Colored screenshot of the card or rank crop
    :return: Single character abbreviation of the card suit
    """
    for row in card_crop:
        for pixel in row:
            if np.array_equal(pixel, SUIT_RGB_VALS['red']):
                return SUIT_COLOR_MAP['red']
            elif np.array_equal(pixel, SUIT_RGB_VALS['green']):
                return SUIT_COLOR_MAP['green']
            elif np.array_equal(pixel, SUIT_RGB_VALS['blue']):
                return SUIT_COLOR_MAP['blue']
            elif np.array_equal(pixel, SUIT_RGB_VALS['black']):
                return SUIT_COLOR_MAP['black']

    return SUIT_COLOR_MAP['unknown']


def parse_card(card_crop, size='small') -> str:
    """
    Parses a screenshot of a card into a two character representation of the card (ex: Js or Td)
    :param card_crop: Cropped screenshot of a single card
    :param size: 'small' cards represent the hand's card size, 'large' cards represent the cards on the board
    :return:
    """
    if size == 'small':
        rank_crop = card_crop[0:50, 10:-30]
    else:
        rank_crop = card_crop[0:80, 10:-30]

    # Convert to grayscale and find rank
    rank_crop_gray = cv2.cvtColor(rank_crop, cv2.COLOR_RGB2GRAY)
    rank_ocr_config = f'--psm 7 -c tessedit_char_whitelist={CARD_RANKS}'
    rank_str = ocr(img=rank_crop_gray, config=rank_ocr_config).strip().replace('10', 'T')

    # Ensure a card is found before determining suit
    if len(rank_str) > 0:
        suit = get_card_suit(rank_crop)
        return '' if suit == 'u' else (rank_str + suit)

    return ''


def get_player_details(seat_crop, seat_location) -> Player:
    """
    Uses tesseract to parse a player's data from what is visible on the screenshot
    :param seat_crop: Screenshot of the player's seat
    :param seat_location: Name of the seat location (ex: 'bot_left', 'bot_mid', 'bot_right', etc.)
    :return: Player object initialized with correct player details
    """
    # Setup screenshot crops for varying info
    seat_crop_gray = cv2.cvtColor(seat_crop, cv2.COLOR_RGB2GRAY)
    player_crops = {
        'cards_both': seat_crop[0:110, 40:205],  # Note this crop is in color to check suit
        'seat_num': seat_crop_gray[130:160, 20:50],
        'stack': seat_crop_gray[120:-15, 60:230],  # TODO: fix why 1 sometimes shows up as 4...
        'button': [],  # TODO: button moves dynamically based on spot - right/left positions have it to the left/right
        'vacant_text': seat_crop_gray[115:-20, 85:170]
    }
    player_crops['card_left'] = player_crops['cards_both'][0:-1, 0:80]
    player_crops['card_right'] = player_crops['cards_both'][0:-1, 85:165]

    # Setup default attributes
    is_vacant = True if 'vacant' in ocr(img=player_crops['vacant_text'], config="--psm 8").lower() else False
    seat_num = -1
    hand = '[] []'
    position = ''
    stack = 0.0

    # Grab details if the seat is not vacant
    if not is_vacant:
        seat_num_str = ocr(img=player_crops['seat_num'], config="--psm 10 -c tessedit_char_whitelist=123456789").strip()
        seat_num = int(seat_num_str) if seat_num_str.isdigit() else 0
        stack_str = '0' + ocr(img=player_crops['stack'], config="--psm 7 -c tessedit_char_whitelist=0123456789,.")
        stack_str = stack_str.strip().replace(',', '')
        # Fix incorrect decimal points in place of commas
        if stack_str.count('.') > 1:
            stack_str = stack_str.replace('.', '', stack_str.count('.') - 1)
        stack = float(stack_str) if FLOAT_P.match(stack_str) else 0.0

        # Only retrieve hand if we are looking at the hero
        if seat_location == 'bot_mid':
            hand = (parse_card(player_crops['card_left']) + ' ' + parse_card(player_crops['card_right'])).strip()

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
    table_height = height - (TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1] + FOOTER_DIMENSIONS[1])

    if section == 'title_bar':
        return screenshot[0:TITLE_BAR_DIMENSIONS[1], 0:width - 1]
    elif section == 'title_bar_watermark':
        return screenshot[2:TITLE_BAR_DIMENSIONS[1] - 2, width - 1 - 155:width - 1 - 40]
    elif section == 'header':
        return screenshot[TITLE_BAR_DIMENSIONS[1]:(TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1]), 0:width - 1]
    elif section == 'footer':
        return screenshot[(height - 1 - FOOTER_DIMENSIONS[1]):height - 1, 0:width - 1]
    elif section == 'table':
        return screenshot[(TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1]):(height - 1 - FOOTER_DIMENSIONS[1]),
                          0:width - 1]


def get_seat_crops(screenshot, num_seats) -> dict:
    """
    Crops the main screenshot to get each seat
    :param screenshot: Screenshot of the table window. The format for cropping is as follows: [y1:y2, x1:x2]
    :param num_seats: Number of seats available for the table
    :return: Dictionary full of cropped screenshots of each seat
    """
    table = get_static_crop(screenshot, 'table')

    # TODO: add 2 handed, 3 handed, and 6 handed
    if num_seats == 9:
        return {
            # 'bot_left': table[601:601 + 180, 347:347 + 255],
            'bot_mid': table[625:625 + 180, 695:695 + 255],
            # 'bot_right': table[601:601 + 180, 1043:1043 + 255]
            # TODO: add the rest of the seat locations
        }


def populate_players(game_state) -> None:
    """
    Creates Player objects for each player found. For each player, sets seat_num, is_hero, and stack.
    These players are added to game_state's players dictionary.
    :param game_state: CashGameState object
    """
    # Crop current screen to hero's seat number (bot_mid is preferred seat setup in Ignition Casino's settings)
    seat_crops = get_seat_crops(game_state.screenshot, game_state.num_seats)
    game_state.clear_players()
    for seat_location, crop in seat_crops.items():
        player = get_player_details(crop, seat_location)
        game_state.add_player(player)


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
    dimensions = '{' + str(int(config.get('DEFAULT', 'table_window_width')) // 2) + ', '
    dimensions += str(int(config.get('DEFAULT', 'table_window_height')) // 2) + '}'
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
            table_id = str(table_windows[i][2])
            log.debug('Table closed: {0} [{1}]'  # Title [ID]
                      .format(table_windows[i][1], table_id))
            if str(table_windows[i][2]) in game_states:
                game_states.pop(table_id)
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
    if config.get('Environment', 'OS') == 'Darwin':
        for window in windows:
            if window[2] == hwnd:
                return True

    # Windows (to be implemented...)
    elif config.get('Environment', 'OS') == 'Windows':
        pass

    return False


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
        screenshot = capture_bounds(bbox)
        if not is_valid_screenshot(screenshot):
            continue

        # Update return dict
        ret[f'{str(title)} {str(hwnd)}'] = (screenshot, bbox_raw)

    return None if len(ret) == 0 else ret


def update_screenshots(forever=False) -> None:
    """
    Updates screenshot of each game_state
    """
    screenshots = grab_screenshots()
    if screenshots:
        for title, screenshot in screenshots.items():
            table_id = re.findall(TABLE_ID_P, title)[0]
            if table_id in game_states:
                game_states[table_id].set_screenshot(screenshot[0])

    if forever:
        time.sleep(float(config.get('DEFAULT', 'screenshot_refresh_time_seconds')))
        update_screenshots(forever)


def begin_background_refresh(func_str) -> None:
    """
    Initializes a new thread that repeats a specified function forever
    :param func_str: Specified function to run
    """
    def repeat_forever(func):
        forever_thread = threading.Thread(target=func, args=(True,))
        forever_thread.start()
        forever_thread.join()
        repeat_forever(func)

    if func_str == 'refresh_table_windows':
        threading.Thread(target=repeat_forever, args=(refresh_table_windows,)).start()
    elif func_str == 'update_screenshots':
        threading.Thread(target=repeat_forever, args=(update_screenshots,)).start()
    elif func_str == 'refresh_game_states':
        threading.Thread(target=repeat_forever, args=(refresh_game_states,)).start()


def refresh_table_windows(forever=False) -> None:
    """
    Updates table_windows (recurs until found)
    :param forever: Boolean determining whether to infinitely repeat this function
    """
    global table_windows

    # MacOS
    if config.get('Environment', 'OS') == 'Darwin':
        # Retrieve all active windows
        opened_windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID)
        opened_windows_formatted = []

        # Find all Ignition Casino windows
        for opened_window in opened_windows:
            if opened_window['kCGWindowOwnerName'] == 'Ignition Casino Poker':
                window_name = opened_window.get('kCGWindowName', None)
                hwnd = str(opened_window['kCGWindowNumber'])
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
    elif config.get('Environment', 'OS') == 'Windows':
        pass

    if forever:
        time.sleep(float(config.get('DEFAULT', 'window_refresh_time_seconds')))
        refresh_table_windows(forever)


def init() -> None:
    """
    Called on startup. Responsible for initialization of game_state objects
    """
    begin_background_refresh('refresh_table_windows')
    begin_background_refresh('update_screenshots')
    begin_background_refresh('refresh_game_states')
    init_gfx()


if __name__ == '__main__':
    game_states = {}
    init()


