from functools import reduce

__all__ = ['convert']

_alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

_alphabet = {v: k + 1 for k, v in dict(enumerate(_alphabet)).items()}

def __alphabet_to_number(s):
    l = list(s.upper())
    l.reverse()
    def _bit_value(t):
        return _alphabet[t[1]] * (len(_alphabet) ** t[0])
    try:
        return reduce(lambda x, y: x + y, map(_bit_value, list(enumerate(l))))
    except:
        raise ValueError('{} is not convertable alphabet string.'.format(s))

convert = __alphabet_to_number

if __name__ == '__main__':
    def test(s):
        print('%s\t%d' % (s, __alphabet_to_number(s)))

    test('A')
    test('H')
    test('Z')
    test('AA')
    test('AH')
    test('AZ')
    test('CA')
    test('CH')
    test('CZ')
    test('ZA')
    test('ZH')
    test('ZZ')
    test('AAT')
    test('CNX')
    test('ZZX')