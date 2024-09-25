'''
File: qmh.py
Created Date: Wednesday, September 25th 2024, 1:42:38 pm
Author: alex-crouch

Project Ver 2024
'''

from collections import deque
import asyncio
from enum import Enum
import time
import os
import gpiod
from gpiod.line import Bias, Edge
from datetime import timedelta
import select
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np
import requests
from queue import Queue, Empty
import re
from vosk import Model, KaldiRecognizer
import json
import queue

FALLING_EDGE = "Falling"
RISING_EDGE = "Rising"
GPIO_A = 2
GPIO_B = 3

class State(Enum):
    IDLE = 0
    CASEA = 1
    CASEB = 2
    BOOT = 3

class AudioStreamer(object):
    def __init__(self, base_address='192.168.193.33', port=8000, samplerate=24000, channels=1):
        self.base_address = base_address
        self.port = port
        self.url = f'http://{base_address}:{port}'
        self.samplerate = samplerate
        self.channels = channels
        self.stream = None
        self.response = None
        self.starttime = None
        self.call = False
        self.waiting_sound, self.file_samplerate = sf.read('/home/ver/cr2/lib_client/waiting.wav')
        self.no_internet_sound, self.file_samplerate = sf.read('/home/ver/cr2/lib_client/internot.wav')
    
    def play_loop(self, no_loop_event, sound):
        time.sleep(2)
        while not no_loop_event.is_set():
            sd.play(sound, self.file_samplerate)
            time.sleep(2)
    
    def run_audio_stream(self, stop_event, image_path, text, timer=False):
        # Flag to print request to stream time handling
        if timer is True:
            self.starttime = time.time()
            self.call = True
        
        # Initialise sounddevice stream
        self.stream = sd.OutputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype='float32',
        )
        
        files = {'file': open(image_path, 'rb')}
        data = {'text': text}
        
        no_loop_event = threading.Event()
        audioL = threading.Thread(target=self.play_loop, args=(no_loop_event, self.waiting_sound), daemon=True)
        audioL.start()
        try:
            self.response = requests.get(self.url, files=files, data=data, stream=True)

            no_loop_event.set()
            audioL.join()

            with self.stream:
                print("Audio Stream Commenced")
                try:
                    for chunk in self.response.iter_content(chunk_size=56):
                        if self.call is True:   # print time on first chunk if enabled
                            elapsed_time = time.time() - self.starttime
                            print('[{}] finished in {} ms'.format('Request to Stream', int(elapsed_time * 1_000)))
                            self.call = False
                        
                        if chunk and not stop_event.is_set():  # continuously write to output device
                            audio_data = np.frombuffer(chunk, dtype=np.int16)
                            audio_float = audio_data.astype(np.float32) / 32768.0
                            self.stream.write(audio_float)
                        else:
                            print('cancelled')
                            break
                except Exception as e:
                    print(f"Error: {e}")
                finally:
                    self.response.close()

        except Exception as e:
            print(f"Error: {e}")
            no_loop_event.set()
            audioL.join()
            sd.play(self.no_internet_sound, self.file_samplerate)
            sd.wait()

        finally: # Tidy up stream and connection
            print("Finished Audio Stream")
            self.stream.close()


