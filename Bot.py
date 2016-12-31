# coding: utf-8

# 2017 © Guillermo Gómez Fonfría <guillermo.gf@openmailbox.org>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys
import os
import json
import requests
import time
import ConfigParser
import signal


class Bot():
    def __init__(self, bot_name, config_path):
        # Load Config
        self.default = {"token_path": "token", "lastupdate_path": "lastupdate",
                        "log_status": True, "log_path": "log",
                        "sleep_time": 1.0, "unknown_text": "Unknown command"}
        self.config = ConfigParser.ConfigParser(self.default)
        self.config.read(config_path)

        self.token_path = self.config.get(bot_name, "token_path")
        self.lastupdate_path = self.config.get(bot_name, "lastupdate_path")
        self.log_status = self.config.getboolean(bot_name, "log_status")
        self.log_path = self.config.get(bot_name, "log_path")
        self.sleep_time = self.config.getfloat(bot_name, "sleep_time")
        self.unknown_text = self.config.get(bot_name, "unknown_text")

        try:
            with open(self.token_path) as self.token_file:
                self.token = self.token_file.read().rstrip("\n")
        except IOError:
            print("Token file not found")
            sys.exit(1)

        self.api_url = "https://api.telegram.org/bot"
        self.token_url = self.api_url + self.token
        self.getupdates_url = self.token_url + "/getUpdates?offset="
        self.sendmessage_url = self.token_url + "/sendMessage?chat_id="
        self.sendimage_url = self.token_url + "/sendPhoto"

        # Set empty commands list
        self.text_commands = [[], []]
        self.commands = [[], []]

        try:
            with open(self.lastupdate_path) as self.last_update_file:
                self.last_update = self.last_update_file.read().rstrip("\n")
        except:
            # If lastupdate file not present, read all updates
            self.last_update = "0"

    def setTextCommands(self, commands, texts):
        # List of commands which only send some text
        # Commands should start with '/'
        if len(commands) != len(texts):
            print("Length of command and texts lists do not agree")
            sys.exit(1)

        self.text_commands = [commands, texts]

    def setCommands(self, commands, functions):
        # List of commands which require advanced functionality
        # Commands should start with '/'
        if len(commands) != len(functions):
            print("Length of command and function lists do not agree")
            sys.exit(1)

        self.commands = [commands, functions]

    def getUpdates(self):
        self.getupdates_offset_url = self.getupdates_url + self.last_update

        self.get_updates = requests.get(self.getupdates_offset_url)
        if self.get_updates.status_code != 200:
            print(self.get_updates.status_code)  # For debugging
            self.updates = ""
        else:
            self.updates = json.loads(self.get_updates.content)["result"]

    def sendMessage(self, chat_id, message):
        self.message = requests.get(self.sendmessage_url + str(chat_id) +
                                    "&text=" + message)

    def sendImage(self, chat_id, image_path):
        data = {"chat_id": str(chat_id)}
        files = {"photo": (image_path, open(image_path, "rb"))}
        requests.post(self.sendimage_url, data=data, files=files)

    def getMessage(self):
        # Group's status messages don't include "text" key
        try:
            self.text = self.item["message"]["text"]
        except KeyError:
            return

        self.chat_id = self.item["message"]["chat"]["id"]
        self.sent = False

        for i in range(0, len(self.commands[0])):
            if self.commands[0][i] in self.text:
                self.commands[1][i](self.item)
                self.sent = True
                break

        if not self.sent:
            for i in range(0, len(self.text_commands[0])):
                if self.text_commands[0][i] in self.text:
                    self.sendMessage(self.chat_id, self.text_commands[1][i])
                    self.sent = True
                    break

        if not self.sent:
            self.sendMessage(self.chat_id, self.unknown_text)

    def start(self):
        signal.signal(signal.SIGTERM, self.stop)

        while True:
            self.getUpdates()
            for self.item in self.updates:
                try:
                    tmp = self.item["message"]
                except KeyError:  # ignore other updates
                    continue

                if self.log_status:  # Store time to log
                    with open(self.log_path, "a") as self.log_file:
                        self.log_file.write(str(time.time()) + "\n")

                self.getMessage()
                time.sleep(self.sleep_time)
                self.last_update = str(self.item["update_id"] + 1)

    def stop(self, signum, frame):
        with open(self.lastupdate_path, "w") as self.last_update_file:
            self.last_update_file.write(self.last_update)
        sys.exit(0)
