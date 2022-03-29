import logging


class CashGameState:
    def __init__(self, num_seats: int, table_id: str, sb: float, bb: float, title: str, screenshot: object, bbox: dict):
        self.num_seats: int = num_seats
        self.table_id: str = table_id
        self.sb: float = sb
        self.bb: float = bb
        self.title: str = title
        self.board: str = '[] [] [] [] []'
        self.screenshot: object = screenshot
        self.bbox: dict = bbox
        self.players: dict = {}
        self.pot: float = 0.0
        self.is_visible: bool = False
        self.calculations: dict = {
            'is_calculating': False,
            'last_calc_hash': '[] []1[] [] [] [] []',
            'odds': {
                'win': 0.00,
                'win%': '0.00%',
                'win_expected': 0.00,
                'win_expected%': '0.00%',
                'tie': 0.00,
                'tie%': '0.00%',
                'ways_to_lose': {}
            }
        }

    def set_title(self, title) -> None:
        self.title = title

    def get_title(self) -> str:
        return self.title

    def set_blinds(self, blinds) -> None:
        self.sb = blinds['sb']
        self.bb = blinds['bb']

    def get_blinds(self) -> dict:
        return {'sb': self.sb, 'bb': self.bb}

    def set_bbox(self, bbox) -> None:
        self.bbox = bbox

    def get_bbox(self) -> dict:
        return self.bbox

    def get_table_id(self) -> str:
        return self.table_id

    def set_num_seats(self, num_seats) -> None:
        self.num_seats = num_seats

    def get_num_seats(self) -> int:
        return self.num_seats

    def set_screenshot(self, screenshot) -> None:
        self.screenshot = screenshot

    def get_screenshot(self) -> object:
        return self.screenshot

    def get_players(self) -> dict:
        return self.players

    def set_is_calculating(self, is_calculating) -> None:
        self.calculations['is_calculating'] = is_calculating

    def set_odds(self, odds) -> None:
        self.calculations['odds'] = odds

    def get_calculations(self) -> str:
        return self.calculations

    def set_board(self, board: str) -> None:
        self.board: str = board

    def get_board(self) -> str:
        return self.board

    def set_hash(self, new_hash) -> None:
        self.calculations['last_calc_hash'] = new_hash

    def get_hash(self) -> str:
        hero = None
        num_active_players = 0  # TODO: get accurate number of current opponents from screenshot
        for player in self.players.values():
            if player.is_hero:
                hero = player
            if player.is_active:  # TODO: get accurate number of current opponents from screenshot (update .is_active)
                num_active_players += 1

        return hero.hand + str(num_active_players) + self.board.strip()

    def add_player(self, player: dict):
        self.players[str(player.seat_num)] = player

    def clear_players(self):
        self.players: dict = {}

    def set_pot(self, pot: float):
        self.pot: float = pot

    def get_pot(self) -> float:
        return self.pot
