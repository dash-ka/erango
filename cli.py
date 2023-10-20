from argparse import ArgumentParser

parser = ArgumentParser(prog="era", usage="Provide path to excel file and a path")
parser.add_argument("path")
args = parser.parse_args()