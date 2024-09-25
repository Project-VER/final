'''
File: swapouts_qmh.py
Created Date: Wednesday, September 25th 2024, 8:31:36 pm
Author: alex-crouch

Project Ver 2024
'''

### Differing functionality for qmh.py functions

# Case B hold and accompanying input_speech function
elif self.state == State.CASEB:
                print('CASE B')
                self.current_task = asyncio.create_task(self.play_sound_async(self.read_sound))
                self.caseb_start_time = time.time()
                stop_event = threading.Event()
                # result = ''
                # result = self.input_speech(stop_event)
                que = Queue()
                audioR = threading.Thread(target=lambda q, arg1: q.put(self.input_speech(arg1)), args=(que, stop_event), daemon=True)
                audioR.start()
                print('good')
                self.mq.clear()
                await asyncio.sleep(1)
                while audioR.is_alive(): # Allow cancel when audio stream is active
                # while self.mq.count([GPIO_B, RISING_EDGE])!=0:
                    await asyncio.sleep(0.01)
                    if self.mq.count([GPIO_B, RISING_EDGE])!=0:
                        stop_event.set()
                        # await asyncio.sleep(0.1)  # Give a short time for the audio stream to stop
                        # # await self.play_sound_async(self.cancel_sound)
                        audioR.join()
                        # print(" ".join(result))
                        self.mq.clear()
                        await asyncio.sleep(2)
                        break
                self.mq.clear()
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
                    print('good')
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

def input_speech(self, stop_event):
        detection = None
        with sd.RawInputStream(samplerate=self.samplerate, blocksize = 8000, device=None,
            dtype="int16", channels=1, callback=self.audio_callback): # begin recording
            print("Start speaking...")
            rec = KaldiRecognizer(self.model, self.samplerate)
            while True:
                if not stop_event.is_set():
                    data = self.q.get() # Get audio data from the queue
                    if rec.AcceptWaveform(data):
                        self.play_sound(self.ping_sound) # Play voice received ping
                        ting = json.loads(rec.Result()) # Inference on model
                        print(ting.get("text", "")) # Format detection
                else:
                    break
            try:
                return ting.get("text", "") # Format detection
            except:
                return None