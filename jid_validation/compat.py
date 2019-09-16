import sys


if sys.version_info < (3, 0):
    _PY3 = False
else:
    _PY3 = True


if _PY3:
    unicode = str
    long = int
else:
    unicode = unicode
    long = long


if _PY3:
    unichr = chr
    raw_input = input
else:
    unichr = unichr
    raw_input = raw_input
