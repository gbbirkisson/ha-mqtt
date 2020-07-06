from unittest import TestCase

from components import create_average_sensor, create_weighted_average_sensor
from mqtt import MqttSharedTopic
from registry import ComponentRegistry
from sensor import Sensor, SettableSensor, ErrorSensor
from tests.mock_mqtt import MockMqtt


class Sen(Sensor):
    def __init__(self, name='Test Name', state_func=lambda: 1.2424353463,
                 **kwargs):
        super().__init__(name, '°C', state_func=state_func, **kwargs)


class TestSensor(TestCase):
    def test_simple(self):
        mqtt = MockMqtt(self)

        sensor = Sen(mqtt=mqtt)

        with sensor:
            sensor.available_set(True)
            sensor.send_update()

        mqtt.assert_messages('homeassistant/sensor/test_name/config', [
            {'name': 'Test Name',
             'state_topic': 'homeassistant/sensor/test_name/state',
             'unit_of_measurement': '°C'},
            None
        ])

        mqtt.assert_messages('homeassistant/sensor/test_name/state', ["1.24"])
        mqtt.assert_messages('homeassistant/sensor/test_name/available', None)

    def test_shared_topic(self):
        mqtt = MockMqtt(self)

        state = MqttSharedTopic(mqtt, "/my/topic")

        sensor = Sen(mqtt=mqtt, state_topic=state, availability_topic=True)

        with sensor:
            sensor.available_set(True)
            state.publish()

        mqtt.assert_messages('homeassistant/sensor/test_name/config',
                             [{'availability_topic': 'homeassistant/sensor/test_name/available',
                               'name': 'Test Name',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.test_name }}'},
                              None])

        mqtt.assert_messages('/my/topic', [{"test_name": "1.24"}])
        mqtt.assert_messages('homeassistant/sensor/test_name/available', ["online"])


class SetSen(SettableSensor):
    def __init__(self, name='Test Name', **kwargs):
        super().__init__(name, '°C', 0, 10, 0.5, 7.5, **kwargs)


class TestSettableSensor(TestCase):
    def test_simple(self):
        mqtt = MockMqtt(self)

        sensor = SetSen(mqtt=mqtt)

        with sensor:
            sensor.available_set(True)
            sensor.send_update()
            mqtt.publish('homeassistant/sensor/test_name/cmd', '3.68')

        mqtt.assert_messages('homeassistant/sensor/test_name/config', [
            {'name': 'Test Name',
             'state_topic': 'homeassistant/sensor/test_name/state',
             'unit_of_measurement': '°C'},
            None
        ])

        mqtt.assert_messages('homeassistant/sensor/test_name/state', ["7.50", "3.68"])
        mqtt.assert_messages('homeassistant/sensor/test_name/available', None)

    def test_shared_topic(self):
        mqtt = MockMqtt(self)

        state = MqttSharedTopic(mqtt, "/my/topic")

        sensor = SetSen(mqtt=mqtt, state_topic=state, availability_topic=True)

        with sensor:
            sensor.available_set(True)
            state.publish()
            mqtt.publish('homeassistant/sensor/test_name/cmd', '3.68')
            state.publish()

        mqtt.assert_messages('homeassistant/sensor/test_name/config',
                             [{'availability_topic': 'homeassistant/sensor/test_name/available',
                               'name': 'Test Name',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.test_name }}'},
                              None])

        mqtt.assert_messages('/my/topic', [{"test_name": "7.50"}, {"test_name": "3.68"}])
        mqtt.assert_messages('homeassistant/sensor/test_name/available', ["online"])

    def test_print(self):
        mqtt = MockMqtt(self)
        state = MqttSharedTopic(mqtt, "/my/topic")
        registry = ComponentRegistry()

        registry.add_component(Sen(name='Test 1', mqtt=mqtt))
        registry.add_component(Sen(name='Test 2', mqtt=mqtt, availability_topic=True))
        registry.add_component(Sen(name='Test 3', mqtt=mqtt, state_topic=state))
        registry.add_component(Sen(name='Test 4', mqtt=mqtt, state_topic=state, availability_topic=True))
        registry.add_component(SetSen(name='Test 5', mqtt=mqtt))
        registry.add_component(SetSen(name='Test 6', mqtt=mqtt, availability_topic=True))
        registry.add_component(SetSen(name='Test 7', mqtt=mqtt, state_topic=state))
        registry.add_component(SetSen(name='Test 8', mqtt=mqtt, state_topic=state, availability_topic=True))
        registry.add_component(ErrorSensor('errors', mqtt=mqtt))

        file = open('config_sensors.yaml', mode='r')
        config = file.read()
        file.close()

        self.assertEqual(config, registry.create_config())


