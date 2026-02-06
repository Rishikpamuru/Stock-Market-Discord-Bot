import discord
import sqlite3
from discord.ext import commands
import time
import random

# Define constants and shared data
STOCKS = {
    'rgi': 'Reedy Gangstas Inc',
    'wb': 'Weylin Businesses',
    'gbc': 'Good Boy Corp',
    'vi': 'Vidur Industries',
    'sp': 'sparkyCORP' 
}
db_file = 'users.db'
ALLOWED_CHANNELS = [1331140740587196416, 1331148632883331155,1468486620930904260]

# Shared data
stock_prices = {}
users = {}

# Database connection
def connect_db():
    conn = sqlite3.connect(db_file)
    return conn

def load_data():
    global stock_prices, users
    conn = connect_db()
    c = conn.cursor()

    # Load stock prices
    c.execute("SELECT stock_name, value FROM stock_prices")
    stock_prices = {row[0]: row[1] for row in c.fetchall()}

    # Load user data
    c.execute("SELECT id, balance, last_pay_time FROM users")
    users = {row[0]: {'balance': row[1], 'last_pay_time': row[2], 'stocks': {}} for row in c.fetchall()}

    # Load user stocks
    c.execute("SELECT user_id, stock_name, amount FROM user_stocks")
    for row in c.fetchall():
        user_id, stock_name, amount = row
        if user_id in users:
            users[user_id]['stocks'][stock_name] = amount

    conn.close()

def save_data(stock_prices, users):
    conn = connect_db()
    c = conn.cursor()

    # Save stock prices
    for stock_name, value in stock_prices.items():
        c.execute("INSERT OR REPLACE INTO stock_prices (stock_name, value) VALUES (?, ?)", (stock_name, value))

    # Save user data
    for user_id, data in users.items():
        c.execute("INSERT OR REPLACE INTO users (id, balance, last_pay_time) VALUES (?, ?, ?)",
                  (user_id, data['balance'], data['last_pay_time']))
        for stock_name, amount in data['stocks'].items():
            c.execute("INSERT OR REPLACE INTO user_stocks (user_id, stock_name, amount) VALUES (?, ?, ?)",
                      (user_id, stock_name, amount))

    conn.commit()
    conn.close()

