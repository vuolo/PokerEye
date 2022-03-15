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
    from ScriptingBridge import *

# Windows (to be implemented...)
elif config['Environment']['OS'] == 'Windows':
    pass

table_windows = []  # j=0: window object, j=1: window title, j=2: hwnd


# TODO: Need more templates so that we can compare table at any state.
# TODO: Specifically, 6handed with button and spotlight, heads up with button, heads up with spotlight
def get_num_seats(img_gray) -> int:
    """
    Finds the number of seats from a grayscale screenshot
    Method: Check to see if all seats are found from the largest template first
    :param img_gray: Grayscale screenshot of the table
    :return: Number of seats
    """
    width = img_gray.shape[1]
    height = img_gray.shape[0]
    board_height = height - (TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1] + FOOTER_DIMENSIONS[1])
    # aspect_ratio = width / height

    # Compare the largest templates first to avoid incorrect matching
    # nine_crop = img_gray[410:(410 + 29), 321:(321 + 181)]  # [y1:y2, x1:x2]
    # for t in NINE_HANDED_TEMPLATES:
    #     if np.array_equal(t, nine_crop):
    #         return 9
    # six_crop = heads_up_crop  # TODO
    # for t in SIX_HANDED_TEMPLATES:
    #     if np.array_equal(t, six_crop):
    #         return 6
    # heads_up_crop = img_gray[410:(410 + 28), 270:(270 + 282)]  # [y1:y2, x1:x2]
    # for t in HEADS_UP_TEMPLATES:
    #     if np.array_equal(t, heads_up_crop):
    #         return 2

    # Check if 9-handed
    nine_handed_seats = {
        # [y1:y2, x1:x2]
        # 'title_bar': img_gray[0:TITLE_BAR_DIMENSIONS[1], 0:width - 1],
        # 'header': img_gray[TITLE_BAR_DIMENSIONS[1]:(TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1]), 0:width - 1],
        # 'footer': img_gray[(height - 1 - FOOTER_DIMENSIONS[1]):height - 1, 0:width - 1],
        # 'board': img_gray[(TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1]):(height - 1 - FOOTER_DIMENSIONS[1]), 0:width - 1],
        'bot_mid': img_gray[(TITLE_BAR_DIMENSIONS[1] + HEADER_DIMENSIONS[1]) + int((board_height / 4.75) * 4) - 1:height - 1 - FOOTER_DIMENSIONS[1],
                            int((width / 5) * 2) - 1:width - int((width / 5) * 2) - 1]
    }

    # width/height max growth aspect ratio: 1645 / 1255 = 1.31075
    # if aspect_ratio > 1.3

    # divide img_gray.shape dimensions by 2 to get # pixels (i=0: x, i=1: y)
    # log.debug(width)
    # log.debug(height)

    cv2.imshow('_', nine_handed_seats['bot_mid'])
    cv2.waitKey(0)
    return None


def resize_tables() -> None:
    app = SBApplication.applicationWithBundleIdentifier_("Poker-Lobby")
    if hasattr(app, 'windows'):
        log.debug(app)
        log.debug(app.windows())
        finderWin = app.windows()[0]
        finderWin.setBounds_([[100, 100], [100, 100]])
        finderWin.setPosition_([20, 20])

    # import applescript
    # resp = applescript.tell.app("System Events", '''
    # set frontApp to name of first application process whose frontmost is true
    # return "Done"
    # ''')
    # assert resp.code == 0, resp.err
    # print(resp.out)



    # import subprocess
    #
    # def get_window_title():
    #     cmd = """
    #         tell application "System Events"
    #             set frontApp to name of first application process whose frontmost is true
    #         end tell
    #         tell application frontApp
    #             if the (count of windows) is not 0 then
    #                 set window_name to name of front window
    #             end if
    #         end tell
    #         return window_name
    #     """
    #     result = subprocess.run(['osascript', '-e', cmd], capture_output=True)
    #     return result.stdout

    print(get_window_title())


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
                        # TODO: add functionality for updating blinds (should update an object incl. window attrib, etc.)
                        update_window_attributes(hwnd, opened_window)

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


def grab_screenshots(table_id=None) -> dict:
    """
    Grabs screenshots of all open table windows
    :param table_id: HWND (window number) of the table. Optional parameter to grab a single table screenshot
    :return: Object full of screenshots represented as bgr val arrays (OpenCV uses BGR instead of RGB)
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
        img = np.array(ImageGrab.grab(bbox))  # convert to array full of rgb vals
        img = img[:, :, ::-1]  # rgb to bgr (for OpenCV)
        ret[f'{str(title)} {str(hwnd)}'] = img

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
    Updates current_screenshot of each game_state
    """
    screenshots = grab_screenshots()
    for title, screenshot in screenshots.items():
        table_id = re.findall(TABLE_ID_P, title)[0]
        game_states[table_id].set_current_screenshot(screenshot)

    if forever:
        time.sleep(float(config.get('DEFAULT', 'screenshot_refresh_time_seconds')))
        refresh_table_windows(forever)


def init() -> None:
    """
    Called on startup. Responsible for initialization of game_state objects
    """
    screenshots = setup_tables()

    # Update game_states for each screenshot
    for title, screenshot in screenshots.items():
        gray_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

        # cv2.imshow('BGR to Grayscale', gray_screenshot)
        # cv2.waitKey(0)

        num_seats = get_num_seats(gray_screenshot)
        table_id = re.findall(TABLE_ID_P, title)[0]
        sb, bb = re.findall(STAKE_P, title)[0]
        sb = float(sb)
        bb = float(bb)
        game_states[table_id] = CashGameState(num_seats=num_seats, table_id=table_id, bb_size=bb, sb_size=sb,
                                              current_screenshot=screenshots[title])

    # Begin background refresh for table screenshots
    threading.Thread(target=update_screenshots, args=(True,)).start()


if __name__ == '__main__':
    # TODO: use mp.Pool(num_seats) later (not this func) to parse player chip stacks using mp with tesseract
    mp.set_start_method('spawn')
    game_states = {}
    init()

    for key, value in game_states.items():
        log.debug(value.num_seats)
