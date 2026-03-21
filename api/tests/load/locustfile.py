import os

from locust import FastHttpUser, between, task

"""
Load test can be executed by running:

LOCUST_ENV_HOST=<HOST> uv run locust -f tests/load/locustfile.py
"""


class Workflow(FastHttpUser):
    host: str = os.environ.get("LOCUST_HOST_ENV", "")
    origin = host.replace("https://", "")
    default_headers = {
        "Origin": origin,
        "sec-ch-ua": '"Chromium";v="133", "Not(A:Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Accept": "*/*",
        "Upgrade-Insecure-Requests": "1",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.16 Safari/537.36",
        "Host": origin,
    }

    wait_time = between(5, 10)

    @task
    def execute_task(self) -> None:
        """
        Replace with calls to API

        See: https://docs.locust.io/en/stable/quickstart.html
        """
        pass
