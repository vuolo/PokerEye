class CashGameState:
    def __init__(self, num_seats: int, table_id: str, sb: float, bb: float, title: str, screenshot):
        self.num_seats: int = num_seats
        self.table_id: str = table_id
        self.sb: float = sb
        self.bb: float = bb
        self.title: str = title
        self.board: str = '[] [] [] [] []'
        self.screenshot = screenshot
        self.players: dict = {}

    def set_board(self, board: str):
        self.board: str = board

    def set_players(self, players: dict):
        self.players: dict = players

    def set_screenshot(self, screenshot):
        self.screenshot = screenshot
