#!/usr/bin/env python3

from typing import *
from collections import namedtuple
from datetime import datetime, timedelta
from sortedcollection import SortedCollection
from copy import copy
from abc import ABC, abstractmethod

"""
Author: d86leader@mail.com, 2019
License: published under GNU GPL-3

Description: a class to decide when to delete which messages.
The rule to delete is simple: if in 15 seconds we received 5 messages,
delete and join them into one new message. Then each new messages from the same
user will be appended to the message. This stops if the user hasn't sent
anything in last 10 seconds.

Usage: create an instance of MessageCounter and call decide() method,
and it will tell you what to do. The method is highly stateful. It's best if
it's called on all arriving messages.
"""


DelayDelete = timedelta(seconds=15)
DelayRelease = timedelta(seconds=10)
MessageThreshold = 5
ContentMaxLength = 32


# actions returned to caller:
class Action(ABC):
    pass
class DoNothing(Action):
    pass
class JoinUserMessages(Action):
    "Join multiple messages of single user"
    def __init__(self, sources : list): # list of telegram messages
        self.messages = sources
class UniteMessagesContent(Action):
    "Unite identical messages of multiple users"
    def __init__(self, sources : list): # list of telegram messages
        self.messages = sources
class UniteMessagesReply(Action):
    "Unite messages of multiple users based on what they replied to"
    def __init__(self, sources : list): # list of telegram messages
        self.messages = sources


class IMessageCounter(ABC):
    "What you use to decide if messages should be joined"
    @abstractmethod
    def decide(self, message) -> Action:
        ...

class MessageCounter(IMessageCounter):
    "Aggregate of multiple counters. What you want to use in main code"
    counters : List[IMessageCounter]
    def __init__(self):
        self.counters = [ UserMessageCounter()
                        , ContentMessageCounter()
                        ]

    def decide(self, message) -> Action:
        if message == None:
            print("wut")
        for counter in self.counters:
            decision = counter.decide(message)
            if not isinstance(decision, DoNothing):
                return decision
        return DoNothing()

# telegram messages are not comparable, so we compare them
# on their date with key function. This is a function
# to create a correct collection
def new_queue(item):
    key = lambda x: x.date
    return SortedCollection([item], key)

# For each user/message in chat we keep their status
class AbstractStatus(ABC):
    def update(self, message) -> 'AbstractStatus':
        return self
    def is_strict(self) -> bool:
        return False
    def is_lax(self) -> bool:
        return False

class StatusLax(AbstractStatus):
    "User allowed to post messages"
    "This carries a payload of recent posted messages"

    def __init__(self, initial_message):
        self.queue = new_queue(copy(initial_message))

    def update(self, message) -> AbstractStatus:
        # insert the new message
        self.queue.insert(copy(message))

        # drop all old messages
        latest_time = self.queue[-1].date
        threshold_time = latest_time - DelayDelete

        while len(self.queue) > 0 and self.queue[0].date <= threshold_time:
            self.queue.drop_index(0)

        # if the queue has too much late messages
        if len(self.queue) >= MessageThreshold:
            # we return a new status
            return StatusSwitching(self.queue)
        else:
            return self

    def is_lax(self) -> bool:
        return True

class StatusSwitching(AbstractStatus):
    "When switching from lax to strict"
    "Payload is recently posted messages to be united"

    def __init__(self, messages):
        self.messages = messages

    def update(self, message) -> AbstractStatus:
        # compute stop time for strict status
        stop_time = max(map(lambda x: x.date, self.messages)) + DelayRelease

        if message.date <= stop_time:
            # switch completely to strict mode
            stop_time = max(stop_time, message.date + DelayRelease)
            return StatusStrict(stop_time)
        else:
            return StatusLax(message)

    def is_strict(self) -> bool:
        return True

class StatusStrict(AbstractStatus):
    "User has their messages instantly deleted"
    "Payload is time when to stop deletion"

    def __init__(self, stop_time):
        self.stop_time = stop_time

    def update(self, message) -> AbstractStatus:
        # update stop time
        stop_time = self.stop_time
        self.stop_time = max(self.stop_time, message.date + DelayRelease)

        if message.date <= stop_time:
            # still should delete the message
            return self
        else:
            return StatusLax(message)

    def is_strict(self) -> bool:
        return True

def is_forwarded(msg) -> bool:
    return ( msg.forward_from != None
          or msg.forward_from_chat != None
          or msg.forward_from_message_id != None
          or msg.forward_signature != None
          or msg.forward_date != None
           )


##### UserMessageCounter implementation #####


# a complex key for our table
UID = NamedTuple("UID", [("chat_id", int)
                        ,("from_id", int)
                        ])

UserCollection = Dict[UID, AbstractStatus]

class UserMessageCounter(IMessageCounter):
    def __init__(self, base_queue : UserCollection = {}) -> None:
        self.msg_queue = base_queue

    def decide(self, message) -> Action:
        chat_id = message.chat.id
        from_id = message.from_user.id
        time    = message.date
        if not chat_id or not from_id or not time:
            return DoNothing()
        if is_forwarded(message):
            # don't join forwared messages, there may be many and it's ok
            return DoNothing()

        user_id = UID(chat_id=chat_id, from_id=from_id)

        if user_id not in self.msg_queue:
            self.msg_queue[user_id] = StatusLax(message)
            return DoNothing()

        new_status = self.msg_queue[user_id].update(message)
        self.msg_queue[user_id] = new_status

        if new_status.is_lax():
            return DoNothing()

        if isinstance(new_status, StatusSwitching):
            return JoinUserMessages(new_status.messages)
            # messages contains even the new message, no need to manually add
            # it to insertion list
        elif isinstance(new_status, StatusStrict):
            return JoinUserMessages([message])
        else:
            # this is impossible state, but type checker doesn't know that
            return DoNothing()


##### ContentMessageCounter implementation #####


# a complex key for our table
MsgID = NamedTuple("UID", [("chat_id", int)
                          ,("content", str) # keep shorter
                          ])

MessageCollection = Dict[MsgID, AbstractStatus]

class ContentMessageCounter(ABC):
    def __init__(self, base_queue : MessageCollection = {}) -> None:
        self.msg_queue = base_queue

    def decide(self, message) -> Action:
        chat_id = message.chat.id
        text    = message.text
        time    = message.date

        if not chat_id or not text or not time:
            return DoNothing()
        if is_forwarded(message):
            # don't join forwared messages, there may be many and it's ok
            return DoNothing()
        if len(text) > ContentMaxLength:
            # ignore messages that are too long. For memory's sake
            return DoNothing()

        msg_id = MsgID(chat_id = chat_id, content = text)

        if msg_id not in self.msg_queue:
            self.msg_queue[msg_id] = StatusLax(message)
            return DoNothing()

        new_status = self.msg_queue[msg_id].update(message)
        self.msg_queue[msg_id] = new_status

        if new_status.is_lax():
            return DoNothing()

        if isinstance(new_status, StatusSwitching):
            return UniteMessagesContent(new_status.messages)
            # messages contains even the new message, no need to manually add
            # it to insertion list
        elif isinstance(new_status, StatusStrict):
            return UniteMessagesContent([message])
        else:
            # this is impossible state, but type checker doesn't know that
            return DoNothing()
