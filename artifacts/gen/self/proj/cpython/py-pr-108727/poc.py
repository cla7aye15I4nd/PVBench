# cat zz.py                        
__lltrace__ = True

import _testinternalcapi

def f():
    _testinternalcapi.get_counter_optimizer()

f()