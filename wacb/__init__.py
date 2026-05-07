#!python
# Whats App Chat Browser

import sys
from .wacb import *
from .wacbchat import *
from .wacbapp import *
from .wacbemoji import *
from .wacbhtml import *
from .wacbhttp import *

if not "-m" in sys.argv:
    def runWacb(ui=None):
        wacb.run(ui)

    def runWacbUi():
        runWacb(True)

    def runWacbCli():
        runWacb(False)

    def mergeChatsCli():
        wacb.mergeChatsCli()
