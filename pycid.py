import re
import argparse
import gntp.notifier
import time
from contactscache import ContactsCache

def process_line(line, contacts, growl):
    if 'INVITE sip' in line:
        result = re.search(r'From: ".*" <sip:(.*?)@', line)
        if result:
            number = result.group(1)
            detail = ''
            image = None
            (name, formatted_number, image) = contacts.find_contact(number)
            detail = name + "\n" + formatted_number
            print 'incoming call from: ' + detail.replace('\n', ' - ')
            growl.notify(
                noteType = 'Incoming Call',
                title = 'You have an incoming call',
                description = detail,
                sticky = False,
                priority = 1,
                icon = image)
#    print line

def follow(file_handle):
    file_handle.seek(0, 2)
    while True:
        line = file_handle.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('logfile', help = 'the pap2t log file to watch')
    parser.add_argument(
        'growl_hostname',
        help = 'hostname that will receive growl notifications',
        type = str)
    parser.add_argument(
        '-u',
        '--username',
        help = 'Google username',
        type = str,
        dest = 'username')
    parser.add_argument(
        '-p',
        '--password',
        help = 'Google (application-specific) password',
        type = str,
        dest = 'password')
    parser.add_argument(
        '-v',
        '--verbose',
        help = 'increase output verbosity',
        dest = 'verbose',
        action = 'store_true')
    args = parser.parse_args()

    if args.verbose:
        print 'Registering Growl'

    growl = gntp.notifier.GrowlNotifier(
        applicationName = 'pycid',
        notifications = ['Incoming Call'],
        defaultNotifications = ['Incoming Call'],
        hostname = args.growl_hostname)
    growl.register()

    contacts = ContactsCache(args.username, args.password)
    contacts.refresh()

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
