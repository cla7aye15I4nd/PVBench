import array


def test_gh_128961():
    """gh-128961: Test array iterator __setstate__ after exhaustion."""
    a = array.array('i')
    it = iter(a)
    list(it)
    it.__setstate__(0)

    try:
        next(it)
        assert False, "Expected StopIteration"
    except StopIteration:
        pass


if __name__ == '__main__':
    test_gh_128961()
