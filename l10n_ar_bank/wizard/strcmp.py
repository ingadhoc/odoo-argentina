# -*- coding: utf-8 -*-
#!/usr/bin/python

def shist(s, chars="abcdefghijklmnopqrstuvwxyz .01234567"):
    """
    Generate a histogram for s

    >>> shist('hola mundo')
    [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    """
    h = [0] * len(chars)
    _i = dict(zip(chars, range(len(chars))))
    for c in s:
        try:
            h[_i[c]] = h[_i[c]] + 1
        except:
            pass
    return h

def mostequivalent(strings, S):
    """
    Return the index of the most equivalent string in strings to S using a
    histogram.

    >>> mostequivalent(['el perro esta en la casa', 'mundo nuevo'], 'hola mundo')
    1
    """
    Sshist = shist(S)
    stringshist = map(shist, strings)
    md = -1
    for i in xrange(len(stringshist)):
        d = sum(map(lambda (a,b): abs(a-b), zip(stringshist[i], Sshist)))
        if i == 0 or d < md:
            mi, md = i, d
    return mi

def test_suite():
    import doctest
    return doctest.DocTestSuite()

if __name__ == "__main__":
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(test_suite())

