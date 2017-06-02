from pymongo.collection import Collection
from pymongo import ASCENDING
from telebot.types import User


def get_connected_name(user: User) -> str:
    if user.last_name is not None:
        return "{} {}".format(user.first_name,
                              user.last_name)

    return user.first_name


def is_entries_in_collection(col: Collection, find_filter=None) -> bool:
    if find_filter is None:
        find_filter = {}
    return col.find(find_filter).count() > 0


def get_user_achievements(users_col: Collection, user: User) -> str:
    result = ''
    for achievement in users_col.find_one({'user_id': user.id})['achievements']:
        result += achievement
        result += "\n"

    return result.strip()


def is_user_admin(user_col: Collection, user: User) -> bool:
    return user_col.find_one({'user_id': user.id})['is_admin']


def is_valid_achievement_set(user_col: Collection, set_body: str) -> bool:
    splitted = set_body.split(":")
    if len(splitted) != 2:
        return False

    return user_col.find_one({'name': splitted[0]}) is not None


def is_valid_event(event: str) -> bool:
    splitted = event.split(maxsplit=1)

    if len(splitted) != 2 or len(splitted[0].split(":")) != 2:
        return False

    time = splitted[0].split(":")

    try:
        int(time[0])
        int(time[1])
    except Exception:
        return False

    return True


def get_schedule_text_from_collection(schedule_col: Collection) -> str:
    result = ''
    for event in schedule_col.find().sort([('hours', ASCENDING), ('minutes', ASCENDING)]):
        minutes = str(event['minutes'])
        if len(minutes) < 2:
            minutes = "0" + minutes

        result += "{}:{} {}\n".format(event['hours'], minutes, event['name'])

    return result.strip()
