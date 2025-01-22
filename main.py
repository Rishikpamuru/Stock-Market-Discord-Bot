import discord
from discord.ext import commands
import sqlite3
import config
import os
from commands import setup_commands

# Database file
db_file = 'users.db'
ALLOWED_CHANNELS = [1331140740587196416, 1331148632883331155]

# Set up bot intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize the bot with command prefix
bot = commands.Bot(command_prefix="-", intents=intents)

# Load commands from the commands file
setup_commands(bot)

# Run the bot
bot.run(config.api)
