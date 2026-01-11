import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from modules.configuration import config

scheduler = AsyncIOScheduler(jobstore_retry_interval=10)

db_path = os.path.join("data", "jobs.sqlite")
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# scheduler.add_jobstore('sqlalchemy', url=config.DATABASE_URL.get_secret_value(), alias='default')
scheduler.add_jobstore('sqlalchemy', url=f"sqlite:///{db_path}", alias='default')