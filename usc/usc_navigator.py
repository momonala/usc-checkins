import logging
import re
from datetime import datetime
from time import sleep

import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from usc.cached_requests import get_venue_html
from usc.values import email, password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class USCNavigator:
    usc_url_base = "https://urbansportsclub.com"

    def __init__(self, browser: webdriver.Chrome):
        self._browser = browser

    def _wait_till_available(self, xpath: str):
        element_present = expected_conditions.presence_of_element_located((By.XPATH, xpath))
        WebDriverWait(self._browser, 10).until(element_present)

    @staticmethod
    def _find_between(start: str, end: str, text: str) -> list[str]:
        regex = fr'{start}\s*(.*?)\s*{end}'
        results: list[str] = re.findall(regex, text)
        return results

    @staticmethod
    def _sanitize_html(html: str) -> str:
        return html.replace(" ", "").replace("\n", "").replace("&quot;", "").replace("&amp;", "")

    @staticmethod
    def _log_check_ins(check_ins_df: pd.DataFrame):
        """Log the check_ins dataframe."""

        def get_date(checkin):
            return datetime(day=checkin.day, month=checkin.month, year=checkin.year).strftime("%d %B, %Y")

        start_end = check_ins_df.iloc[[0, -1]].apply(lambda r: get_date(r), axis=1).values
        logger.info(f"Got data from: {start_end[1]} - {start_end[0]}. Size:{check_ins_df.shape}")

    def login(self):
        usc_login_page = f"{self.usc_url_base}/en/login"
        email_html_id = "email"
        pass_html_id = "password"
        signin_button_xpath = '//*[@id="login-group"]/input'
        customer_id_xpath = '//*[@id="appointment"]/header/div/ul[2]/li[2]'

        self._browser.get(usc_login_page)
        self._browser.find_element(By.ID, email_html_id).send_keys(email)
        self._browser.find_element(By.ID, pass_html_id).send_keys(password)
        self._browser.find_element(By.XPATH, signin_button_xpath).click()
        sleep(1)
        self._wait_till_available(customer_id_xpath)
        logger.info("Logged in!")

    def get_check_ins(self, pages: int = 43):
        """Get check_ins from USC website.
        Args:
            pages (int, optional): Number of pages to look back.
        """

        def checkin_scroll_button_xpath(n: int) -> str:
            return f'/html/body/div[5]/section/div/div/div[{n}]/button'

        def scroll_almost_to_bottom():
            self._browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self._browser.execute_script("window.scrollTo(0, window.scrollY - 300);")

        check_ins_url = f"{self.usc_url_base}/en/profile/check-ins"
        self._browser.get(check_ins_url)
        scroll_almost_to_bottom()
        logger.info(f"Opened {check_ins_url} page.")

        for page in range(3, 3 + pages):
            sleep(1.5)
            try:
                self._wait_till_available(checkin_scroll_button_xpath(page))
                self._browser.find_element(By.XPATH, checkin_scroll_button_xpath(page)).click()
                scroll_almost_to_bottom()
            except ElementNotInteractableException:
                logger.info("Got all check ins!")
                break

    def extract_total_check_ins(self) -> pd.DataFrame:
        header = self._browser.page_source.split('<div class="table-date">')[0]
        sanitized_header = self._sanitize_html("".join(header.split("Total check-ins:")[1:]))
        sports = self._find_between('<spanclass="smm-checkin-stats__text">', '</span>', sanitized_header)
        counts = self._find_between('<spanclass="smm-checkin-stats__hint">', '</span>', sanitized_header)

        total_check_ins = tuple(zip(sports, counts))
        logger.debug(f"\n{total_check_ins}")
        return pd.DataFrame(total_check_ins, columns=["sport", "count"])

    def extract_check_ins(self) -> pd.DataFrame:
        check_ins_html = self._browser.page_source.split('<div class="table-date">')[1:]

        rows = []
        for checkin_html in check_ins_html:
            sanitized_html = self._sanitize_html(checkin_html)

            sports = self._find_between(',name:', ',category:', sanitized_html)
            sports = list(dict.fromkeys(sports))

            venues = self._find_between(
                '<iclass="fafa-map-marker"></i>', '</a></div><divclass="detailscol', sanitized_html
            )
            venues = [x.split("</a>")[0] for x in venues]

            date_raw = sanitized_html.split("</div>")[0]
            date_obj = datetime.strptime(date_raw, "%A,%d%B")
            date = date_obj.strftime("%d.%m (%a)")

            venue_uris = self._find_between('target="_self" href="', '">\n', checkin_html)
            checkin_limits = []
            for venue_uri in venue_uris:
                venue_html = get_venue_html(f"{self.usc_url_base}{venue_uri}")
                visit_limit_option1 = self._find_between("M-.*Mitglieder können ", "besuchen", venue_html)
                visit_limit_option2 = self._find_between("M-.*Mitglieder können ", "teilnehmen", venue_html)
                visit_limit_option3 = self._find_between("M-.*Mitglieder können ", "nutzen", venue_html)
                visit_limit_option4 = self._find_between("M-.*Mitglieder können ", "bouldern", venue_html)
                visit_limit_option5 = self._find_between("M-.*Mitglieder können ", "wahrnehmen", venue_html)
                visit_limit_option6 = self._find_between("M-.*Mitglieder können ", "bouldern", venue_html)
                visit_limit_option3 = self._find_between("M-.*Mitglieder können ", "spielen", venue_html)
                visit_limit_raw = visit_limit_option1 or visit_limit_option2 or visit_limit_option3
                if not visit_limit_raw:
                    logger.warning(f"Could not find visit limit for {venue_uri=}")
                    checkin_limit = 31
                else:
                    visit_limit_raw = visit_limit_raw[0].replace(" ", "").replace("(max.1xproTag)", "")
                    checkin_limit = re.sub(r'\D', '', visit_limit_raw)
                    checkin_limit = checkin_limit if checkin_limit != 1 else 31  # 1/day --> 31/month
                checkin_limits.append(checkin_limit)

            for sport, venue, checkin_limit in tuple(zip(sports, venues, checkin_limits)):
                logger.debug(f"{date:15s}{sport:25s}{venue}")
                rows.append(
                    {
                        "day": date_obj.day,
                        "month": date_obj.month,
                        "weekday": date_obj.weekday(),
                        "sport": sport,
                        "venue": venue,
                        "checkin_limit": checkin_limit,
                    }
                )
        check_ins = pd.DataFrame(rows)
        check_ins = _add_year_to_check_ins_df(check_ins)
        check_ins = _add_cost_to_check_ins_df(check_ins)

        self._log_check_ins(check_ins)
        return check_ins


