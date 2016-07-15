import csv
import sys
import os
import datetime
import codecs

from functools import reduce
from inspect import isfunction
from random import random

from six import string_types, integer_types

import alph_to_num

default_encoding = 'utf-8_sig'
safe_list = ['random', 'abs', ]

def get_safe_object():
    global_dict = globals()
    builtins_module = global_dict.get('__builtins__')

    def _get_safe_object(name):
        try:
            if global_dict.get(name, None):
                return global_dict[name]
            elif hasattr(builtins_module, name):
                return getattr(builtins_module, name)
            else:
                return None
        except Exception as ex:
            print(ex)
            return None

    return dict([(k, _get_safe_object(k)) for k in safe_list])

def safe_eval(expression):
    f = eval(expression)
    # return f
    return eval(expression, {'__builtins__': {}}, get_safe_object())

"""
Usage::

  > python sub_csv.py path/to/your/original/file.csv N=Jack
  39 filter result saved. path/to/your/original/2016-06-28 10-30-41.csv

  > python sub_csv.py path/to/your/original/file.csv N=Jack AA=72KG
  2 filter result saved. path/to/your/original/2016-06-28 10-30-41.csv
"""
class SubCsv():
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
        if isfunction(converter):
            SubCsv.converter_repo.update({name: converter})
        elif isinstance(converter, string_types):
            try:
                SubCsv.converter_repo.update({name: safe_eval('lambda %s' % converter)})
            except Exception as ex:
                raise SyntaxError('{} is not valid converter function content.'.format(converter))

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
            raise TypeError('{} is not a valid column marking.'.format(col))
        
        # Directly use the converter function 
        #  or: find it in static repository
        #  or: generate and save it.
        if isfunction(converter):
            self.convert_strategy.update({col_num: converter})
        elif isinstance(converter, string_types):
            if converter not in SubCsv.converter_repo:
                SubCsv._register_converter(converter, converter)
            self.convert_strategy.update({col_num: SubCsv.converter_repo[converter]})
        else:
            raise TypeError('{} is not a valid converter marking.'.format(type(converter)))

    def __convert_row(self, row):
        """Convert each cell value in single row into new value by preseted convert mappings."""
        for k, v in self.convert_strategy.items():
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


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit('Not enough parameters to continue.')

    print(' '.join(sys.argv))

    try:
        def prefix(cell):
            return 'pre_{}'.format(cell)

        SubCsv._register_converter('plus_one', 'x: int(x) + 1')
        SubCsv._register_converter('prefix', prefix)

        file_path = sys.argv[1]
        sc = SubCsv(file_path)
        sc.sub(sys.argv[2:])
        sc.convert(1, 'plus_one')
        sc.convert('p', 'prefix')
        sc.convert('f', 'x: random()')
    except Exception as ex:
        print(ex)
        sys.exit(ex)

    print('%d filter result saved. %s' % sc.write_all())
