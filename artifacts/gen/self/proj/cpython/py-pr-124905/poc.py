import _curses
_curses.initscr()
try:
    _curses.resizeterm(+35000, 1)
except:
    pass
_curses.initscr()