import multiprocessing as mp
import threading
import time

from config import *
from classes.CashGameState import CashGameState
from classes.Player import Player

table_windows = []


# Update window title using current window state
def update_window_title(window_number, opened_window) -> None:
    for i in range(0, len(table_windows)):
        if window_number == table_windows[i][2] and table_windows[i][1] != opened_window['kCGWindowName']:
            if table_windows[i][1] != 'Poker':
                log.debug('Table game updated: {0} -> {1} [{2}]'
                          .format(table_windows[i][1], opened_window['kCGWindowName'], window_number))
            table_windows[i][1] = opened_window['kCGWindowName']
            break


# Remove old/invalid table windows (recurs until valid)
def validate_table_windows(opened_windows) -> None:
    for i in range(0, len(table_windows)):
        if not window_already_found(table_windows[i][2], opened_windows):
            log.debug('Table closed: {0} [{1}]'
                      .format(table_windows[i][1], table_windows[i][2]))
            table_windows.pop(i)
            validate_table_windows(opened_windows)
            break


# Checks whether a window number is already found
def window_already_found(window_number, windows=table_windows) -> bool:
    # MacOS
    if config['Environment']['OS'] == 'Darwin':
        for window in windows:
            if window[2] == window_number:
                return True

    # Windows (to be implemented...)
    elif config['Environment']['OS'] == 'Windows':
        pass

    return False


# Updates table_windows (recurs until found)
def refresh_table_windows() -> None:
    global table_windows

    # MacOS
    if config['Environment']['OS'] == 'Darwin':
        # Retrieve all active windows
        import Quartz
        opened_windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID)
        opened_windows_formatted = []

        for opened_window in opened_windows:
            if opened_window['kCGWindowOwnerName'] == 'Ignition Casino Poker':
                window_name = opened_window.get('kCGWindowName', None)
                window_number = opened_window['kCGWindowNumber']
                opened_windows_formatted.append([opened_window, window_name, window_number])
                if window_name is None:
                    log.error('Unable to read window titles... Ensure you have enabled Screen Recording privileges for '
                              'the IDE in System Preferences > Security & Privacy > Screen Recording')
                    sys.exit(-1)
                elif 'Poker Lobby' not in window_name:
                    if not window_already_found(window_number):
                        # Still loading
                        if window_name == 'Poker':
                            log.debug('Loading newly opened table... [{0}]'
                                      .format(window_number))
                        # Unknown blinds
                        elif '/' not in window_name:
                            log.debug('Found newly opened table ({0} [{1}]). Loading blinds...'
                                      .format(window_name, window_number))
                        # Blinds found... load table window
                        else:
                            log.debug('Loaded newly opened table: {0} [{1}]'
                                      .format(window_name, window_number))
                        table_windows.append([opened_window, window_name, window_number])
                    else:
                        # TODO: add functionality for updating blinds (should update an object incl. window attrib, etc.)
                        update_window_title(window_number, opened_window)

        validate_table_windows(opened_windows_formatted)

        # Recur until a table window is found...
        if len(table_windows) == 0:
            log.error('No open tables found. Searching again in {0} second{1}...'
                      .format(config.get('DEFAULT', 'table_windows_recur_sleep_time'),
                              '(s)' if config.get('DEFAULT', 'table_windows_recur_sleep_time') != '1' else ''))
            time.sleep(float(config.get('DEFAULT', 'table_windows_recur_sleep_time')))
            refresh_table_windows()

    # Windows (to be implemented...)
    elif config['Environment']['OS'] == 'Windows':
        pass


# TODO: improve grab_screens method. Make so we can get a screenshot of a particular table by hwnd
def setup_tables() -> dict:
    # refresh_table_windows()

    # Begin background refresh for table windows
    while True:
        table_thread = threading.Thread(target=refresh_table_windows)
        table_thread.start()
        # TODO: remove .join()? figure out what to do here
        table_thread.join()

    # log.debug(table_windows)

    # for result in search_results:
    #     hwnd = result[0]
    #     title = result[1]
    #     bbox = win32gui.GetWindowRect(hwnd)
    #     img = np.array(ImageGrab.grab(bbox))
    #     img = img[:, :, ::-1]  # rgb to bgr
    #     ret[str(title) + str(hwnd)] = img
    #
    # if len(ret) > 0:
    #     return ret
    # else:
    #     return None


# Updates current_screen of each game_state
# def update_screens():
#     screens = grab_screens()
#     for title, screen in screens.items():
#         table_id = re.findall(TABLE_ID_P, title)[0]
#         game_states[table_id].current_screen = screen
#     return


def init():
    """
    Called on startup. Responsible for initializing of game_state objects
    """
    setup_tables()


if __name__ == '__main__':
    # TODO: use mp.Pool(num_seats) later to parse player chip stacks using mp with tesseract
    mp.set_start_method('spawn')
    game_states = {}
    init()
