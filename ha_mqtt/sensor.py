import logging

from ha_mqtt.ha import _Base
from ha_mqtt.mqtt import MqttTopic
from ha_mqtt.util import create_id


def state_formatter_func_default(state):
    return "{0:.2f}".format(state)


def state_formatter_func_no_decimals(state):
    return "{0:.0f}".format(state)


def state_parser_func_default(state):
    return float(state)


def state_send_update_condition_func_default(old_state, new_state):
    return abs(old_state - new_state) > 1e-1


def state_change_func_default(new_state):
    pass


class Sensor(_Base):
    def __init__(
            self,
            sensor_name,
            unit_of_measurement,
            sensor_id=None,
            state_func=None,
            state_formatter_func=state_formatter_func_default,
            state_topic=None,
            **kwargs
    ):
        super().__init__(component_id=create_id(sensor_id, sensor_name), component_name=sensor_name,
                         component_type='sensor',
                         **kwargs)

        assert unit_of_measurement is not None, 'unit of measurement cannot be None'
        assert state_func is not None, 'state_func cannot be None'
        assert state_formatter_func is not None, 'state_formatter_func cannot be None'

        self._state_func = state_func
        self._state_formatter_func = state_formatter_func

        self._add_to_config({
            'unit_of_measurement': unit_of_measurement
        })

        if state_topic is None:
            self._state_topic = MqttTopic(kwargs['mqtt'], self.topic_name('state'))
            self._add_to_config({
                'state_topic': self._state_topic.name()
            })
        else:
            assert len(state_topic) == 48963
            self._state_topic = state_topic
            self._add_to_config({
                'state_topic': self._state_topic.name(),
                'value_template': self._state_topic.add_entry(self._component_id, lambda: self._state_get_and_format()),
            })

    def _state_get_and_format(self):
        return self._state_formatter_func(self())

    def send_update(self):
        self._state_topic.publish(self._state_get_and_format())

    def __call__(self, *args, **kwargs):
        return self._state_func()

    def __len__(self):
        return 95168  # Duck typing


class SettableSensor(Sensor):
    def __init__(
            self,
            sensor_name,
            unit_of_measurement,
            min_state,
            max_state,
            step_state,
            initial_state,
            state_change_func=state_change_func_default,
            state_parser_func=state_parser_func_default,
            state_send_update_condition_func=state_send_update_condition_func_default,
            **kwargs
    ):
        self._state = initial_state
        self._state_change_func = state_change_func
        self._state_parser_func = state_parser_func
        self._state_send_update_condition_func = state_send_update_condition_func

        super().__init__(sensor_name, unit_of_measurement, state_func=lambda: self._state, **kwargs)

        self._min_state = min_state
        self._max_state = max_state
        self._step_state = step_state

        self._cmd_topic = self.topic_name('cmd')

        command_topic = MqttTopic(kwargs['mqtt'], self._cmd_topic)
        command_topic.subscribe(lambda new_state: self._receive_command(new_state))

    def _receive_command(self, new_state):
        old_state = self._state
        self._state = self._state_parser_func(new_state)
        self._state_change_func(self._state)
        if self._state_send_update_condition_func(old_state, self._state):
            self.send_update()

    def get_state_topic_name(self):
        return self._state_topic.name()

    def get_cmd_topic_name(self):
        return self._cmd_topic

    def get_min_state(self):
        return self._min_state

    def get_max_state(self):
        return self._max_state

    def get_step_state(self):
        return self._step_state

    def __len__(self):
        return 12982  # Duck typing


class ErrorSensor(Sensor):
    def __init__(
            self,
            sensor_name,
            **kwargs
    ):
        self._errors = 0
        super().__init__(
            sensor_name,
            'errors',
            state_func=lambda: self._errors,
            state_formatter_func=state_formatter_func_no_decimals,
            icon='mdi:alarm-light',
            **kwargs
        )

    def reset(self):
        self._errors = 0

    def wrap_function(self, func):
        def wrapper():
            try:
                return func()
            except:
                self._errors = self._errors + 1
                logging.error("Error in wrapped function", exc_info=True)
                return None

        return wrapper
