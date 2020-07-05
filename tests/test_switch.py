from unittest import TestCase

from mqtt import MqttSharedTopic
from switch import Switch
from tests.mock_mqtt import MockMqtt
from util import config_creator


class Swi(Switch):
    def __init__(self, sid='test_id', name='test_name', mqtt=None, state_topic=None, **kwargs):
        super().__init__(sid, name, lambda new_state: print(new_state), state_topic=state_topic, mqtt=mqtt,
                         **kwargs)


class TestSwitch(TestCase):
    def test_simple(self):
        mqtt = MockMqtt(self)

        sensor = Swi(mqtt=mqtt)

        with sensor:
            sensor.available_set(True)
            sensor.send_update()
            sensor(True)

        mqtt.assert_messages('homeassistant/switch/test_id/config',
                             [{'command_topic': 'homeassistant/switch/test_id/cmd',
                               'name': 'test_name',
                               'payload_off': 'off',
                               'payload_on': 'on',
                               'state_off': 'off',
                               'state_on': 'on',
                               'state_topic': 'homeassistant/switch/test_id/state'},
                              None])

        mqtt.assert_messages('homeassistant/switch/test_id/state', ["off", "on"])
        mqtt.assert_messages('homeassistant/switch/test_id/available', None)

    def test_shared_topic(self):
        mqtt = MockMqtt(self)

        state = MqttSharedTopic(mqtt, "/my/topic")

        sensor = Swi(mqtt=mqtt, state_topic=state, availability_topic=True)

        with sensor:
            sensor.available_set(True)
            state.publish()

        mqtt.assert_messages('homeassistant/switch/test_id/config',
                             [{'availability_topic': 'homeassistant/switch/test_id/available',
                               'command_topic': 'homeassistant/switch/test_id/cmd',
                               'name': 'test_name',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'payload_off': 'off',
                               'payload_on': 'on',
                               'state_off': 'off',
                               'state_on': 'on',
                               'state_topic': '/my/topic',
                               'value_template': '{{ value_json.test_id }}'},
                              None])

        mqtt.assert_messages('/my/topic', [{"test_id": "off"}])
        mqtt.assert_messages('homeassistant/switch/test_id/available', ["online"])


class TestConfigPrint(TestCase):
    def test_print(self):
        mqtt = MockMqtt(self)
        state = MqttSharedTopic(mqtt, "/my/topic")

        components = []
        components.append(Swi(sid='1', name='test1', mqtt=mqtt))
        components.append(Swi(sid='2', name='test2', mqtt=mqtt, availability_topic=True))
        components.append(Swi(sid='3', name='test3', mqtt=mqtt, state_topic=state))
        components.append(Swi(sid='4', name='test4', mqtt=mqtt, state_topic=state, availability_topic=True))

        file = open('config_switches.yaml', mode='r')
        config = file.read()
        file.close()

        self.assertEqual(config, config_creator(components))
