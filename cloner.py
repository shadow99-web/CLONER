import discord
import asyncio
import os
import sys
import json
import logging
from flask import Flask
from threading import Thread
from huggingface_hub import HfApi, upload_file, hf_hub_download
import shutil

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
    ACCOUNT_TOKEN = "YOUR_HARDCODED_TOKEN_HERE"

# Hugging Face settings
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    HF_TOKEN = "YOUR_HF_TOKEN_HERE"

HF_DATASET_REPO = "DiscordBOTNHIHUN/P2AURA-FARMER"
CONFIG_FILE = "cloner_config.json"

# ─── COMMAND CHANNEL ───
COMMAND_CHANNEL_ID = 1486752232438235207  # Replace with your channel ID

# ─── HF FUNCTIONS ───
hf_api = HfApi()

def load_config():
    try:
        path = hf_hub_download(
            repo_id=HF_DATASET_REPO,
            filename=CONFIG_FILE,
            repo_type="dataset",
            token=HF_TOKEN
        )
        with open(path, "r") as f:
            config = json.load(f)
            logger.info("✅ Config loaded from Hugging Face.")
            return config
    except Exception as e:
        logger.warning(f"⚠️ Could not download config from HF: {e}")

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    return {"source_id": None, "target_id": None}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    try:
        upload_file(
            path_or_fileobj=CONFIG_FILE,
            path_in_repo=CONFIG_FILE,
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            token=HF_TOKEN
        )
        logger.info("☁️ Config uploaded to Hugging Face.")
    except Exception as e:
        logger.error(f"❌ Failed to upload config to HF: {e}")

# ─── LOAD CONFIG ───
config = load_config()

