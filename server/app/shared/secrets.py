import os

from dotenv import load_dotenv

load_dotenv()


def get_secret(key: str) -> str:
    value = os.getenv(key)

    if value is None or value == "":
        raise KeyError(
            f"Missing env var '{key}'. "
            f"Copy .example.env to .env and fill it in."
        )

    return value
