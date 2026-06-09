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
Helpers for accessing information in a CSS file.
"""

import sys
import pkgutil
from os import path

class ElementHelper:
    """
    Helper for accessing properties in a CSS element.
    """

    def __init__(self, parent, elementPos, closingBracePos):
        self.parent = parent
        self.elementPos = elementPos
        self.closingBracePos = closingBracePos

    def __contains__(self, parameter):
        try:
            # pylint: disable=unused-variable
            item = self[parameter]
        except:
            return False
        return True

    def __getitem__(self, parameter):
        parameterPos = self.parent.css.find(parameter, self.elementPos, self.closingBracePos)
        colonPos = self.parent.css.find(":", parameterPos, self.closingBracePos)
        semicolonPos = self.parent.css.find(";", colonPos, self.closingBracePos)
        if parameterPos == -1 or colonPos == -1 or semicolonPos == -1:
            return KeyError
        return self.parent.css[colonPos+1:semicolonPos].strip()

    #
    # This class only supports modifying existing values, not adding new parameters.
    #

    def __setitem__(self, parameter, value):
        parameterPos = self.parent.css.find(parameter, self.elementPos, self.closingBracePos)
        colonPos = self.parent.css.find(":", parameterPos, self.closingBracePos)
        semicolonPos = self.parent.css.find(";", colonPos, self.closingBracePos)
        if parameterPos == -1 or colonPos == -1 or semicolonPos == -1:
            raise KeyError
        svalue = str(value)
        lengthDiff = len(svalue) - (semicolonPos - colonPos) + 1
        self.parent.css = self.parent.css[:colonPos] + ": " + svalue + self.parent.css[semicolonPos:]
        self.closingBracePos += lengthDiff

class Document:
    """
    Represents a CSS document.
    """

    def __init__(self):
        self.css = None

    @property
    def data(self):
        return self.css

    def __contains__(self, element):
        try:
            # pylint: disable=unused-variable
            item = self[element]
        except:
            return False
        return True

    def __getitem__(self, element):
        if not isinstance(element, str):
            raise TypeError
        elementPos = self.css.find(element)
        closingBracePos = self.css.find("}", elementPos)
        if elementPos == -1 or closingBracePos == -1:
            raise KeyError
        return ElementHelper(self, elementPos, closingBracePos)

class File(Document):
    """
    Load a CSS document from a file.
    """

    def __init__(self, fileName):
        super().__init__()
        with open(fileName, encoding="utf-8") as cssFile:
            self.css = cssFile.read()

class Builtin(Document):
    """
    Load the built-in CSS document.
    """

    def __init__(self):
        super().__init__()
        data = pkgutil.get_data("wacb", "wacb.css")
        self.css = data.decode()

def makeBuiltinCss():
    if "wacb" in sys.modules:
        return Builtin()
    else:
        return File(path.abspath(path.join(path.dirname(__file__), "wacb.css")))

def makeCssProvider(fileName, useBuiltin):
    return makeBuiltinCss() if useBuiltin else File(fileName)
