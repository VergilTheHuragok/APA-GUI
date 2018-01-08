import threading
import time

import nidaqmx
import pyglet
import xlsxwriter
# TODO: Create Spreadsheets
# TODO: allow file choice (tkinter)
# TODO: Allow file overwrite or append
# TODO: Add batch to file on next batch press
# TODO: Replace export button with select file button

from sensor_generation import TaskReadThread
from sensor_generation import task_read

GUI = True
simulated = True

slide_time = 1000  # TODO: Time seeds for actual amount
use_slide_time = False

column_colors = 2
lightest_background_shade = .3

width = 1080
height = 720
fps = 60
update_interval = 100  # How often to redraw

active_box_height = 50
active_sensor_label_height = 5
small_box_min_y = height - 300
squares_per_row = 1

count_positions = {}
nudge_buttons = []

start_button = None  # TODO: Finish buttons, make file interaction
clear_button = None
next_batch_button = None
export_button = None

batch_num = 1

active_sensors = []
count_log = {}

task = None

labels = []
main_batch = pyglet.graphics.Batch()
update = True
resized = True

started = False


def get_active_sensors(data):
    _sensors = []
    sensor_id = 0
    for channel_data in data:
        # Convert each channel to reversed binary
        # Each digit corresponds to a sensor
        for sensor in bin(channel_data)[2:][::-1] + \
                ("0" * (8 - len(bin(channel_data)[2:]))):  # BLACK MAGIC!
            sensor_id += 1
            if int(sensor) and not sensor_id == 24:
                _sensors.append(sensor_id)
    return _sensors


class Button:
    """Creates a button"""

    def __init__(self, x, y, w, h, c, t, tc, ts=None):
        self.ts = ts
        self.t = t
        self.tc = list(tc)
        self.tc.append(255)
        self.c = list(c)
        self.h = h
        self.w = w
        self.y = y
        self.x = x
        if isinstance(self.ts, type(None)):
            self.ts = self.w

    def render(self):
        """Renders the button to the screen"""
        x = self.x
        y = self.y
        w = self.w
        h = self.h
        rect = [x, y, x + w, y, x + w, y - h, x, y - h]
        label = pyglet.text.Label(self.t, font_name='segoeui',
                                  font_size=self.ts, x=x + w / 2,
                                  y=y - h / 2, anchor_x='center',
                                  anchor_y='center',
                                  color=self.tc)
        labels.append(label)
        colors = []
        for i in range(0, 4):
            for color in self.c:
                colors.append(color)
        main_batch.add(4, pyglet.gl.GL_QUADS, None,
                       ("v2f", rect),
                       ("c3f", colors))

    def get_pressed(self, x, y):
        if self.x <= x <= self.x + self.w and self.y >= y >= self.y - self.h:
            return True
        return False


class CountThread(threading.Thread):
    """Counts the seeds"""

    def __init__(self):
        global count_log

        threading.Thread.__init__(self, name="CountThread")
        count_log = {i: 0 for i in range(1, 24)}
        self.activation_time_log = {i: int(round(time.time() * 1000))
                                    for i in range(1, 24)}
        self.previous_log = {i: False for i in range(1, 24)}

    def run(self):
        global active_sensors
        global count_log
        global update

        while True:
            time.sleep(.01)  # Necessary to prevent lag with pyglet
            if simulated:
                raw_data = task_read()
            else:
                raw_data = task.read()

            new_active_sensors = get_active_sensors(raw_data)
            if active_sensors != new_active_sensors:
                active_sensors = new_active_sensors
                update = True
                print("HJERE")
            if started:
                for sensor in active_sensors:
                    if use_slide_time:
                        if self.activation_time_log[sensor] + slide_time \
                                <= int(round(time.time() * 1000)) \
                                or not self.previous_log[sensor]:
                            update = True
                            self.previous_log[sensor] = True
                            count_log[sensor] += 1
                            self.activation_time_log[sensor] = int(
                                round(time.time() * 1000))
                    else:
                        if not self.previous_log[sensor]:
                            update = True
                            self.previous_log[sensor] = True
                            count_log[sensor] += 1
                for sensor in filter(lambda x: x not in active_sensors,
                                     range(1, 24)):
                    # Remove inactive sensors from previous list
                    self.previous_log[sensor] = False


