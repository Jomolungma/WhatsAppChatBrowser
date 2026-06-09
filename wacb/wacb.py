#!python
#
#    WhatsApp Chat Browser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

"""
Command-line interface.
"""

import glob
import locale
import argparse

if __package__ == "wacb":
    from . import wacbui
    from . import wacbapp
    from . import wacbchat
else:
    import wacbui
    import wacbapp
    import wacbchat

def mergeChatsCli():
    locale.setlocale(locale.LC_ALL, '')
    wacbchat.mergeChatsCli()

def run(ui=None):
    locale.setlocale(locale.LC_ALL, '')
    parser = argparse.ArgumentParser(prog="WhatsApp Chat Browser")
    parser.add_argument('--exportAsChat', default=None, help="Export Chat to this ZIP file.")
    parser.add_argument('--exportAsHtml', default=None, help="Export HTML to this ZIP file.")
    parser.add_argument('-n', '--noConfigFile', default=False, action="store_true", help="Do not load default configuration file.")
    parser.add_argument('-c', '--configFile', default=None, help="Use this configuration file.")
    parser.add_argument('-v', '--verbose', default=0, action="count", help="Verbosity level.")
    parser.add_argument('--ui', default=None, action=argparse.BooleanOptionalAction, help="Whether to run the UI or on the console.")
    parser.add_argument('-t', '--title', default=None, help="The title to use for HTML pages.")
    parser.add_argument('chats', nargs="*", default=[], help="The exported chat file to load.")
    args = parser.parse_args()

    useUi = True if ui is None and args.ui is None else (ui if args.ui is None else args.ui)
    useConfigFile = not args.noConfigFile
    configFile = args.configFile
    verbosity = args.verbose
    title = args.title

    chatFiles = []
    for chat in args.chats:
        chatFiles.extend(glob.glob(chat))

    if args.exportAsChat:
        wacbchat.mergeChats(args.exportAsChat, chatFiles, verbosity)
    elif args.exportAsHtml:
        wacbapp.exportAsHtml(args.exportAsHtml, chatFiles, title, useConfigFile, configFile, verbosity)
    elif useUi:
        wacbui.run(chatFiles, title, useConfigFile, configFile, verbosity)
    else:
        if len(chatFiles) == 0:
            # pylint: disable=consider-using-sys-exit
            print("Must provide exported chat file.")
            exit(1)
        wacbapp.run(chatFiles, title, useConfigFile, configFile, verbosity)

if __name__ == "__main__":
    run()
