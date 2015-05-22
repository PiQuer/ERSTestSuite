'''
Created on 22.05.2015

@author: Raimar Sandner
'''

import autopy
import time
import math
import cv2
import WaitForKey as key
import numpy as np
import os
import datetime
import logging
import ConfigParser
import StringIO

# Setup logger for this module
logger = logging.getLogger(__name__)
handler=logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s'))
logger.setLevel(logging.INFO)
logger.handlers=[handler]
logger.propagate=False

shortsleep = 0.1
longsleep = 0.9
fastsleep = 0.03
confidence = 0.95

def config_parser(files=None):
  if files is None: files=[]
  if type(files) is str: files=[files]
  defaults= """
[Config]
basedir={basedir}
packagedir={packagedir}
display=:1
""".format(basedir=os.path.expanduser('~/.ersTestSuite'),packagedir=os.path.dirname(__file__))
  config = ConfigParser.SafeConfigParser()
  config.optionxform = str
  config.readfp(StringIO.StringIO(defaults))
  config.read(map(os.path.expanduser,files))
  return config


templates = {}
"""A dictionary with all template images used in image recognition.
"""
cal = {}
"""A dictionary with all calibration points. These are found by image recognition 
during calibration (see :func:`linetoCal`). The coordinates of all other elements are given
relative to these calibration points, for example::

    _clickto(cal['friend'] + Point(67, -32))
"""
spots = {}
"""This dictionary basicly contains 'named' points. It is initialized during
calibration and translates names into instances of :class:`Point`. We can click on
a 'spot', but if we want to check if an element is really there before clicking on it,
better use a :class:`ClientElement` (stored in :data:`elements`).
"""
bboxes = {}
"""A dictionary containing bounding boxes for image recognition. It is initialized during
calibration.
"""
elements = {}
"""A dictionary with :class:`ClientElement` objects we wish to use. It is initialized during
calibration.
"""


class CalibrationError(Exception):
  """This exception is raised whenever an element that was expected is not found
  on screen during calibration.
  """
  pass


class ClientInconsistency(Exception):
  """This is currently unused.
  """
  pass


class Timeout(Exception):
  """This exception is raised if we have waited too long for a client element to become
  visible (for example when opening an offer from the mailbox).
  """
  pass


class ElementError(Exception):
  """This exception is raised if something unexpected is visible on screen.
  """
  pass


class Match(object):
  """This class stores a match of an image recognition task.

  :param c: The confidence with which the match was performed (between 0 and 1).
  :type c: float
  :param p: The point at which the template was found.
  :type p: :class:`Point`

  Comparison of ``Match``-objects is implemented by comparing the confidence-values. Therefore
  we can conveniently sort a list of ``Match``-objects.
  """

  def __init__(self, c, p):
    self.conf = c
    self.point = p

  def __lt__(self, other):
    if isinstance(other, Match):
      return self.conf < other.conf
    else:
      return NotImplemented

  def __le__(self, other):
    if isinstance(other, Match):
      return self.conf <= other.conf
    else:
      return NotImplemented

  def __gt__(self, other):
    if isinstance(other, Match):
      return self.conf > other.conf
    else:
      return NotImplemented

  def __ge__(self, other):
    if isinstance(other, Match):
      return self.conf >= other.conf
    else:
      return NotImplemented

  def __str__(self):
    return (self.conf, self.point).__str__()


