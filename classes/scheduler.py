from modules.configuration import config

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_jobstore('sqlalchemy', url=config.DATABASE_URL.get_secret_value(), alias='default')