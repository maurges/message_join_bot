#!/usr/bin/env python3

from typing import *
from html import escape
from telegram import Message # type: ignore

"""
Author: d86leader@mail.com, 2019
License: published under GNU GPL-3

Description: routines with joining messages and keeping track of what to put
where. To use this you need to create a joiner instance. After deciding on an
action (with a counter for example) you execute Joiner#join() and it tells you
whether you need to send a new message or edit an existing one.
Important! After sending a message you need to execute Joiner#message_sent()
with the message you have sent and any user message that has triggered you.
Also or on some timer, you should execute Joiner#cleanup() so this won't decide
to join messages to a very old thread.
"""

# complex keys for our tables
UID = NamedTuple("UID", [("chat_id", int)
                        ,("from_id", int)
                        ])
BodyID = NamedTuple("BodyID", [("chat_id", int)
                              ,("text", str)
                              ])
MsgID = NamedTuple("MsgID", [("chat_id", int)
                            ,("msg_id", int)
                            ])
MessageInfo = NamedTuple("MessageInfo",
        [("message_id",   Optional[int])
        ,("current_text", str)
        ])


class Action:
    pass
class SendMessage(Action):
    def __init__(self, chat_id : int, text : str) -> None:
        self.chat_id = chat_id
        self.text = text
class EditMessage(Action):
    def __init__(self, chat_id : int
                     , message_id : int
                     , text : str
                ) -> None:
        self.chat_id = chat_id
        self.message_id = message_id
        self.text = text


class Joiner:
    def __init__(self) -> None:
        self.user_bases: Dict[UID, MessageInfo] = {}
        self.content_bases: Dict[BodyID, MessageInfo] = {}
        self.reply_bases: Dict[MsgID, MessageInfo] = {}

    def join(self, messages_a : List[Message]) -> Action:
        message = messages_a[0]
        messages: Iterator[str] = map(lambda x: x.text, messages_a)

        chat_id = message.chat.id
        from_id = message.from_user.id
        # throws something when fields not present
        user_id = UID(chat_id=chat_id, from_id=from_id)

        if user_id not in self.user_bases:
            author = message.from_user.full_name
            link = message.from_user.link

            text = f"<i><a href=\"{link}\">{author}</a> says:</i>\n"
            text += "\n".join(map(escape, messages))

            self.user_bases[user_id] = MessageInfo(message_id=None
                                                  ,current_text=text
                                                  )
            return SendMessage(chat_id, text)
        else:
            message_id, text = self.user_bases[user_id]
            assert message_id is not None
            if message_id == None:
                raise RuntimeError("Encountered None as message id. Did you forget to call `sent_message`?")

            text += "\n" + "\n".join(map(escape, messages))
            self.user_bases[user_id] = MessageInfo(message_id, text)
            return EditMessage(chat_id, message_id, text)

    def unite_content(self, messages : List[Message]) -> Action:
        message = messages[0]
        chat_id = message.chat_id
        content = message.text
        key = BodyID(chat_id=chat_id, text=content)

        if key not in self.content_bases:
            text = message.text + "\n" + join_signatures(messages)
            self.content_bases[key] = MessageInfo(None, text)
            return SendMessage(chat_id, text)
        else:
            message_id, text = self.content_bases[key]
            assert message_id is not None
            if message_id == None:
                raise RuntimeError("Encountered None as message id. Did you forget to call `sent_message`?")
            text += "\n" + join_signatures(messages)
            self.content_bases[key] = MessageInfo(message_id, text)
            return EditMessage(chat_id, message_id, text)

    def unite_reply(self, messages : List[Message]) -> Action:
        message = messages[0]
        chat_id = message.chat_id
        reply_id = message.reply_to_message.message_id
        key = MsgID(chat_id=chat_id, msg_id=reply_id)

        if key not in self.reply_bases:
            text = join_users_texts(messages)
            self.reply_bases[key] = MessageInfo(None, text)
            return SendMessage(chat_id, text)
        else:
            message_id, text = self.reply_bases[key]
            assert message_id is not None
            if message_id == None:
                raise RuntimeError("Encountered None as message id. Did you forget to call `sent_message`?")
            text += "\n" + join_users_texts(messages)
            self.reply_bases[key] = MessageInfo(message_id, text)
            return EditMessage(chat_id, message_id, text)



    # cleanup when the first unification message was sent
    def sent_message(self, user_message : Message, bot_message : Message) -> None:
        self.sent_message_join(user_message, bot_message)
        self.sent_message_content(user_message, bot_message)
        self.sent_message_reply(user_message, bot_message)

    def sent_message_join(self, user_message : Message, bot_message : Message) -> None:
        chat_id = user_message.chat.id
        from_id = user_message.from_user.id
        user_id = UID(chat_id=chat_id, from_id=from_id)

        if user_id not in self.user_bases:
            return

        # insert the missing message_id which is used fo editing further
        _, text = self.user_bases[user_id]
        self.user_bases[user_id] = MessageInfo(message_id=bot_message.message_id
                                              ,current_text=text
                                              )

    def sent_message_content(self, user_message : Message, bot_message : Message) -> None:
        chat_id = user_message.chat.id
        content = user_message.text
        key = BodyID(chat_id=chat_id, text=content)

        if key not in self.content_bases:
            return

        # insert the missing message_id which is used fo editing further
        _, text = self.content_bases[key]
        self.content_bases[key] = MessageInfo(message_id=bot_message.message_id
                                             ,current_text=text
                                             )

    def sent_message_reply(self, user_message : Message, bot_message : Message) -> None:
        chat_id = user_message.chat.id
        if not user_message.reply_to_message:
            return
        reply_id = user_message.reply_to_message.message_id
        key = MsgID(chat_id=chat_id, msg_id=reply_id)

        if key not in self.reply_bases:
            return

        # insert the missing message_id which is used fo editing further
        _, text = self.reply_bases[key]
        self.reply_bases[key] = MessageInfo(message_id=bot_message.message_id
                                           ,current_text=text
                                           )


    # when user no longer needs joining, cleanup their data from collection
    def cleanup(self, message : Message) -> None:
        chat_id = message.chat.id

        from_id = message.from_user.id
        key1 = UID(chat_id=chat_id, from_id=from_id)
        if key1 in self.user_bases:
            del self.user_bases[key1]

        content = message.text
        key2 = BodyID(chat_id=chat_id, text=content)
        if key2 in self.content_bases:
            del self.content_bases[key2]

        if message.reply_to_message != None:
            reply_id = message.reply_to_message.message_id
            key3 = MsgID(chat_id=chat_id, msg_id=reply_id)
            if key3 in self.reply_bases:
                del self.reply_bases[key3]

def join_signatures(messages: list) -> str:
    "Join as as sign-off of who wrote the messages"
    def format_one(msg) -> str:
        link = msg.from_user.link
        name = msg.from_user.full_name
        return f" - <i><a href=\"{link}\">{name}</a></i>"
    return "\n".join(map(format_one, messages))


def join_users_texts(messages: list) -> str:
    "Join messages from different users prettily"
    def format_one(msg) -> str:
        link = msg.from_user.link
        name = msg.from_user.full_name
        text = msg.text
        if len(msg.text) > 32:
            text = msg.text[:32] + "..."
        text = escape(text)
        return f"<i><a href=\"{link}\">{name}</a></i>: {text}"
    return "\n".join(map(format_one, messages))
