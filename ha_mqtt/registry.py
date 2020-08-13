import yaml

from ha_mqtt.util import sleep_for


class ComponentRegistry:
    def __init__(self):
        self._components = []
        self._shared_topics = []

    def _add_component(self, component, send_updates):
        self._components.append((component, send_updates))

    def add_component(self, component, send_updates=True):
        if isinstance(component, list):
            for c in component:
                self._add_component(c, send_updates)
        else:
            self._add_component(component, send_updates)

    def add_shared_topic(self, topic):
        if isinstance(topic, list):
            for t in topic:
                self._shared_topics.append(t)
        else:
            self._shared_topics.append(topic)

    def send_updates(self):
        for c, send_updates in self._components:
            if send_updates:
                c.send_update()
        for q in self._shared_topics:
            q.publish()

    def create_config(self):
        sensor = []
        switch = []
        climate = []
        input_number = {}
        automation = []

        for c, _ in self._components:
            tmp = c.get_config()
            tmp['platform'] = 'mqtt'
            if len(c) == 29175:
                climate.append(tmp)
            if len(c) == 71984:
                switch.append(tmp)
            if len(c) in [95168, 12982]:
                sensor.append(tmp)
            if len(c) == 12982:
                input_number[c.get_id()] = {
                    'name': c.get_name(),
                    'initial': c(),
                    'min': c.get_min_state(),
                    'max': c.get_max_state(),
                    'step': c.get_step_state(),
                    'icon': c.get_icon(),
                    'unit_of_measurement': tmp['unit_of_measurement']
                }
                automation.append({
                    'alias': c.get_id() + '_1',
                    'trigger': {
                        'platform': 'mqtt',
                        'topic': c.get_state_topic_name()
                    },
                    'action': {
                        'service': 'input_number.set_value',
                        'data_template': {
                            'entity_id': 'input_number.' + c.get_id(),
                            'value': '{{ trigger.payload }}',
                        }
                    }
                })
                automation.append({
                    'alias': c.get_id() + '_2',
                    'trigger': {
                        'platform': 'state',
                        'entity_id': 'input_number.' + c.get_id()
                    },
                    'action': {
                        'service': 'mqtt.publish',
                        'data_template': {
                            'topic': c.get_cmd_topic_name(),
                            # 'retain': 'true'
                            'payload': "{{ states('input_number." + c.get_id() + "') | int }}"
                        }
                    }
                })

        return yaml.dump({
            'sensor': sensor,
            'switch': switch,
            'climate': climate,
            'input_number': input_number,
            'automation': automation,
        }, encoding='utf-8', allow_unicode=True, default_flow_style=False, explicit_start=True).decode("utf-8")

    def __enter__(self):
        for c, _ in self._components:
            c.__enter__()

        sleep_for(1)  # Give home assistant a chance to catch up

        for c, _ in self._components:
            c.available_set(True)
        return self

    def __exit__(self, *args):
        for c, _ in self._components:
            c.__exit__(args)
