import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://benchvault:benchvault@localhost:5432/benchvault",
)
