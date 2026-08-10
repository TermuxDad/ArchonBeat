import sys
from pyrogram import Client

import config
from ..logging import LOGGER

assistants = []
assistantids = []


class Userbot(Client):
    def __init__(self):
        self.one = Client(
            name="AnonXAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1) if config.STRING1 else None,
            no_updates=True,
        )
        self.two = Client(
            name="AnonXAss2",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING2) if config.STRING2 else None,
            no_updates=True,
        )
        self.three = Client(
            name="AnonXAss3",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING3) if config.STRING3 else None,
            no_updates=True,
        )
        self.four = Client(
            name="AnonXAss4",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING4) if config.STRING4 else None,
            no_updates=True,
        )
        self.five = Client(
            name="AnonXAss5",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING5) if config.STRING5 else None,
            no_updates=True,
        )

    async def _setup_assistant(self, client, index, name):
        await client.start()
        
        # Optional Channel Auto-Joins (Handled Safely)
        for channel in ["College_wali_masti", "Saykkunomusic"]:
            try:
                await client.join_chat(channel)
            except Exception:
                pass

        # Check Logger Group Access
        try:
            await client.send_message(config.LOGGER_ID, f"Assistant {index} Started Successfully!")
        except Exception:
            LOGGER(__name__).error(
                f"Assistant Account {index} failed to access Logger Group. Make sure it is added and made ADMIN!"
            )
            # We don't hard exit here to allow multi-assistant resiliency

        client.id = client.me.id
        client.name = client.me.mention
        client.username = client.me.username or ""
        
        assistants.append(index)
        assistantids.append(client.id)
        LOGGER(__name__).info(f"Assistant {index} Started as {client.name}")

    async def start(self):
        LOGGER(__name__).info("Starting Assistant Clients...")

        if config.STRING1:
            await self._setup_assistant(self.one, 1, "One")

        if config.STRING2:
            await self._setup_assistant(self.two, 2, "Two")

        if config.STRING3:
            await self._setup_assistant(self.three, 3, "Three")

        if config.STRING4:
            await self._setup_assistant(self.four, 4, "Four")

        if config.STRING5:
            await self._setup_assistant(self.five, 5, "Five")

    async def stop(self):
        LOGGER(__name__).info("Stopping Assistant Clients...")
        
        clients = [
            (config.STRING1, self.one),
            (config.STRING2, self.two),
            (config.STRING3, self.three),
            (config.STRING4, self.four),
            (config.STRING5, self.five),
        ]

        for string_session, client in clients:
            if string_session:
                try:
                    await client.stop()
                except Exception as e:
                    LOGGER(__name__).warning(f"Error stopping assistant client: {e}")

