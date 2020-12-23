import datetime
import re
import os
import shelve

# How many times the user can postpone a shutdown
INITIAL_POSTPONES = 1

data = shelve.open("data")
KEY_scheduledShutdown = 'scheduledShutdown'
KEY_remainingPostpones = 'remainingPostpones'
# Reset the number of remaining/available delays if eligible
if not data.get(KEY_scheduledShutdown) or data[KEY_scheduledShutdown] < datetime.datetime.now():
    data[KEY_remainingPostpones] = INITIAL_POSTPONES

os.system("title Shutdown Scheduler")


def get_shutdown_string(eventTime):
    if not eventTime or eventTime < datetime.datetime.now():
        return ""
    delta = eventTime - datetime.datetime.now()
    deltaString = ""
    if delta.seconds >= 3600:
        deltaString += str(delta.seconds // 3600) + "h "
    if (delta.seconds % 3600) >= 60:
        deltaString += str((delta.seconds % 3600) // 60) + "m "
    deltaString += str(delta.seconds % 60) + "s"
    return f"Shutdown scheduled for {eventTime.hour if eventTime.hour <= 12 else eventTime.hour - 12}:{eventTime:%M:%S %p} " \
           f"(in {deltaString}). "


print(f"""
********************* Shutdown Scheduler *********************
 Enter a time or countdown duration in which to shutdown. 
 Examples:
      Time: 10:00PM, 10PM, 10 pm, 10p, 10:00 (12-hour format)
      Duration: 0h15m, 15m, 15
 {get_shutdown_string(data.get(KEY_scheduledShutdown))}Remaining postpones: {data[KEY_remainingPostpones]}     
      """)


def infer_a_or_p(hour, minute):
    now = datetime.datetime.now()
    current_minute = now.minute
    current_hour_24h = now.hour
    current_hour_12h = current_hour_24h % 12  # This makes noon and midnight 0, but thats fine for sake of computation here
    hour = hour % 12  # we mod the input hour as well for consistency

    if hour > current_hour_12h or (hour == current_hour_12h and minute > now.minute):
        # e.g. now is 5pm, time is 6 ---> 6 pm.
        # return current/unchanged a/p
        return 'p' if current_hour_24h >= 12 else 'a'
    else:  # e.g. now is 5pm, time is 4 ---> 4am
        # invert current a/p
        return 'a' if current_hour_24h >= 12 else 'p'


sec = 0
while sec == 0:
    command = re.sub(r'[^0-9padhms:]', '', input("> "), re.IGNORECASE).lower()  # Remove random characters & make lowercase

    if m := re.match(r'^((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?$', command):  # duration
        sec = int(m.group("days") or 0) * 24 * 3600 \
              + int(m.group("hours") or 0) * 3600 \
              + int(m.group("minutes") or 0) * 60 \
              + int(m.group("seconds") or 0)

    elif m := re.match(r'^(\d+)$', command): # minutes only duration (e.g. "5")
        sec = int(m.group(1)) * 60

    elif m := re.match(r'^(?P<hour>\d{1,2}):?(?P<minute>\d{1,2})?((?P<a_or_p>[ap])m?)?$', command):
        __raw_hour_12h = int(m.group("hour"))
        if __raw_hour_12h > 12 or __raw_hour_12h < 1:
            print("Please enter the target time in 12-hour format.")
            continue
        minute = int(m.group("minute") or 0)

        a_or_p = m.group('a_or_p') or infer_a_or_p(__raw_hour_12h, minute)

        hour_24h = (__raw_hour_12h % 12 if a_or_p == 'a' else (__raw_hour_12h % 12) + 12) % 24

        current_hour_24h = datetime.datetime.now().hour % 24
        current_minute = datetime.datetime.now().minute

        sec = (3600 * (hour_24h - current_hour_24h) + 60 * (minute - current_minute)) % (3600 * 24)
        sec -= datetime.datetime.now().second

    if sec == 0:
        print("Error: please enter a valid 12-hour time or duration")
        continue

    delta = datetime.timedelta(seconds=sec)
    eventTime = datetime.datetime.now() + delta

    if data.get(KEY_scheduledShutdown) and eventTime > data[KEY_scheduledShutdown]:  # if postponing a shutdown
        if data[KEY_remainingPostpones] <= 0:
            print("Error: No postpones remaining.")
            continue
        else:
            data[KEY_remainingPostpones] = data[KEY_remainingPostpones] - 1

    os.system("shutdown /a 2> nul")

    data[KEY_scheduledShutdown] = eventTime
    print(f"{get_shutdown_string(eventTime)} Press any key to exit.")

    os.system(f"shutdown /s /t {sec}")
    os.system("pause > nul")
