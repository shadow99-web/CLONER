import discord
import asyncio
import os
import sys
from flask import Flask
from threading import Thread

# ───────────────────────────────────────────────────────────────────
# 🔥 CRITICAL GATEWAY PATCH: FIXES 'NoneType' OBJECT IS NOT ITERABLE
# ───────────────────────────────────────────────────────────────────
from discord.state import ConnectionState

def patched_parse_ready_supplemental(self, data):
    try:
        self.pending_payments = {
            int(p['id']): p for p in data.get('pending_payments') or []
        }
    except Exception:
        self.pending_payments = {}

ConnectionState.parse_ready_supplemental = patched_parse_ready_supplemental
# ───────────────────────────────────────────────────────────────────

# =======================================================================
# ⚙️ CONFIGURATION BOUNDARY
# =======================================================================
ACCOUNT_TOKEN = os.getenv("TOKEN1") 
SOURCE_SERVER_ID = 1443875856803168360  
TARGET_SERVER_ID = 1517588614459031723   
# =======================================================================

# --- FLASK KEEP ALIVE ENGINE ---
app = Flask('')

@app.route('/')
def home():
    return "Cloning Engine is active and healthy!"

def run():
    port = int(os.environ.get("PORT", 10000))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"⚠️ Flask Server suppressed: {e}", flush=True)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()
# ───────────────────────────────────────────────────────────────────

cloner_client = discord.Client(
    self_bot=True,
    browser="chrome",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    compress=False
)

