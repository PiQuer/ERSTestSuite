'''
Created on 22.05.2015

@author: Raimar Sandner
'''

import time
import math
import WaitForKey as key
import os
import logging
import numpy as np
import cv2

# Setup logger for this module
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s'))
logger.setLevel(logging.DEBUG)
logger.handlers = [handler]
logger.propagate = False

shortsleep = 0.1
longsleep = 0.9
fastsleep = 0.03
confidence = 0.8

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

class ClientInterface(object):

  def __init__(self, display):
    global gui
    os.environ['DISPLAY'] = display
    import pyautogui as gui
    gui.FAILSAFE = False
    self.imagedirs = ['']
    self.default_timeout = 10


  def _moveto(self, point, movesleep=shortsleep, smooth=False, offset=Point(0, 0)):
    newpoint = point + offset
    gui.moveTo(newpoint[0], newpoint[1], 1 if smooth else 0, pause=movesleep)


  def _mousedown(self, s=shortsleep):
    gui.mouseDown(pause=s)

  def _mouseup(self, s=shortsleep):
    gui.mouseUp(pause=s)

  def _click(self, clicksleep=longsleep, **kwargs):
    gui.click(pause=clicksleep)


  def keypress(self, i):
    gui.press(str(i))


  def type_string(self, s, typesleep=shortsleep):
    gui.typewrite(s, interval=typesleep)


  def _mark_all(self, spot):
    self._drag(spot, spot + Point(200, 0), smooth=True)


  def clickto(self, point, wait=False, **kwargs):
    if wait:
      _, point = self.waitforelement(point)
    else:
      point = self.locate(point)
    args = dict(movesleep=0.3)
    args.update(kwargs)
    self._moveto(point, **args)
    self._click(**kwargs)
    self._moveto(Point(0, 0), **args)


  def _drag(self, point1, point2, smooth=False, **kwargs):
    self._moveto(point1, smooth=smooth)
    gui.dragTo(point2[0], point2[1], 1 if smooth else 0)


  def getpos(self, offset=Point(0, 0)):
    if isinstance(offset, str):
      offset = self.locate(offset)
    return Point(*gui.position()) - offset


  def waitforelement(self, positive, timeout=None, negative=[], sleep=0.5, **kwargs):
    """Wait for an element ``positive`` at most ``timeout`` seconds and
    raise :class:`Timeout`. Return `True` if `positive` was found or
    `False` if one of the elements in ``negative`` was found during that time.
    """
    if timeout is None:
      timeout = self.default_timeout
    while timeout > 0:
      vis = ClientInterface.isvisible(self, positive, location=True, **kwargs)
      if vis:
        return (True, vis)
      for n in negative:
        if self.isvisible(n):
          return (False, n)
      time.sleep(sleep)
      timeout -= sleep
    raise Timeout("Timeout beim Warten auf Steuerelement: " + positive)

  def _imreadRGB(self, filename):
    return gui.Image.open(filename, 'r')

  def _imwriteRGB(self, filename, im):
    im.save(filename)

  def grab(self, delay=0, bbox=None):
    """Make a screenshot of the screen. This is the basis for methods like :func:`ClientElement.isvisible()`.
  
    :param delay: Seconds to wait before grabbing the screen.
    :type delay: int
    :param bbox: Bounding box
    :type bbox: :class:`BBox`
    :returns: Image of the screen region in ``bbox`` or the full screen.
    :rtype: :class:`numpy.ndarray`
    """
    for i in range(1, delay):
      print(str(i) + "..")
      time.sleep(1)
    rect = tuple(bbox[0:2]) + (bbox[2] - bbox[0] + 1, bbox[3] - bbox[1] + 1) if not bbox is None else None
    return gui.screenshot(region=rect)

  def _pil_to_numpy(self, pic):
    return np.array(pic)

  def match(self, target, source=None, bbox=None, conf=confidence, mult=False):
    """Image recognition: find ``target`` in ``source``. Unfortunately, the implementation of
    pyautogui is incredibly slow :(
   
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
    offset = bbox.offset() if not bbox is None else Point(0, 0)
    r = []
    if type(target) == list:
      for t in target:
        r.append(self.match(source, t, conf, mult))
      return r
    if source is None:
      source = self.grab(bbox=bbox)
    if type(target) is str:
      if not target.endswith('.png'):
        target = target + '.png'
      for d in self.imagedirs:
        try:
          target = self._imreadRGB(os.path.join(d, target))
          break
        except IOError:
          pass
    source = self._pil_to_numpy(source)
    target = self._pil_to_numpy(target)
    (t_height, t_width, _) = target.shape
    result = cv2.matchTemplate(source, target, cv2.TM_CCOEFF_NORMED)
    if mult:
      match_indices = np.arange(result.size)[(result > conf).flatten()]
      for i in match_indices:
        (y, x) = np.unravel_index(i, result.shape)
        r.append(
            Match(result[y, x], Point(int(x + t_width / 2), int(y + t_height / 2)) + offset))
    else:
      (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)
      if maxVal >= conf:
        r.append(
            Match(maxVal, Point(int(maxLoc[0] + t_width / 2), int(maxLoc[1] + t_height / 2)) + offset))
    return sorted(r, key=lambda r: r.conf, reverse=True)

  def locate(self, im, **kwargs):
    try:
      return self.match(im, **kwargs)[0].point
    except IndexError:
      raise ElementError(im)

  def isvisible(self, im, location=False, **kwargs):
    try:
      pos = self.locate(im, **kwargs)
      if location:
        return pos
      else:
        return True
    except ElementError:
      return False

  def size(self):
    return gui.size()

  def getbbox(self, offset=Point(0, 0), relative=False):
    """This is a convenience function for development. For the upper left and lower right
    position, this function waits for a key to be entered and records the mouse position
    at this time. It then prints the bounding box which can be copied to the code.
  
    :param offset: An offset which is added to the bounding box.
    :type offset: :class:`Point`
  
    Typical usage::
  
        >>> import ClientInterface as CI
        >>> CI.autocalibration()
        >>> CI.getbbox(offset=CI.cal['handshake'])
        top left: a<enter> 
        (50, 10)
        bottom right: a<enter>
        (150, 210)
        (50, 10, 150, 210)
    """
    if type(offset) == str:
      offset = self.locate(offset)
    if relative:
      offset = self.getpos()
    print("top left: ")
    key.read_single_keypress()
    p1 = self.getpos(offset)
    print(p1)
    print("bottom right: ")
    key.read_single_keypress()
    p2 = self.getpos(offset)
    print(p2)
    return p1 * p2


  def savescreenshot(self, filename=None, dirname=None, full=False, delay=0, bbox=()):
    """This is a convenience function for development. It saves a screenshot to the
    image directory, typically images inside the package directory.
  
    :param filename: The filename where the image is saved. Prompt for a filename if empty.
    :type filename: str
    :param full: If ``True``, grab the full screen, otherwise use ``bbox`` or use :func:`getbbox`
    :type full: bool
    :param delay: Seconds to wait before taking the screenshot.
    :type delay: int
    :param bbox: The bounding box of the screen region to grab. If empty and ``full`` is ``False``, use :func:`getbbox`
    :type bbox: :class:`BBox`
  
    Typical usage::
        >>> import ClientInterface as CI
        >>> CI.autocalibration()
        >>> CI.savescreenshot(filename="debug.bmp", delay=2, bbox=CI.bboxes['item_angebot'])
    """
    d = delay
    if dirname is None:
      dirname = self.imagedirs[0]
    if full:
      im = self.grab(delay=d)
    else:
      if bbox is ():
        bb = self.getbbox()
      else:
        bb = bbox
      im = self.grab(delay=d, bbox=bb)
    if filename is None:
      filename = raw_input("Filename: ").strip()
    self._imwriteRGB(os.path.join(dirname if dirname else '', filename), im)

