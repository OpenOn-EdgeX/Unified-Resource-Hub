from functools import wraps
from http import HTTPStatus
from typing import Any, Optional

class ApiException(Exception):

    def __init__(
        self,
        message: str,
        status_code: int,
        code: str,
        detail: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = int(status_code)
        self.code = code
        self.detail = detail

def api_error(message: str, code: str, status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR):

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)

            except ApiException:
                raise

            except Exception as exc:
                raise ApiException(
                    message=message,
                    status_code=status_code,
                    code=code,
                ) from exc

        return wrapper

    return decorator
