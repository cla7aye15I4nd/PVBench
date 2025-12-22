import sys
FrameLocalsProxy=type([sys._getframe().f_locals for x in range(1)][0])
FrameLocalsProxy()