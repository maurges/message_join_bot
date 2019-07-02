#!/usr/bin/env python3

from typing import *
from collections import namedtuple
from datetime import datetime, timedelta
from sortedcollection import SortedCollection

"""
Description: a class to decide when to delete which messages.
The rule to delete is simple: if in 5 seconds we received 5 messages,
delete and join them into one new message. Then each new messages from the same
user will be appended to the message. This stops if the user hasn't sent
anything in last 5 seconds.

Usage: create an instance of MessageCounter and call decide() method,
and it will tell you what to do. The method is highly stateful. It's best if
it's called on all arriving messages.
"""


DelayDelete = timedelta(seconds=5)
DelayRelease = timedelta(seconds=5)
MessageThreshold = 5


# For each user in chat we keep their status
class UserStatus:
    def update(self, message) -> 'UserStatus':
        return self
    def is_strict(self) -> bool:
        return False
    def is_lax(self) -> bool:
        return True

class UserLax(UserStatus):
    "User allowed to post messages"
    "This carries a payload of recent posted messages"

    def __init__(self, initial_message):
        self.queue = new_queue(initial_message)

    def update(self, message) -> UserStatus:
        # insert the new message
        self.queue.insert(message)

        # drop all old messages
        latest_time = self.queue[-1].date
        threshold_time = latest_time - DelayDelete

        while self.queue[0].date > threshold_time:
            self.queue.drop_index(0)

        # if the queue has too much late messages
        if len(self.queue) > MessageThreshold:
            # we return a new status
            return UserStrict(self.queue[-1])
        else:
            return self

    def is_lax(self) -> bool:
        return True

class UserStrict(UserStatus):
    "User has their messages instantly deleted"
    "Payload is time when to stop deletion"

    def __init__(self, initial_message):
        self.base_message = initial_message
        self.stop_time = message.date + DelayRelease

    def update(self, message) -> UserStatus:
        # update stop time
        stop_time = self.stop_time
        self.stop_time = max(self.stop_time, message.date + DelayRelease)

        if message.date <= stop_time:
            # still should delete the message
            return self
        else:
            return UserLax(message)



    def is_strict(self) -> bool:
        return True


# a complex key for our table
UID = namedtuple("UID", ["chat_id", "from_id"])
# telegram messages are not comparable, so we compare them
# on their date with key function. This is a function
# to create a correct collection
def new_queue(item):
    key = lambda x: x.date
    return SortedCollection([item], key)

UserCollection = Dict[UID, UserStatus]


# actions returned to caller:
class Action:
    pass
class DoNothing(Action):
    pass
class InsertInto(Action):
    def __init__(self, receiver, source):
        self.receiver = receiver
        self.source = source


class MessageCounter:
    def __init__(self, base_queue : UserCollection = {}) -> None:
        self.msg_queue = base_queue

    def decide(self, message) -> Action:
        chat_id = message.chat.id
        from_id = message.from_user.id
        time    = message.date
        if not chat_id or not from_id or not time:
            return DoNothing()

        user_id = UID(chat_id=chat_id, from_id=from_id)

        if user_id not in self.msg_queue:
            self.msg_queue[user_id] = UserLax(message)
            return DoNothing()

        new_status = self.msg_queue[user_id].update(message)
        self.msg_queue[user_id] = new_status

        if new_status.is_lax():
            return DoNothing()
        elif isinstance(new_status, UserStrict):
            return InsertInto(new_status.base_message, message)
        else:
            return DoNothing()
