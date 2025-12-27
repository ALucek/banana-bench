# This util contains a verifier for the Scrabble Tournament Word List 2006
# Original code can be found at: https://github.com/fogleman/TWL06

import itertools
import struct
import zlib
from pathlib import Path

def check(word):
    '''
    Returns True if `word` exists in the TWL06 dictionary.
    Returns False otherwise.
    '''
    return word in _DAWG

END = '$'

class _Dawg(object):
    def __init__(self, data):
        data = zlib.decompress(data)
        self.data = data
    def _get_record(self, index):
        a = index * 4
        b = index * 4 + 4
        x = struct.unpack('<I', self.data[a:b])[0]
        more = bool(x & 0x80000000)
        letter = chr((x >> 24) & 0x7f)
        link = int(x & 0xffffff)
        return (more, letter, link)
    def _get_child(self, index, letter):
        while True:
            more, other, link = self._get_record(index)
            if other == letter:
                return link
            if not more:
                return None
            index += 1
    def __contains__(self, word):
        index = 0
        for letter in itertools.chain(word, END):
            index = self._get_child(index, letter)
            if index is None:
                return False
        return True

# Load the TWL dictionary data from binary file
_DATA_FILE = Path(__file__).parent / "twl_data.bin"
_DAWG = _Dawg(_DATA_FILE.read_bytes())
