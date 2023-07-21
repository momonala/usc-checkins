import logging

from browser_session import browser_session, virtual_display_if_needed

logger = logging.getLogger(__name__)
with virtual_display_if_needed(), browser_session() as webbrowser:
    webbrowser.get('https://www.google.com/')
    logger.info(webbrowser.page_source)
