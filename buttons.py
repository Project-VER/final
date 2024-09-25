import gpiod
from gpiod.line import Bias, Edge
import select
import os
import threading
import time
from enum import Enum
from datetime import timedelta

class State(Enum):
    IDLE = 0
    CASEA = 1
    CASEB = 2
    CHECK = 3
    GRACE = 4
    SEND = 5
    PLAY = 6
    CANCEL = 7

class GPIOStateMachine:
    def __init__(self):
        self.done_fd = os.eventfd(0)
        self.state = State.IDLE
        self.next_state = None
        self.caseb_start_time = 0
        self.play_start_time = 0
        self.grace_start_time = 0
        self.grace_period = False
        self.a_pressed = False
        self.b_pressed = False
        self.input_queue = []

    def edge_type_str(self, event):
        if event.event_type is event.Type.RISING_EDGE:
            return "Rising"
        if event.event_type is event.Type.FALLING_EDGE:
            return "Falling"
        return "Unknown"

    def async_watch_line_value(self, chip_path, line_offsets, done_fd):
        with gpiod.request_lines(
            chip_path,
            consumer="gpio-state-machine",
            config={tuple(line_offsets): gpiod.LineSettings(edge_detection=Edge.BOTH,debounce_period=timedelta(milliseconds=20))},
        ) as request:
            poll = select.poll()
            poll.register(request.fd, select.POLLIN)
            poll.register(done_fd, select.POLLIN)
            
            while True:
                for fd, _ in poll.poll():
                    if fd == done_fd:
                        return
                    for event in request.read_edge_events():
                        self.handle_gpio_event(event)

    def handle_gpio_event(self, event):
        print(f"offset: {event.line_offset}  type: {self.edge_type_str(event):<7}  event #{event.line_seqno}")
        
        if event.line_offset == 2:  # Assuming GPIO 2 is for 'a' button
            if self.edge_type_str(event) == "Falling":
                self.input_queue.append(('a', True))
            elif self.edge_type_str(event) == "Rising":
                self.input_queue.append(('a', False))
        
        elif event.line_offset == 3:  # Assuming GPIO 3 is for 'b' button
            if self.edge_type_str(event) == "Falling":
                self.input_queue.append(('b', True))
            elif self.edge_type_str(event) == "Rising":
                self.input_queue.append(('b', False))

    def process_input(self):
        while self.input_queue:
            button, pressed = self.input_queue.pop(0)
            if button == 'a':
                self.a_pressed = pressed
            elif button == 'b':
                self.b_pressed = pressed

    def run_state_machine(self):
        while True:
            print(f"Current State: {self.state.name}")
            
            if self.state == State.IDLE:
                self.process_input()
                if self.a_pressed:
                    self.next_state = State.CASEA
                elif self.b_pressed:
                    self.next_state = State.CASEB
                    self.caseb_start_time = time.time()
                else:
                    time.sleep(0.1)

            elif self.state == State.CASEA:
                print("CASEA")
                time.sleep(0.5)  # Simulating some processing time
                self.next_state = State.SEND

            elif self.state == State.CASEB:
                print("CASEB")
                self.process_input()
                if not self.b_pressed:
                    self.next_state = State.CHECK
                else:
                    time.sleep(0.1)

            elif self.state == State.CHECK:
                print("CHECK")
                caseb_duration = time.time() - self.caseb_start_time
                print(f"CASEB ran for {caseb_duration:.2f} seconds")
                if caseb_duration < 3:
                    print("TOO SHORT")
                    self.next_state = State.IDLE
                else:
                    self.next_state = State.SEND

            elif self.state == State.GRACE:
                print("GRACE")
                if not self.grace_period:
                    self.grace_start_time = time.time()
                    self.grace_period = True
                
                self.process_input()
                
                if time.time() - self.grace_start_time >= 1:
                    print("Grace period ended")
                    self.grace_period = False
                    self.next_state = State.PLAY
                    self.play_start_time = time.time()
                elif self.a_pressed or self.b_pressed:
                    print("Button pressed during grace period")
                    self.next_state = State.CANCEL
                else:
                    time.sleep(0.1)

            elif self.state == State.SEND:
                print("SEND")
                time.sleep(0.5)  # Simulating some processing time
                self.next_state = State.GRACE
                self.grace_period = False  # Reset grace period

            elif self.state == State.PLAY:
                elapsed_time = time.time() - self.play_start_time
                if elapsed_time >= 10:
                    print("PLAY finished")
                    self.next_state = State.IDLE
                else:
                    self.process_input()
                    if self.a_pressed or self.b_pressed:
                        self.next_state = State.CANCEL
                    else:
                        print(f"PLAY ({int(elapsed_time) + 1})")
                        time.sleep(1)

            elif self.state == State.CANCEL:
                print("CANCEL")
                time.sleep(0.5)  # Simulating some processing time
                self.next_state = State.IDLE

            if self.next_state:
                self.state = self.next_state
                self.next_state = None
            
            if self.state == State.IDLE:
                time.sleep(0.1)  # Prevent busy-waiting in IDLE state

    def run(self):
        self.t = threading.Thread(target=self.async_watch_line_value, args=("/dev/gpiochip4", [2, 3], self.done_fd))
        self.t.start()
        
        try:
            self.run_state_machine()
        except KeyboardInterrupt:
            print("Exiting...")
            os.eventfd_write(self.done_fd, 1)
            self.t.join()

if __name__ == "__main__":
    GPIOStateMachine().run()