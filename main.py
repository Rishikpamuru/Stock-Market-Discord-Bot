import discord
import config
from discord.ext import commands
import sqlite3
import time
import os
import random
# Database file
db_file = 'users.db'
ALLOWED_CHANNELS = [1331140740587196416, 1331148632883331155]

# Set up bot intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize the bot with command prefix
bot = commands.Bot(command_prefix="-", intents=intents)

# Available stocks
STOCKS = {
    'rgi': 'Reedy Gangstas Inc',
    'wb': 'Weylin Businesses',
    'gbc': 'Good Boy Corp'
}

def connect_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # Create updated tables with explicit column definitions
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 50,
            last_pay_time INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS stock_prices (
            stock_name TEXT PRIMARY KEY,
            value INTEGER DEFAULT 50
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS user_stocks (
            user_id INTEGER,
            stock_name TEXT,
            amount INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, stock_name),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Initialize stock prices if they don't exist
    for stock_code in STOCKS.keys():
        c.execute("INSERT OR IGNORE INTO stock_prices (stock_name, value) VALUES (?, 50)", (stock_code,))

    conn.commit()
    return conn

def load_data():
    conn = connect_db()
    c = conn.cursor()

    # Get all stock prices
    stock_prices = {}
    c.execute("SELECT stock_name, value FROM stock_prices")
    for row in c.fetchall():
        stock_prices[row[0]] = row[1]

    # Fetch user data
    users = {}
    c.execute("SELECT id, balance, last_pay_time FROM users")
    for row in c.fetchall():
        user_id, balance, last_pay_time = row
        users[user_id] = {
            'balance': balance,
            'last_pay_time': last_pay_time,
            'stocks': {}
        }

    # Fetch user stocks
    c.execute("SELECT user_id, stock_name, amount FROM user_stocks")
    for row in c.fetchall():
        user_id, stock_name, amount = row
        if user_id in users:
            users[user_id]['stocks'][stock_name] = amount

    conn.close()
    return stock_prices, users

def save_data(stock_prices, users):
    conn = connect_db()
    c = conn.cursor()

    # Update stock prices
    for stock_name, value in stock_prices.items():
        c.execute("INSERT OR REPLACE INTO stock_prices (stock_name, value) VALUES (?, ?)",
                 (stock_name, value))

    # Update user data
    for user_id, data in users.items():
        c.execute("INSERT OR REPLACE INTO users (id, balance, last_pay_time) VALUES (?, ?, ?)",
                 (user_id, data['balance'], data['last_pay_time']))
        
        # Update user stocks
        for stock_name, amount in data['stocks'].items():
            c.execute("INSERT OR REPLACE INTO user_stocks (user_id, stock_name, amount) VALUES (?, ?, ?)",
                     (user_id, stock_name, amount))

    conn.commit()
    conn.close()

# Load initial data
stock_prices, users = load_data()

@bot.command()
async def stock(ctx, stock_code=None):
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return
    if stock_code is None:
        stocks_list = ["Available Stocks:"]
        for code, name in STOCKS.items():
            price = stock_prices.get(code, 50)
            stocks_list.append(f"• {name} ({code.upper()}): ${price}")
        
        await ctx.send(f"```\n{chr(10).join(stocks_list)}\n```")
    else:
        stock_code = stock_code.lower()
        if stock_code in STOCKS:
            price = stock_prices.get(stock_code, 50)
            await ctx.send(f"```\nStock Information:\n• Name: {STOCKS[stock_code]}\n• Code: {stock_code.upper()}\n• Current Price: ${price}\n```")
        else:
            await ctx.send("```\nError: Invalid stock code.\nUse -stock to see available stocks.\n```")

@bot.command()
async def buy(ctx, stock_code: str, amount: int = 1):
    stock_code = stock_code.lower()
    user_id = ctx.author.id
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return
    if user_id not in users:
        users[user_id] = {'balance': 50, 'last_pay_time': 0, 'stocks': {}}
    if 'stocks' not in users[user_id]:
        users[user_id]['stocks'] = {}

    if stock_code not in STOCKS:
        await ctx.send("```\nError: Invalid stock code.\nUse -stock to see available stocks.\n```")
        return

    if amount <= 0:
        await ctx.send("```\nError: Invalid amount.\nYou need to buy at least one stock.\n```")
        return

    price = stock_prices.get(stock_code, 50)

    # Randomly increase the price between 1 and 5
    #price_increase = random.randint(1, 5)
    price += amount

    total_cost = amount * price

    if users[user_id]['balance'] >= total_cost:
        if stock_code not in users[user_id]['stocks']:
            users[user_id]['stocks'][stock_code] = 0
        users[user_id]['stocks'][stock_code] += amount
        users[user_id]['balance'] -= total_cost
        stock_prices[stock_code] = price  # Update stock price after the purchase
        save_data(stock_prices, users)
        
        await ctx.send(f"```\nTransaction Successful:\n• Bought: {amount} {STOCKS[stock_code]} stock(s)\n• Cost per share: ${price}\n• Total cost: ${total_cost}\n• Remaining balance: ${users[user_id]['balance']}\n```")
    else:
        await ctx.send(f"```\nError: Insufficient funds\n• Cost per share: ${price}\n• Total cost needed: ${total_cost}\n• Your balance: ${users[user_id]['balance']}\n```")


@bot.command()
async def sell(ctx, stock_code: str, amount: int = 1):
    stock_code = stock_code.lower()
    user_id = ctx.author.id
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return
    if user_id not in users or 'stocks' not in users[user_id]:
        await ctx.send("```\nError: No stocks owned.\nUse -stock to see available stocks to buy.\n```")
        return

    if stock_code not in STOCKS:
        await ctx.send("```\nError: Invalid stock code.\nUse -stock to see available stocks.\n```")
        return

    if amount <= 0:
        await ctx.send("```\nError: Invalid amount.\nYou need to sell at least one stock.\n```")
        return

    user_stock_amount = users[user_id]['stocks'].get(stock_code, 0)
    if user_stock_amount >= amount:
        # Get the current price of the stock
        price = stock_prices.get(stock_code, 50)

        # Randomly decrease the price between 1 and 10
        price -= amount
        
        # Ensure the price doesn't go below 0
        if price < 0:
            price = 0

        total_value = amount * price
        
        # Update user's stock and balance
        users[user_id]['stocks'][stock_code] -= amount
        users[user_id]['balance'] += total_value
        stock_prices[stock_code] = price  # Update stock price after the sale
        save_data(stock_prices, users)
        
        await ctx.send(f"```\nTransaction Successful:\n• Sold: {amount} {STOCKS[stock_code]} stock(s)\n• Price per share: ${price}\n• Total received: ${total_value}\n• New balance: ${users[user_id]['balance']}\n```")
    else:
        await ctx.send(f"```\nError: Insufficient stocks\n• Owned: {user_stock_amount} shares\n• Attempted to sell: {amount} shares\n• Stock: {STOCKS[stock_code]}\n```")



@bot.command()
async def mvalue(ctx):
    user_id = ctx.author.id
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return
    if user_id not in users:
        users[user_id] = {'balance': 50, 'last_pay_time': 0, 'stocks': {}}
    
    portfolio = [f"Current Balance: ${users[user_id]['balance']}"]
    portfolio.append("\nYour Stock Portfolio:")
    
    if not users[user_id].get('stocks'):
        portfolio.append("• No stocks owned")
    else:
        total_portfolio_value = users[user_id]['balance']
        for stock_code, amount in users[user_id]['stocks'].items():
            if amount > 0:
                stock_name = STOCKS[stock_code]
                current_price = stock_prices.get(stock_code, 50)
                total_value = amount * current_price
                total_portfolio_value += total_value
                portfolio.append(f"• {stock_name} ({stock_code.upper()}):")
                portfolio.append(f"  - Shares owned: {amount}")
                portfolio.append(f"  - Current price: ${current_price}")
                portfolio.append(f"  - Total value: ${total_value}")
        
        portfolio.append(f"\nTotal Portfolio Value: ${total_portfolio_value}")
    
    await ctx.send(f"```\n{chr(10).join(portfolio)}\n```")

@bot.command()
async def reset(ctx):
    # Check if the user has administrator permissions
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return
    if ctx.author.guild_permissions.administrator:
        global users, stock_prices
        users = {}
        stock_prices = {code: 50 for code in STOCKS.keys()}
        save_data(stock_prices, users)
        await ctx.send("```\nReset Successful:\n• All stock prices reset to $50\n• All user balances reset to $50\n• All stock holdings cleared\n```")
    else:
        await ctx.send(f"```\nError: You need administrator permissions to use this command.\n```")

@bot.command()
async def dock(ctx, member: discord.Member, amount: int):
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return    
    # Check if the author has administrator permissions
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("```\nError: You need administrator permissions to use this command.\n```")
        return

    # Ensure the amount is positive
    if amount <= 0:
        await ctx.send("```\nError: You must specify a positive amount to dock.\n```")
        return

    # Ensure the member has a balance
    if member.id not in users:
        users[member.id] = {'balance': 50, 'last_pay_time': 0, 'stocks': {}}

    # Check if the user has enough balance to be docked
    if users[member.id]['balance'] < amount:
        await ctx.send(f"```\nError: {member.name} does not have enough balance to dock {amount}.\n```")
        return

    # Deduct the amount from the member's balance
    users[member.id]['balance'] -= amount

    # Save the changes
    save_data(stock_prices, users)

    # Notify the server
    await ctx.send(f"```\nAdmin Dock Successful:\n• {amount} was removed from {member.name}'s balance\n• New balance for {member.name}: ${users[member.id]['balance']}\n```")

@bot.command()
async def pay(ctx, member: discord.Member = None, amount: int = 50):
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return    
    # Ensure the amount is positive
    if amount <= 0:
        await ctx.send("```\nError: The amount must be a positive number.\n```")
        return

    user_id = ctx.author.id
    current_time = time.time()

    # If no member is specified, pay the command issuer (the user who called the command)
    if member is None:
        member = ctx.author

    # Ensure both users exist in the users data
    if user_id not in users:
        users[user_id] = {'balance': 50, 'last_pay_time': 0, 'stocks': {}}
    
    if member.id not in users:
        users[member.id] = {'balance': 50, 'last_pay_time': 0, 'stocks': {}}

    last_pay_time = users[user_id]['last_pay_time']

    # If the user is not an admin and trying to pay too soon, enforce cooldown
    if not ctx.author.guild_permissions.administrator:
        if current_time - last_pay_time < 86400:
            time_remaining = 86400 - (current_time - last_pay_time)
            hours = int(time_remaining // 3600)
            minutes = int((time_remaining % 3600) // 60)
            await ctx.send(f"```\nPayment Cooldown:\n• Time remaining: {hours} hours and {minutes} minutes\n```")
            return

    # Admin can pay any amount
    if ctx.author.guild_permissions.administrator:
        users[member.id]['balance'] += amount
        await ctx.send(f"```\nAdmin Payment Received:\n• Amount: ${amount}\n• New balance for {member.name}: ${users[member.id]['balance']}\n```")
    else:
        # Non-admins will only be able to pay themselves after the cooldown
        users[user_id]['balance'] += 50
        users[user_id]['last_pay_time'] = current_time
        await ctx.send(f"```\nPayment Received:\n• Amount: $50\n• New balance: ${users[user_id]['balance']}\n```")

    save_data(stock_prices, users)



@bot.command()
async def cmds(ctx):
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return    
    commands = [
        "Available Commands:",
        "• -stock - View all stocks",
        "• -stock [code] - View specific stock details",
        "• -buy [code] [amount] - Buy stocks",
        "• -sell [code] [amount] - Sell stocks",
        "• -mvalue - View your portfolio",
        "• -pay - Receive daily payment",
        "• -transfer - transfer monet to another user",
        "• -cmds - Show this command list"
    ]
    await ctx.send(f"```\n{chr(10).join(commands)}\n```")
@bot.command()
async def admin(ctx):
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return    
    commands = [
        "Available Commands:",
        "• -dock [User] - take money from a user",
        "• -pay [User] - gives user money",
        "• -reset - resets the ENTIRE market and all user holdings"
    ]
    await ctx.send(f"```\n{chr(10).join(commands)}\n```")
@bot.command()
async def transfer(ctx, recipient: discord.Member, amount: int):
    if ctx.channel.id not in ALLOWED_CHANNELS:
        await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
        return    
    sender_id = ctx.author.id
    recipient_id = recipient.id

    # Check if both users exist in the users data
    if sender_id not in users:
        users[sender_id] = {'balance': 50, 'last_pay_time': 0, 'stocks': {}}
    
    if recipient_id not in users:
        users[recipient_id] = {'balance': 50, 'last_pay_time': 0, 'stocks': {}}
    
    sender_balance = users[sender_id]['balance']

    # Check if the sender has enough balance
    if amount <= 0:
        await ctx.send(f"```\nError: You need to transfer a positive amount of money.\n```")
        return

    if sender_balance < amount:
        await ctx.send(f"```\nError: Insufficient funds.\n• Your balance: ${sender_balance}\n• Transfer amount: ${amount}\n```")
        return

    # Deduct the amount from the sender and add it to the recipient
    users[sender_id]['balance'] -= amount
    users[recipient_id]['balance'] += amount

    # Save the data
    save_data(stock_prices, users)

    await ctx.send(f"```\nTransfer Successful:\n• Transferred: ${amount} to {recipient.name}\n• Your new balance: ${users[sender_id]['balance']}\n• {recipient.name}'s new balance: ${users[recipient_id]['balance']}\n```")




# Replace with your bot token
bot.run(config.api)