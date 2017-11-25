#!/usr/bin/env python
from __future__ import print_function
from datetime import datetime
from time import mktime
from peewee import *
import gdax
import config, db

auth_client = gdax.AuthenticatedClient(config.g_key, config.g_secret,
        config.g_passphrase)

try:
    ga = auth_client.get_accounts()
except ValueError as err:
    print('ValueError: ', err)
    quit()
if (type(ga) is not list):
    print('API Error: ', ga["message"])
    quit()

def main():
    try:
        update_transactions()
        tx = latest_tx()
        if ((datetime.utcnow() - tx['created']).total_seconds() > config.interval):
            if (fill_wallet()):
                order_coins()
            else:
                print( "Error filling wallet. Check if funds are available in Coinbase account.")
                quit()
            update_transactions()
        send_coins()
    except ValueError as err:
        print('ValueError: ', err)
        quit()

def add_transaction(tx):
    order = auth_client.get_order(tx["id"])
    price = float(order["executed_value"]) / float(order["filled_size"])
    created = mktime(datetime.strptime(order["created_at"],"%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
    db.Orders.insert(txid=order["id"], price=price,
            amount=order["filled_size"],
            created=created,
            status=order["status"]).execute()
    print(order["created_at"] + " - " + order["filled_size"] + "BTC bought at " + str(price))

def update_transactions():
    for tx in db.Orders.select().where(db.Orders.status != "done"):
        order = auth_client.get_order(tx.txid)
        price = float(order["executed_value"]) / float(order["filled_size"])
        created = mktime(datetime.strptime(order["created_at"],"%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
        db.Orders.update(price=price,
                amount=order["filled_size"],
                created=created,
                status=order["status"]).where(db.Orders.txid == tx.txid).execute()

def latest_tx():
    ret = dict()
    try:
        tx = db.Orders.select().order_by(db.Orders.created.desc()).get()
        ret['created'] = datetime.utcfromtimestamp(tx.created)
        ret['price'] = tx.price
        return ret
    except DoesNotExist:
        ret['created'] = datetime.utcfromtimestamp(0)
        ret['price'] = float('Inf')
        return ret

def fill_wallet():
    for a in ga:
        if (a.get("currency") == "USD"):
            account_id = a["id"]
            available = float(a["available"])
            break
    if (available < config.amount + config.extra):
        needed = config.amount + config.extra - available
        ca = auth_client.get_coinbase_accounts()
        for a in ca:
            if (a["currency"] == "USD" and float(a["balance"]) >= needed):
                auth_client.coinbase_deposit("{:.2f}".format(needed), "USD", a["id"])
                break
    return float(auth_client.get_account(account_id)["available"]) >= config.amount + config.extra

def order_coins():
    low = float(auth_client.get_product_24hr_stats("BTC-USD")["low"])
    if (low < 1):
        return 0
    current = float(auth_client.get_product_ticker(product_id="BTC-USD")["ask"])
    if ((low * 1.01) >= current):
        buy = auth_client.buy(type="market", funds="{:.2f}".format(config.amount), product_id="BTC-USD")
        if (buy["id"] is not None):
            add_transaction(buy)

def send_coins():
    for a in ga:
        if (a.get("currency") == "BTC" and float(a["available"]) > 0.00005460):
            auth_client.crypto_withdraw(a["available"], "BTC", config.dest)
            print(a["available"] + " BTC sent to " + str(config.dest))

if __name__=="__main__":
    main()
