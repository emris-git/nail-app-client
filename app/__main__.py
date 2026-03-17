from __future__ import annotations

import asyncio
import logging

from app.bot import create_bot_and_dispatcher


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot, dp = create_bot_and_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

