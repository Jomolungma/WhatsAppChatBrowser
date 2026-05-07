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

import json
import pathlib

class DictWrapper:
    def __init__(self, config, groupName):
        self.config = config
        self.groupName = groupName

    def __contains__(self, key):
        return key in self.config.config[self.groupName]

    def __getitem__(self, key):
        return self.config.config[self.groupName][key]

    def __setitem__(self, key, value):
        if value != self.config.config[self.groupName][key]:
            self.config.modified = True
            self.config.config[self.groupName][key] = value

    def items(self):
        return self.config.config[self.groupName].items()

class WacbConfig:
    configFileLocations = [
        "~/.wacb",
    ]

    defaultConfig = {
        "html": {
            "builtinCss": True,
            "cssFileName": "",
            "inlineImages": True,
            "inlineVideo": True,
            "inlineAudio": True,
            "showAs": "Single",
            "formatForYear": "%Y",
            "formatForMonth": "%B",
            "formatForDay": "%B %d, %Y"
        },
        "emoji": {
            "images": False,
            "inline": True,
            "dataBase": "",
            "pathInZip": "",
            "ignoreAscii": True,
            "emojiPath": "emoji"
        },
        "http": {
            "hostName": "localhost",
            "portNumber": 0
        },
        "autostart": False,
        "me": [],
        "userNameMap": {},
        "nobody": "(None)"
    }

    def __init__(self, useConfigFile, configFile=None):
        self.modified = False
        self.config = WacbConfig.defaultConfig
        self.useConfigFile = useConfigFile
        self.configFile = configFile if useConfigFile else None
        self.load()

    def __contains__(self, groupName):
        return groupName in self.config

    def __getitem__(self, groupName):
        if isinstance(self.config[groupName], dict):
            return DictWrapper(self, groupName)
        return self.config[groupName]

    def __setitem__(self, groupName, value):
        if isinstance(self.config[groupName], dict):
            raise Exception("Oops.")
        if value != self.config[groupName]:
            self.config[groupName] = value
            self.modified = True

    def load(self):
        if not self.useConfigFile:
            return
        if self.configFile:
            self.loadConfigFromFile(path)
            return
        for fileName in WacbConfig.configFileLocations:
            try:
                self.loadConfigFromFile(fileName)
                self.configFile = fileName
            except:
                pass

    def save(self):
        if not self.useConfigFile:
            return
        if not self.modified:
            return
        if self.configFile:
            self.writeConfigToFile(self.configFile)
            self.modified = False
            return
        for fileName in WacbConfig.configFileLocations:
            try:
                self.writeConfigToFile(fileName)
                self.configFile = fileName
                self.modified = False
            except:
                pass

    def writeConfigToFile(self, fileName):
        path = pathlib.Path(fileName)
        path = path.expanduser()
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.config, file, indent=4)

    def loadConfigFromFile(self, fileName):
        path = pathlib.Path(fileName)
        path = path.expanduser()
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        self.merge(data)

    def merge(self, data):
        for toplevel in ["html", "http", "emoji"]:
            self.mergeToplevel(data, toplevel)
        self.mergeValues(self.config, data, ["autostart", "nobody"])
        if "me" in data:
            for alias in data["me"]:
                self.addMeAlias(alias, False)
        if "userNameMap" in data:
            for userName, alias in data["userNameMap"].items():
                self.addUserNameAlias(userName, alias)

    def mergeToplevel(self, data, toplevel):
        if toplevel in data:
            keys = WacbConfig.defaultConfig[toplevel].keys()
            self.mergeValues(self.config[toplevel], data[toplevel], keys)

    def mergeValues(self, config, data, keys):
        for key in keys:
            if key in data:
                if config[key] != data[key]:
                    config[key] = data[key]
                    self.modified = True

    def addToListOfNames(self, configKey, name, front=True):
        configList = self.config[configKey]
        if name not in configList:
            if front:
                configList.insert(0, name)
            else:
                configList.append(name)
            self.modified = True
        elif front and (configList[0] != name):
            configList.remove(name)
            configList.insert(0, name)
            self.modified = True

    def addMeAlias(self, alias, front=True):
        self.addToListOfNames("me", alias, front)

    def addUserNameAlias(self, userName, alias):
        unmConfig = self.config["userNameMap"]
        if alias and ((userName not in unmConfig) or alias != unmConfig[userName]):
            unmConfig[userName] = alias
            self.modified = True