def _add_year_to_check_ins_df(check_ins: pd.DataFrame) -> pd.DataFrame:
    """Adds a year column to the check_ins Dataframe by tracking the month-to-month changes."""
    year_change = check_ins.month.diff() > 1
    year_changes = year_change[year_change]

    current_year = datetime.now().year
    year_arr = np.zeros((check_ins.shape[0], 1), dtype=int)

    if not len(year_changes):
        year_arr[:] = current_year

    else:
        years = range(current_year, current_year - len(year_changes), -1)
        end = 0
        for i, year in enumerate(years):
            start = 0 if i == 0 else year_changes.index[i - 1]
            end = year_changes.index[i]
            year_arr[start:end] = year
        year_arr[end:] = years[-1] - 1
    check_ins["year"] = year_arr
    return check_ins


def _add_cost_to_check_ins_df(check_ins: pd.DataFrame) -> pd.DataFrame:
    """Add"""
    sport_costs = {
        'Bouldering': 12,
        'Fitness': 5,
        'Bouldern': 12,
        'Schwimmen': 5.5,
        'Calisthenics|AllLevels': 12.5,
        'bouldern': 12,
        'BeachVolleyball': 10,
        'PowerYoga': 12.5,
        'IntrotoAcroyoga': 12.5,
    }
    check_ins["cost"] = check_ins["sport"].apply(lambda sport: sport_costs.get(sport, 12))
    logger.debug(f"Euro: {check_ins['cost'].sum()}")
    return check_ins
