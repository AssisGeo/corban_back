from datetime import datetime


def format_string_datetime(datetime: datetime) -> str:
    return datetime.strftime("%Y-%m-%dT%H:%M:%S")
