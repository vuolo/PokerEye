class Player:
    def __init__(self, seat_location: str, seat_num: int, is_hero: bool, is_vacant: bool, hand: str, position: str,
                 stack: float):
        self.seat_location: str = seat_location
        self.seat_num: int = seat_num
        self.is_hero: bool = is_hero
        self.is_vacant: bool = is_vacant

        self.hand: str = hand or '[] []'
        self.position: str = position  # TODO: continuously update position based on # of non-vacant players and button
        self.stack: float = stack
