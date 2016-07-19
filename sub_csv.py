import csv
import sys
import os
import datetime
import codecs

from functools import reduce
import inspect
from random import random

from six import string_types, integer_types

import alph_to_num

DEBUG = False

default_encoding = 'utf-8_sig'
safe_list = ['random', 'abs', 'int', 'ss']

def log(value):
    if DEBUG:
        print(value)

def get_safe_object():
    all_builtin = {
        name: obj for name, obj in inspect.getmembers(__builtins__)
                  if inspect.isbuiltin(obj) or (inspect.isclass(obj) and not issubclass(obj, Exception))
    }

    all_global = {
        name: obj for name, obj in globals().items()
                  if inspect.isbuiltin(obj) or (inspect.isclass(obj) and not issubclass(obj, Exception))
    }

    def _get_safe_object(name):
        try:
            if name in all_global:
                log('get `{}` from global.'.format(name))
                return all_global[name]
            elif name in all_builtin:
                log('get `{}` from builtin.'.format(name))
                return all_builtin[name]
            else:
                log("can't find allowed object for `{}`.".format(name))
                return None
        except Exception as ex:
            log(ex)
            return None

    return dict([(k, _get_safe_object(k)) for k in safe_list])

safe_objects = get_safe_object()

def safe_eval(expression):
    no_builtin_dict = {'__builtins__': {}}
    no_builtin_dict.update(safe_objects)
    return eval(expression, no_builtin_dict)