SOURCE_SERVER_ID = config.get("source_id") or int(os.getenv("SOURCE_SERVER_ID", 0)) or 1443875856803168360
TARGET_SERVER_ID = config.get("target_id") or int(os.getenv("TARGET_SERVER_ID", 0)) or 1517625015195926629

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
async def start_cloning_engine(client, source_guild, target_guild, dry_run=False):
    logger.info(f"\n{'='*50}\n🚀 CLONING INITIALIZED\n📁 Source: {source_guild.name}\n🎯 Target: {target_guild.name}\n{'='*50}")

    try:
        self_member = await target_guild.fetch_member(client.user.id)
    except discord.NotFound:
        logger.error("❌ Could not find yourself in the target guild.")
        return
    except discord.Forbidden:
        logger.error("❌ Bot does not have permission to view members in the target guild.")
        return

    if not self_member.guild_permissions.manage_channels:
        logger.error("❌ Account does not have 'Manage Channels' permission in the target server.")
        return
    logger.info("✅ Permission check passed.")

    logger.info("🧹 [1/4] Clearing target channels...")
    if not dry_run:
        for channel in target_guild.channels:
            try:
                await channel.delete()
                await asyncio.sleep(0.2)
            except Exception:
                pass

    logger.info("\n🎭 [2/4] Duplicating roles...")
    role_mapping = {}
    for role in sorted(source_guild.roles, key=lambda r: r.position, reverse=True):
        if role.is_default():
            if not dry_run:
                try:
                    await target_guild.default_role.edit(permissions=role.permissions)
                except Exception:
                    pass
            continue
        if role.managed:
            continue
        if not dry_run:
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

    logger.info("\n📁 [3/4] Building categories and channels...")
    try:
        source_channels = await source_guild.fetch_channels()
        logger.info(f"✅ Fetched {len(source_channels)} channels from source.")
    except Exception as e:
        logger.error(f"❌ Failed to fetch channels: {e}")
        return

    source_categories = [ch for ch in source_channels if isinstance(ch, discord.CategoryChannel)]
    source_text_channels = [ch for ch in source_channels if isinstance(ch, discord.TextChannel)]
    source_voice_channels = [ch for ch in source_channels if isinstance(ch, discord.VoiceChannel)]

    logger.info(f"📊 Categories: {len(source_categories)}, Text: {len(source_text_channels)}, Voice: {len(source_voice_channels)}")

    category_mapping = {}
    for category in sorted(source_categories, key=lambda c: c.position):
        cat_overwrites = {}
        for role_or_member, overwrite in category.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    cat_overwrites[mapped_role] = overwrite

        if not dry_run:
            try:
                new_category = await target_guild.create_category(
                    name=category.name,
                    overwrites=cat_overwrites
                )
                category_mapping[category.id] = new_category
                logger.info(f"📂 Category: {category.name}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Failed category {category.name}: {e}")

    for txt_chan in sorted(source_text_channels, key=lambda c: c.position):
        chan_overwrites = {}
        for role_or_member, overwrite in txt_chan.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    chan_overwrites[mapped_role] = overwrite

        parent_category = category_mapping.get(txt_chan.category_id) if txt_chan.category_id else None

        if not dry_run:
            try:
                await target_guild.create_text_channel(
                    name=txt_chan.name,
                    category=parent_category,
                    topic=txt_chan.topic,
                    nsfw=txt_chan.nsfw,
                    slowmode_delay=txt_chan.slowmode_delay,
                    overwrites=chan_overwrites
                )
                logger.info(f"  ├── 📝 Text: {txt_chan.name}")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"  ├── ❌ Failed text channel {txt_chan.name}: {e}")

    for vc_chan in sorted(source_voice_channels, key=lambda c: c.position):
        chan_overwrites = {}
        for role_or_member, overwrite in vc_chan.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    chan_overwrites[mapped_role] = overwrite

        parent_category = category_mapping.get(vc_chan.category_id) if vc_chan.category_id else None

        if not dry_run:
            try:
                max_bitrate = target_guild.bitrate_limit
                bitrate = max(8000, min(vc_chan.bitrate, max_bitrate))
                await target_guild.create_voice_channel(
                    name=vc_chan.name,
                    category=parent_category,
                    user_limit=vc_chan.user_limit,
                    bitrate=bitrate,
                    overwrites=chan_overwrites
                )
                logger.info(f"  ├── 🔊 Voice: {vc_chan.name}")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"  ├── ❌ Failed voice channel {vc_chan.name}: {e}")

    logger.info("\n👾 [4/4] Syncing emojis...")
    if source_guild.emojis:
        available = target_guild.emoji_limit - len(target_guild.emojis)
        emojis_to_copy = source_guild.emojis[:available]
        logger.info(f"📊 Copying {len(emojis_to_copy)} emojis...")
        for i, emoji in enumerate(emojis_to_copy):
            if not dry_run:
                try:
                    emoji_bytes = await emoji.read()
                    await target_guild.create_custom_emoji(
                        name=emoji.name,
                        image=emoji_bytes
                    )
                    logger.info(f"  ✅ Copied emoji :{emoji.name}: ({i+1}/{len(emojis_to_copy)})")
                    await asyncio.sleep(1.0)
                except discord.HTTPException as e:
                    if e.status == 429:
                        retry_after = getattr(e, 'retry_after', 5)
                        logger.warning(f"  ⏳ Rate limited on :{emoji.name}: waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        try:
                            emoji_bytes = await emoji.read()
                            await target_guild.create_custom_emoji(name=emoji.name, image=emoji_bytes)
                            logger.info(f"  ✅ Retry succeeded :{emoji.name}:")
                        except Exception as e2:
                            logger.error(f"  ❌ Failed to copy emoji :{emoji.name}: {e2}")
                    else:
                        logger.error(f"  ❌ Failed to copy emoji :{emoji.name}: {e}")
                except Exception as e:
                    logger.error(f"  ❌ Failed to copy emoji :{emoji.name}: {e}")

    logger.info("\n" + "="*50)
    logger.info("🎉 CLONING COMPLETED SUCCESSFULLY!")
    logger.info(f"📊 Roles created: {len(role_mapping)}")
    logger.info(f"📊 Categories created: {len(category_mapping)}")
    logger.info("="*50 + "\n")

# ─── COMMAND HANDLER ───
async def handle_commands(message):
    global config  # <-- Move this to the top
    
    if message.channel.id != COMMAND_CHANNEL_ID:
        return
    
    content = message.content.strip()
    if not content.startswith('.'):
        return
    
    args = content.split()
    cmd = args[0].lower()

    if cmd == '.setsource' and len(args) == 2:
        try:
            guild_id = int(args[1])
            config['source_id'] = guild_id
            save_config(config)
            await message.channel.send(f"✅ Source guild set to `{guild_id}` (saved to HF).")
        except ValueError:
            await message.channel.send("❌ Invalid guild ID. Please provide a valid integer.")
        return

    if cmd == '.settarget' and len(args) == 2:
        try:
            guild_id = int(args[1])
            config['target_id'] = guild_id
            save_config(config)
            await message.channel.send(f"✅ Target guild set to `{guild_id}` (saved to HF).")
        except ValueError:
            await message.channel.send("❌ Invalid guild ID. Please provide a valid integer.")
        return

    if cmd == '.status':
        source = config.get('source_id') or 'Not set'
        target = config.get('target_id') or 'Not set'
        await message.channel.send(f"📊 **Current Settings**\nSource: `{source}`\nTarget: `{target}`\n\nConfig stored on Hugging Face dataset `{HF_DATASET_REPO}`.")
        return

    if cmd == '.pullconfig':
        config.clear()
        config.update(load_config())
        await message.channel.send("✅ Config reloaded from Hugging Face.")
        return

    if cmd == '.clone':
        source_id = config.get('source_id')
        target_id = config.get('target_id')
        if not source_id or not target_id:
            await message.channel.send("❌ Source or target guild not set. Use `.setsource` and `.settarget` first.")
            return

        try:
            source_guild, target_guild = await asyncio.gather(
                cloner_client.fetch_guild(source_id),
                cloner_client.fetch_guild(target_id)
            )
        except discord.NotFound:
            await message.channel.send("❌ One or both guilds not found. Check the IDs.")
            return
        except discord.Forbidden:
            await message.channel.send("❌ Bot does not have access to one or both guilds.")
            return
        except Exception as e:
            await message.channel.send(f"❌ Error fetching guilds: {e}")
            return

        await message.channel.send(f"🚀 Starting clone from `{source_guild.name}` to `{target_guild.name}`...")
        await start_cloning_engine(cloner_client, source_guild, target_guild, dry_run=False)
        await message.channel.send("✅ Cloning completed!")
        return

    if cmd == '.help':
        help_text = (
            "**Available Commands**:\n"
            "`.setsource <id>` - Set source guild ID (saved to HF)\n"
            "`.settarget <id>` - Set target guild ID (saved to HF)\n"
            "`.status` - Show current settings\n"
            "`.pullconfig` - Reload config from Hugging Face\n"
            "`.clone` - Start cloning with current settings\n"
            "`.help` - Show this message"
        )
        await message.channel.send(help_text)
        return

# ─── CLIENT ───
cloner_client = discord.Client(
    self_bot=True,
    browser="chrome",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    compress=False
)

@cloner_client.event
async def on_ready():
    logger.info(f"✨ [ON_READY] Authenticated as: {cloner_client.user}")

@cloner_client.event
async def on_message(message):
    await handle_commands(message)

# ─── MAIN BOOT ───
async def main_boot():
    keep_alive()
    logger.info("🚀 SYSTEM BOOT: DIRECT CONNECTION MODE")

    if not ACCOUNT_TOKEN or ACCOUNT_TOKEN == "YOUR_HARDCODED_TOKEN_HERE":
        logger.error("❌ TOKEN1 not set!")
        return

    asyncio.create_task(cloner_client.start(ACCOUNT_TOKEN.strip()))

    logger.info("⏳ Waiting for client to authenticate...")
    auth_attempts = 0
    while cloner_client.user is None and auth_attempts < 30:
        await asyncio.sleep(1)
        auth_attempts += 1

    if cloner_client.user is None:
        logger.error("❌ Authentication failed after 30 seconds.")
        return

    logger.info(f"✨ Authenticated as: {cloner_client.user}")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main_boot())
    except KeyboardInterrupt:
        logger.info("Stopping Cloner...")
    except Exception as e:
        logger.error(f"Fatal System Error: {e}")