class ClientElement(object):
  """A ``ClientElement`` consists of a template image and a region (bbox) where to look
  for the template. We can then check if the element is visible and click on it.

  :param bbox: The bounding box where to look for the client element.
  :type bbox: :class:`BBox`
  :param template: The template image which defines the visual appearance of the element.
  :type template: :mod:`cv2`-image, :class:`numpy.ndarray`
  :param conf: The confidence with which to look for the template (optional).
  :type conf: float
  :param clickpoint: Where to click on the element (optional, defaults to the center of the bbox).
  :type clickpoint: :class:`Point` or None
  """

  def __init__(self, name, bbox, template, conf=confidence, clickpoint=None, relative=False, clickvisible=False):
    (self.name, self.bbox, self.template, self.conf, self.clickpoint) = (
        name, bbox, template, conf, clickpoint)
    self._lastpos = None
    self.lastcount = 0
    self.relative = relative
    self.clickvisible = clickvisible

  def assertvisible(self):
    """Assert that the client element is visible.

    :raises: :class:`ElementError` if the client element is not visible.
    """
    if not self.isvisible():
      raise ElementError("Steuerelement nicht sichtbar")

  def assertnotvisible(self):
    """Assert that the client element is not visible.

    :raises: :class:`ElementError` if the client element is visible.
    """
    if self.isvisible():
      raise ElementError("Steuerelement unerwartet sichtbar")

  def isvisible(self, at=None, delay=0, conf=None):
    """:returns: True if the client element is visible.

    If the element is visible, the position where it has been found within
    the bounding box is stored and can be accessed with :func:`lastpos`.
    """
    time.sleep(delay)
    cbbox = self._currentbbox(at)
    im = grab(bbox=cbbox)
    localconf = self.conf if conf == None else conf
    found = match(im, self.template, localconf, mult=True)
    self.lastcount = len(found)
    offset = Point(0, 0) if self.bbox == None else cbbox.offset()
    self._lastpos = [f.point + offset for f in found]
    self._lastconf = [f.conf for f in found]
    return bool(self._lastpos)

  def morevisible(self):
    return bool(self._lastpos)

  def click(self, blind=False, ifvisible=False, wait=None, **kwargs):
    """Click to the element.

    :param blind: Click blindly without checking that the element is visible.
    :raises: :class:`ElementError` if ``blind`` is False and the element is not visible.
    """
    if wait:
      _waitforelement(self, timeout=wait)
    if (not blind) and (not self.isvisible()):
      if ifvisible:
        return
      raise ElementError("Steuerelement nicht sichtbar: " + self.name)
    _clickto(self._currentclickpoint(), **kwargs)

  def clicklast(self, remove=False, **kwargs):
    _clickto(self.lastpos(remove), **kwargs)

  def lastpos(self, remove=False):
    """:returns: :class:`Point` as absolute coordinate where the element was last visibile.
    :raises: :class:`ElementError` if :func:`isvisible` previously returned False or was not called.  
    """
    if not self._lastpos:
      raise ElementError("Targetposition nicht bekannt.")
    return self._lastpos[0] if not remove else self._lastpos.pop(0)

  def _currentbbox(self, at=None):
    if self.bbox == None:
      return None
    if self.relative:
      if at:
        offset = at
      else:
        offset = _getpos()
    else:
      offset = Point(0, 0)
    return self.bbox + offset

  def _currentclickpoint(self):
    if self.clickpoint == None:
      if self._currentbbox() and not self.clickvisible:
        return self._currentbbox().midpoint()
      else:
        return self.lastpos()
    else:
      return (self.clickpoint + _getpos()) if self.relative else self.clickpoint


class BBox(tuple):
  """Stores a bounding box (two points with upper-left and lower-right coordinates).

  :param x1:
  :param y1:
  :param x2:
  :param y2: The coordinates.

  We can add a :class:`Point` to a :class:`BBox` to give it an offset.
  """
  def __new__(cls, x1, y1, x2, y2):
    return tuple.__new__(cls, (x1, y1, x2, y2))

  def __add__(self, other):
    if isinstance(other, Point):
      return BBox(self[0] + other[0], self[1] + other[1],
                  self[2] + other[0], self[3] + other[1])
    else:
      return NotImplemented

  def __sub__(self, other):
    if isinstance(other, Point):
      return BBox(self[0] - other[0], self[1] - other[1],
                  self[2] - other[0], self[3] - other[1])
    else:
      return NotImplemented

  def midpoint(self):
    """:returns: The middle of the bounding box.
    :rtype: :class:`Point`
    """
    return Point(int((self[0] + self[2]) / 2), int((self[1] + self[3]) / 2))

  def offset(self):
    """:returns: The upper left corner of the bounding box.
    :rtype: :class:`Point`
    """
    return Point(self[0], self[1])

  @property
  def width(self):
    return self[2] - self[0]

  @property
  def height(self):
    return self[3] - self[1]

  def center_vertically(self, pos):
    return BBox(self[0], pos - self.height / 2, self[2],
                pos + (self.height - self.height / 2))


