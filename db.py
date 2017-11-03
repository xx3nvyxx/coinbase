from peewee import *

db = SqliteDatabase('market.sqlite', **{})

class UnknownField(object):
    def __init__(self, *_, **__): pass

class BaseModel(Model):
    class Meta:
        database = db

class Orders(BaseModel):
    amount = FloatField(null=True)
    created = IntegerField(null=True)
    price = FloatField(null=True)
    status = TextField(null=True)
    txid = TextField(unique=True)

    class Meta:
        db_table = 'Orders'

class SqliteSequence(BaseModel):
    name = UnknownField(null=True)  #
    seq = UnknownField(null=True)  #

    class Meta:
        db_table = 'sqlite_sequence'
        primary_key = False

