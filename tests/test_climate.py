from unittest import TestCase

from climate import Climate
from mqtt import MqttSharedTopic
from registry import ComponentRegistry
from tests.mock_mqtt import MockMqtt

temp1 = 5.5
temp2 = 5.5


def fake_temp1():
    global temp1
    temp1 = temp1 + 1
    return temp1


def fake_temp2():
    global temp2
    temp2 = temp2 + 1
    return temp2


class Cli(Climate):
    def __init__(self, sid='test_id', name='test_name', mqtt=None, state_topic=None, **kwargs):
        super().__init__(sid, name, state_topic=state_topic, mqtt=mqtt,
                         **kwargs)


class TestSwitch(TestCase):
    def test_simple(self):
        mqtt = MockMqtt(self)

        climate = Cli(mqtt=mqtt, thermometer=fake_temp1)

        with climate:
            climate.available_set(True)
            self.assertEqual(climate.is_on(), False)
            mqtt.publish('homeassistant/climate/test_id/cmdMode', 'heat')
            self.assertEqual(climate.is_on(), True)
            mqtt.publish('homeassistant/climate/test_id/cmdTargetTemp', '80')
            climate.send_update()

        mqtt.assert_messages('homeassistant/climate/test_id/config',
                             [{'current_temperature_topic': 'homeassistant/climate/test_id/stateCurrTemp',
                               'max_temp': '100',
                               'min_temp': '0',
                               'mode_command_topic': 'homeassistant/climate/test_id/cmdMode',
                               'mode_state_topic': 'homeassistant/climate/test_id/stateMode',
                               'modes': ['off', 'heat'],
                               'name': 'test_name',
                               'temp_step': '1',
                               'temperature_command_topic': 'homeassistant/climate/test_id/cmdTargetTemp',
                               'temperature_state_topic': 'homeassistant/climate/test_id/stateTargetTemp'},
                              None])

        mqtt.assert_messages('homeassistant/climate/test_id/stateCurrTemp', ['7.50', '8.50', '9.50'])
        mqtt.assert_messages('homeassistant/climate/test_id/available', None)
        mqtt.assert_messages('homeassistant/climate/test_id/cmdMode', ["heat"])
        mqtt.assert_messages('homeassistant/climate/test_id/stateMode', ["heat"])
        mqtt.assert_messages('homeassistant/climate/test_id/cmdTargetTemp', ["80"])
        mqtt.assert_messages('homeassistant/climate/test_id/stateTargetTemp', ["80.00"])

    def test_shared_topic(self):
        mqtt = MockMqtt(self)

        state = MqttSharedTopic(mqtt, "/my/topic")

        climate = Cli(mqtt=mqtt, thermometer=fake_temp2, state_topic=state, availability_topic=True)

        with climate:
            climate.available_set(True)
            self.assertEqual(climate.is_on(), False)
            state.publish()
            mqtt.publish('homeassistant/climate/test_id/cmdMode', 'heat')
            self.assertEqual(climate.is_on(), True)
            mqtt.publish('homeassistant/climate/test_id/cmdTargetTemp', '80')
            state.publish()

        mqtt.assert_messages('homeassistant/climate/test_id/config',
                             [{'availability_topic': 'homeassistant/climate/test_id/available',
                               'current_temperature_template': '{{ value_json.test_id_curr_temp }}',
                               'current_temperature_topic': '/my/topic',
                               'max_temp': '100',
                               'min_temp': '0',
                               'mode_command_topic': 'homeassistant/climate/test_id/cmdMode',
                               'mode_state_template': '{{ value_json.test_id_mode }}',
                               'mode_state_topic': '/my/topic',
                               'modes': ['off', 'heat'],
                               'name': 'test_name',
                               'payload_available': 'online',
                               'payload_not_available': 'offline',
                               'temp_step': '1',
                               'temperature_command_topic': 'homeassistant/climate/test_id/cmdTargetTemp',
                               'temperature_state_template': '{{ value_json.test_id_target_temp }}',
                               'temperature_state_topic': '/my/topic'},
                              None])

        mqtt.assert_messages('homeassistant/climate/test_id/available', ['online'])
        mqtt.assert_messages('homeassistant/climate/test_id/cmdMode', ["heat"])
        mqtt.assert_messages('homeassistant/climate/test_id/cmdTargetTemp', ["80"])
        mqtt.assert_messages('/my/topic', [{'test_id_curr_temp': '7.50',
                                            'test_id_mode': 'off',
                                            'test_id_target_temp': '6.50'},
                                           {'test_id_curr_temp': '10.50',
                                            'test_id_mode': 'heat',
                                            'test_id_target_temp': '80.00'}])

    def test_print(self):
        mqtt = MockMqtt(self)
        state = MqttSharedTopic(mqtt, "/my/topic")
        registry = ComponentRegistry()
        therm = lambda: 1

        registry.add_component(Cli(sid='1', name='test1', mqtt=mqtt, thermometer=therm))
        registry.add_component(Cli(sid='2', name='test2', mqtt=mqtt, thermometer=therm, availability_topic=True))
        registry.add_component(Cli(sid='3', name='test3', mqtt=mqtt, thermometer=therm, state_topic=state))
        registry.add_component(
            Cli(sid='4', name='test4', mqtt=mqtt, thermometer=therm, state_topic=state, availability_topic=True))

        file = open('config_climates.yaml', mode='r')
        config = file.read()
        file.close()

        self.assertEqual(config, registry.create_config())
