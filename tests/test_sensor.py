from unittest import TestCase

from mqtt import MqttSharedTopic
from sensor import Sensor, SettableSensor
from tests.mock_mqtt import MockMqtt
from util import config_creator


class Sen(Sensor):
    def __init__(self, sid='test_id', name='test_name', mqtt=None, state_topic=None, **kwargs):
        super().__init__(sid, name, '°C', mqtt=mqtt, state_topic=state_topic,
                         state_func=lambda: 1.2424353463,
                         **kwargs)


class TestSensor(TestCase):
    def test_simple(self):
        mqtt = MockMqtt(self)

        sensor = Sen(mqtt=mqtt)

        with sensor:
            sensor.available_set(True)
            sensor.send_update()

        mqtt.assert_messages('homeassistant/sensor/test_id/config', [
            {'name': 'test_name',
             'state_topic': 'homeassistant/sensor/test_id/state',
             'unit_of_measurement': '°C'},
            None
        ])

        mqtt.assert_messages('homeassistant/sensor/test_id/state', ["1.24"])
        mqtt.assert_messages('homeassistant/sensor/test_id/available', None)

    def test_shared_topic(self):
        mqtt = MockMqtt(self)

        state = MqttSharedTopic(mqtt, "/my/topic")

        sensor = Sen(mqtt=mqtt, state_topic=state, availability_topic=True)

        with sensor:
            sensor.available_set(True)
            state.publish()

        mqtt.assert_messages('homeassistant/sensor/test_id/config',
                             [{'availability_topic': 'homeassistant/sensor/test_id/available',
                               'name': 'test_name',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.test_id }}'},
                              None])

        mqtt.assert_messages('/my/topic', [{"test_id": "1.24"}])
        mqtt.assert_messages('homeassistant/sensor/test_id/available', ["online"])


class SetSen(SettableSensor):
    def __init__(self, sid='test_id', name='test_name', mqtt=None, state_topic=None, **kwargs):
        super().__init__(sid, name, '°C', 0, 10, 0.5, 7.5, mqtt=mqtt, state_topic=state_topic,
                         **kwargs)


class TestSettableSensor(TestCase):
    def test_simple(self):
        mqtt = MockMqtt(self)

        sensor = SetSen(mqtt=mqtt)

        with sensor:
            sensor.available_set(True)
            sensor.send_update()
            mqtt.publish('homeassistant/sensor/test_id/cmd', '3.68')

        mqtt.assert_messages('homeassistant/sensor/test_id/config', [
            {'name': 'test_name',
             'state_topic': 'homeassistant/sensor/test_id/state',
             'unit_of_measurement': '°C'},
            None
        ])

        mqtt.assert_messages('homeassistant/sensor/test_id/state', ["7.50", "3.68"])
        mqtt.assert_messages('homeassistant/sensor/test_id/available', None)

    def test_shared_topic(self):
        mqtt = MockMqtt(self)

        state = MqttSharedTopic(mqtt, "/my/topic")

        sensor = SetSen(mqtt=mqtt, state_topic=state, availability_topic=True)

        with sensor:
            sensor.available_set(True)
            state.publish()
            mqtt.publish('homeassistant/sensor/test_id/cmd', '3.68')
            state.publish()

        mqtt.assert_messages('homeassistant/sensor/test_id/config',
                             [{'availability_topic': 'homeassistant/sensor/test_id/available',
                               'name': 'test_name',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.test_id }}'},
                              None])

        mqtt.assert_messages('/my/topic', [{"test_id": "7.50"}, {"test_id": "3.68"}])
        mqtt.assert_messages('homeassistant/sensor/test_id/available', ["online"])


class TestConfigPrint(TestCase):
    def test_print(self):
        mqtt = MockMqtt(self)
        state = MqttSharedTopic(mqtt, "/my/topic")

        components = []
        components.append(Sen(sid='1', name='test1', mqtt=mqtt))
        components.append(Sen(sid='2', name='test2', mqtt=mqtt, availability_topic=True))
        components.append(Sen(sid='3', name='test3', mqtt=mqtt, state_topic=state))
        components.append(Sen(sid='4', name='test4', mqtt=mqtt, state_topic=state, availability_topic=True))
        components.append(SetSen(sid='5', name='test5', mqtt=mqtt))
        components.append(SetSen(sid='6', name='test6', mqtt=mqtt, availability_topic=True))
        components.append(SetSen(sid='7', name='test7', mqtt=mqtt, state_topic=state))
        components.append(SetSen(sid='8', name='test8', mqtt=mqtt, state_topic=state, availability_topic=True))

        file = open('config_sensors.yaml', mode='r')
        config = file.read()
        file.close()

        self.assertEqual(config, config_creator(components))
