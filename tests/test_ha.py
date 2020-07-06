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
        sensor1 = ErrorSensor('Error 1', mqtt=mqtt)
        sensor2 = ErrorSensor('Error 2', mqtt=mqtt, availability_topic=True)
        sensor3 = ErrorSensor('Error 3', mqtt=mqtt, state_topic=state)
        sensor4 = ErrorSensor('Error 4', mqtt=mqtt, state_topic=state, availability_topic=True)

        registry.add_shared_topic(state)
        registry.add_component(sensor1)
        registry.add_component(sensor2)
        registry.add_component(sensor3)
        registry.add_component(sensor4)

        with registry:
            registry.send_updates()

        mqtt.assert_messages('homeassistant/sensor/error_1/config',
                             [{'icon': 'mdi:alarm-light',
                               'name': 'Error 1',
                               'state_topic': 'homeassistant/sensor/error_1/state',
                               'unit_of_measurement': 'errors'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/error_2/config',
                             [{'availability_topic': 'homeassistant/sensor/error_2/available',
                               'icon': 'mdi:alarm-light',
                               'name': 'Error 2',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'state_topic': 'homeassistant/sensor/error_2/state',
                               'unit_of_measurement': 'errors'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/error_3/config',
                             [{'icon': 'mdi:alarm-light',
                               'name': 'Error 3',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': 'errors',
                               'value_template': '{{ value_json.error_3 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/error_4/config',
                             [{'availability_topic': 'homeassistant/sensor/error_4/available',
                               'icon': 'mdi:alarm-light',
                               'name': 'Error 4',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': 'errors',
                               'value_template': '{{ value_json.error_4 }}'},
                              None])

        mqtt.assert_messages('homeassistant/sensor/error_1/available', None)
        mqtt.assert_messages('homeassistant/sensor/error_2/available', ['online'])
        mqtt.assert_messages('homeassistant/sensor/error_3/available', None)
        mqtt.assert_messages('homeassistant/sensor/error_4/available', ['online'])

        mqtt.assert_messages('homeassistant/sensor/error_1/state', ['0'])
        mqtt.assert_messages('homeassistant/sensor/error_2/state', ['0'])
        mqtt.assert_messages('/my/topic', [{'error_3': '0', 'error_4': '0'}])
