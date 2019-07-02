#!/usr/bin/env python3

"""
Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import logic
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Handler
from telegram import Update

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

def describe(obj):
    print(f"type: {type(obj)}")
    print(f"dir: {dir(obj)}")


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(bot, update):
    """Send a message when the command /describe is issued."""
    update.message.reply_text('describe!')


def reply(counter):
    def internal(bot, update):
        decision = counter.decide(update.message)

        message = ""
        if isinstance(decision, logic.DoNothing):
            message = "nothing"
        elif isinstance(decision, logic.Waited):
            message = (f"waited {decision.seconds} seconds" +
                       f" for {decision.messages} messages")

        update.message.reply_text(message)
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
    dp.add_handler(MessageHandler(Filters.text, reply(logic.MessageCounter())))

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
