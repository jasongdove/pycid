import sys
import os
import re
import argparse
import pyinotify
import gntp.notifier
import phonenumbers
import gdata.contacts.data
import gdata.contacts.client

class PTmp(pyinotify.ProcessEvent):
  def __init__(self, file_path, debug, growl, contacts):
    self.file_path = file_path
    self.file_handle = open(self.file_path, 'r')
    self.file_handle.seek(0, 2)
    self.debug = debug
    self.growl = growl
    self.contacts = contacts

  def process_IN_MODIFY(self, event):
    if self.file_path not in os.path.join(event.path, event.name):
      return
    else:
      self.process_line(self.file_handle.readline().rstrip())

  def process_IN_MOVE_SELF(self, event):
    if self.debug:
      print 'The file moved! Continuing to read from that until a new one is created.'

  def process_IN_CREATE(self, event):
    if self.file_path in os.path.join(event.path, event.name):
      self.file_handle.close()
      self.file_handle = open(self.file_path, 'r')
      if self.debug:
        print 'New file was created; catching up with lines.'
      for line in self.file_handle.readlines():
        self.process_line(line.rstrip())
      self.file_handle.seek(0, 2)
    return

  def close(self):
    self.file_handle.close()

  def process_line(self, line):
    if 'INVITE sip' in line:
      result = re.search(r'From: "(.*)"', line)
      if result:
        number = result.group(1)
        detail = ''
        image = None
        if number in self.contacts:
          contact = self.contacts[number]
          detail = contact['name'] + ' ' + contact['number']
          image = contact['photo']
        else:
          phone_number = phonenumbers.parse(number, 'US')
          formatted_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.NATIONAL)
          detail = 'Unknown ' + formatted_number
        print 'incoming call from: ' + detail
        self.growl.notify(
          noteType = 'Incoming Call',
          title = 'You have an incoming call',
          description = detail,
          sticky = False,
          priority = 1,
          icon = image
        )
#    print line

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

  wm = pyinotify.WatchManager()
  dirmask = pyinotify.IN_MODIFY | pyinotify.IN_DELETE | pyinotify.IN_MOVE_SELF | pyinotify.IN_CREATE

  pt = PTmp(args.logfile, args.verbose, growl, contacts)

  notifier = pyinotify.Notifier(wm, pt)

  index = args.logfile.rfind('/')
  wm.add_watch(args.logfile[:index], dirmask)

  while True:
    try:
      notifier.process_events()
      if notifier.check_events():
        notifier.read_events()
    except KeyboardInterrupt:
      print ''
      break

  notifier.stop()
  pt.close()

  sys.exit(0)



if __name__ == '__main__':
  main()
