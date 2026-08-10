import asyncio
import importlib

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from AnonXMusic import LOGGER, app, userbot
from AnonXMusic.core.call import Anony
from AnonXMusic.misc import sudo
from AnonXMusic.plugins import ALL_MODULES
from AnonXMusic.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS

# Fast Event Loop Integration (Linux/Termux Support)
try:
    import uvloop
    uvloop.install()
except ImportError:
    pass


async def init():
    # Check if at least one assistant string session exists
    if not any([config.STRING1, config.STRING2, config.STRING3, config.STRING4, config.STRING5]):
        LOGGER("AnonXMusic").error("Assistant client variables not defined, exiting...")
        return

    # Load Sudo Users & Banned Users
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except Exception as e:
        LOGGER("AnonXMusic").warning(f"Error while fetching banned users: {e}")

    # Start Main Bot Client
    await app.start()

    # Dynamic Plugin Loader
    for all_module in ALL_MODULES:
        module_path = "AnonXMusic.plugins" + (all_module if all_module.startswith(".") else f".{all_module}")
        importlib.import_module(module_path)
    LOGGER("AnonXMusic.plugins").info("Successfully Imported All Modules...")

    # Start Assistant Client & PyTgCalls Client
    await userbot.start()
    await Anony.start()

    # Initial Stream Test on Logger Group
    try:
        await Anony.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("AnonXMusic").error(
            "Please turn on the Voice Chat / Video Chat in your LOG_GROUP.\nStopping Bot..."
        )
        return
    except Exception as e:
        LOGGER("AnonXMusic").warning(f"Initial stream test failed/skipped: {e}")

    await Anony.decorators()
    LOGGER("AnonXMusic").info("AnonX Music Bot Started Successfully!")
    
    # Keep Bot Running
    await idle()

    # Graceful Shutdown Sequence
    LOGGER("AnonXMusic").info("Stopping AnonX Music Bot Services...")
    await app.stop()
    await userbot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(init())
    except (KeyboardInterrupt, SystemExit):
        LOGGER("AnonXMusic").info("Bot stopped forcefully.")
