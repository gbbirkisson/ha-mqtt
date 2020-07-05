from mqtt import Mqtt


class MockMqtt(Mqtt):
    def __init__(self, test):
        self.test = test
        self._topics = {}
        self.messages = {}
        self.subscriptions = {}

    def get_published_messages(self, topic):
        return self.messages.get(topic)

    def assert_messages(self, topic, l):
        self.test.assertEqual(l, self.get_published_messages(topic))

    def subscribe(self, topic, func):
        subs = self.subscriptions.get(topic, [])
        subs.append(func)
        self.subscriptions[topic] = subs

    def publish(self, topic, message):
        messages = self.messages.get(topic, [])
        messages.append(message)
        self.messages[topic] = messages

        subs = self.subscriptions.get(topic, [])
        for sub in subs:
            sub(message)
