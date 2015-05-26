'''
Created on 23.05.2015

@author: Raimar Sandner
'''

import logging
import ERSClientInterface
import unittest
import time

# Setup logger for this module
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s'))
logger.setLevel(logging.DEBUG)
logger.handlers = [handler]
logger.propagate = False



class OrderTestCase(unittest.TestCase):
  def setUp(self):
    CI.empty_shopping_cart()
    CI.go_home()
  def test_ticket_order_week_normal_sepa(self):
    self.assertTrue(CI.order_ticket(ticket='week', age='normal', payment='sepa'))
  def test_ticket_order_week_reduced_sepa(self):
    self.assertTrue(CI.order_ticket(ticket='week', age='reduced', payment='sepa'))
  def test_ticket_order_week_free_sepa(self):
    self.assertTrue(CI.order_ticket(ticket='week', age='free', payment='sepa'))
  def test_ticket_order_day_normal_sepa(self):
    self.assertTrue(CI.order_ticket(ticket='day', age='normal', payment='sepa'))
  def test_ticket_order_day_reduced_sepa(self):
    self.assertTrue(CI.order_ticket(ticket='day', age='reduced', payment='sepa'))
  def test_ticket_order_day_free_sepa(self):
    self.assertTrue(CI.order_ticket(ticket='day', age='free', payment='sepa'))
  def test_ticket_order_gala_normal_sepa(self):
    self.assertTrue(CI.order_ticket(ticket='gala', age='normal', payment='sepa'))
  def test_ticket_order_gala_reduced_sepa(self):
    self.assertTrue(CI.order_ticket(ticket='gala', age='reduced', payment='sepa'))
  def test_ticket_order_gala_free_sepa(self):
    self.assertTrue(CI.order_ticket(ticket='gala', age='free', payment='sepa'))


suite = unittest.TestLoader().loadTestsFromTestCase(OrderTestCase)

if __name__ == '__main__':
  logger.info('Sleeping 10 seconds, please bring the browser with the ERS site loaded to the front.')
  time.sleep(10)
  CI = ERSClientInterface.ERSClientInterface()
  unittest.main()