class Point(tuple):
  """Stores the coordinates of a point.

  :param x:
  :param y: The coordinates of the point.

  We can add one point to another to give it an offset, substract two points to have
  the coordinates of one point relative to the other, or 'multiply' two points to
  get a bounding box::

      Point(x1,y1)*Point(x2,y2)==BBox(x1,y1,x2,y2)
  """
  def __new__(cls, x, y):
    return tuple.__new__(cls, (x, y))

  def __add__(self, other):
    if isinstance(other, Point):
      return Point(self[0] + other[0], self[1] + other[1])
    elif isinstance(other, BBox):
      return other + self
    else:
      return NotImplemented

  def __sub__(self, other):
    if not isinstance(other, Point):
      return NotImplemented
    else:
      return Point(self[0] - other[0], self[1] - other[1])

  def __mul__(self, other):
    if isinstance(other, Point):
      return BBox(self[0], self[1], other[0], other[1])
    elif isinstance(other, int):
      return Point(other * self[0], other * self[1])
    else:
      return NotImplemented

  def distance(self, other):
    return math.sqrt((self[0] - other[0]) ** 2 + (self[1] - other[1]) ** 2)


def _moveto(point, movesleep=shortsleep, offset=Point(0, 0), **kwargs):
  movefunc = autopy.mouse.smooth_move if kwargs.get(
      'smooth') else autopy.mouse.move
  movefunc((point + offset)[0], (point + offset)[1])
  time.sleep(movesleep)


def _mousedown(s=shortsleep):
  autopy.mouse.toggle(True)
  time.sleep(s)


def _mouseup(s=shortsleep):
  autopy.mouse.toggle(False)
  time.sleep(s)


def _click(clicksleep=longsleep, **kwargs):
  autopy.mouse.click()
  time.sleep(clicksleep)


def _keypress(i):
  autopy.key.tap(str(i))


def _type_string(s, typesleep=shortsleep):
  autopy.key.type_string(s)
  time.sleep(typesleep)


def _mark_all(spot):
  _drag(spot, spot + Point(200, 0), smooth=True)


def _clickto(point, **kwargs):
  args = dict(movesleep=0.3)
  args.update(kwargs)
  _moveto(point, **args)
  _click(**kwargs)


def _drag(point1, point2, smooth=False, **kwargs):
  _moveto(point1, **kwargs)
  _mousedown(**kwargs)
  _moveto(point2, smooth=smooth, **kwargs)
  _mouseup(**kwargs)


def _getpos(offset=Point(0, 0)):
  if isinstance(offset, str):
    offset = spots[offset]
  return Point(*autopy.mouse.get_pos()) - offset


def _waitforelement(positive, negative=[], timeout=120, sleep=0.5):
  """Wait for a :class:`ClientElement` ``positive`` at most ``timeout`` seconds and
  raise :class:`Timeout`. Return `True` if `positive` was found or
  `False` if one of the elements in ``negative`` was found during that time.
  """
  while timeout > 0:
    if positive.isvisible():
      return (True, positive)
    for n in negative:
      if n.isvisible():
        return (False, n)
    time.sleep(sleep)
    timeout -= sleep
  raise Timeout("Timeout beim Warten auf Steuerelement: " + positive.name)

def _imreadRGB(filename):
  return cv2.imread(os.path.expanduser(filename))

def _imwriteRGB(filename, im):
  cv2.imwrite(os.path.expanduser(filename), im)

def grab(delay=0, bbox=None):
  """Make a screenshot of the screen. This is the basis for methods like :func:`ClientElement.isvisible()`.

  :param delay: Seconds to wait before grabbing the screen.
  :type delay: int
  :param bbox: Bounding box
  :type bbox: :class:`BBox`
  :returns: Image of the screen region in ``bbox`` or the full screen.
  :rtype: :class:`numpy.ndarray`
  """
  for i in range(1, delay):
    print `i` + ".."
    time.sleep(1)
  if bbox:
    rect = (bbox[0:2], (bbox[2] - bbox[0] + 1, bbox[3] - bbox[1] + 1))
    return autopy.bitmap.capture_screen(rect).to_numpy()
  else:
    im = autopy.bitmap.capture_screen().to_numpy()
    if bbox:
      im = im[bbox[1]:bbox[3] + 1, bbox[0]:bbox[2] + 1, :]
    return im