class Window(pyglet.window.Window):
    def __init__(self):
        super(Window, self).__init__(vsync=False, width=width, height=height,
                                     resizable=True,
                                     caption="Aerodynamic Properties Analyzer")
        self.iteration = 0
        self.fps = pyglet.clock.ClockDisplay()
        pyglet.clock.schedule_interval(self.update, 1.0 / fps)
        pyglet.clock.set_fps_limit(fps)

    def update(self, dt):
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        global update, started, count_log, squares_per_row
        button_id = 0
        for button in nudge_buttons:
            if button.get_pressed(x, y):
                update = True
                if button_id % 2 == 0:
                    count_log[button_id // 2 + 1] -= 1
                else:
                    count_log[button_id // 2 + 1] += 1
                break
            button_id += 1

        if start_button.get_pressed(x, y):
            update = True
            started = not started
        if clear_button.get_pressed(x, y):
            update = True
            count_log = {}
            for sensor in range(1, 24):
                count_log[sensor] = 0
                squares_per_row = 1

    def on_draw(self):
        global main_batch, labels, update, width, height, squares_per_row, \
            resized

        pyglet.clock.tick()
        self.clear()
        self.fps.draw()
        # Print events for debugging
        # self.push_handlers(pyglet.window.event.WindowEventLogger())

        new_width, new_height = self.get_size()
        if width != new_width or height != new_height:
            squares_per_row = 1
            update = True
            resized = True
        width = new_width
        height = new_height

        # Iterations necessary to clear active sensors
        if self.iteration >= update_interval or update:
            main_batch = pyglet.graphics.Batch()
            labels = []

            display_active_sensors(active_sensors)
            display_sensor_count(count_log)
            create_control_buttons()

            if resized:
                create_nudge_buttons()

            display_nudge_buttons()
            display_control_buttons()
            # Other processes go here
            self.iteration = 0
            update = False

        # Draw batch and labels
        main_batch.draw()
        for label in labels:
            label.draw()

        self.iteration += 1
        resized = False
        # TODO: Count, average, export, ect
        # TODO: Finish GUI and buttons, etc
        # TODO: Change to bars graph past certain count scaled from 0
        # TODO:     to highest count
        # TODO: Cx_Freeze


def box_details():
    box_space = width / 23
    margin = box_space / 3
    box_width = box_space - margin
    return box_space, margin, box_width


def display_active_sensors(_active_sensors):
    box_space, margin, box_width = box_details()
    if_sim = ""
    if simulated:
        if_sim = " | Simulation Running"
    label = pyglet.text.Label('Batch Num: ' + str(batch_num) + if_sim,
                              font_name='couriernew',
                              font_size=width / (5 * len("Active Sensors")),
                              x=margin / 2, y=height - margin / 2,
                              anchor_x='left', anchor_y='top',
                              color=(255, 255, 255, 255))
    labels.append(label)

    for sensor in range(1, 24):
        x = (sensor * box_space) - box_space / 1.25
        y = height - active_box_height
        dx = box_width
        dy = box_width

        shade = (((sensor % column_colors) + 1) / column_colors) * \
                lightest_background_shade

        background_rect = [x - dx / 4, y + dy / 2, x + dx * 2, y + dy / 2,
                           x + dx * 2,
                           small_box_min_y - dy, x - dx / 4,
                           small_box_min_y - dy]
        main_batch.add(4, pyglet.gl.GL_QUADS, None, ("v2f", background_rect),
                       ("c3f", list(shade for i in range(0, 12))))

        sensor_rect = [x, y, x + dx, y, x + dx, y - dy, x, y - dy]
        color = None
        if sensor in _active_sensors:
            color = (0, 1, 0)
        else:
            color = (.5, .5, .5)

        main_batch.add(4, pyglet.gl.GL_QUADS, None, ("v2f", sensor_rect),
                       ("c3f", list(color[j] for i in range(0, 4) for j in
                                    range(0, 3))))

        label = pyglet.text.Label(str(sensor),
                                  font_name='segoeui',
                                  font_size=box_width / 2,
                                  x=x + box_width / 2, y=y - box_width / 2,
                                  anchor_x='center', anchor_y='center',
                                  color=(50, 50, 50, 255))
        labels.append(label)


def display_sensor_count(sensor_count):
    global squares_per_row
    global count_positions

    box_space, margin, box_width = box_details()

    small_box_width = box_width / (squares_per_row + 1)
    small_box_margin = (box_width - (small_box_width * squares_per_row)) \
                       / squares_per_row
    small_box_y_start = height - (active_box_height + box_width)

    for sensor in range(1, 24):
        for tally in range(0, sensor_count[sensor]):

            x = sensor * box_space - box_space / 1.25 + small_box_margin / 2
            x += (tally % squares_per_row) * \
                 (small_box_width + small_box_margin)
            y = small_box_y_start - (((tally // squares_per_row) + 1) *
                                     (small_box_width + 1))
            w = small_box_width
            sensor_rect = [x, y, x + w, y, x + w, y - w, x, y - w]
            main_batch.add(4, pyglet.gl.GL_QUADS, None,
                           ("v2f", sensor_rect),
                           ("c3f", list(.5 for i in range(0, 12))))
            if y - (small_box_width + small_box_margin) <= small_box_min_y:
                squares_per_row += 1

        x = (sensor * box_space) - box_width / 2
        y = small_box_min_y
        count_positions[sensor] = [x, y]
        label = pyglet.text.Label(str(sensor_count[sensor]),
                                  font_name='segoeui', font_size=box_width / 2,
                                  x=x, y=y, anchor_x='center', anchor_y='top',
                                  color=(255, 255, 255, 255))
        labels.append(label)


def display_control_buttons():
    start_button.render()
    clear_button.render()
    next_batch_button.render()
    export_button.render()


def create_control_buttons():
    """Creates buttons for user control"""
    global start_button, clear_button, next_batch_button, export_button

    box_space, margin, box_width = box_details()

    w = width / 23 * 2
    h = w / 3
    text_color = (25, 25, 25)

    text = "Start Recording"
    color = (0, .9, 0)
    if started:
        text = "Stop Recording"
        color = (.9, 0, 0)
    start_button = Button(0, h, w, h, color, text,
                          text_color, w / len(text) * 1.25)
    text = "Clear Batch"
    clear_button = Button((w + margin), h, w, h, (.9, .9, .9),
                          text, text_color, w / len(text) * 1.25)
    text = "Next Batch"
    next_batch_button = Button((w + margin) * 2, h, w, h,
                               (.5, .5, 0), text, text_color,
                               w / len(text) * 1.25)
    text = "Export All"
    export_button = Button((w + margin) * 3, h, w, h, (0, .5, .9),
                           text, text_color, w / len(text) * 1.25)


def create_nudge_buttons():
    """Creates nudge buttons"""
    global nudge_buttons
    nudge_button_positions = {}
    nudge_buttons = []
    box_space, margin, box_width = box_details()
    for i in range(1, 24):
        nudge_button_positions[i] = {
            "left": [count_positions[i][0] - box_width / 1.25,
                     count_positions[i][1] - box_width / 1.25,
                     box_width / 2],
            "right": [count_positions[i][0] - box_width / 10,
                      count_positions[i][1] - box_width / 1.25,
                      box_width / 2]}
    for button in nudge_button_positions:
        for dir in nudge_button_positions[button]:
            rect = nudge_button_positions[button][dir]
            x = rect[0]
            y = rect[1]
            w = rect[2]

            text = "+"
            color = .7
            if dir == "left":
                color = .5
                text = "-"

            nudge_buttons.append(
                Button(x, y, w, w, (color, color, color), text, (50, 50, 50)))


def display_nudge_buttons():
    """Displays nudge buttons"""
    for button in nudge_buttons:
        button.render()


def display_stats():
    """Displays stats"""
    average = 0

    for sensor in count_log:
        pass


def main():
    global task

    if simulated:
        task_read_thread = TaskReadThread()
        task_read_thread.setDaemon(True)
        task_read_thread.start()
    else:
        task = nidaqmx.Task()
        for i in range(0, 3):
            task.di_channels.add_di_chan("Dev1/port" + str(i) + "/line0:7")

    # Counting
    count_thread = CountThread()
    count_thread.setDaemon(True)
    count_thread.start()

    if GUI:
        window = Window()
        # TODO: Allow command based use.

        pyglet.app.run()


if __name__ == "__main__":
    main()
