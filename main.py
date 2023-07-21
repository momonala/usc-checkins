from time import time

from browser_session import browser_session
from database import write_checkins_to_db
from process import format_attendance_per_month_for_msg
from telegram import send_to_telegram
from usc_navigator import USCNavigator

if __name__ == '__main__':
    t0 = time()
    with browser_session() as browser:
        usc = USCNavigator(browser)
        usc.login()
        usc.get_check_ins(pages=1)
        total_checkins = usc.extract_total_check_ins()
        checkins = usc.extract_check_ins()

    write_checkins_to_db(checkins)
    msg = format_attendance_per_month_for_msg()
    print(msg)
    print(time() - t0)
    send_to_telegram(msg)
