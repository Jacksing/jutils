import csv
import sys
import os
import datetime
import codecs

from functools import reduce

import alph_to_num

"""
Usage::

  > python sub_csv.py path/to/your/original/file.csv N=Jack
  39 filter result saved to path/to/your/original/2016-06-28 10-30-41.csv

  > python sub_csv.py path/to/your/original/file.csv N=Jack AA=72KG
  2 filter result saved to path/to/your/original/2016-06-28 10-30-41.csv
"""
class SubCsv():
    __matrix = None
    __sub_matrixes = []

    def __init__(self, csv_file, skip_title=True):
        self.csv_file = csv_file

    # Create the matrix object from the csv file.
    # If the matrix is already created it will be return directly.
    def get_matrix(self):
        if self.__matrix:
            return self.__matrix
        try:
            f = open(self.csv_file, 'r', encoding='utf-8_sig')
            self.__matrix = [line for line in csv.reader(f)]
            f.close()
            return self.__matrix
        except Exception as ex:
            raise ex

    # Get a sub matrix from the matrix of current instance.
    # Once this method is called, the result will be push into 
    # stack `__sub_matrixes`, and the stack can be written to
    # a csv file by calling the method `write_all()`.
    # 
    # Filter condition(s) given by argument `filter_arr`
    # with a format like [""AA=Shanghai", "12=Mary", "ZZX=12345"].
    # 
    # "AA, 12, ZZX" means the column number of the csv matrix.
    # With the same algorithm to excel column display,
    # "AA" will be converted to 27 and "ZZX" to 18276.
    def sub(self, filter_arr):
        matrix = self.get_matrix()
        def combine_param(s):
            k, v = s.split('=')

            # Convert alphabet to column number.
            if not k.isdigit():
                k = alph_to_num.convert(k.upper()) - 1
            
            return '=='.join(['x[%s]' % k, '"%s"' % v])

        # Generate the filter lambda function.
        filter_str = ' and '.join(list(map(combine_param, filter_arr)))
        filter_fun = eval('lambda x: %s' % filter_str)

        self.__sub_matrixes.append(list(filter(filter_fun, matrix)))
        return self.__sub_matrixes[-1]

    def __write(self, matrix, csv_file=None):
        if len(matrix) == 0:
            return 0, "The csv matrix is empty."

        if not csv_file:
            # Create a new file in the original folder.
            sub_csv_file = datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S') + '.csv'
            sub_csv_file = os.path.join(os.path.dirname(self.csv_file), sub_csv_file)
        else:
            # Use the given file name to write back.
            sub_csv_file = csv_file

        f = open(sub_csv_file, 'w', encoding='utf-8_sig', newline='')
        cw = csv.writer(f)
        cw.writerows(matrix)
        f.close()

        return len(matrix), sub_csv_file

    def write_all(self, csv_file=None):
        # Combine all sub matrixes in the stack and write back to the specific file.
        return self.__write(reduce(lambda x, y: x + y, self.__sub_matrixes), csv_file)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit('Not enough parameters to continue.')

    try:
        file_path = sys.argv[1]
        sc = SubCsv(file_path)
        sc.sub(sys.argv[2:])
    except Exception as ex:
        sys.exit(ex)

    print('%d filter result saved to %s' % sc.write_all())
