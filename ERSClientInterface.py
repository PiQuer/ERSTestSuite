'''
Created on 24.05.2015

@author: Raimar Sandner
'''

from ClientInterface import ClientInterface, Point, BBox, Timeout
import os
import ConfigParser
import logging
import StringIO
import random, string
import time

# Setup logger for this module
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s'))
logger.setLevel(logging.DEBUG)
logger.handlers = [handler]
logger.propagate = False

def randomword(length):
  return ''.join(random.choice(string.lowercase) for _ in range(length))

class ERSClientInterface(ClientInterface):
  def __init__(self,delay=0):
    self.global_bbox = None
    self.config = self.config_parser(os.path.expanduser('~/.ersTestSuite/config.txt'))
    self.Config = dict(self.config.items('Config'))
    ClientInterface.__init__(self, self.Config['display'])
    self.imagedirs = [os.path.join(self.Config['basedir'],'images'),os.path.join(self.Config['packagedir'], 'images')]
    self.timeout = self.Config['timeout']

    if delay:
      logger.info('Sleeping {} seconds, please bring browser to front.'.format(delay))
      time.sleep(delay)
    left = Point(self.locate('logo')[0] - 62, 0)
    right = Point(self.locate('help')[0] + 80, self.size()[1])
    self.global_bbox = BBox(left[0], left[1], right[0], right[1])
    site_loaded = self.locate('site_loaded')
    self.loaded_bbox = (site_loaded - Point(17, 17)) * (site_loaded + Point(17, 17))

  def config_parser(self, files=None):
    if files is None: files = []
    if type(files) is str: files = [files]
    defaults = """
[Config]
basedir={basedir}
packagedir={packagedir}
display=:0
timeout=10
[Person]
email=disp.reg.ejc.RND@typename.de
name=Raimar Sandner
""".format(basedir=os.path.abspath(os.path.expanduser('~/.ersTestSuite')),
           packagedir=os.path.abspath(os.path.dirname(__file__)))
    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.readfp(StringIO.StringIO(defaults))
    config.read(map(os.path.expanduser, files))
    return config

  def wait_site_loaded(self):
    self.waitforelement('site_loaded', bbox=self.loaded_bbox)

  def clickto(self, *args, **kwargs):
    self.wait_site_loaded()
    return super(ERSClientInterface, self).clickto(*args, **kwargs)

  def isvisible(self, *args, **kwargs):
    self.wait_site_loaded()
    return super(ERSClientInterface, self).isvisible(*args, **kwargs)

  def empty_shopping_cart(self):
    self.clickto('my_shopping_cart')
    self.waitforelement('reset_all')
    self.clickto('reset_all')
    self.clickto('yes')

  def go_home(self):
    self.clickto('logo')
    self.wait_site_loaded()

  def _enter_name(self, name=None):
    if name is None:
      name = self.config.get('Person', 'name')
    self.clickto('first_name')
    self.type_string(name.split()[0])
    self.keypress('tab')
    self.type_string(name.split()[1])
    self.keypress('tab')

  def _enter_email(self, email=None):
    if email is None:
      email = self.config.get('Person', 'email').replace('RND', randomword(5))
    self.type_string(email)
    self.keypress('tab')

  def add_person(self, name=None, email=None, age='normal', if_necessary=True):
    if if_necessary:
      if not self.isvisible('add_a_new_person'):
        return
      else:
        self.clickto('add_a_new_person')
    self._enter_name(name=name)
    if age == 'normal':
      self.type_string('1.1.1980')
    elif age == 'reduced':
      self.type_string('1.1.2005')
    else:
      self.type_string('1.1.2010')
    self.keypress('tab')
    self._enter_email(email=email)
    self.keypress('down')
    self.keypress('down')
    self.clickto('save')

  def add_buyer(self, name=None, email=None):
    self.clickto('add_buyer')
    self._enter_name(name=name)
    self._enter_email(email=email)
    self.keypress('enter')

  def select_week_ticket(self, name=None, email=None, age='normal'):
    self.clickto('week_ticket')
    self.add_person(name=name, email=email, age=age, if_necessary=True)
    self.clickto('show')
    self.keypress('down')
    self.keypress('enter')

  def select_day_ticket(self, name=None, email=None, age='normal'):
    self.clickto('day_ticket')
    self.add_person(name=name, email=email, age=age, if_necessary=True)
    self.clickto('day')
    self.keypress('down')
    self.keypress('down')
    self.keypress('enter')
    self.wait_site_loaded()

  def select_gala_ticket(self, name=None, email=None, age='normal'):
    self.clickto('gala_show_ticket')
    self.clickto('gala_{}'.format(age))
    self.clickto('show')
    self.keypress('down')
    self.keypress('enter')
    self.wait_site_loaded()

  def checkout(self, amount, payment='sepa'):
    if not self.isvisible('reset_all'):
      self.clickto('my_shopping_cart')
    self.clickto('continue')
    if self.isvisible('empty_radio_button'):
      self.clickto('empty_radio_button')
    elif self.isvisible('no_buyer'):
      self.add_buyer()
    self.clickto('save_and_continue')
    if payment == 'sepa': self.clickto('sepa')
    elif payment == 'credit': self.clickto('credit')
    else: raise NotImplementedError("Payment type {} not implemented.".format(payment))
    self.clickto('save_and_continue')
    self.clickto('i_accept')
    self.clickto('buy_now')
    if self.isvisible('amount_{}'.format(amount)):
      return True
    else:
      return False


  def order_ticket(self, ticket='week', name=None, email=None, age='normal', payment='sepa'):
    amounts = {('week', 'normal'):180,
             ('week', 'reduced'):135,
             ('week', 'free'):0,
             ('day', 'normal'):35,
             ('day', 'reduced'):27,
             ('day', 'free'):0,
             ('gala', 'normal'):25,
             ('gala', 'reduced'):20,
             ('gala', 'free'):0 }
    self.clickto('go_to_product_overview')
    if   ticket == 'week': self.select_week_ticket(name=name, email=email, age=age)
    elif ticket == 'day' : self.select_day_ticket(name=name, email=email, age=age)
    elif ticket == 'gala': self.select_gala_ticket(name=name, email=email, age=age)
    else: raise NotImplementedError("Ticket type {} not implemented.".format(ticket))
    self.clickto('add_to_cart')
    self.clickto('shopping_cart_next')
    return self.checkout(amount=amounts[(ticket, age)], payment=payment)
