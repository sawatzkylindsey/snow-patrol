
from argparse import ArgumentParser
from darksky.api import DarkSky
from darksky.types import languages, units, weather
import datetime as dt
import logging
import os
import pytz
import random
import requests
import sys
import time
import traceback

from pytils.log import setup_logging, teardown, user_log

import model

TIME_ZONE = pytz.timezone("America/Vancouver")

# Long polling time maximum of every 6 hours -> 4 times a day.
LONG_POLL = dt.timedelta(hours=1)
SNOW_POLL = dt.timedelta(minutes=10)
SNOW_THRESHOLD = dt.timedelta(minutes=5)
EMPTY_DURATION = dt.timedelta()
CONNECTION_WAIT = dt.timedelta(minutes=5)

INITIAL_SNOWING_MESSAGE = "Congratulations %s, it's FINALLY snowing!  Expecting ~%.2fcm"
ALREADY_SNOWING_MESSAGES = [
    "What a day - still snowing!",
    "Snow is pure bliss.",
    "Yes, snowing is nigh!",
    "Suck it sun, its time for SNOW!",
]
NOT_SNOWING_MESSAGES = [
    "We should move to Anchorage..",
]

ARTIFICIAL_SNOW_POINT = model.ArtificialPoint(0.9, 0.5, "snow", 1.2)


@teardown
def main(argv):
    ap = ArgumentParser(prog="snow-patrol daemon")
    ap.add_argument("-v", "--verbose", default=False, action="store_true", help="Turn on verbose logging.")
    ap.add_argument("config_path")
    aargs = ap.parse_args(argv)
    setup_logging(".%s.log" % os.path.splitext(os.path.basename(__file__))[0], aargs.verbose, False, True, True)
    config = model.load(aargs.config_path)
    logging.debug("Running under: %s" % config)
    run_continuously(config)
    return 0


def run_continuously(config):
    #thestorm = dt.datetime(2020, 1, 12, 8)
    #thestorm.isoformat()
    darksky = DarkSky(config.darksky_key)
    already_snowing = False

    while True:
        now = dt.datetime.now(TIME_ZONE)
        forecast = get_forecast(darksky, config)
        snow_event = next_snowfall(forecast)

        if snow_event is None:
            # We don't have a clue when the next snowfall may be
            next_poll = LONG_POLL
            already_snowing = False
        else:
            if snow_event.time >= now:
                # The next snowfall is at some point in the future (or right this moment).
                duration_estimate = snow_event.time - now
            else:
                # This is a historical query - pretend now is the predicted time point.
                duration_estimate = EMPTY_DURATION

            if duration_estimate < SNOW_THRESHOLD:
                user_log.info("It's snowing in %s!" % config.location)
                send_message(snow_event.accumulation, already_snowing, config)
                next_poll = SNOW_POLL
                already_snowing = True
            else:
                if already_snowing:
                    user_log.info("Stopped")

                already_snowing = False

                if duration_estimate > LONG_POLL:
                    # If the next predicted snowfall is too far in the future, cap it off at the long poll duration.
                    next_poll = LONG_POLL
                else:
                    estimate = dt.timedelta(seconds=int(duration_estimate.seconds * 0.8))
                    next_poll = max(SNOW_THRESHOLD, estimate)

        logging.debug("Sleeping for %s seconds." % next_poll.seconds)
        time.sleep(next_poll.seconds)


def get_forecast(darksky, config):
    logging.debug("Checking the forecast for %s at (%s, %s)." % (config.location, config.latitude, config.longitude))
    forecast = None
    tries = 0

    while forecast is None:
        tries += 1

        try:
            forecast = darksky.get_forecast(config.latitude, config.longitude, units=units.SU)
            #forecast = darksky.get_time_machine_forecast(config.latitude, config.longitude, units=units.SU, time=thestorm)
        except requests.exceptions.ConnectionError as error:
            if tries > 10:
                tries = 0
                error_type = type(error)
                error_message = repr(error)
                traceback_message = "".join(traceback.format_exception(error_type, error, error.__traceback__, chain=False)).strip()
                user_log.error("Persistent connection issue: %s.%s\n%s" % (error_type.__module__, error_message, traceback_message))

            logging.debug("Connection error.. waiting %s." % CONNECTION_WAIT)
            time.sleep(CONNECTION_WAIT.seconds)

    return forecast


def next_snowfall(forecast):
    now = dt.datetime.now(TIME_ZONE)
    event = model.PrecipitationEvent(now, forecast.currently)
    #event = model.PrecipitationEvent(now, ARTIFICIAL_SNOW_POINT)
    logging.debug("currently (darksky %s): %s" % (forecast.currently.time, event))

    if event.is_snowing():
        return event
    else:
        for i, hour_point in enumerate(forecast.hourly.data):
            event = model.PrecipitationEvent(now + dt.timedelta(hours=i + 1), hour_point)
            logging.debug("hourly %d: %s" % (i, event))

            if event.is_snowing():
                return event

        return None


def send_message(precip_accumulation, already_snowing, config):
    message = INITIAL_SNOWING_MESSAGE % (config.name, precip_accumulation)

    if already_snowing:
        message = random.choice(ALREADY_SNOWING_MESSAGES)

    body = {
      "phone": config.phone_number,
      "message": message,
      "key": "%s_test" % config.textbelt_key,
    }
    response = requests.post("https://textbelt.com/text", body)
    logging.debug("textbelt: body: %s, response: %s" % (body, response.json()))


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)

