from ha import _Base
from mqtt import MqttTopic, MqttSharedTopic


def state_formatter(state):
    return "{0:.2f}".format(state)


def state_parser(state):
    return float(state)


def state_send_update_condition(old_state, new_state):
    return abs(old_state - new_state) > 1e-1


class Sensor(_Base):
    def __init__(self, sensor_id, sensor_name, unit_of_measurement, state_func=None,
                 state_formatter_func=state_formatter, mqtt=None, state_topic=None, **kwargs):
        super().__init__(mqtt=mqtt, component_id=sensor_id, component_name=sensor_name, component_type='sensor',
                         **kwargs)

        assert unit_of_measurement is not None, 'unit of measurement cannot be None'
        assert state_func is not None, 'state_func cannot be None'

        self._state_func = state_func
        self._state_formatter_func = state_formatter_func

        self._add_to_config({
            'unit_of_measurement': unit_of_measurement
        })

        if state_topic is None:
            self._state_topic = MqttTopic(mqtt, self.topic_name('state'))
            self._add_to_config({
                'state_topic': self._state_topic.name()
            })
        else:
            assert type(state_topic) is MqttSharedTopic
            self._state_topic = state_topic
            self._add_to_config({
                'state_topic': self._state_topic.name(),
                'value_template': self._state_topic.add_entry(sensor_id, lambda: self._state_get_and_format()),
            })

    def _state_get_and_format(self):
        return self._state_formatter_func(self())

    def send_update(self):
        self._state_topic.publish(self._state_get_and_format())

    def __call__(self, *args, **kwargs):
        return self._state_func()


class SettableSensor(Sensor):
    def __init__(self, sensor_id, sensor_name, unit_of_measurement, min_state, max_state, step_state, initial_state,
                 state_parser_func=state_parser,
                 state_send_update_condition_func=state_send_update_condition, mqtt=None, **kwargs):
        self._state = initial_state
        super().__init__(sensor_id, sensor_name, unit_of_measurement, mqtt=mqtt, state_func=lambda: self._state,
                         **kwargs)

        self._min_state = min_state
        self._max_state = max_state
        self._step_state = step_state
        self._state = initial_state
        self._state_parser_func = state_parser_func
        self._state_send_update_condition_func = state_send_update_condition_func

        command_topic = MqttTopic(mqtt, self.topic_name('cmd'))
        command_topic.subscribe(lambda new_state: self._receive_command(new_state))

    def _receive_command(self, new_state):
        old_state = self._state
        self._state = self._state_parser_func(new_state)
        if self._state_send_update_condition_func(old_state, self._state):
            self.send_update()

    def get_min_state(self):
        return self._min_state

    def get_max_state(self):
        return self._max_state

    def get_step_state(self):
        return self._step_state
