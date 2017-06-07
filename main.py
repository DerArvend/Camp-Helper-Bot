from threading import Thread
from time import sleep
from pymongo import MongoClient
import telebot
import config
from utils import *
import answers

bot = telebot.TeleBot(config.bot_token)
polling = Thread(target=bot.polling, kwargs={"none_stop": True, "interval": 1})
client = MongoClient(config.MONGO_HOST, config.MONGO_PORT)
db = client[config.MONGO_DB]


@bot.message_handler(commands=['start'])
def init_user(message):
    if is_entries_in_collection(db.users, {'user_id': message.from_user.id}):
        return

    name = get_connected_name(message.from_user)
    is_admin = not is_entries_in_collection(db.users)

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
    if not is_valid_command(db, message, admin_only=True, command_length=2):
        return

    alert_text = message.text.split(maxsplit=1)[1]

    notify_all_users(db.users, bot, alert_text)


@bot.message_handler(commands=['achievements'])
def handle_achivements(message):
    splitted_msg = message.text.split(maxsplit=2)

    if len(splitted_msg) == 1:
        achievements = get_user_achievements(db.users, message.from_user)
        if len(achievements) == 0:
            bot.send_message(message.from_user.id, answers.ACHIEVEMENT_NODATA)
            return

        bot.send_message(message.from_user.id, achievements)
        return

    if len(splitted_msg) == 3 and splitted_msg[1] == "add":
        if not is_user_admin(db.users, message.from_user):
            bot.send_message(message.from_user.id, answers.PERMISSION_DENIED)
            return

        if not is_valid_achievement_set(db.users, splitted_msg[2]):
            bot.send_message(message.from_user.id, answers.ACHIEVEMENT_SET_INVALID)
            return

        name, achievement = splitted_msg[2].split(":")
        name = name.strip()
        achievement = achievement.strip()

        db.users.update_one(
            {'name': name},
            {'$push': {'achievements': achievement}}
        )
        notify_all_users(db.users, bot, "{} {} \"{}\"!".format(name, answers.NEW_ACHIEVEMENT_NOTIFICATION, achievement))


@bot.message_handler(commands=['setroom'])
def setroom(message):
    if not is_valid_command(db, message, command_length=2):
        return
    room = message.text.split(maxsplit=1)[1]

    db.users.update_one(
        {'user_id': message.from_user.id},
        {'$set': {'room': room}}
    )
    bot.send_message(message.from_user.id, "{} {}".format(answers.ROOM_SET_SUCCESS, room))


@bot.message_handler(commands=['getroom'])
def getroom(message):
    if not is_valid_command(db, message, command_length=2):
        return

    username = message.text.split(maxsplit=1)[1]

    if not is_entries_in_collection(db.users, {'name': username}):
        bot.send_message(message.from_user.id, answers.ROOM_GET_USER_NOT_EXIST)
        return

    bot.send_message(message.from_user.id, db.users.find_one({'name': username})['room'])


@bot.message_handler(commands=['setinfo'])
def set_info(message):
    if not is_valid_command(db, message, admin_only=True, command_length=2):
        return

    info = message.text.split(maxsplit=1)[1]

    if db.info.find().count() == 0:
        db.info.insert_one({'info': info})
        bot.send_message(message.from_user.id, answers.INFO_SET_SUCCESS)
        return

    db.info.update_one(
        {},
        {'$set': {'info': info}}
    )

    bot.send_message(message.from_user.id, answers.INFO_SET_SUCCESS)


@bot.message_handler(commands=['getinfo'])
def send_info(message):
    bot.send_message(message.from_user.id, db.info.find_one()['info'])


@bot.message_handler(commands=['setschedule'])
def set_schedule(message):
    if not is_valid_command(db, message, admin_only=True, command_length=2):
        return

    text_schedule = message.text.split(maxsplit=1)[1]
    splitted_text_schedule = text_schedule.split("\n")
    db.drop_collection('schedule')

    for event in splitted_text_schedule:
        if is_valid_event(event):
            splitted_event = event.split(maxsplit=1)
            hours, minutes = splitted_event[0].split(":")
            event_name = splitted_event[1]
            db.schedule.insert({
                'hours': int(hours),
                'minutes': int(minutes),
                'name': event_name
            })

    bot.send_message(message.from_user.id, answers.SCHEDULE_SET_SUCCESS)
    notify_all_users(db.users, bot, "{}\n{}".format(answers.NEW_SCHEDULE, text_schedule))


@bot.message_handler(commands=['getschedule'])
def get_schedule(message):
    schedule = get_schedule_text_from_collection(db.schedule)
    bot.send_message(message.from_user.id, schedule)


@bot.message_handler(commands=['users'])
def get_users(message):
    users_text = ''
    for user in db.users.find():
        users_text += user['name']
        users_text += "\n"
    bot.send_message(message.from_user.id, users_text)


@bot.message_handler(commands=['admin'])
def set_admin(message):
    if not is_valid_command(db, message, admin_only=True, command_length=3):
        return

    option, username = message.text.split(maxsplit=2)[1:]
    if option != "set" and option != "unset":
        bot.send_message(message.from_user.id, answers.ADMIN_SET_FAIL)

    operation_type = {'set': True, 'unset': False}[option]

    if not is_entries_in_collection(db.users, {'name': username}):
        bot.send_message(message.from_user.id, answers.USER_NOT_FOUND)

    db.users.update_one(
        {'name': username},
        {'$set': {'is_admin': operation_type}}
    )

    bot.send_message(message.from_user.id, answers.ADMIN_SET_SUCCESS)


if __name__ == '__main__':
    polling.start()
