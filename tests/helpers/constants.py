from datetime import datetime, timezone
from pathlib import Path

TESTS_PATH = Path(__file__).parent.parent
FIXTURES_PATH = TESTS_PATH / "fixtures"

DEFAULT_PAGE_SIZE = 20
DEFAULT_PAGE = 1

DEFAULT_DATETIME = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

SMALL_BATCH_SIZE = 2
MEDIUM_BATCH_SIZE = 5

USER_PASSWORD = "S3cr3t-Us3r-P455w0rd"
USER_EMAIL = "johndoe@whimo.com"
USER_PHONE = "+12223334455"

ADMIN_PASSWORD = "S3cr3t-4dm1n-P455w0rd"
