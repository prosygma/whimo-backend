import json
from typing import Any


class PrettyJSONEncoder(json.JSONEncoder):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["indent"] = kwargs.get("indent", 4)
        kwargs["sort_keys"] = kwargs.get("sort_keys", True)
        super().__init__(*args, **kwargs)
