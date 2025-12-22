import curses

try:
    curses.initscr()
except curses.error:
    # No terminal available, skip test
    pass
else:
    try:
        curses.resizeterm(35000, 1)
        assert False, "Expected OverflowError"
    except OverflowError:
        pass

    try:
        curses.resizeterm(1, 35000)
        assert False, "Expected OverflowError"
    except OverflowError:
        pass

    # GH-120378: Overflow failure in resizeterm() causes refresh to fail
    tmp = curses.initscr()
    tmp.erase()

    curses.endwin()
