import argparse

from usc.main import monthly_checkin_pipeline
from usc.process import get_total_check_ins_for_msg
from usc.telegram import send_to_telegram

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("pages", default=50, type=int, help="number of checkin pages to look through")
    args = parser.parse_args()

    monthly_checkin_pipeline(pages=args.pages)
    msg = get_total_check_ins_for_msg()
    send_to_telegram(msg)