class TestUtil(TestCase):
    def test_average(self):
        mqtt = MockMqtt(self)
        registry = ComponentRegistry()
        state = MqttSharedTopic(mqtt, "/my/topic")

        sensor1 = Sen(name='S 1', mqtt=mqtt, state_topic=state, state_func=lambda: 1)
        sensor2 = Sen(name='S 2', mqtt=mqtt, state_topic=state, state_func=lambda: 4)
        sensor3 = Sen(name='S 3', mqtt=mqtt, state_topic=state, state_func=lambda: 7)

        sensors = [sensor1, sensor2, sensor3]

        s1 = create_average_sensor('Test 1', '°C', sensors, mqtt=mqtt, state_topic=state)
        s2, weights = create_weighted_average_sensor('Test 2', '°C', 0, 100, 1, 50, sensors, mqtt=mqtt,
                                                     state_topic=state)
        registry.add_component(sensor1)
        registry.add_component(sensor2)
        registry.add_component(sensor3)
        registry.add_component(s1)
        registry.add_component(s2)
        registry.add_shared_topic(state)
        for w in weights:
            registry.add_component(w)

        with registry:
            registry.send_updates()
            mqtt.publish('homeassistant/sensor/s_1_weight/cmd', '20')
            mqtt.publish('homeassistant/sensor/s_2_weight/cmd', '40')
            mqtt.publish('homeassistant/sensor/s_3_weight/cmd', '80')
            registry.send_updates()

        mqtt.assert_messages('homeassistant/sensor/s_1/config',
                             [{'name': 'S 1',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.s_1 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s_2/config',
                             [{'name': 'S 2',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.s_2 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s_3/config',
                             [{'name': 'S 3',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.s_3 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/test_1/config',
                             [{'name': 'Test 1',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.test_1 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/test_2/config',
                             [{'name': 'Test 2',
                               'state_topic': '/my/topic',
                               'unit_of_measurement': '°C',
                               'value_template': '{{ value_json.test_2 }}'},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s_1_weight/config',
                             [{'icon': 'mdi:weight',
                               'name': 'S 1 weight',
                               'state_topic': 'homeassistant/sensor/s_1_weight/state',
                               'unit_of_measurement': ''},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s_2_weight/config',
                             [{'icon': 'mdi:weight',
                               'name': 'S 2 weight',
                               'state_topic': 'homeassistant/sensor/s_2_weight/state',
                               'unit_of_measurement': ''},
                              None])
        mqtt.assert_messages('homeassistant/sensor/s_3_weight/config',
                             [{'icon': 'mdi:weight',
                               'name': 'S 3 weight',
                               'state_topic': 'homeassistant/sensor/s_3_weight/state',
                               'unit_of_measurement': ''},
                              None])
        mqtt.assert_messages('/my/topic',
                             [{'s_1': '1.00', 's_2': '4.00', 's_3': '7.00', 'test_1': '4.00', 'test_2': '4.00'},
                              {'s_1': '1.00', 's_2': '4.00', 's_3': '7.00', 'test_1': '4.00', 'test_2': '5.29'}])
        mqtt.assert_messages('homeassistant/sensor/s_1_weight/state', ['50.00', '20.00', '20.00'])
        mqtt.assert_messages('homeassistant/sensor/s_2_weight/state', ['50.00', '40.00', '40.00'])
        mqtt.assert_messages('homeassistant/sensor/s_3_weight/state', ['50.00', '80.00', '80.00'])
