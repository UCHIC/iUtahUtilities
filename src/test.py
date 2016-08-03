import unittest

from src.UpdateTool import DIR_SYMBOL, PROJECT_DIR


if __name__ == '__main__':
    testing_dir = '{}{}Tests'.format(PROJECT_DIR, DIR_SYMBOL)
    test_suites = unittest.TestLoader().discover(testing_dir)
    test_runner = unittest.TextTestRunner()
    test_runner.verbosity = 5
    test_runner.run(test_suites)
