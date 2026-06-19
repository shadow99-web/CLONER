import discord
import asyncio
import os
import sys
import logging
from flask import Flask
from threading import Thread

# ─── LOGGING ───
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', stream=sys.stdout)
logger = logging.getLogger("ClonerEngine")

# ─── GATEWAY PATCH ───
from discord.state import ConnectionState
def patched_parse_ready_supplemental(self, data):
    try:
        self.pending_payments = {int(p['id']): p for p in data.get('pending_payments') or []}
    except Exception:
        self.pending_payments = {}
ConnectionState.parse_ready_supplemental = patched_parse_ready_supplemental

# ─── CONFIG ───
ACCOUNT_TOKEN = os.getenv("TOKEN1")
if not ACCOUNT_TOKEN:
    ACCOUNT_TOKEN = "YOUR_HARDCODED_TOKEN_HERE"  # Replace with your token

SOURCE_SERVER_ID = 1443875856803168360
TARGET_SERVER_ID = 1517588614459031723
DRY_RUN = False

# ─── FLASK KEEP-ALIVE ───
app = Flask('')
@app.route('/')
def home():
    return "Cloning Engine is active!"

def run():
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run, daemon=True).start()

# ─── CLONING ENGINE ───
async def start_cloning_engine(client, source_guild, target_guild):
    logger.info(f"\n{'='*50}\n🚀 CLONING INITIALIZED\n📁 Source: {source_guild.name}\n🎯 Target: {target_guild.name}\n{'='*50}")

    # STEP 1: Purge channels
    logger.info("🧹 [1/4] Clearing target channels...")
    if not DRY_RUN:
        for channel in target_guild.channels:
            try:
                await channel.delete()
                await asyncio.sleep(0.2)
            except Exception:
                pass

    # STEP 2: Roles
    logger.info("\n🎭 [2/4] Duplicating roles...")
    role_mapping = {}
    for role in sorted(source_guild.roles, key=lambda r: r.position, reverse=True):
        if role.is_default():
            if not DRY_RUN:
                try:
                    await target_guild.default_role.edit(permissions=role.permissions)
                except Exception:
                    pass
            continue
        if role.managed:
            continue
        if not DRY_RUN:
            try:
                new_role = await target_guild.create_role(
                    name=role.name,
                    permissions=role.permissions,
                    color=role.color,
                    hoist=role.hoist,
                    mentionable=role.mentionable
                )
                role_mapping[role.id] = new_role
                logger.info(f"✅ Created role: {role.name}")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"❌ Failed to create role {role.name}: {e}")

    # STEP 3: Categories & Channels
    logger.info("\n📁 [3/4] Building categories and channels...")
    for category in source_guild.categories:
        cat_overwrites = {}
        for role_or_member, overwrite in category.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    cat_overwrites[mapped_role] = overwrite

        if not DRY_RUN:
            try:
                new_category = await target_guild.create_category(name=category.name, overwrites=cat_overwrites)
                logger.info(f"📂 Category: {category.name}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Failed category {category.name}: {e}")
                continue
        else:
            new_category = None

        for txt_chan in sorted(category.text_channels, key=lambda c: c.position):
            chan_overwrites = {}
            for role_or_member, overwrite in txt_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite
            if not DRY_RUN:
                try:
                    await target_guild.create_text_channel(
                        name=txt_chan.name,
                        category=new_category,
                        topic=txt_chan.topic,
                        nsfw=txt_chan.nsfw,
                        slowmode_delay=txt_chan.slowmode_delay,
                        overwrites=chan_overwrites
                    )
                    logger.info(f"  ├── 📝 Text: {txt_chan.name}")
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

        for vc_chan in sorted(category.voice_channels, key=lambda c: c.position):
            chan_overwrites = {}
            for role_or_member, overwrite in vc_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite
            if not DRY_RUN:
                try:
                    max_bitrate = target_guild.bitrate_limit
                    bitrate = max(8000, min(vc_chan.bitrate, max_bitrate))
                    await target_guild.create_voice_channel(
                        name=vc_chan.name,
                        category=new_category,
                        user_limit=vc_chan.user_limit,
                        bitrate=bitrate,
                        overwrites=chan_overwrites
                    )
                    logger.info(f"  ├── 🔊 Voice: {vc_chan.name}")
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

    # STEP 4: Emojis
    logger.info("\n👾 [4/4] Syncing emojis...")
    if source_guild.emojis:
        available = target_guild.emoji_limit - len(target_guild.emojis)
        for i, emoji in enumerate(source_guild.emojis[:available]):
            if not DRY_RUN:
                try:
                    emoji_bytes = await emoji.read()
                    await target_guild.create_custom_emoji(name=emoji.name, image=emoji_bytes)
                    logger.info(f"  ✅ Copied emoji :{emoji.name}:")
                    await asyncio.sleep(1.0)
                except Exception as e:
                    logger.error(f"  ❌ Failed emoji :{emoji.name}: {e}")

    logger.info("\n🎉 CLONING COMPLETED!")

# ─── MAIN BOOT ───
async def main_boot():
    keep_alive()
    logger.info("🚀 SYSTEM BOOT: DIRECT CONNECTION MODE")

    if not ACCOUNT_TOKEN or ACCOUNT_TOKEN == "YOUR_HARDCODED_TOKEN_HERE":
        logger.error("❌ TOKEN1 not set!")
        return

    client = discord.Client(
        self_bot=True,
        browser="chrome",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        compress=False
    )

    @client.event
    async def on_ready():
        logger.info(f"✨ [ON_READY] Authenticated as: {client.user}")

    # Start client
    await client.start(ACCOUNT_TOKEN.strip())

    # Wait for the client to be ready (gateway connection established)
    await client.wait_until_ready()
    logger.info("✅ Client is ready.")

    # Poll for guilds until they appear (max 30 attempts, 2s apart = 60s)
    source = target = None
    for attempt in range(1, 31):
        source = client.get_guild(SOURCE_SERVER_ID)
        target = client.get_guild(TARGET_SERVER_ID)
        if source and target:
            logger.info(f"✅ Found both guilds after {attempt*2}s.")
            break
        logger.info(f"Attempt {attempt}/30 – Source: {source is not None}, Target: {target is not None}")
        await asyncio.sleep(2)

    if not source or not target:
        logger.error("❌ Guilds not found after 60 seconds.")
        logger.error(f"📋 Guilds in cache: {[g.id for g in client.guilds]}")
        return

    await start_cloning_engine(client, source, target)

    # Keep alive
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main_boot())
    except KeyboardInterrupt:
        logger.info("Stopping Cloner...")
    except Exception as e:
        logger.error(f"Fatal System Error: {e}")