def match(source, target, conf=confidence, mult=False):
  """Image recognition: find ``target`` in ``source``.

  :param source: Image to search in.
  :type source: :class:`numpy.ndarray`
  :param target: Template to search for.
  :type target: :class:`numpy.ndarray`
  :param conf: Minimum confidence for a match (between 0 and 1)
  :type conf: float
  :param mult: Allow multiple matches. If False, only return the match with maximum confidence.
  :type mult: bool
  :returns: A list of :class:`Match` objects. 
  """
  r = []
  if type(target) == list:
    for t in target:
      r.append(match(source, t, conf, mult))
    return r
  (t_height, t_width, _) = target.shape
  result = cv2.matchTemplate(source, target, cv2.TM_CCOEFF_NORMED)
  if mult:
    match_indices = np.arange(result.size)[(result > conf).flatten()]
    for i in match_indices:
      (y, x) = np.unravel_index(i, result.shape)
      r.append(
          Match(result[y, x], Point(int(x + t_width / 2), int(y + t_height / 2))))
  else:
    (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)
    if maxVal >= conf:
      r.append(
          Match(maxVal, Point(int(maxLoc[0] + t_width / 2), int(maxLoc[1] + t_height / 2))))
  return sorted(r, key=lambda r: r.conf, reverse=True)


def getbbox(offset=Point(0, 0), relative=False):
  """This is a convenience function for development. For the upper left and lower right
  position, this function waits for a key to be entered and records the mouse position
  at this time. It then prints the bounding box which can be copied to the code.

  :param offset: An offset which is added to the bounding box.
  :type offset: :class:`Point`

  Typical usage::

      >>> import siedlerbot.ClientInterface as CI
      >>> CI.autocalibration()
      >>> CI.getbbox(offset=CI.cal['handshake'])
      top left: a<enter> 
      (50, 10)
      bottom right: a<enter>
      (150, 210)
      (50, 10, 150, 210)
  """
  if type(offset) == str:
    offset = spots[offset]
  if relative:
    offset = _getpos()
  print "top left: "
  key.read_single_keypress()
  p1 = _getpos(offset)
  print p1
  print "bottom right: "
  key.read_single_keypress()
  p2 = _getpos(offset)
  print p2
  return p1 * p2


def savescreenshot(filename="", full=False, delay=0, bbox=()):
  """This is a convenience function for development. It saves a screenshot to the
  image directory, typically siedlerbot/images inside the package directory.

  :param filename: The filename where the image is saved. Prompt for a filename if empty.
  :type filename: str
  :param full: If ``True``, grab the full screen, otherwise use ``bbox`` or use :func:`getbbox`
  :type full: bool
  :param delay: Seconds to wait before taking the screenshot.
  :type delay: int
  :param bbox: The bounding box of the screen region to grab. If empty and ``full`` is ``False``, use :func:`getbbox`
  :type bbox: :class:`BBox`

  Typical usage::
      >>> import siedlerbot.ClientInterface as CI
      >>> CI.autocalibration()
      >>> CI.savescreenshot(filename="debug.bmp", delay=2, bbox=CI.bboxes['item_angebot']
  """
  d = delay
  if full:
    im = grab(delay=d)
  else:
    if bbox is ():
      bb = getbbox()
    else:
      bb = bbox
    im = grab(delay=d, bbox=bb)
  if filename == "":
    filename = raw_input("Filename: ").strip()
  _imwriteRGB(os.path.expanduser(filename), im)


def stopwatch():
  now = datetime.datetime.now()
  raw_input("Stop:")
  then = datetime.datetime.now()
  print (then - now).total_seconds()


def debugbbox(bbox, shift=None, offset=None):
  if type(bbox) == str:
    bbox = bboxes[bbox]
  if shift:
    bbox = bbox + Point(*shift)
  if offset:
    print bbox - spots[offset]
  im = grab()
  im[bbox[1], bbox[0]:bbox[2] + 1, :] = 255
  im[bbox[3] + 1, bbox[0]:bbox[2] + 1, :] = 255
  im[bbox[1]:bbox[3] + 1, bbox[0], :] = 255
  im[bbox[1]:bbox[3] + 1, bbox[2] + 1, :] = 255
  _imwriteRGB(os.path.expanduser('~/debug.bmp'), im)
