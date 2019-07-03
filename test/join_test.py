#!/usr/bin/env python3

"""
Author: d86leader@mail.com, 2019
License: published under GNU GPL-3
"""

import join
import unittest
from typing import *

import random
from copy import deepcopy

class SimpleMessage:
    class HasId:
        def __init__(self, id):
            self.id = id
    class HasIdName:
        def __init__(self, id, name : str) -> None:
            self.id = id
            self.first_name = name
            self.last_name = None

    def __init__(self, chat_id : int, user_id : int
                ,text : str, message_id : int
                ,name : str
                ) -> None:
        self.chat = SimpleMessage.HasId(chat_id)
        self.from_user = SimpleMessage.HasIdName(user_id, name)
        self.text = text
        self.message_id = message_id

    @staticmethod
    def gen() -> 'SimpleMessage':
        chat_id = random.randint(0, 1<<63)
        user_id = random.randint(0, 1<<63)
        message_id = random.randint(0, 1<<63)
        time = "textity text"
        name = "mcnamelton"
        return SimpleMessage(chat_id, user_id, time, message_id, name)


class TestJoin(unittest.TestCase):

    def test_first_join_sends(self):
        joiner = join.Joiner()
        msg = SimpleMessage.gen()

        r = joiner.join([msg] * 4)
        self.assertIsInstance(r, join.SendMessage)

    def test_keeps_base(self):
        joiner = join.Joiner()
        msg = SimpleMessage.gen()
        sent_msg = SimpleMessage.gen()
        sent_msg.chat.id = msg.chat.id

        r = joiner.join([msg]*4)
        self.assertIsInstance(r, join.SendMessage)
        joiner.sent_message(msg, sent_msg)

        r = joiner.join([msg]*2)
        self.assertIsInstance(r, join.EditMessage)
        self.assertEqual(sent_msg.message_id, r.message_id)

    def test_resets_base(self):
        joiner = join.Joiner()
        msg = SimpleMessage.gen()
        sent_msg1 = SimpleMessage.gen()
        sent_msg2 = SimpleMessage.gen()
        sent_msg1.chat.id = msg.chat.id
        sent_msg2.chat.id = msg.chat.id

        r = joiner.join([msg]*4)
        self.assertIsInstance(r, join.SendMessage)
        joiner.sent_message(msg, sent_msg1)
        joiner.cleanup(msg)

        r = joiner.join([msg]*4)
        self.assertIsInstance(r, join.SendMessage)
        joiner.sent_message(msg, sent_msg2)

        r = joiner.join([msg]*2)
        self.assertIsInstance(r, join.EditMessage)
        self.assertEqual(sent_msg2.message_id, r.message_id)


if __name__ == '__main__':
    unittest.main()

