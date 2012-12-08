import sys, os, pyinotify, re
from optparse import OptionParser

class PTmp(pyinotify.ProcessEvent):
  def __init__(self, file_path, debug):
    self.file_path = file_path
    self.file_handle = open(self.file_path, 'r')
    self.file_handle.seek(0, 2)
    self.debug = debug

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
        print 'incoming call from: ' + number
#    print line
      

def main():
  parser = OptionParser()
  parser.add_option('-d', '--debug', help = 'print debug messages', dest = 'debug')
  (options, args) = parser.parse_args()

  if len(sys.argv) < 2:
    parser.print_usage()
    sys.exit(1)

  myfile = args[0]
  if options.debug:
    print 'Watching ' + myfile

  wm = pyinotify.WatchManager()

  dirmask = pyinotify.IN_MODIFY | pyinotify.IN_DELETE | pyinotify.IN_MOVE_SELF | pyinotify.IN_CREATE

  pt = PTmp(myfile, options.debug)

  notifier = pyinotify.Notifier(wm, pt)

  index = myfile.rfind('/')
  wm.add_watch(myfile[:index], dirmask)

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
