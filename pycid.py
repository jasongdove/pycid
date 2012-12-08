import sys
import os
import re
import argparse
import pyinotify
import gntp.notifier
import phonenumbers

class PTmp(pyinotify.ProcessEvent):
  def __init__(self, file_path, debug, growl):
    self.file_path = file_path
    self.file_handle = open(self.file_path, 'r')
    self.file_handle.seek(0, 2)
    self.debug = debug
    self.growl = growl

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
        phone_number = phonenumbers.parse(number, 'US')
        formatted_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.NATIONAL)
        print 'incoming call from: ' + formatted_number
        self.growl.notify(
          noteType = 'Incoming Call',
          title = 'You have an incoming call',
          description = 'From ' + formatted_number,
          sticky = False,
          priority = 1
        )
#    print line
      

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('logfile', help = 'the pap2t log file to watch')
  parser.add_argument('growl_hostname', help = 'hostname that will receive growl notifications', type = str)
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

  if args.verbose:
    print 'Watching ' + args.logfile

  wm = pyinotify.WatchManager()
  dirmask = pyinotify.IN_MODIFY | pyinotify.IN_DELETE | pyinotify.IN_MOVE_SELF | pyinotify.IN_CREATE

  pt = PTmp(args.logfile, args.verbose, growl)

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
