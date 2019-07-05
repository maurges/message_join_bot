#!/usr/bin/env python3

"""
Author: d86leader@mail.com, 2019
License: published under GNU GPL-3

Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import logic
import join
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Handler
from telegram import Update

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(bot, update):
    """Send a message when the command /help is issued."""
    message = """
    Hello! I'm a bot created to combat flood in supergroups. I'm a message join bot!
See my github: https://github.com/d86leader/message_join_bot for more info.
If you want to use this bot in your group, please set up your own copy. I'm currently running on {platform}.
    """.format(platform="LG Smart TV")
    update.message.reply_text(message)


def reply(counter, joiner):
    def internal(bot, update):
        decision = counter.decide(update.message)

        if isinstance(decision, logic.DoNothing):
            joiner.cleanup(update.message)
            return
        # otherwise instance is UniteMessages
        user_messages = decision.messages
        decision = joiner.join(user_messages)

        if isinstance(decision, join.SendMessage):
            did_send = bot.send_message(
                    chat_id = decision.chat_id
                    ,text   = decision.text
                    )
            joiner.sent_message(update.message, did_send)
        elif isinstance(decision, join.EditMessage):
            bot.edit_message_text(
                    chat_id     = decision.chat_id
                    ,message_id = decision.message_id
                    ,text       = decision.text
                    )
        # delete user's messages
        for msg in user_messages:
            bot.delete_message(msg.chat.id, msg.message_id)
    return internal


def error(bot, update):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main(token):
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(token)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    # on noncommand i.e message - echo the message on Telegram
    reply_func = reply(logic.MessageCounter(), join.Joiner())
    dp.add_handler(MessageHandler(Filters.text, reply_func))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    with open("token.txt", "r") as tfile:
        token = tfile.read().strip()
    main(token)