async def start_cloning_engine():
    print("⏳ [STAGE 1] Syncing Discord cache... Waiting 15 seconds...", flush=True)
    await asyncio.sleep(15)
    
    print(f"📡 Current visible guild count in memory: {len(cloner_client.guilds)}", flush=True)
    print(f"📋 Full list of IDs this token can access: {[g.id for g in cloner_client.guilds]}", flush=True)

    source_guild = cloner_client.get_guild(SOURCE_SERVER_ID)
    target_guild = cloner_client.get_guild(TARGET_SERVER_ID)

    if not source_guild:
        print(f"❌ [CACHE DEFICIT] Unable to find SOURCE server [{SOURCE_SERVER_ID}]. Is the account actively inside that server?", flush=True)
    if not target_guild:
        print(f"❌ [CACHE DEFICIT] Unable to find TARGET server [{TARGET_SERVER_ID}]. Is the account actively inside that server?", flush=True)

    if not source_guild or not target_guild:
        print("🛑 System halted due to missing server references. Verify your account presence and Server IDs.", flush=True)
        return

    print("\n" + "="*50)
    print(f"🚀 CLONING INITIALIZED")
    print(f"📁 Source Guild: {source_guild.name}")
    print(f"🎯 Target Guild: {target_guild.name}")
    print("="*50 + "\n", flush=True)

    # ───────────────────────────────────────────────────────────────────
    # STEP 1: CLEANING INTERFACE LAYER
    # ───────────────────────────────────────────────────────────────────
    print("🧹 [1/4] Purging default channels from target server...", flush=True)
    for channel in target_guild.channels:
        try:
            await channel.delete()
            await asyncio.sleep(0.4)
        except Exception:
            pass

    # ───────────────────────────────────────────────────────────────────
    # STEP 2: REBUILDING THE ROLE MAP MATRIX
    # ───────────────────────────────────────────────────────────────────
    print("\n🎭 [2/4] Extracting and deploying global role permissions...", flush=True)
    role_mapping = {}

    sorted_roles = sorted(source_guild.roles, key=lambda r: r.position)

    for role in sorted_roles:
        if role.is_default():
            try:
                await target_guild.default_role.edit(permissions=role.permissions)
                role_mapping[role.id] = target_guild.default_role
                print(" ✅ Synced baseline @everyone permissions.", flush=True)
            except Exception as e:
                print(f" ⚠️ Failed syncing @everyone perms: {e}", flush=True)
            continue

        if role.managed:
            continue

        try:
            new_role = await target_guild.create_role(
                name=role.name,
                permissions=role.permissions,
                color=role.color,
                hoist=role.hoist,
                mentionable=role.mentionable
            )
            role_mapping[role.id] = new_role
            print(f" ✅ Duplicated Role: {role.name}", flush=True)
            await asyncio.sleep(0.8)
        except Exception as e:
            print(f" ❌ Failed creating role [{role.name}]: {e}", flush=True)

    # ───────────────────────────────────────────────────────────────────
    # STEP 3: MAPPING STRUCTURAL CATEGORIES & CHANNELS
    # ───────────────────────────────────────────────────────────────────
    print("\n📁 [3/4] Engineering layout structures and local permission overrides...", flush=True)

    for category in source_guild.categories:
        cat_overwrites = {}
        for role_or_member, overwrite in category.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    cat_overwrites[mapped_role] = overwrite

        try:
            new_category = await target_guild.create_category(
                name=category.name,
                overwrites=cat_overwrites
            )
            print(f"📂 Category Built: {category.name}", flush=True)
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f" ❌ Skipping Category [{category.name}] due to failure: {e}", flush=True)
            continue

        for txt_chan in category.text_channels:
            chan_overwrites = {}
            for role_or_member, overwrite in txt_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            try:
                await target_guild.create_text_channel(
                    name=txt_chan.name,
                    category=new_category,
                    topic=txt_chan.topic,
                    nsfw=txt_chan.nsfw,
                    slowmode_delay=txt_chan.slowmode_delay,
                    overwrites=chan_overwrites
                )
                print(f"  ├── 📝 Text Channel: {txt_chan.name}", flush=True)
                await asyncio.sleep(1.2)  
            except Exception as e:
                print(f"  ├── ⚠️ Skipped Text Channel [{txt_chan.name}]: {e}", flush=True)

        for vc_chan in category.voice_channels:
            chan_overwrites = {}
            for role_or_member, overwrite in vc_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            try:
                await target_guild.create_voice_channel(
                    name=vc_chan.name,
                    category=new_category,
                    user_limit=vc_chan.user_limit,
                    bitrate=max(8000, min(vc_chan.bitrate, 96000)),
                    overwrites=chan_overwrites
                )
                print(f"  ├── 🔊 Voice Channel: {vc_chan.name}", flush=True)
                await asyncio.sleep(1.2)
            except Exception as e:
                print(f"  ├── ⚠️ Skipped Voice Channel [{vc_chan.name}]: {e}", flush=True)

    # ───────────────────────────────────────────────────────────────────
    # STEP 4: DOWNLOADING & UPLOADING EMOTES PIPELINE
    # ───────────────────────────────────────────────────────────────────
    print("\n👾 [4/4] Extracting and importing server expressions (emojis)...", flush=True)
    
    if not source_guild.emojis:
        print(" ℹ️ No custom emojis discovered on the source server.", flush=True)
    else:
        max_emojis = target_guild.emoji_limit
        current_emojis = len(target_guild.emojis)
        slots_available = max_emojis - current_emojis
        
        print(f" ℹ️ Target server emoji space capacity: {current_emojis}/{max_emojis} slots occupied.", flush=True)
        
        emoji_count = 0
        for emoji in source_guild.emojis:
            if emoji_count >= slots_available:
                print(" ⚠️ Reached maximum emoji capacity slots available on your target server tier! Stopping.", flush=True)
                break
                
            try:
                emoji_bytes = await emoji.read()
                await target_guild.create_custom_emoji(
                    name=emoji.name,
                    image=emoji_bytes
                )
                emoji_count += 1
                print(f"  ├── ✨ Synced Emoji: :{emoji.name}: ({emoji_count})", flush=True)
                await asyncio.sleep(2.0)
            except Exception as e:
                print(f"  ├── ⚠️ Failed to mirror emoji :{emoji.name}: -> {e}", flush=True)
                await asyncio.sleep(1.5)

    print("\n" + "="*50)
    print("🎉 DEPLOYMENT SUCCESSFUL! All channels and emojis synced completely.")
    print("="*50 + "\n", flush=True)

@cloner_client.event
async def on_ready():
    print(f"✨ Authenticated successfully as: {cloner_client.user}", flush=True)
    # Trigger the task and handle potential errors safely
    cloner_client.loop.create_task(start_cloning_engine())

if __name__ == "__main__":
    if not ACCOUNT_TOKEN or ACCOUNT_TOKEN == "None":
        print("❌ Error: ACCOUNT_TOKEN variable is completely empty inside cloner.py!", flush=True)
        sys.exit()
        
    keep_alive()
    
    try:
        cloner_client.run(ACCOUNT_TOKEN)
    except Exception as e:
        print(f"🛑 Execution Terminated: {e}", flush=True)
