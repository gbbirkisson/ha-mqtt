from ha import _Base
from mqtt import MqttTopic, MqttSharedTopic
from util import create_id


def _state_format(state):
    return 'on' if state else 'off'


class Switch(_Base):
    def __init__(
            self,
            switch_name,
            switch_id=None,
            state_change_func=None,
            state_topic=None,
            **kwargs
    ):
        super().__init__(component_id=create_id(switch_id, switch_name), component_name=switch_name,
                         component_type='switch', **kwargs)

        assert state_change_func is not None, 'switch_func cannot be None'

        command_topic = MqttTopic(kwargs['mqtt'], self.topic_name('cmd'))
        self._state_change_func = state_change_func
        self._state = False

        self._add_to_config({
            'payload_on': 'on',
            'payload_off': 'off',
            'state_on': 'on',
            'state_off': 'off',
            'command_topic': command_topic.name(),
        })

        if state_topic is None:
            self._state_topic = MqttTopic(kwargs['mqtt'], self.topic_name('state'))
            self._add_to_config({
                'state_topic': self._state_topic.name()
            })
        else:
            assert type(state_topic) is MqttSharedTopic
            self._state_topic = state_topic
            self._add_to_config({
                'state_topic': self._state_topic.name(),
                'value_template': self._state_topic.add_entry(self._component_id, lambda: _state_format(self._state)),
            })

        command_topic.subscribe(lambda new_state: self._receive_command(new_state))

    def _receive_command(self, new_state):
        self(new_state == 'on')

    def send_update(self):
        self._state_topic.publish(_state_format(self._state))

    def __call__(self, new_state):
        self._state = new_state
        self._state_change_func(self._state)
        self.send_update()
