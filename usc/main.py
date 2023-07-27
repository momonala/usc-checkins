"""Executes the pipeline on run on a schedule (like a cronjob)"""
import logging
from datetime import datetime
from time import time, sleep

import schedule

from usc.browser_session import browser_session, virtual_display_if_needed
from usc.database import write_checkins_to_db
from usc.process import format_attendance_per_month_for_msg, get_total_check_ins_for_msg
from usc.telegram import send_to_telegram
from usc.usc_navigator import USCNavigator

logger = logging.getLogger(__name__)


def monthly_checkin_pipeline():
    t0 = time()
    with virtual_display_if_needed(), browser_session() as browser:
        usc = USCNavigator(browser)
        usc.login()
        usc.get_check_ins(pages=1)
        checkins = usc.extract_check_ins()
    write_checkins_to_db(checkins)
    msg = format_attendance_per_month_for_msg()
    logger.info(f"Elapsed time: {round(time() - t0, 2)}s")
    print(msg)
    send_to_telegram(msg)


def total_checkin_pipeline():
    if datetime.today().day == 1:
        msg = get_total_check_ins_for_msg()
        send_to_telegram(msg)


if __name__ == '__main__':
    execution_time = "00:00"
    schedule.every().day.at(execution_time).do(monthly_checkin_pipeline)
    schedule.every().day.at(execution_time).do(total_checkin_pipeline)
    logger.info(f"Registered pipeline. Running every day at {execution_time}, indefintely.")
    while True:
        schedule.run_pending()
        sleep(1)
