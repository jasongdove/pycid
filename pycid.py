import re
import argparse
import time
from contactscache import ContactsCache
from notifier import Notifier

def process_line(line, contacts, notifier):
    if 'INVITE sip' in line:
        result = re.search(r'From: ".*" <sip:(.*?)@', line)
        if result:
            number = result.group(1)
            detail = ''
            image = None
            (name, formatted_number, image) = contacts.find_contact(number)
            detail = name + "\n" + formatted_number
            print 'incoming call from: ' + detail.replace('\n', ' - ')
            notifier.notify(detail, image)
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
        '-n',
        '--namespace',
        help = 'Azure Service Bus namespace',
        type = str,
        dest = 'service_bus_namespace')
    parser.add_argument(
        '-k',
        '--account-key',
        help = 'Azure Service Bus account key',
        type = str,
        dest = 'service_bus_account_key')
    parser.add_argument(
        '-i',
        '--issuer',
        help = 'Azure Service bus issuer',
        dest = 'service_bus_issuer')
    parser.add_argument(
        '-t',
        '--service-bus-topic',
        help = 'Azure Service Bus topic',
        dest = 'service_bus_topic')
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

    notifier = Notifier(args)

    contacts = ContactsCache(args.username, args.password)
    contacts.refresh()

    if args.verbose:
        print 'Watching ' + args.logfile

    file_handle = open(args.logfile, 'r')

    try:
        loglines = follow(file_handle)
        for line in loglines:
            process_line(line, contacts, notifier)
    except KeyboardInterrupt:
        print ''

if __name__ == '__main__':
    main()
