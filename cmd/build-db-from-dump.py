

import argparse

#TODO to initialize the DB
# 1- we consider the schema is ready
# 2- load CSV files into SQLite and use an SQL to insert into the corresponding tables
# TODO - choose the option to update(add) or replace


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--experiment-dirs', type=str, required=True, nargs='+')
    parser.add_argument('-t', '--test-folder', type=str, required=True)
    parser.add_argument('-m', '--selection-metric', type=str, required=True)
    parser.add_argument('-o', '--output-folder', type=str, required=False)
    parser.add_argument('--task', type=str, required=True)
    parser.add_argument('--eval_only', default=False, action='store_true',
                        help='False to run model on set, True evaluate only')
    args = vars(parser.parse_args())