# Bot commands
def setup_commands(bot):
    global stock_prices, users

    load_data()
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
        total_cost = 0
        temp_price = price
        # Simulate price increase for each share to calculate total cost
        for _ in range(amount):
            total_cost += temp_price
            temp_price = temp_price + 1 + random.randint(1, 10)

        if users[user_id]['balance'] >= total_cost:
            if stock_code not in users[user_id]['stocks']:
                users[user_id]['stocks'][stock_code] = 0
            users[user_id]['stocks'][stock_code] += amount
            users[user_id]['balance'] -= total_cost
            # Set the new price to original + moderate increase (not full temp_price)
            new_price = price + (amount // 2) + random.randint(1, 5)
            stock_prices[stock_code] = new_price
            save_data(stock_prices, users)
            
            await ctx.send(f"```\nTransaction Successful:\n• Bought: {amount} {STOCKS[stock_code]} stock(s)\n• Total cost: ${total_cost}\n• Remaining balance: ${users[user_id]['balance']}\n```")
        else:
            await ctx.send(f"```\nError: Insufficient funds\n• Total cost needed: ${total_cost}\n• Your balance: ${users[user_id]['balance']}\n```")

    @bot.command()
    async def buymax(ctx, stock_code: str):
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
        balance = users[user_id]['balance']
        price = stock_prices.get(stock_code, 50)
        amount = 0
        total_cost = 0
        temp_price = price
        # Simulate price increase for each share
        while balance >= temp_price:
            balance -= temp_price
            total_cost += temp_price
            amount += 1
            temp_price = temp_price + 1 + random.randint(1, 10)
        if amount < 1:
            await ctx.send(f"```\nError: Insufficient funds\n• Cost per share: ${price}\n• Your balance: ${users[user_id]['balance']}\n```")
            return
        users[user_id]['stocks'][stock_code] = users[user_id]['stocks'].get(stock_code, 0) + amount
        users[user_id]['balance'] -= total_cost
        # Set the new price to original + moderate increase (not full temp_price)
        new_price = price + (amount // 2) + random.randint(1, 5)
        stock_prices[stock_code] = new_price
        save_data(stock_prices, users)
        await ctx.send(f"```\nTransaction Successful:\n• Bought: {amount} {STOCKS[stock_code]} stock(s)\n• Total cost: ${total_cost}\n• Remaining balance: ${users[user_id]['balance']}\n```")

    @bot.command()
    async def arrest(ctx, member: discord.Member = None):
        x = member
        if ctx.channel.id not in ALLOWED_CHANNELS:
            await ctx.send("\nError: Bot can only be used in #stocks.\n")
            return
        if member is None:
            await ctx.send("\nError: You need to specify a member to arrest.\n```")
        else:
            await ctx.send(f"```\n{x} is arrested!!!\n```")
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
            total_value = 0
            temp_price = price
            # Simulate price decrease for each share sold
            for _ in range(amount):
                total_value += temp_price
                temp_price = temp_price - 1 - random.randint(1, 10)
                if temp_price < 0:
                    temp_price = 0
            users[user_id]['stocks'][stock_code] -= amount
            users[user_id]['balance'] += total_value
            # Now update the price for future transactions
            stock_prices[stock_code] = temp_price
            save_data(stock_prices, users)
            
            await ctx.send(f"```\nTransaction Successful:\n• Sold: {amount} {STOCKS[stock_code]} stock(s)\n• Price per share: ${price}\n• Total received: ${total_value}\n• New balance: ${users[user_id]['balance']}\n```")
        else:
            await ctx.send(f"```\nError: Insufficient stocks\n• Owned: {user_stock_amount} shares\n• Attempted to sell: {amount} shares\n• Stock: {STOCKS[stock_code]}\n```")

    @bot.command()
    async def sellmax(ctx, stock_code: str):
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
        user_stock_amount = users[user_id]['stocks'].get(stock_code, 0)
        if user_stock_amount < 1:
            await ctx.send(f"```\nError: You do not own any shares of {STOCKS[stock_code]}.\n```")
            return
        price = stock_prices.get(stock_code, 50)
        total_value = 0
        temp_price = price
        amount = user_stock_amount
        # Simulate price decrease for each share
        for _ in range(amount):
            total_value += temp_price
            temp_price = temp_price - 1 - random.randint(1, 10)
            if temp_price < 0:
                temp_price = 0
        users[user_id]['stocks'][stock_code] = 0
        users[user_id]['balance'] += total_value
        stock_prices[stock_code] = temp_price
        save_data(stock_prices, users)
        await ctx.send(f"```\nTransaction Successful:\n• Sold: {amount} {STOCKS[stock_code]} stock(s)\n• Total received: ${total_value}\n• New balance: ${users[user_id]['balance']}\n```")

    @bot.command()
    async def mvalue(ctx, member: discord.Member = None):
        user_id = ctx.author.id
        boolean1 = False
        if member is not None:
            user_id = member.id
            boolean1 = True
        if ctx.channel.id not in ALLOWED_CHANNELS:
            await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
            return
    

        if user_id not in users:
            users[user_id] = {'balance': 50, 'last_pay_time': 0, 'stocks': {}}
        
        portfolio = [f"Current Balance: ${users[user_id]['balance']}"]
        if boolean1 == True:
            portfolio.append(f"\n{member.name}'s Stock Portfolio:")
        else:
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
            "• -buymax [code] - Buy the maximum number of stocks you can afford",
            "• -sell [code] [amount] - Sell stocks",
            "• -sellmax [code] - Sell all stocks you own of a type",
            "• -mvalue - View your portfolio",
            "• -mvalue [user] - View a user's portfolio",
            "• -pay - Receive daily payment",
            "• -transfer [user] - transfer monet to another user",
            "• -arrest [user] - arrest a user",
            "• -shop - things you can buy",
            "• -shop [item] - buy thing",
            "• -cmds - Show this command list"
        ]
        await ctx.send(f"```\n{chr(10).join(commands)}\n```")
    @bot.command()
    async def shop(ctx, item: str = None):
        user_id = ctx.author.id
        if ctx.channel.id not in ALLOWED_CHANNELS:
            await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
            return

        # Ensure user data exists
        if user_id not in users:
            users[user_id] = {'balance': 50, 'last_pay_time': 0, 'stocks': {}}

        # Shop items and their prices
        SHOP = {
            "shareholder": 3500,
            "custom role": 1200,
            "modification": 5000,
            "become cto": 10000
        }

        # If no item is provided, list available items
        if item is None:
            shop_list = ["Shop (use -shop [item] to buy):"]
            for key, value in SHOP.items():
                shop_list.append(f"• {key.title()} - ${value}")
            await ctx.send(f"```\n{chr(10).join(shop_list)}\n```")
            return

        # Attempt to purchase the specified item
        item = item.lower()
        if item not in SHOP:
            await ctx.send(f"```\nError: Invalid item.\nAvailable items:\n{chr(10).join([f'• {key.title()} - ${value}' for key, value in SHOP.items()])}\n```")
            return

        price = SHOP[item]

        # Check if the user has enough balance
        if users[user_id]['balance'] < price:
            await ctx.send(f"```\nError: Insufficient funds.\n• Item cost: ${price}\n• Your balance: ${users[user_id]['balance']}\n```")
            return

        # Process the purchase
        users[user_id]['balance'] -= price
        save_data()  # Save the updated balance

        # Handle item-specific actions
        if item == "shareholder":
            await ctx.send(f"```\nPurchase Successful:\n• You are now the Shareholder! The poorest shareholder has been replaced.\n• Remaining balance: ${users[user_id]['balance']}\n```")
        elif item == "custom role":
            await ctx.send(f"```\nPurchase Successful:\n• You can now create your own custom role.\n• Remaining balance: ${users[user_id]['balance']}\n```")
        elif item == "modification":
            await ctx.send(f"```\nPurchase Successful:\n• You forced a modification on the bot. Changes will be made soon!\n• Remaining balance: ${users[user_id]['balance']}\n```")
        elif item == "become cto":
            await ctx.send(f"```\nPurchase Successful:\n• Congratulations! You are now the CTO of the bot.\n• Remaining balance: ${users[user_id]['balance']}\n```")

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

    @bot.command()
    async def setprice(ctx, stock_code: str, new_price: int):
        if ctx.channel.id not in ALLOWED_CHANNELS:
            await ctx.send("```\nError: Bot can only be used in #stocks.\n```")
            return
        if not ctx.author.guild.permissions.administrator:
            await ctx.send("```\nError: You need administrator permissions to use this command.\n```")
            return
        stock_code = stock_code.lower()
        if stock_code not in STOCKS:
            await ctx.send("```\nError: Invalid stock code.\nUse -stock to see available stocks.\n```")
            return
        if new_price < 0:
            await ctx.send("```\nError: Price must be non-negative.\n```")
            return
        stock_prices[stock_code] = new_price
        save_data(stock_prices, users)
        await ctx.send(f"```\nAdmin Price Change Successful:\n• {STOCKS[stock_code]} ({stock_code.upper()}) price set to ${new_price}\n```")


