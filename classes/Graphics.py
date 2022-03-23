import tkinter as tk
from random import seed, choice
from string import ascii_letters

COLORS = ('red', 'yellow', 'green', 'cyan', 'blue', 'magenta')


class Graphics:
    def __init__(self, width: int = 1645, height: int = 100, x: int = 20, y: int = 700):
        self.width = width
        self.height = height
        self.x = x
        self.y = y

        self.root = tk.Tk()
        self.root.wm_overrideredirect(True)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.label = tk.Label(text='', font=("Helvetica", 60))
        self.label.pack(expand=True)

        # TODO: init graphics w/ PokerEye header
        self.hide()
        # self.root.mainloop()

    def hide(self):
        self.root.withdraw()

    def show(self):
        self.root.deiconify()

    def update(self, game_state: object):
        self.show()
        self.root.geometry(f"{self.width}x{self.height}+{game_state.bbox['X']}+{game_state.bbox['Y']}")
        s = ''.join([choice(ascii_letters) for i in range(10)])
        color = choice(COLORS)
        self.label.config(text=s, fg=color)
