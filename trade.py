#!/usr/bin/env python
from __future__ import print_function
from datetime import datetime
from time import mktime
from peewee import *
import gdax
import config, db

auth_client = gdax.AuthenticatedClient(config.g_key, config.g_secret,
        config.g_passphrase)

ga = auth_client.get_accounts()
if (type(ga) is not list):
    raise Exception(ga["message"])

def main():
    update_transactions()
    if ((datetime.utcnow() - latest_tx()).total_seconds() > config.interval):
        if (fill_wallet()):
            order_coins()
        else:
            print( "Error filling wallet. Check if funds are available in Coinbase account.")
        update_transactions()

def add_transaction(tx):
    order = auth_client.get_order(tx["id"])
    price = float(order["executed_value"]) / float(order["filled_size"])
    created = mktime(datetime.strptime(order["created_at"],"%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
    print(order["created_at"] + " - " + order["filled_size"] + "BTC bought at " + price)
    db.Orders.insert(txid=order["id"], price=price,
            amount=order["filled_size"],
            created=created,
            status=order["status"]).execute()

def update_transactions():
    for tx in db.Orders.select().where(db.Orders.status != "done"):
        order = auth_client.get_order(tx.txid)
        db.Orders.update(status == order.get("status", "done")).where(db.Orders.txid == tx.txid)

def latest_tx():
    try:
        created = db.Orders.select().order_by(db.Orders.created.desc()).get().created
        return datetime.utcfromtimestamp(created)
    except DoesNotExist:
        return datetime.utcfromtimestamp(0)

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


if __name__=="__main__":
    main()
