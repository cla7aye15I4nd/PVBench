import xml.etree.ElementTree as ET


def test_remove_with_clear_assume_missing():
    """gh-126033: Check that concurrent clear() for missing element doesn't crash."""

    class E(ET.Element):
        pass

    class X(E):
        def __eq__(self, o):
            del root[:]
            return False

    class Y(E):
        def __eq__(self, o):
            root.clear()
            return False

    for Z, side_effect in [(X, 'del root[:]'), (Y, 'root.clear()')]:
        # test removing R() from [U()]
        for R, U in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one')])
            try:
                root.remove(R('missing'))
                assert False, "Expected ValueError"
            except ValueError:
                pass

        # test removing R() from [U(), V()]
        for U, V in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            try:
                root.remove(E('missing'))
                assert False, "Expected ValueError"
            except ValueError:
                pass

        for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            try:
                root.remove(Z('missing'))
                assert False, "Expected ValueError"
            except ValueError:
                pass


def test_remove_with_clear_assume_existing():
    """gh-126033: Check that concurrent clear() for existing element doesn't crash."""

    class E(ET.Element):
        pass

    class X(E):
        def __eq__(self, o):
            del root[:]
            return True

    class Y(E):
        def __eq__(self, o):
            root.clear()
            return True

    for Z, side_effect in [(X, 'del root[:]'), (Y, 'root.clear()')]:
        # test removing R() from [U()]
        for R, U in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one')])
            root.remove(R('missing'))  # Should not raise

        # test removing R() from [U(), V()]
        for U, V in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            root.remove(E('missing'))  # Should not raise

        for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            root.remove(Z('missing'))  # Should not raise


def test_remove_with_mutate_root_assume_missing():
    """gh-126033: Check that concurrent mutation for missing element doesn't crash."""
    E = ET.Element

    class Z(E):
        def __eq__(self, o):
            del root[0]
            return False

    # test removing R() from [U(), V()]
    for U, V in [(E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        try:
            root.remove(E('missing'))
            assert False, "Expected ValueError"
        except ValueError:
            pass

    for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        try:
            root.remove(Z('missing'))
            assert False, "Expected ValueError"
        except ValueError:
            pass


def test_remove_with_mutate_root_assume_existing():
    """gh-126033: Check that concurrent mutation for existing element doesn't crash."""
    E = ET.Element

    class Z(E):
        def __eq__(self, o):
            del root[0]
            return True

    # test removing R() from [U(), V()]
    for U, V in [(E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        root.remove(E('missing'))  # Should not raise

    for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        root.remove(Z('missing'))  # Should not raise


if __name__ == '__main__':
    test_remove_with_clear_assume_missing()
    test_remove_with_clear_assume_existing()
    test_remove_with_mutate_root_assume_missing()
    test_remove_with_mutate_root_assume_existing()
