from threading import Thread
from time import sleep
from pymongo import MongoClient
import telebot
import config
import utils
import answers

bot = telebot.TeleBot(config.bot_token)
polling = Thread(target=bot.polling, kwargs={"none_stop": True, "interval": 1})
client = MongoClient(config.MONGO_HOST, config.MONGO_PORT)
db = client[config.MONGO_DB]


def notify_all_users(notification: str):
    for user in db.users.find():
        bot.send_message(user['user_id'], notification)
        sleep(0.04)  # to avoid telegram bot API limitations


@bot.message_handler(commands=['start'])
def init_user(message):
    if utils.is_entries_in_collection(db.users, {'user_id': message.from_user.id}):
        return

    name = utils.get_connected_name(message.from_user)
    is_admin = not utils.is_entries_in_collection(db.users)

    db.users.insert({
        'name': name,
        'user_id': message.from_user.id,
        'room': 0,
        'is_admin': is_admin,
        'achievements': []
    })

    bot.send_message(message.from_user.id, answers.WELCOME)


@bot.message_handler(commands=['alert'])
def alert(message):
    if not utils.is_user_admin(db.users, message.from_user):
        bot.send_message(message.from_user.id, answers.PERMISSION_DENIED)
        return

    msg_splitted = message.text.split(maxsplit=1)
    if len(msg_splitted) != 2:
        return

    notify_all_users(msg_splitted[1])


@bot.message_handler(commands=['achievements'])
def handle_achivements(message):
    splitted_msg = message.text.split(maxsplit=2)

    if len(splitted_msg) == 1:
        achievements = utils.get_user_achievements(db.users, message.from_user)
        if len(achievements) == 0:
            bot.send_message(message.from_user.id, answers.ACHIEVEMENT_NODATA)
            return

        bot.send_message(message.from_user.id, achievements)
        return

    if len(splitted_msg) == 3 and splitted_msg[1] == "add":
        if not utils.is_user_admin(db.users, message.from_user):
            bot.send_message(message.from_user.id, answers.PERMISSION_DENIED)
            return

        if not utils.is_valid_achievement_set(db.users, splitted_msg[2]):
            bot.send_message(message.from_user.id, answers.ACHIEVEMENT_SET_INVALID)
            return

        name, achievement = splitted_msg[2].split(":")
        name = name.strip()
        achievement = achievement.strip()

        db.users.update_one(
            {'name': name},
            {'$push': {'achievements': achievement}}
        )
        notify_all_users("{} {} \"{}\"!".format(name, answers.NEW_ACHIEVEMENT_NOTIFICATION, achievement))


@bot.message_handler(commands=['setroom'])
def setroom(message):
    splitted = message.text.split(maxsplit=1)
    if len(splitted) != 2:
        bot.send_message(message.from_user.id, answers.ROOM_SET_INVALID)
        return

    db.users.update_one(
        {'user_id': message.from_user.id},
        {'$set': {'room': splitted[1]}}
    )
    bot.send_message(message.from_user.id, "{} {}".format(answers.ROOM_SET_SUCCESS, splitted[1]))


@bot.message_handler(commands=['getroom'])
def getroom(message):
    splitted = message.text.split(maxsplit=1)
    if len(splitted) != 2:
        bot.send_message(message.from_user.id, answers.ROOM_GET_INVALID)
        return

    if not utils.is_entries_in_collection(db.users, {'name': splitted[1]}):
        bot.send_message(message.from_user.id, answers.ROOM_GET_USER_NOT_EXIST)
        return

    bot.send_message(message.from_user.id, db.users.find_one({'name': splitted[1]})['room'])


@bot.message_handler(commands=['setinfo'])
def set_info(message):
    if not utils.is_user_admin(db.users, message.from_user):
        bot.send_message(message.from_user.id, answers.PERMISSION_DENIED)
        return

    splitted = message.text.split(maxsplit=1)
    if len(splitted) != 2:
        bot.send_message(message.from_user.id, answers.INFO_SET_INVALID)
        return

    if db.info.find().count() == 0:
        db.info.insert_one({'info': splitted[1]})
        bot.send_message(message.from_user.id, answers.INFO_SET_SUCCESS)
        return

    db.info.update_one(
        {},
        {'$set': {'info': splitted[1]}}
    )

    bot.send_message(message.from_user.id, answers.INFO_SET_SUCCESS)


@bot.message_handler(commands=['getinfo'])
def send_info(message):
    bot.send_message(message.from_user.id, db.info.find_one()['info'])


@bot.message_handler(commands=['setschedule'])
def set_schedule(message):
    if not utils.is_user_admin(db.users, message.from_user):
        bot.send_message(message.from_user.id, answers.PERMISSION_DENIED)
        return

    splitted = message.text.split(maxsplit=1)

    if len(splitted) != 2:
        bot.send_message(message.from_user.id, answers.SCHEDULE_SET_INVALID)
        return

    text_schedule = splitted[1].split("\n")
    db.drop_collection('schedule')

    for event in text_schedule:
        if utils.is_valid_event(event):
            splitted_event = event.split(maxsplit=1)
            hours, minutes = splitted_event[0].split(":")
            event_name = splitted_event[1]
            db.schedule.insert({
                'hours': int(hours),
                'minutes': int(minutes),
                'name': event_name
            })

    bot.send_message(message.from_user.id, answers.SCHEDULE_SET_SUCCESS)


@bot.message_handler(commands=['getschedule'])
def get_schedule(message):
    schedule = utils.get_schedule_text_from_collection(db.schedule)
    bot.send_message(message.chat.id, schedule)


if __name__ == '__main__':
    polling.start()
