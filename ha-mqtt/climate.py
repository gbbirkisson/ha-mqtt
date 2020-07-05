from ha import _Base
from mqtt import MqttTopic, MqttSharedTopic


def temp_formatter(state):
    return "{0:.2f}".format(state)


class Climate(_Base):
    def __init__(self, climate_id, climate_name, thermometer, heat=True, cool=False, state_change_func=lambda x, y: x,
                 temp_min=0, temp_max=100, temp_step=1,
                 temp_formatter_func=temp_formatter,
                 mqtt=None, state_topic=None, **kwargs):
        super().__init__(mqtt=mqtt, component_id=climate_id, component_name=climate_name, component_type='climate',
                         **kwargs)

        assert state_change_func is not None, 'state_change_func cannot be None'
        assert thermometer is not None, 'thermometer cannot be None'
        assert heat is not None or cool is not None, 'heat and cool cannot both be None'

        self._state_change_func = state_change_func
        self._mode = 'off'
        self._target = thermometer()
        self._thermometer = thermometer
        self._temp_formatter_func = temp_formatter_func

        modes = ['off']
        if heat:
            modes.append('heating')
        if cool:
            modes.append('cooling')

        topic_command_mode = MqttTopic(mqtt, self.topic_name('cmdMode'))
        topic_command_target_temp = MqttTopic(mqtt, self.topic_name('cmdTargetTemp'))

        self._add_to_config({
            'min_temp': str(temp_min),
            'max_temp': str(temp_max),
            'temp_step': str(temp_step),
            'modes': modes,
            'mode_command_topic': topic_command_mode.name(),
            'temperature_command_topic': topic_command_target_temp.name(),
        })

        if state_topic is None:
            self._topic_state_mode = MqttTopic(mqtt, self.topic_name('stateMode'))
            self._topic_state_curr_temp = MqttTopic(mqtt, self.topic_name('stateCurrTemp'))
            self._topic_state_target_temp = MqttTopic(mqtt, self.topic_name('stateTargetTemp'))
            self._add_to_config({
                'mode_state_topic': self._topic_state_mode.name(),
                'current_temperature_topic': self._topic_state_curr_temp.name(),
                'temperature_state_topic': self._topic_state_target_temp.name()
            })
        else:
            assert type(state_topic) is MqttSharedTopic
            self._topic_state_mode = state_topic
            self._topic_state_curr_temp = state_topic
            self._topic_state_target_temp = state_topic
            self._add_to_config({
                'mode_state_topic': self._topic_state_mode.name(),
                'mode_state_template': self._topic_state_mode.add_entry(climate_id + '_mode', lambda: self._mode),
                'current_temperature_topic': self._topic_state_curr_temp.name(),
                'current_temperature_template': self._topic_state_curr_temp.add_entry(climate_id + '_curr_temp',
                                                                                      lambda: self._temp_formatter_func(
                                                                                          self._thermometer())),
                'temperature_state_topic': self._topic_state_mode.name(),
                'temperature_state_template': self._topic_state_mode.add_entry(climate_id + '_target_temp',
                                                                               lambda: self._temp_formatter_func(
                                                                                   self._target))
            })

        topic_command_mode.subscribe(lambda new_mode: self.set_mode(new_mode))
        topic_command_target_temp.subscribe(lambda target: self.set_target(target))

    def is_on(self):
        return self._mode != 'off'

    def set_mode(self, new_mode):
        if new_mode != self._mode:
            self._mode = new_mode
            self._topic_state_mode.publish(self._mode)
            self._handle_state_change()

    def set_target(self, target):
        target = float(target)
        if abs(self._target - target) > 1e-1:
            self._target = target
            self._topic_state_target_temp.publish(self._temp_formatter_func(self._target))
            self._handle_state_change()

    def send_update(self):
        self._topic_state_curr_temp.publish(self._temp_formatter_func(self._thermometer()))

    def _handle_state_change(self):
        self._state_change_func(self._mode, self._target)
        self.send_update()
