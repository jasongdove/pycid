import dateutil.parser
import gdata.contacts.data
import gdata.contacts.client
import phonenumbers
import sqlite3
from contextlib import closing
from datetime import datetime

DEFAULT_DATE = datetime(1990, 1, 1)

def _initialize_database():
    connection = sqlite3.connect('pycid.db')
    connection.text_factory = str
    with closing(connection.cursor()) as cursor:
        sql = """create table if not exists contacts (
            id text primary key,
            phone_number text,
            name text,
            photo blob,
            updated timestamp)"""
        cursor.execute(sql)
        sql = """create table if not exists last_updated (
            key int primary key, 
            value timestamp)"""
        cursor.execute(sql)
        sql = 'insert or ignore into last_updated values (?, ?)'
        cursor.execute(sql, (0, datetime(1990, 1, 1)))
        connection.commit()
        return connection

def _normalize_phone_number(unformatted):
    phone_number = phonenumbers.parse(unformatted, 'US')
    formatted = phonenumbers.format_number(
      phone_number,
      phonenumbers.PhoneNumberFormat.NATIONAL)
    return formatted

class ContactsCache():
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.client = gdata.contacts.client.ContactsClient()
        self.connection = _initialize_database()

    def refresh(self):
        if not self.email or not self.password:
            return

        last_refresh = None
        with closing(self.connection.cursor()) as cursor:
            sql = 'select value from last_updated where key = 0'
            cursor.execute(sql)
            last_refresh = dateutil.parser.parse(
                cursor.fetchone()[0],
                default = DEFAULT_DATE).isoformat()

        self.client.ClientLogin(self.email, self.password, self.client.source)
        query = gdata.contacts.client.ContactsQuery()
        query.updated_min = last_refresh
        feed = self.client.GetContacts(q = query)
        feed_updated = dateutil.parser.parse(
            feed.updated.text,
            default = DEFAULT_DATE).isoformat()
        while feed:
            for entry in feed.entry:
                self.process_contact(entry)
            nextlink = feed.GetNextLink()
            feed = None
            if nextlink:
                feed = self.client.GetContacts(uri = nextlink.href)

        with closing(self.connection.cursor()) as cursor:
            sql = 'update last_updated set key = (?), value = (?)'
            cursor.execute(sql, (0, feed_updated))
            self.connection.commit()

    def process_contact(self, entry):
        if entry.title and entry.title.text and entry.phone_number:
            normalized = _normalize_phone_number(entry.phone_number[0].text)
            photo = None
            try:
                photo = self.client.GetPhoto(entry)
            except gdata.client.RequestError:
                pass
            name = entry.title.text
            updated = entry.updated.text
            with closing(self.connection.cursor()) as cursor:
                sql = """insert or replace into contacts
                    (id, phone_number, name, photo, updated)
                    values (?, ?, ?, ?, ?)"""
                cursor.execute(
                   sql,
                   (entry.id.text, normalized, name, photo, updated))
                self.connection.commit()
#                print 'Caching contact ' + name
    
    def find_contact(self, unformatted):
        normalized = _normalize_phone_number(unformatted)
        with closing(self.connection.cursor()) as cursor:
            sql = 'select name, photo from contacts where phone_number = ?'
            cursor.execute(sql, [normalized])
            contact = cursor.fetchone()
            if contact:
                return (contact[0], normalized, contact[1])
            else:
                return ('Unknown', normalized, None)
