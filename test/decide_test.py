#!/usr/bin/env python3

import logic
import unittest
from typing import *

import random
from datetime import datetime, timedelta
from copy import deepcopy

def rand_time(delta : int) -> datetime:
    seconds = random.randint(0, delta)
    return datetime.utcnow() - timedelta(seconds=seconds)

class SimpleMessage:
    class HasId:
        def __init__(self, id):
            self.id = id

    def __init__(self, chat_id : int, user_id : int, time : datetime) -> None:
        self.chat = SimpleMessage.HasId(chat_id)
        self.from_user = SimpleMessage.HasId(user_id)
        self.date = time

    @staticmethod
    def gen() -> 'SimpleMessage':
        chat_id = random.randint(0, 1<<63)
        user_id = random.randint(0, 1<<63)
        time = rand_time(10)
        return SimpleMessage(chat_id, user_id, time)


class TestDecide(unittest.TestCase):

    def test_returns_nothing(self):
        counter = logic.MessageCounter()

        msg = SimpleMessage.gen()
        r = counter.decide(msg)
        self.assertIsInstance(r, logic.DoNothing)

        msg.chat.id += 1
        r = counter.decide(msg)
        self.assertIsInstance(r, logic.DoNothing)

        msg.from_user.id += 1
        r = counter.decide(msg)
        self.assertIsInstance(r, logic.DoNothing)

    def test_inserts_after_five(self):
        counter = logic.MessageCounter()

        msg = SimpleMessage.gen()
        for _ in range(logic.MessageThreshold):
            r = counter.decide(msg)
            msg.date += logic.DelayDelete * 0.2

        self.assertIsInstance(r, logic.UniteMessages)
        sources = r.messages
        self.assertEqual(len(sources), logic.MessageThreshold)

        # insert one more after threshold
        r = counter.decide(msg)
        self.assertIsInstance(r, logic.UniteMessages)
        sources = r.messages
        self.assertEqual(len(sources), 1)

        # insert a later message
        msg.date += logic.DelayRelease * 1.2
        r = counter.decide(msg)
        self.assertIsInstance(r, logic.DoNothing)

    def test_no_joining_separated(self):
        counter = logic.MessageCounter()

        msg = SimpleMessage.gen()
        for _ in range(logic.MessageThreshold):
            r = counter.decide(msg)
            self.assertIsInstance(r, logic.DoNothing)

            msg.date += logic.DelayDelete * 0.25


if __name__ == '__main__':
    unittest.main()
