'''
Created on 23.05.2015

@author: Raimar Sandner
'''

import logging
import ClientInterface as CI
import unittest
import random, string

def randomword(length):
  return ''.join(random.choice(string.lowercase) for _ in range(length))


# Setup logger for this module
logger = logging.getLogger(__name__)
handler=logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s'))
logger.setLevel(logging.DEBUG)
logger.handlers=[handler]
logger.propagate=False

#===============================================================================
# def execute(filename):
#   script=open(filename).read().split('\n')
#   for line in script:
#     if line.startswith('#'):
#       continue
#     try:
#       command=ast.literal_eval(line)
#     except SyntaxError:
#       continue
# 
#     if command[0]=='click':
#       CI.clickto(command[1])
#     elif command[0]=='waitfor':
#       CI.waitforelement(command[1], timeout=command[2])
#===============================================================================

def empty_shopping_cart():
  CI.clickto('my_shopping_cart')
  CI.waitforelement('reset_all')
  CI.clickto('reset_all')
  CI.clickto('yes')

def go_home():
  CI.clickto('logo')
  CI.waitforelement('go_to_product_overview')

def add_person(name=None,email=None,age='normal'):
  if email is None:
    email=CI.config.get('Person','email').replace('RND',randomword(5))
  if name is None:
    name=CI.config.get('Person','name')
  CI.clickto('first_name')
  CI.type_string(name.split()[0])
  CI.keypress('tab')
  CI.type_string(name.split()[1])
  CI.keypress('tab')
  if age=='normal':
    CI.type_string('1.1.1980')
  elif age=='reduced':
    CI.type_string('1.1.2005')
  else:
    CI.type_string('1.1.2010')
  CI.keypress('tab')
  CI.type_string(email)
  CI.keypress('tab')
  CI.keypress('down')
  CI.keypress('down')
  CI.clickto('save')
  


def order_week_ticket(name=None,email=None,age='normal'):
  CI.clickto('go_to_product_overview')
  CI.clickto('week_ticket')
  CI.clickto('add_a_new_person')
  add_person(name=name,email=email,age=age)
  CI.clickto('show')
  CI.keypress('down')
  CI.keypress('enter')
  CI.clickto('add_to_cart')
  CI.clickto('shopping_cart_next')
  

class OrderTestCase(unittest.TestCase):
  def setUp(self):
    empty_shopping_cart()
    go_home()
  def test_week_ticket_normal(self):
    order_week_ticket()

suite = unittest.TestLoader().loadTestsFromTestCase(OrderTestCase)

if __name__ == '__main__':
  CI.init()
  unittest.main()