from usc.main import monthly_checkin_pipeline

from usc.process import get_total_check_ins_for_msg
from usc.telegram import send_to_telegram

if __name__ == '__main__':
    monthly_checkin_pipeline(pages=50)
    msg = get_total_check_ins_for_msg()
    send_to_telegram(msg)
