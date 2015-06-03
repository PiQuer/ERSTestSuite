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
  def __init__(self, delay=0):
    self.global_bbox = None
    self.config = self.config_parser(os.path.expanduser('~/.ersTestSuite/config.txt'))
    ClientInterface.__init__(self, self.config.get('Config', 'display'))
    self.imagedirs = [os.path.join(self.config.get('Config', 'basedir'), 'images'), os.path.join(self.config.get('Config', 'packagedir'), 'images')]
    self.timeout = self.config.get('Config', 'timeout')

    if delay:
      logger.info('Sleeping {} seconds, please bring browser to front.'.format(delay))
      time.sleep(delay)
    left = Point(self.locate('logo')[0] - 62, 0)
    right = Point(self.locate('help')[0] + 80, self.size()[1])
    self.global_bbox = BBox(left[0], left[1], right[0], right[1])
    site_loaded = self.locate('site_loaded')
    self.loaded_bbox = (site_loaded - Point(17, 17)) * (site_loaded + Point(17, 17))
    self.confidence = self.config.getfloat('Config', 'confidence')

  def config_parser(self, files=None):
    if files is None: files = []
    if type(files) is str: files = [files]
    defaults = """
[Config]
basedir={basedir}
packagedir={packagedir}
display=:0
timeout=10
confidence=0.8
[Person]
email=disp.reg.ejc.RND@typename.de
name1=Raimar Sandner
name2=Foo Bar
creditcard_number=4111111111111111
creditcard_sec=123
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

  def _enter_name(self, name=None, person_id=None):
    if name is None:
      if person_id is None: person_id = 1
      name = self.config.get('Person', 'name' + str(person_id))
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

  def login(self):
    self.clickto('login')
    self.clickto('email')
    self.type_string(self.config.get('Config', 'username'))
    self.keypress('tab', s=0.5)
    self.type_string(self.config.get('Config', 'password'))
    self.keypress('enter')
    self.waitforelement('my_profile')

  def add_person(self, name=None, email=None, age='normal', person_id=None, if_necessary=True):
    if if_necessary:
      if self.isvisible('this_ticket'):
        return
    self.clickto('add_a_new_person')
    self._enter_name(name=name, person_id=person_id)
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

  def add_buyer(self, name=None, email=None, person_id=None):
    self.clickto('add_buyer')
    self._enter_name(name=name, person_id=None)
    self._enter_email(email=email)
    self.keypress('enter')

  def select_week_ticket(self, name=None, email=None, age='normal', always_add=False, person_id=None):
    self.clickto('week_ticket')
    self.add_person(name=name, email=email, age=age, if_necessary=not always_add, person_id=person_id)
    self.clickto('show')
    self.keypress('down')
    self.keypress('enter')

  def select_day_ticket(self, name=None, email=None, age='normal', always_add=False, person_id=None, day=2):
    self.clickto('day_ticket')
    self.add_person(name=name, email=email, age=age, if_necessary=not always_add, person_id=None)
    self.clickto('day')
    for _ in range(day):
      self.keypress('down')
    self.keypress('enter')
    self.wait_site_loaded()

  def select_gala_ticket(self, age='normal'):
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
    return self.isvisible('amount_{}'.format(str(amount).replace('.', ',')))

  def pay(self, payment='sepa'):
    self.clickto('buy_now')
    if payment == 'sepa':
      return self.isvisible('sepa_success')
    if payment == 'credit':
      self.clickto('cardholder')
      self.type_string(self.config.get('Person', 'name'))
      self.keypress('tab')
      self.keypress('tab')
      self.type_string(self.config.get('Person', 'creditcard_number'))
      self.keypress('tab')
      self.type_string(self.config.get('Person', 'creditcard_sec'))
      self.keypress('tab')
      for _ in range(8): self.keypress('down')
      self.keypress('tab');self.keypress('tab');
      self.keypress('enter')
      return self.isvisible('credit_success')


  def order_ticket(self, ticket='week', name=None, email=None, age='normal', payment='sepa', login=False):
    amounts = {'sepa':
               {('week', 'normal'):180,
                ('week', 'reduced'):135,
                ('week', 'free'):0,
                ('day', 'normal'):35,
                ('day', 'reduced'):27,
                ('day', 'free'):0,
                ('gala', 'normal'):25,
                ('gala', 'reduced'):20,
                ('gala', 'free'):0 },
               'credit':
               {('week', 'normal'):184.77,
                ('week', 'reduced'):138.58,
                ('week', 'free'):0,
                ('day', 'normal'):35.93,
                ('day', 'reduced'):27.72,
                ('day', 'free'):0,
                ('gala', 'normal'):25.66,
                ('gala', 'reduced'):20.53,
                ('gala', 'free'):0}
              }
    if login:
      self.login()
    self.clickto('products')
    if   ticket == 'week': self.select_week_ticket(name=name, email=email, age=age)
    elif ticket == 'day' : self.select_day_ticket(name=name, email=email, age=age)
    elif ticket == 'gala': self.select_gala_ticket(name=name, email=email, age=age)
    else: raise NotImplementedError("Ticket type {} not implemented.".format(ticket))
    self.clickto('add_to_cart')
    self.clickto('shopping_cart_next')
    if not self.checkout(amount=amounts[payment][(ticket, age)], payment=payment): return False
    return self.pay(payment=payment)

  def order_two_weektickets(self):
    self.clickto('products')
    self.select_week_ticket(person_id=1)
    self.clickto('add_to_cart')
    self.clickto('add_more_products')
    self.select_week_ticket(person_id=2, always_add=True)
    self.clickto('add_to_cart')
    self.clickto('shopping_cart_next')
    if not self.checkout(amount=360, payment='sepa'): return False
    return self.pay(payment='sepa')

  def order_week_and_day(self):
    self.clickto('products')
    self.select_week_ticket(person_id=1)
    self.clickto('add_to_cart')
    self.clickto('add_more_products')
    self.select_day_ticket(person_id=2, always_add=True)
    self.clickto('add_to_cart')
    self.clickto('shopping_cart_next')
    if not self.checkout(amount=215, payment='sepa'): return False
    return self.pay(payment='sepa')

  def order_two_daytickets(self):
    self.clickto('products')
    self.select_day_ticket(day=2)
    self.clickto('add_to_cart')
    self.clickto('add_more_products')
    self.select_day_ticket(day=3)
    self.clickto('add_to_cart')
    self.clickto('shopping_cart_next')
    if not self.checkout(amount=70, payment='sepa'): return False
    return self.pay(payment='sepa')
