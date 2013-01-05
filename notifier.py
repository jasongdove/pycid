import base64
from azure.servicebus import ServiceBusService, Message

class Notifier():
    def __init__(self, args):
        if args.service_bus_namespace:
            if args.verbose:
                print 'Notifying via Azure Service Bus'
            self.topic = args.service_bus_topic
            self.service_bus = ServiceBusService(
                service_namespace=args.service_bus_namespace,
                account_key=args.service_bus_account_key,
                issuer=args.service_bus_issuer)
        else:
            self.service_bus = None

    def notify(self, detail, image):
        title = 'You have an incoming call'
        priority = 1 # high
        if self.service_bus:
            properties = {
                'title': title,
                'priority': priority,
                'image': base64.b64encode(image)
            }
            msg = Message(detail, custom_properties=properties)
            self.service_bus.send_topic_message(self.topic, msg)
