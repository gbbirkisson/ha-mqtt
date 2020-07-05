import yaml

from climate import Climate
from sensor import Sensor, SettableSensor
from switch import Switch


def config_creator(components):
    sensor = []
    switch = []
    climate = []
    input_number = {}

    for c in components:
        tmp = c.get_config()
        tmp['platform'] = 'mqtt'
        if issubclass(type(c), Climate):
            climate.append(tmp)
        if issubclass(type(c), Switch):
            switch.append(tmp)
        if issubclass(type(c), Sensor):
            sensor.append(tmp)
        if issubclass(type(c), SettableSensor):
            input_number[c.get_id()] = {
                'name': c.get_name(),
                'min': c.get_min_state(),
                'max': c.get_max_state(),
                'step': c.get_step_state(),
                'icon': c.get_icon(),
                'unit_of_measurement': tmp['unit_of_measurement']
            }

    return yaml.dump({
        'sensor': sensor,
        'switch': switch,
        'climate': climate,
        'input_number': input_number
    }, encoding='utf-8', allow_unicode=True, default_flow_style=False, explicit_start=True).decode("utf-8")