class QueuedMessageHandler:
    def __init__(self):
        self.done_fd = os.eventfd(0)
        self.mq = deque()
        self.state = State.IDLE
        self.ASC = AudioStreamer()
        self.base_address = '192.168.193.33'
        self.port = 8000
        self.cancel_url = f'http://{self.base_address}:{self.port}/cancel'
        self.running = True
        self.help = True
        
        # Load the sounds
        self.cancel_sound, self.file_samplerate = sf.read('/home/ver/cr2/lib_client/cancel.wav')
        self.desc_sound, self.file_samplerate = sf.read('/home/ver/cr2/lib_client/desc.wav')
        self.chat_sound, self.file_samplerate = sf.read('/home/ver/cr2/lib_client/chat.wav')
        self.helper_sound, self.file_samplerate = sf.read('/home/ver/cr2/lib_client/helper.wav')
        self.ping_sound = self.generate_ping()
        self.ping_samplerate = 44100

        # Set the pre-configured prompts
        self.describe_prompt = 'Describe the content in 40 words or less. Use natural language suitable for conversion to speech.'
        self.read_prompt = 'Read the text in 40 words or less. Include what the text represents. If there is no text respond as such. Use natural language suitable for conversion to speech.'

        # Initialize Vosk model for speech recognition
        self.model = Model(lang="en-us")
        self.device_info = sd.query_devices(None, "input")
        self.samplerate = int(self.device_info["default_samplerate"])
        self.rec = KaldiRecognizer(self.model, self.samplerate)
        self.q = queue.Queue()
    
    def generate_ping(self, freq1=1500, freq2=1800, duration=0.15, sample_rate=44100):
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Generate two sine waves
        tone1 = np.sin(2 * np.pi * freq1 * t)
        tone2 = np.sin(2 * np.pi * freq2 * t)
        
        # Combine the tones
        tone = tone1 + tone2
        
        # Normalize
        tone = tone / np.max(np.abs(tone))
        
        # Apply an exponential decay envelope
        envelope = np.exp(-t * 30)
        tone = tone * envelope
        
        return tone

    def play_sound(self, sound):
        sd.play(sound, self.file_samplerate)

    def play_cancellable_sound(self, stop_event, sound):
        self.data = sound.reshape(-1, 1)
        fs = self.file_samplerate

        self.current_frame = 0

        stream = sd.OutputStream(
            samplerate=fs, device=None, channels=1,
            callback=self.output_callback, finished_callback=stop_event.set)
        with stream:
            while not stop_event.is_set():
                stop_event.wait()  # Wait until playback is finished

    def input_callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def edge_type_str(self, event):
        if event.event_type is event.Type.RISING_EDGE:
            return RISING_EDGE
        if event.event_type is event.Type.FALLING_EDGE:
            return FALLING_EDGE
        return "Unknown"

    async def async_watch_line_value(self, chip_path, line_offsets, done_fd):
        with gpiod.request_lines(
            chip_path,
            consumer="gpio-state-machine",
            config={tuple(line_offsets): gpiod.LineSettings(edge_detection=Edge.BOTH, debounce_period=timedelta(milliseconds=20))},
        ) as request:
            while self.running:
                # Use asyncio.get_event_loop().run_in_executor to run blocking operations in a separate thread
                events = await asyncio.get_event_loop().run_in_executor(None, request.read_edge_events)
                for event in events:
                    self.mq.append([event.line_offset, self.edge_type_str(event)])
                
                # Check if we need to stop
                if await self.is_done(done_fd):
                    return

    async def is_done(self, done_fd):
        # Use asyncio.select to check the done_fd without blocking
        r, _, _ = await asyncio.get_event_loop().run_in_executor(None, select.select, [done_fd], [], [], 0)
        return bool(r)

    def input_speech(self, stop_event):
        detection = None
        with sd.RawInputStream(samplerate=self.samplerate, blocksize = 8000, device=None,
            dtype="int16", channels=1, callback=self.input_callback): # begin recording
            print("Start speaking...")
            rec = KaldiRecognizer(self.model, self.samplerate)
            while not stop_event.is_set():
                data = self.q.get() # Get audio data from the queue
                if rec.AcceptWaveform(data):
                    self.play_sound(self.ping_sound) # Play voice received ping
                    ting = json.loads(rec.Result()) # Inference on model
                    print(ting.get("text", "")) # Format detection
                    return ting.get("text", "") # Format detection

    def output_callback(self, outdata, frames, time, status):
            if status:
                print(status)
            chunksize = min(len(self.data) - self.current_frame, frames)
            outdata[:chunksize] = self.data[self.current_frame:self.current_frame + chunksize]
            if chunksize < frames:
                outdata[chunksize:] = 0
                raise sd.CallbackStop()
            self.current_frame += chunksize

    async def state_run(self):
        stop_event = threading.Event()
        audioB = threading.Thread(target=self.play_cancellable_sound, args=(stop_event, self.helper_sound), daemon=True)
        audioB.start()
        while audioB.is_alive(): # Allow cancel when audio stream is active
            await asyncio.sleep(0.1)
            if self.mq.count([GPIO_A, FALLING_EDGE])!=0 or self.mq.count([GPIO_B, FALLING_EDGE])!=0:
                stop_event.set()
                await asyncio.sleep(0.1)  # Give a short time for the audio stream to stop
                break
        audioB.join()
        self.mq.clear()
                
        while self.running:
            await asyncio.sleep(0.01)

            if self.state == State.IDLE:
                await asyncio.sleep(0.01)
                if self.mq.count([GPIO_A, FALLING_EDGE])!=0:
                    self.state = State.CASEA
                    self.mq.clear()
                if self.mq.count([GPIO_B, FALLING_EDGE])!=0:
                    self.state = State.CASEB
                    self.mq.clear()

            elif self.state == State.CASEA:
                print('CASE A')
                print(threading.active_count())
                asyncio.create_task(self.play_sound_async(self.desc_sound))
                stop_event = threading.Event()
                audioS = threading.Thread(target=self.ASC.run_audio_stream, name='AudioStream',
                    args=(stop_event,'/home/ver/cr2/lib_client/mpv-shot0001.jpg', self.describe_prompt), daemon=True)
                audioS.start()
                await asyncio.sleep(1)
                self.mq.clear()
                while audioS.is_alive(): # Allow cancel when audio stream is active
                    await asyncio.sleep(0.01)
                    if self.mq.count([GPIO_A, FALLING_EDGE])!=0 or self.mq.count([GPIO_B, FALLING_EDGE])!=0:
                        stop_event.set()
                        try:
                            response = requests.post(self.cancel_url)
                        except Exception as e:
                            print(f"Error: {e}")
                        await asyncio.sleep(0.1)  # Give a short time for the audio stream to stop
                        await self.play_sound_async(self.cancel_sound)
                        audioS.join()
                        self.mq.clear()
                        break
                self.mq.clear()
                try:
                    audioS.join()
                except:
                    pass
                self.state = State.IDLE
            
            elif self.state == State.CASEB:
                print('CASE B')
                result = None
                asyncio.create_task(self.play_sound_async(self.chat_sound))
                stop_event = threading.Event()
                que = Queue()
                audioR = threading.Thread(target=lambda q, arg1: q.put(self.input_speech(arg1)), args=(que, stop_event), daemon=True)
                audioR.start()
                self.mq.clear()
                await asyncio.sleep(1)
                while audioR.is_alive(): # Allow cancel when audio stream is active
                    await asyncio.sleep(0.01)
                    if self.mq.count([GPIO_A, FALLING_EDGE])!=0 or self.mq.count([GPIO_B, FALLING_EDGE])!=0:
                        stop_event.set()
                        await asyncio.sleep(0.1)  # Give a short time for the audio stream to stop
                        await self.play_sound_async(self.cancel_sound)
                        break
                self.mq.clear()
                audioR.join()
                result = que.get()
                print(result)
                if result == None:
                    await self.play_sound_async(self.cancel_sound)
                    self.mq.clear()
                    self.state = State.IDLE

                if result != None:
                    stop_event = threading.Event()
                    audioS = threading.Thread(target=self.ASC.run_audio_stream, name='AudioStream', args=(stop_event,'/home/ver/cr2/lib_client/mpv-shot0001.jpg', result), daemon=True)
                    audioS.start()
                    await asyncio.sleep(1)
                    self.mq.clear()
                    while audioS.is_alive(): # Allow cancel when audio stream is active
                        await asyncio.sleep(0.01)
                        if self.mq.count([GPIO_A, FALLING_EDGE])!=0 or self.mq.count([GPIO_B, FALLING_EDGE])!=0:
                            stop_event.set()
                            response = requests.post(self.cancel_url)
                            await asyncio.sleep(0.1)  # Give a short time for the audio stream to stop
                            await self.play_sound_async(self.cancel_sound)
                            audioS.join()
                            self.mq.clear()
                            break
                    stop_event.set()
                    self.mq.clear()
                    self.active_operation = False
                    try:
                        audioS.join()
                    except:
                        pass
                    self.state = State.IDLE
                
    async def play_sound_async(self, sound):
        await asyncio.get_event_loop().run_in_executor(None, self.play_sound, sound)

    async def run(self):
        await asyncio.gather(
            self.async_watch_line_value("/dev/gpiochip4", [2, 3], self.done_fd),
            self.state_run())

    def stop(self):
        self.running = False

async def main():
    qmh = QueuedMessageHandler()
    try:
        await qmh.run()
    except asyncio.CancelledError:
        qmh.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping...")