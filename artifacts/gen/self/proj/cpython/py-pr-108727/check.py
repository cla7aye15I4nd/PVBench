import _testinternalcapi

if not hasattr(_testinternalcapi, 'get_counter_optimizer'):
    # Feature not available in this Python version, skip test
    pass
else:
    def f():
        _testinternalcapi.get_counter_optimizer()

    f()
    # If we reach here without crash, the test passes
