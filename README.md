# ERSTestSuite
Automatic Testsuite for the ers project.
## Installation Requirements
* Python 2.7
* [pyautogui](https://github.com/asweigart/pyautogui)
* [numpy](http://www.numpy.org/)
* [opencv2](http://opencv.org/), which comes with python bindings
Only tested under Linux.

## Configuration
To configure the test suite you can create the file `~/.ersTestSuite/config.txt`:

    [Config]
    display=:0      # useful if you want to test in a VNC session, in this case put for example :1
    timeout=10      # timeout to wait before calibrating the client (time to bring the browser to the front)
    confidence=0.8  # confidence level for image matching
    username=your.login@email.de
    password=your_password
    [Person]
    email=your.RND@mail.de  # RND is replaced by five random letters
    name=Your Name
    creditcard_number=4111111111111111  # this default works with the dev site
    creditcard_sec=123

The most defaults work fine, but you have to specify your login email and password.

## Screenshots

Most likely some or all of the screenshots have to be adjusted. Whenever a match fails, you can put your
own version of the image to `~/.ersTestSuite/images`, these have precedence over the packaged images. Most 
important is the image `site_loaded.png`, this should be a browser element which is only visible when the 
site has finished loading, such es the "reload" button. Put your version of this button (25x25 pixels) into
the images directory.

The `ERSClientInterface` has a `savescreenshot` method to help creating screenshots. To use it, you need
some kind of drop-down console like yakuake which can be activated and displayed over the browser window
by a keypress (F12 for yakuake). Open an ipython session:

    from ERSClientInterface import ERSClientInterface
    CI=ERSClientInterface()
    CI.savescreenshot()

Then place the mouse to the top left corner of the screen section you want to capture. Go back to the
python session without moving the mouse and press any key, then do the same for the bottom right corner.
Enter a filename, the image will be saved to `~/.ersTestSuite/images`.

## Running the tests

The whole test suite can be run with `python main.py`, individual tests can be run for example by calling
`python main.py OrderTestCase.test_ticket_order_week_normal_sepa`.
