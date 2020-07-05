from unittest import TestCase

from ha import ComponentUpdater
from mqtt import MqttSharedTopic
from sensor import Sensor, SettableSensor, ErrorSensor
from tests.mock_mqtt import MockMqtt
from util import create_ha_config, create_average_sensor, create_weighted_average_sensor


class Sen(Sensor):
    def __init__(self, sid='test_id', name='test_name', mqtt=None, state_topic=None, state_func=lambda: 1.2424353463,
                 **kwargs):
        super().__init__(sid, name, '°C', mqtt=mqtt, state_topic=state_topic,
                         state_func=state_func,
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
        components.append(ErrorSensor('errors', 'errors', mqtt=mqtt))

        file = open('config_sensors.yaml', mode='r')
        config = file.read()
        file.close()

        self.assertEqual(config, create_ha_config(components))


class TestUtil(TestCase):
    def test_average(self):
        mqtt = MockMqtt(self)
        updater = ComponentUpdater()
        state = MqttSharedTopic(mqtt, "/my/topic")

        sensor1 = Sen(sid='s1', name='s1', mqtt=mqtt, state_topic=state, state_func=lambda: 1)
        sensor2 = Sen(sid='s2', name='s2', mqtt=mqtt, state_topic=state, state_func=lambda: 4)
        sensor3 = Sen(sid='s3', name='s3', mqtt=mqtt, state_topic=state, state_func=lambda: 7)

        sensors = [sensor1, sensor2, sensor3]

        s1 = create_average_sensor('test1', 'test1', '°C', sensors, mqtt=mqtt, state_topic=state)
        s2, weights = create_weighted_average_sensor('test2', 'test2', '°C', 0, 100, 1, 50, sensors, mqtt=mqtt,
                                                     state_topic=state)
        updater.add_component(sensor1)
        updater.add_component(sensor2)
        updater.add_component(sensor3)
        updater.add_component(s1)
        updater.add_component(s2)
        updater.add_shared_topic(state)
        for w in weights:
            updater.add_component(w)

        with updater:
            updater.send_updates()
            mqtt.publish('homeassistant/sensor/s1_weight/cmd', '20')
            mqtt.publish('homeassistant/sensor/s2_weight/cmd', '40')
            mqtt.publish('homeassistant/sensor/s3_weight/cmd', '80')
            updater.send_updates()

        mqtt.assert_messages('homeassistant/sensor/s1/config',
                             [{'name': 's1',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.s1 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s2/config',
                             [{'name': 's2',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.s2 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s3/config',
                             [{'name': 's3',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.s3 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/test1/config',
                             [{'name': 'test1',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.test1 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/test2/config',
                             [{'name': 'test2',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.test2 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s1_weight/config',
                             [{'name': 's1 weight',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '',
                               'value_template': '{{ value_json.s1_weight }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s2_weight/config',
                             [{'name': 's2 weight',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '',
                               'value_template': '{{ value_json.s2_weight }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s3_weight/config',
                             [{'name': 's3 weight',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '',
                               'value_template': '{{ value_json.s3_weight }}'},
                              None])
        mqtt.assert_messages('/my/topic',
                             [{'s1': '1.00',
                               's1_weight': '50.00',
                               's2': '4.00',
                               's2_weight': '50.00',
                               's3': '7.00',
                               's3_weight': '50.00',
                               'test1': '4.00',
                               'test2': '4.00'},
                              {'s1': '1.00',
                               's1_weight': '20.00',
                               's2': '4.00',
                               's2_weight': '40.00',
                               's3': '7.00',
                               's3_weight': '80.00',
                               'test1': '4.00',
                               'test2': '5.29'}])
