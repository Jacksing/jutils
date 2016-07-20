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

filter_operator = '='
convert_operator = '::'


def debug_info(value):
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
                debug_info('get `{}` from global.'.format(name))
                return all_global[name]
            elif name in all_builtin:
                debug_info('get `{}` from builtin.'.format(name))
                return all_builtin[name]
            else:
                debug_info("can't find allowed object for `{}`.".format(name))
                return None
        except Exception as ex:
            debug_info(ex)
            return None

    return dict([(k, _get_safe_object(k)) for k in safe_list])

safe_objects = get_safe_object()


def safe_eval(expression):
    """Eval an expression safely under specified restriction."""
    no_builtin_dict = {'__builtins__': {}}
    no_builtin_dict.update(safe_objects)
    return eval(expression, no_builtin_dict)


# TODO: add features to support more patterns.
def get_lambda_string(lambda_content):
    """
    Reformat lambda_content to allow user to create lambda more flexibly.

    Allowed patterns of lambda_content:
        1) s: s + 'KG'      -->	    lambda s: s + 'KG'

           s is treated as string. 

        2) d: d + 100       -->     lambda d: ast.literal(d) + 100

           d is treated as a digit.
        
        2) random()         -->     lambda s: random()

           no parameter specified, add a default one.
        
        3) 'Shanghai'       -->     lambda s: 'Shanghai'

           no parameter and return a string value directly.
    """
    if lambda_content.startswith('s:'):
        return 'lambda {}'.format(lambda_content)

    if lambda_content.startswith('d:'):
        # TODO: add support for digit.
        return 'lambda {}'.format(lambda_content)

    splited = lambda_content.split(':')
    if len(splited) > 1 and ' ' not in splited[0].strip():
        return 'lambda {}'.format(lambda_content)

    return 'lambda x: {}'.format(lambda_content)


class SubCsv():
    """
    Create sub csv by filter or convert the content of original csv file.

    Usage::

    > python sub_csv.py path/to/your/original/file.csv N=Jack
    39 filter result saved. path/to/your/original/2016-06-28 10-30-41.csv

    > python sub_csv.py path/to/your/original/file.csv N=Jack AA=72KG
    2 filter result saved. path/to/your/original/2016-06-28 10-30-41.csv

    # content of column A will be set to '76KG'
    > python sub_csv.py path/to/your/original/file.csv N=Jack AA=72KG A::x:'76KG'
    2 filter result saved. path/to/your/original/2016-06-28 10-30-41.csv
    """
    encoding = default_encoding
    converter_repo = {}

    def __init__(self, csv_file, ensure_header=True, encoding=None):
        """
        Constructor for SubCsv, with sensible defaults.

        csv_file is file path of the original csv file.

        If ensure_header is true, first line of csv content will be treated as
        the header columns, it will be stacked and exported to sub csv file.
        """
        self.csv_file = csv_file
        self.ensure_header = ensure_header
        if encoding:
            self.encoding = encoding

        self._header = None
        self._matrix = None
        # If `_sub_matrices` is None, whole original matrix will be exported to sub
        # csv file.
        # It will be initialized to an empty list in method `self.sub()`, and then
        # the filter result matrix will be exported to sub csv file.
        self._sub_matrices = None

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

                if self.ensure_header:
                    self._header = self._matrix and self._matrix[0] or []
                    self._matrix = self._matrix[1:]
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
        if not filter_arr:
            return None

        matrix = self.get_matrix()
        def combine_param(s):
            k, v = s.split(filter_operator)

            # Convert alphabet to column number.
            if not k.isdigit():
                # Convert result begins with 1 (A=1, B=2),
                # so decrease the result by 1.
                k = alph_to_num.convert(k.upper()) - 1
            
            return '=='.join(['x[%s]' % k, '"%s"' % v])

        # Generate the filter lambda function.
        filter_str = ' and '.join(list(map(combine_param, filter_arr)))
        expression = 'lambda x: %s' % filter_str
        debug_info('begin eval: `{}`.'.format(expression))
        filter_fun = safe_eval(expression)

        if self._sub_matrices is None:
            self._sub_matrices = []

        self._sub_matrices.append(list(filter(filter_fun, matrix)))
        return self._sub_matrices[-1]

    @staticmethod
    def register_converter(name, converter):
        """
        Generate a convert function and use `name` as the key to represent it.

        Parameter `converter` can be a function or a string type content.
        If a string type is given, it will be used as the parameter to excute
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
                expression = get_lambda_string(converter)
                debug_info('begin eval: `{}`.'.format(expression))
                SubCsv.converter_repo.update({name: safe_eval(expression)})
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
                SubCsv.register_converter(converter, converter)
            self.convert_strategy.update({col_num: SubCsv.converter_repo[converter]})
        else:
            raise TypeError('`{}` is not a valid converter marking.'.format(type(converter)))

    def convert_all(self, mapping, **kwargs):
        """Preset all convert strategy through calling `self.convert()`."""
        if type(mapping) is dict:
            kwargs.update(mapping)

        for col, converter in kwargs.items():
            self.convert(col, converter)

    def __apply_strategy_for_row(self, row):
        """Convert each cell value in single row into new value by preseted convert mappings."""
        for k, v in self.convert_strategy.items():
            debug_info('{col} is {val}'.format(col=k, val=row[k]))
            row[k] = v(row[k])
        return row

    def __write(self, matrix, csv_file=None, ensure_header=True):
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
            matrix = [self.__apply_strategy_for_row(row) for row in matrix]

        try:
            with open(csv_file, 'w', encoding=self.encoding, newline='') as f:
                cw = csv.writer(f)
                if ensure_header and self._header:
                    cw.writerow(self._header)
                cw.writerows(matrix)
        except Exception as ex:
            return 0, ex

        return len(matrix), csv_file

    def write_all(self, csv_file=None, ensure_header=True):
        """Combine all sub matrixes in the stack and write back to the specific file."""
        if self._sub_matrices is None:
            sub_matrix = self.get_matrix()
        else:
            sub_matrix = reduce(lambda x, y: x + y, self._sub_matrices)
        return self.__write(sub_matrix, csv_file, ensure_header)


def execute_command():
    if len(sys.argv) < 3:
        sys.exit('Not enough parameters to continue.')

    debug_info(' '.join(sys.argv))

    try:
        file_path = sys.argv[1]
        all_action_cmd = sys.argv[2:]
        
        # DEBUG = '--debug' in all_action_cmd

        def split_sub_and_convert_command():
            # get all sub action commands into a list
            sub_cmd = [cmd for cmd in all_action_cmd if len(cmd.split(filter_operator)) ==2]
            # get all convert action commands into a dict
            fn = lambda x: x.split(convert_operator)
            convert_cmd = dict([fn(cmd) for cmd in all_action_cmd if len(fn(cmd)) == 2])

            return sub_cmd, convert_cmd
        
        sub, convert = split_sub_and_convert_command()

        ensure_header = '--ensure-header' in all_action_cmd

        sc = SubCsv(file_path, ensure_header=ensure_header)
        sc.sub(sub)
        sc.convert_all(convert)
        result = sc.write_all(ensure_header=ensure_header)
    except Exception as ex:
        debug_info(ex)
        sys.exit(ex)

    print('%d filter result saved. %s' % result)


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
        SubCsv.register_converter('plus_one', 'x: random()')
        SubCsv.register_converter('prefix', prefix)

        sc.convert(1, 'plus_one')
        sc.convert('p', 'prefix')
        sc.convert('f', 'x: random()')

    def test_no_sub_or_convert(self):
        pass


if __name__ == '__main__':
    execute_command()
    # unittest.main()