class SubCsv():
    """
    Usage::

    > python sub_csv.py path/to/your/original/file.csv N=Jack
    39 filter result saved. path/to/your/original/2016-06-28 10-30-41.csv

    > python sub_csv.py path/to/your/original/file.csv N=Jack AA=72KG
    2 filter result saved. path/to/your/original/2016-06-28 10-30-41.csv
    """
    encoding = default_encoding
    converter_repo = {}

    def __init__(self, csv_file, skip_title=True, encoding=None):
        self._matrix = None
        self._sub_matrices = []
        
        if encoding:
            self.encoding = encoding
        self.csv_file = csv_file
        self.convert_strategy = {}  # in the format of {col_index: convert_function}

    def get_matrix(self):
        """
        Create the matrix object from the csv file.

        If the matrix is already created it will be return directly.
        """
        if not self._matrix:
            try:
                with open(self.csv_file, 'r', encoding=self.encoding) as f:
                    self._matrix = [line for line in csv.reader(f)]
            except Exception as ex:
                raise ex
        return self._matrix

    def sub(self, filter_arr):
        """
        Get a sub matrix from the matrix of current instance.

        Once this method is called, the result will be push into 
        stack `_sub_matrices`, and the stack can be written to
        a csv file by calling the method `write_all()`.
        
        Filter condition(s) given by argument `filter_arr` should be
        in the format like [""AA=Shanghai", "12=Mary", "ZZX=12345"].
        
        "AA, 12, ZZX" mean the column numbers of the csv matrix.
        With the same algorithm to excel column display,
        "AA" will be converted to 27 while "ZZX" to 18276.
        
        Filter condition given by parameter `filter_arr` will be
        processed as a `and` operation, and filter conditions given
        by multi callings of function `Sub()` will be processed as
        an `or` operation.
        
        Usage::
        
          1) Want to get sub csv with N=Jack and S=Female:
            >> sc = SubCsv('path/to/file.csv')
            >> sc.sub(['N=Jack', 'S=Female'])
            >> sc.write_all('path/to/output/file.csv')
        
          2) Want to get sub csv with N=Jack or S=Female:
            >> sc = SubCsv('path/to/file.csv')
            >> sc.sub(['N=Jack', ])
            >> sc.sub(['S=Female', ])
            >> sc.write_all('path/to/output/file.csv')
        """
        matrix = self.get_matrix()
        def combine_param(s):
            k, v = s.split('=')

            # Convert alphabet to column number.
            if not k.isdigit():
                # Convert result begins with 1 (A=1, B=2),
                # so decrease the result by 1.
                k = alph_to_num.convert(k.upper()) - 1
            
            return '=='.join(['x[%s]' % k, '"%s"' % v])

        # Generate the filter lambda function.
        filter_str = ' and '.join(list(map(combine_param, filter_arr)))
        filter_fun = safe_eval('lambda x: %s' % filter_str)

        self._sub_matrices.append(list(filter(filter_fun, matrix)))
        return self._sub_matrices[-1]

    @staticmethod
    def _register_converter(name, converter):
        """
        Generate a convert function and use `name` as the key to represent it.

        Parameter `converter` can be a function or a string type content.
        If a string type is given, it will be used as the parameter by calling
        `safe_eval()` to generate a convert function.

        Attention:
            `eval()` may be called and this could be a risk.

            Config the global setting `safe_list` to allow objects that can be used
            in generating functions.
        """
        if inspect.isfunction(converter):
            SubCsv.converter_repo.update({name: converter})
        elif isinstance(converter, string_types):
            try:
                print('begin eval: `{}`.'.format('lambda %s' % converter))
                SubCsv.converter_repo.update({name: safe_eval('lambda %s' % converter)})
            except Exception as ex:
                raise SyntaxError('`{}` is not valid converter function content.'.format(converter))

    def convert(self, col, converter):
        """
        Preset convert strategy whitout converting the sub csv matrices immediately.
        All the strategies will be implemented in function `__write()` is called.
        """
        if isinstance(col, integer_types):
            col_num = col
        elif isinstance(col, string_types):
            try:
                # Convert result begins with 1 (A=1, B=2),
                # so decrease the result by 1.
                col_num = alph_to_num.convert(col) - 1
            except ValueError as ex:
                raise ex
        else:
            raise TypeError('`{}` is not a valid column marking.'.format(col))
        
        # Directly use the converter function 
        #  or: find it in static repository
        #  or: generate and save it.
        if inspect.isfunction(converter):
            self.convert_strategy.update({col_num: converter})
        elif isinstance(converter, string_types):
            if converter not in SubCsv.converter_repo:
                SubCsv._register_converter(converter, converter)
            self.convert_strategy.update({col_num: SubCsv.converter_repo[converter]})
        else:
            raise TypeError('`{}` is not a valid converter marking.'.format(type(converter)))

    def convert_all(self, mapping, **kwargs):
        """Preset all convert strategy by calling `convert()`."""
        if type(mapping) is dict:
            kwargs.update(mapping)

        for col, converter in kwargs.items():
            self.convert(col, converter)

    def __convert_row(self, row):
        """Convert each cell value in single row into new value by preseted convert mappings."""
        for k, v in self.convert_strategy.items():
            log('{col} is {val}'.format(col=k, val=row[k]))
            row[k] = v(row[k])
        return row

    def __write(self, matrix, csv_file=None):
        if len(matrix) == 0:
            return 0, "The csv matrix is empty."

        if not csv_file:
            # Create a new file in the original folder.
            csv_file = datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S') + '.csv'
            csv_file = os.path.join(os.path.dirname(self.csv_file), csv_file)
        else:
            # Use the given file name to write back.
            csv_file = csv_file

        if self.convert_strategy:
            matrix = [self.__convert_row(row) for row in matrix]

        try:
            with open(csv_file, 'w', encoding=self.encoding, newline='') as f:
                cw = csv.writer(f)
                cw.writerows(matrix)
        except Exception as ex:
            return 0, ex

        return len(matrix), csv_file

    def write_all(self, csv_file=None):
        """Combine all sub matrixes in the stack and write back to the specific file."""
        return self.__write(reduce(lambda x, y: x + y, self._sub_matrices), csv_file)

#----------------------------------------------------------------------
# Basic tests.
#----------------------------------------------------------------------
import unittest

def prefix(cell):
    return 'pre_{}'.format(cell)

class TestSubCsv(unittest.TestCase):
    def test_sub_and_convert(self):
        pass

    def test_sub_only(self):
        pass

    def test_convert_only(self):
        SubCsv._register_converter('plus_one', 'x: random()')
        SubCsv._register_converter('prefix', prefix)

        sc.convert(1, 'plus_one')
        sc.convert('p', 'prefix')
        sc.convert('f', 'x: random()')

    def test_no_sub_or_convert(self):
        pass


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit('Not enough parameters to continue.')

    log(' '.join(sys.argv))

    try:
        file_path = sys.argv[1]
        sc = SubCsv(file_path)
        
        def split_sub_and_convert_command():
            all_cmd = sys.argv[2:]
            sub_cmd = [cmd for cmd in all_cmd if len(cmd.split('=')) ==2]
            convert_cmd = dict([cmd.split('::') for cmd in all_cmd if len(cmd.split('::')) == 2])
            return sub_cmd, convert_cmd
        sub, convert = split_sub_and_convert_command()

        sc.sub(sub)
        sc.convert_all(convert)
    except Exception as ex:
        log(ex)
        sys.exit(ex)

    print('%d filter result saved. %s' % sc.write_all())
