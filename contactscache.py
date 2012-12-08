import gdata.contacts.data
import gdata.contacts.client
import phonenumbers

class ContactsCache():
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.client = gdata.contacts.client.ContactsClient()
        self.contacts = {}

    def refresh(self):
        if not self.email or not self.password:
            return

        self.client.ClientLogin(self.email, self.password, self.client.source)
        query = gdata.contacts.client.ContactsQuery()
        feed = self.client.GetContacts(q = query)
        while feed:
            for entry in feed.entry:
                self.process_contact(entry)
            nextlink = feed.GetNextLink()
            feed = None
            if nextlink:
                feed = self.client.GetContacts(uri = nextlink.href)

    def process_contact(self, entry):
        if entry.title and entry.title.text and entry.phone_number:
            unformatted = entry.phone_number[0].text
            phone_number = phonenumbers.parse(unformatted, 'US')
            formatted = phonenumbers.format_number(
                phone_number,
                phonenumbers.PhoneNumberFormat.NATIONAL)
            photo = None
            try:
                photo = self.client.GetPhoto(entry)
            except gdata.client.RequestError:
                pass
            self.contacts[formatted] = dict(
                name = entry.title.text,
                number = formatted,
                photo = photo)
    
    def find_contact(self, unformatted):
        phone_number = phonenumbers.parse(unformatted, 'US')
        formatted = phonenumbers.format_number(
            phone_number,
            phonenumbers.PhoneNumberFormat.NATIONAL)
        if formatted in self.contacts:
            contact = self.contacts[formatted]
            return (contact['name'], contact['number'], contact['photo'])
        else:
            return ('Unknown', formatted, None)
