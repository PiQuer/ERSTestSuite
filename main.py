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
  def __init__(self,*args,**kwargs):
    super(OrderTestCase,self).__init__(*args,**kwargs)
    self.CI=ERSClientInterface.ERSClientInterface()
  def setUp(self):
    if self.CI.isvisible('logout'):
      self.CI.clickto('logout')
    self.CI.empty_shopping_cart()
    self.CI.go_home()
  def test_ticket_order_week_normal_sepa(self):
    self.assertTrue(self.CI.order_ticket(ticket='week',age='normal',payment='sepa'))
  # def test_ticket_order_week_normal_sepa_login(self):
  #  self.assertTrue(self.CI.order_ticket(ticket='week',age='normal',payment='sepa',login=True))
  def test_ticket_order_week_normal_credit(self):
    self.assertTrue(self.CI.order_ticket(ticket='week',age='normal',payment='credit'))
  def test_ticket_order_week_reduced_sepa(self):
    self.assertTrue(self.CI.order_ticket(ticket='week',age='reduced',payment='sepa'))
  def test_ticket_order_week_reduced_credit(self):
    self.assertTrue(self.CI.order_ticket(ticket='week',age='reduced',payment='credit'))
  def test_ticket_order_week_free_sepa(self):
    self.assertTrue(self.CI.order_ticket(ticket='week',age='free',payment='sepa'))
  def test_ticket_order_day_normal_sepa(self):
    self.assertTrue(self.CI.order_ticket(ticket='day',age='normal',payment='sepa'))
  def test_ticket_order_day_normal_credit(self):
    self.assertTrue(self.CI.order_ticket(ticket='day',age='normal',payment='credit'))
  def test_ticket_order_day_reduced_sepa(self):
    self.assertTrue(self.CI.order_ticket(ticket='day',age='reduced',payment='sepa'))
  def test_ticket_order_day_reduced_credit(self):
    self.assertTrue(self.CI.order_ticket(ticket='day',age='reduced',payment='credit'))
  def test_ticket_order_day_free_sepa(self):
    self.assertTrue(self.CI.order_ticket(ticket='day',age='free',payment='sepa'))
  def test_ticket_order_gala_normal_sepa(self):
    self.assertTrue(self.CI.order_ticket(ticket='gala',age='normal',payment='sepa'))
  def test_ticket_order_gala_normal_credit(self):
    self.assertTrue(self.CI.order_ticket(ticket='gala',age='normal',payment='credit'))
  def test_ticket_order_gala_reduced_sepa(self):
    self.assertTrue(self.CI.order_ticket(ticket='gala',age='reduced',payment='sepa'))
  def test_ticket_order_gala_reduced_credit(self):
    self.assertTrue(self.CI.order_ticket(ticket='gala',age='reduced',payment='credit'))
  def test_ticket_order_gala_free_sepa(self):
    self.assertTrue(self.CI.order_ticket(ticket='gala',age='free',payment='sepa'))
  def test_two_weektickets(self):
    self.assertTrue(self.CI.order_two_weektickets())
  def test_week_and_day(self):
    self.assertTrue(self.CI.order_week_and_day())
  def test_two_daytickets(self):
    self.assertTrue(self.CI.order_two_daytickets())

if __name__ == '__main__':
  logger.info('Sleeping 10 seconds, please bring the browser with the ERS site loaded to the front.')
  time.sleep(10)
  unittest.main()
