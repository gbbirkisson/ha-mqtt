from unittest import TestCase

from mqtt import MqttSharedTopic
from registry import ComponentRegistry
from switch import Switch
from tests.mock_mqtt import MockMqtt


class Swi(Switch):
    def __init__(self, name='Test Name', **kwargs):
        super().__init__(name, state_change_func=lambda new_state: print(new_state), **kwargs)


class TestSwitch(TestCase):
    def test_simple(self):
        mqtt = MockMqtt(self)

        sensor = Swi(mqtt=mqtt)

        with sensor:
            sensor.available_set(True)
            sensor.send_update()
            sensor(True)

        mqtt.assert_messages('homeassistant/switch/test_name/config',
                             [{'command_topic': 'homeassistant/switch/test_name/cmd',
                               'name': 'Test Name',
                               'payload_off': 'off',
                               'payload_on': 'on',
                               'state_off': 'off',
                               'state_on': 'on',
                               'state_topic': 'homeassistant/switch/test_name/state'},
                              None])

        mqtt.assert_messages('homeassistant/switch/test_name/state', ["off", "on"])
        mqtt.assert_messages('homeassistant/switch/test_name/available', None)

    def test_shared_topic(self):
        mqtt = MockMqtt(self)

        state = MqttSharedTopic(mqtt, "/my/topic")

        sensor = Swi(mqtt=mqtt, state_topic=state, availability_topic=True)

        with sensor:
            sensor.available_set(True)
            state.publish()

        mqtt.assert_messages('homeassistant/switch/test_name/config',
                             [{'availability_topic': 'homeassistant/switch/test_name/available',
                               'command_topic': 'homeassistant/switch/test_name/cmd',
                               'name': 'Test Name',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'payload_off': 'off',
                               'payload_on': 'on',
                               'state_off': 'off',
                               'state_on': 'on',
                               'state_topic': '/my/topic',
                               'value_template': '{{ value_json.test_name }}'},
                              None])

        mqtt.assert_messages('/my/topic', [{"test_name": "off"}])
        mqtt.assert_messages('homeassistant/switch/test_name/available', ["online"])

    def test_print(self):
        mqtt = MockMqtt(self)
        state = MqttSharedTopic(mqtt, "/my/topic")
        registry = ComponentRegistry()

        registry.add_component(Swi(name='Test 1', mqtt=mqtt))
        registry.add_component(Swi(name='Test 2', mqtt=mqtt, availability_topic=True))
        registry.add_component(Swi(name='Test 3', mqtt=mqtt, state_topic=state))
        registry.add_component(Swi(name='Test 2', mqtt=mqtt, state_topic=state, availability_topic=True))

        file = open('config_switches.yaml', mode='r')
        config = file.read()
        file.close()

        self.assertEqual(config, registry.create_config())
