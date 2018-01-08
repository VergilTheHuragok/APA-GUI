import random
import threading

from time import sleep


# This file will be replaced with data from task.read()

probability = 100  # Higher number is less likely
sleep_multiplier = 10  # Higher is faster counting
raw_data = [0, 0, 128]


def task_read():
    return raw_data


def pick_sensors():
    sensors = {24}
    for sensor in range(1, 24):
        if not random.randint(0, probability):
            sensors.add(sensor)
    return sensors


def to_exponential_list(sensor_list):
    data = [0, 0, 0]
    for sensor in sensor_list:
        data[(sensor-1)//8] += 2**((sensor - 1) % 8)
    return data


class TaskReadThread(threading.Thread):
    """Generates data while main thread is checking data.
    Simulates task.read()
    """
    def __init__(self):
        threading.Thread.__init__(self, name="TaskReadThread")

    def run(self):
        global raw_data
        while True:
            sleep(random.randrange(0, 2000) / (1000 * sleep_multiplier))
            sensors = pick_sensors()
            raw_data = to_exponential_list(sensors)
