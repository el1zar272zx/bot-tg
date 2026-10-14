from shared.scheduler import setup_scheduler

bot = Bot(token=settings.CLIENT_BOT_TOKEN)
dp = Dispatcher()

scheduler = setup_scheduler(bot)
scheduler.start()
