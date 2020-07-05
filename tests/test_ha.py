from unittest import TestCase

from mqtt import MqttSharedTopic
from registry import ComponentRegistry
from sensor import ErrorSensor
from tests.mock_mqtt import MockMqtt


class TestHa(TestCase):
    def test_manager(self):
        mqtt = MockMqtt(self)
        registry = ComponentRegistry()

        state = MqttSharedTopic(mqtt, "/my/topic")
        sensor1 = ErrorSensor('error1', 'error1', mqtt=mqtt)
        sensor2 = ErrorSensor('error2', 'error2', mqtt=mqtt, availability_topic=True)
        sensor3 = ErrorSensor('error3', 'error3', mqtt=mqtt, state_topic=state)
        sensor4 = ErrorSensor('error4', 'error3', mqtt=mqtt, state_topic=state, availability_topic=True)

        registry.add_shared_topic(state)
        registry.add_component(sensor1)
        registry.add_component(sensor2)
        registry.add_component(sensor3)
        registry.add_component(sensor4)

        with registry:
            registry.send_updates()

        mqtt.assert_messages('homeassistant/sensor/error1/config',
                             [{'icon': 'mdi:alarm-light',
                               'name': 'error1',
                               'state_topic': 'homeassistant/sensor/error1/state',
                               'unit_of_measurement': 'errors'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/error2/config',
                             [{'availability_topic': 'homeassistant/sensor/error2/available',
                               'icon': 'mdi:alarm-light',
                               'name': 'error2',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'state_topic': 'homeassistant/sensor/error2/state',
                               'unit_of_measurement': 'errors'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/error3/config',
                             [{'icon': 'mdi:alarm-light',
                               'name': 'error3',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': 'errors',
                               'value_template': '{{ value_json.error3 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/error4/config',
                             [{'availability_topic': 'homeassistant/sensor/error4/available',
                               'icon': 'mdi:alarm-light',
                               'name': 'error3',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': 'errors',
                               'value_template': '{{ value_json.error4 }}'},
                              None])

        mqtt.assert_messages('homeassistant/sensor/error1/available', None)
        mqtt.assert_messages('homeassistant/sensor/error2/available', ['online'])
        mqtt.assert_messages('homeassistant/sensor/error3/available', None)
        mqtt.assert_messages('homeassistant/sensor/error4/available', ['online'])

        mqtt.assert_messages('homeassistant/sensor/error1/state', ['0'])
        mqtt.assert_messages('homeassistant/sensor/error2/state', ['0'])
        mqtt.assert_messages('/my/topic', [{'error3': '0', 'error4': '0'}])
