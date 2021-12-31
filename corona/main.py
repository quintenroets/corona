import argparse

from libs.errorhandler import ErrorHandler

from .visualizer import Visualizer

def main():
    default_start = "2020-11-1"
    
    parser = argparse.ArgumentParser(description='Visualize pandemic situation in Belgium')
    parser.add_argument('--start-date', default=default_start, help=f'Start of date range to visualize (default={default_start})')    
    parser.add_argument('--province', default=None, help='Only visualize specified province if specified [WestVlaanderen, ..]')
    parser.add_argument('--output-folder', default=None, help='Output folder for generated files')
    args = parser.parse_args()
    
    with ErrorHandler():
        Visualizer(args).visualize()
    
if __name__ == "__main__":
    main()
