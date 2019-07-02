#!/usr/bin/env python3

from typing import *
from collections import namedtuple
from datetime import datetime
from SortedCollection import SortedCollection


UID = namedtuple("UID", ["chat_id", "from_id"])

MessageQueue = Dict[UID, SortedCollection]


# actions returned to caller:
class Action:
    pass
class DoNothing(Action):
    pass
class Waited(Action):
    def __init__(self, seconds, messages):
        self.seconds = seconds
        self.messages = messages


class MessageCounter:
    def __init__(self, base_queue : MessageQueue = {}) -> None:
        self.msg_queue = base_queue

    def decide(self, message) -> Action:
        chat_id = message.chat.id
        from_id = message.from_user.id
        time    = message.date
        if not chat_id or not from_id or not time:
            return DoNothing()
        user_id = UID(chat_id=chat_id, from_id=from_id)
        #
        if user_id not in self.msg_queue:
            self.msg_queue[user_id] = SortedCollection([time])
            return DoNothing()
        #
        oldest = self.msg_queue[user_id][0]
        self.msg_queue[user_id].insert(time)
        diff = time - oldest
        message_amount = len(self.msg_queue[user_id])
        #
        return Waited(diff.seconds, message_amount)
