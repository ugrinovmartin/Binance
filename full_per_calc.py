from binance.client import Client
import re
from typing import Final
from telegram import Update
from telegram.ext import *

API_KEY = ''
API_SECRET = ''
TOKEN: Final = '6617007530:AAErjonDJ3UvgbcTMNurUU-ZhbBIVF95V-g'

RISK_PERCENTAGE = 2.0
TP1_PERCENTAGE = 20.0

client = Client(API_KEY, API_SECRET, tld='futures')


def get_account_size():
    try:

        account_balance = client.futures_account()

        for balance in account_balance['assets']:
            if balance['asset'] == 'USDT':
                return float(balance['walletBalance'])

        return 0.0
    except Exception as e:
        print("Error fetching account balance:", e)
        return 0.0


def calculate_quantity(account_balance, risk_percentage, entry_price, stop_loss_price):
    risk_amount = account_balance * (risk_percentage / 100.0)
    quantity = risk_amount / (entry_price - stop_loss_price)
    return quantity


async def handle_message(update: Update):
    message = update.message.text
    if message is not None and 'VIP Trade ID' in message:
        try:
            pair_match = re.search(r'Pair: \$([^\s(]+)', message)
            if not pair_match:
                raise ValueError("Pair not found")
            pair = pair_match.group(1)

            direction_match = re.search(r'Direction: ([\u2191\u2193⬆⬇]+)', message)
            if not direction_match:
                raise ValueError("Direction not found")
            direction = direction_match.group(1)

            ote_match = re.search(r'OTE: (\d+\.\d+)', message)
            entry_range_match = re.search(r'ENTRY : (\d+\.\d+) - (\d+\.\d+)', message)
            if ote_match:
                entry_price = float(ote_match.group(1))  # Use OTE price as entry price
                # OTE price calculate
            elif entry_range_match:
                entry_price = (float(entry_range_match.group(1)) + float(entry_range_match.group(2))) / 2
            else:
                raise ValueError("OTE and ENTRY price not found")

            stop_loss_match = re.search(r'🚫STOP LOSS: (\d+\.\d+)', message)
            if not stop_loss_match:
                raise ValueError("Stop Loss not found")
            stop_loss = float(stop_loss_match.group(1))

            target_lines = re.findall(r'🔘Target \d+ - (\d+\.\d+)', message)
            if not target_lines:
                raise ValueError("Target prices not found")
            target_prices = [float(tp) for tp in target_lines]

            print("Pair:", pair)
            print("Direction:", direction)
            print("Entry Price:", entry_price)
            print("Stop Loss Price:", stop_loss)
            print("Target Prices:", target_prices)

        except Exception as e:
            print("Error parsing message:", e)

        # TP Targets (TBD)
        tp1_price = float(target_lines[0])  # Take 20%
        tp2_price = float(target_lines[-1])  # Take 80%

        stop_loss_price = float(stop_loss)

        account_size = get_account_size()
        quantity = calculate_quantity(account_size, RISK_PERCENTAGE, entry_price, stop_loss_price)
        # Open Long
        if direction == '⬆️LONG':

            order = client.create_order(
                symbol=pair,
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=entry_price
            )
            print(f"Long position buy order placed: {order}")
        # Open Short
        elif direction == '⬇️SHORT':

            order = client.create_order(
                symbol=pair,
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=entry_price
            )
            print(f"Short position sell order placed: {order}")
        else:
            print("Unknown direction. Could not place an order.")

        # Open TP-1 long
        if direction == '⬆️LONG':

            tp1_order = client.create_order(
                symbol=pair,
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity * (TP1_PERCENTAGE / 100.0),
                price=tp1_price
            )
            print(f"Take profit 1 order placed: {tp1_order}")
        # Open TP-1 short
        elif direction == '⬇️SHORT':
            tp1_order = client.create_order(
                symbol=pair,
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity * (TP1_PERCENTAGE / 100.0),
                price=tp1_price
            )
            print(f"Take profit 1 order placed: {tp1_order}")
        # Open TP-2 long
        if direction == '⬆️LONG':

            tp2_order = client.create_order(
                symbol=pair,
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity * (1 - TP1_PERCENTAGE / 100.0),
                price=tp2_price
            )
            print(f"Take profit 2 order placed: {tp2_order}")
            # Open TP-2 Short
        elif direction == '⬇️SHORT':
            tp2_order = client.create_order(
                symbol=pair,
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity * (TP1_PERCENTAGE / 100.0),
                price=tp1_price
            )
            print(f"Take profit 2 order placed: {tp2_order}")

        # Open SL Long
        if direction == '⬆️LONG':
            stop_loss_order = client.create_order(
                symbol=pair,
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_STOP_MARKET,
                stopPrice=stop_loss_price,
                quantity=quantity
            )
            print(f"Stop loss order placed: {stop_loss_order}")
            # Open SL Short
        elif direction == '⬇️SHORT':
            stop_loss_order = client.create_order(
                symbol=pair,
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_STOP_MARKET,
                stopPrice=stop_loss_price,
                quantity=quantity
            )
            print(f"Stop loss order placed: {stop_loss_order}")


if __name__ == '__main__':
    print('starting')
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print('pooling')
    app.run_polling(poll_interval=3)
