class CashGameState:
    def __init__(self, num_seats: int, table_id: str, bb_size: float, sb_size: float, current_screenshot):
        self.num_seats: int = num_seats
        self.table_id: str = table_id
        self.bb_size: float = bb_size
        self.sb_size: float = sb_size
        self.current_screenshot = current_screenshot
        self.players: dict = {}

    def set_players(self, players: dict):
        self.players: dict = players

    def set_current_screenshot(self, screenshot):
        self.current_screenshot = screenshot
