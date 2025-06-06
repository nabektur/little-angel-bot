from modules.configuration import settings

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_jobstore('sqlalchemy', url=settings.DATABASE_URL.get_secret_value(), alias='default')