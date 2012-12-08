import sys
import os
import re
import argparse
import gntp.notifier
import phonenumbers
import gdata.contacts.data
import gdata.contacts.client
import time

def process_line(line, contacts, growl):
  if 'INVITE sip' in line:
    result = re.search(r'From: "(.*)"', line)
    if result:
      number = result.group(1)
      detail = ''
      image = None
      if number in contacts:
        contact = contacts[number]
        detail = contact['name'] + ' ' + contact['number']
        image = contact['photo']
      else:
        phone_number = phonenumbers.parse(number, 'US')
        formatted_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.NATIONAL)
        detail = 'Unknown ' + formatted_number
      print 'incoming call from: ' + detail
      growl.notify(
        noteType = 'Incoming Call',
        title = 'You have an incoming call',
        description = detail,
        sticky = False,
        priority = 1,
        icon = image
      )
#  print line

def get_contacts(verbose, email, password):
  contacts = {}
  
  if email and password:
    if verbose:
      print 'Refreshing Google Contacts'

    client = gdata.contacts.client.ContactsClient()
    client.ClientLogin(email, password, client.source)
    query = gdata.contacts.client.ContactsQuery()
    feed = client.GetContacts(q = query)

    while feed:
      for entry in feed.entry:
        if entry.title and entry.title.text and entry.phone_number:
          unformatted = entry.phone_number[0].text
          phone_number = phonenumbers.parse(unformatted, 'US')
          formatted = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.NATIONAL)
          photo = None
          try:
            photo = client.GetPhoto(entry)
          except gdata.client.RequestError:
            pass
          contacts[unformatted] = dict(name = entry.title.text, number = formatted, photo = photo)
      next = feed.GetNextLink()
      feed = None
      if next:
        feed = client.GetContacts(uri = next.href)

  return contacts

def follow(file_handle):
  file_handle.seek(0,2)
  while True:
    line = file_handle.readline()
    if not line:
      time.sleep(0.1)
      continue
    yield line

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('logfile', help = 'the pap2t log file to watch')
  parser.add_argument('growl_hostname', help = 'hostname that will receive growl notifications', type = str)
  parser.add_argument('-u', '--username', help = 'Google username', type = str, dest = 'username')
  parser.add_argument('-p', '--password', help = 'Google (application-specific) password', type = str, dest = 'password')
  parser.add_argument('-v', '--verbose', help = 'increase output verbosity', dest = 'verbose', action = 'store_true')
  args = parser.parse_args()

  if args.verbose:
    print 'Registering Growl'

  growl = gntp.notifier.GrowlNotifier(
    applicationName = 'pycid',
    notifications = ['Incoming Call'],
    defaultNotifications = ['Incoming Call'],
    hostname = args.growl_hostname
  )
  growl.register()

  contacts = get_contacts(args.verbose, args.username, args.password)

  if args.verbose:
    print 'Watching ' + args.logfile

  file_handle = open(args.logfile, 'r')

  try:
    loglines = follow(file_handle)
    for line in loglines:
      process_line(line, contacts, growl)
  except KeyboardInterrupt:
    print ''

if __name__ == '__main__':
  main()
