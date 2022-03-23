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

    def add_player(self, player: dict):
        self.players[str(player.seat_num)] = player

    def clear_players(self):
        self.players: dict = {}

    def set_board(self, board: str):
        self.board: str = board

    def set_screenshot(self, screenshot):
        self.screenshot = screenshot

    def set_pot(self, pot: float):
        self.pot: float = pot
