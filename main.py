'''
Created on 23.05.2015

@author: Raimar Sandner
'''

import logging
import ClientInterface as CI
import ast

# Setup logger for this module
logger = logging.getLogger(__name__)
handler=logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s'))
logger.setLevel(logging.DEBUG)
logger.handlers=[handler]
logger.propagate=False

def execute(filename):
  script=open(filename).read().split('\n')
  for line in script:
    if line.startswith('#'):
      continue
    try:
      command=ast.literal_eval(line)
    except SyntaxError:
      continue

    if command[0]=='click':
      CI.clickto(command[1])
    elif command[0]=='waitfor':
      CI.waitforelement(command[1], timeout=command[2])


def main():
  CI.init()

if __name__ == '__main__':
  main()