import requests
from joblib import Memory

from usc.values import email

disk_memory = Memory("joblib_cache")


@disk_memory.cache
def get_venue_html(uri: str) -> str:
    base_headers = {
        "authority": "urbansportsclub.com",
        'Connection': "keep-alive",
        'Cache-Control': "max-age=0",
        'Upgrade-Insecure-Requests': "1",
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        'Accept-Encoding': "gzip, deflate, br",
        'Accept-Language': "en-GB,en-US;q=0.9,en;q=0.8",
    }

    with requests.Session() as s:
        resp = s.post(uri, data={"email": email}, headers=base_headers)
    return resp.text
