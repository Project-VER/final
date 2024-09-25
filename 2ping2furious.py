'''
File: 2ping2furious.py
Created Date: Wednesday, September 25th 2024, 6:55:40 pm
Author: alex-crouch

Project Ver 2024
'''

import numpy as np
import sounddevice as sd
import time
import wave

def generate_note(freqs, duration=0.2, sample_rate=24000):
    t = np.linspace(0, duration, int(sample_rate * duration * 2), False)
    note = np.sum([np.sin(2 * np.pi * f * t) for f in freqs], axis=0)
    
    # Apply envelope
    envelope = np.exp(-t * 40)  # Fast decay
    note = note * envelope
    
    return note / np.max(np.abs(note))

def apply_envelope(tone, attack=0.01, decay=0.1):
    total_length = len(tone)
    attack_samples = int(attack * total_length)
    decay_samples = int(decay * total_length)
    
    envelope = np.ones_like(tone)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)
    
    return tone * envelope

def generate_waiting_tone(note1_freqs, note2_freqs, gap=0.05, sample_rate=24000):
    note1 = generate_note(note1_freqs)
    note2 = generate_note(note2_freqs)
    
    gap_samples = int(gap * sample_rate)
    tone = np.concatenate([note1, np.zeros(gap_samples), note2])
    
    # tone = apply_envelope(tone, attack=0.0006, decay=0.0005)

    tone = tone / np.max(np.abs(tone))

    tone = tone / 8
    # tone = apply_envelope(tone, attack=0.5, decay=0.95)
    
    return tone

def play_waiting_tone(tone_func):
    tone = tone_func()
    sd.play(tone, samplerate=44100)
    # sd.wait()
    # time.sleep(1.5)  # Wait before playing the next tone

# Five different waiting tones
def waiting_tone_1():
    return generate_waiting_tone([1000, 1200], [800, 1000], gap=0.8)

def waiting_tone_2():
    return generate_waiting_tone([1500, 1800], [1200, 1500], gap=0.005)

def waiting_tone_3():
    return generate_waiting_tone([900, 1100, 1300], [700, 900, 1100], gap=0)

def waiting_tone_4():
    return generate_waiting_tone([1200, 1400], [1400, 1600], gap=0)

def waiting_tone_5():
    return generate_waiting_tone([800, 1000, 1200], [1000, 1200, 1400], gap=0)

def save_click_as_wav(ping, filename='waiting_sound.wav', sample_rate=44100):
    """Save the click sound as a WAV file."""
    # Convert to 16-bit PCM
    click_int = np.int16(ping * 32767)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(click_int.tobytes())
    
    print(f"ping sound saved as {filename}")

if __name__ == "__main__":
    print(type(waiting_tone_1))
    tone = generate_waiting_tone([1000, 1200], [800, 1000], gap=0.8)
    save_click_as_wav(tone, filename='waiting_sound.wav', sample_rate=44100)
    while True:
        print("Playing waiting tone 1")
        play_waiting_tone(waiting_tone_1)
        time.sleep(2)
    # print("Playing waiting tone 2")
    # play_waiting_tone(waiting_tone_2)
    # print("Playing waiting tone 3")
    # play_waiting_tone(waiting_tone_3)
    # print("Playing waiting tone 4")
    # play_waiting_tone(waiting_tone_4)
    # print("Playing waiting tone 5")
    # play_waiting_tone(waiting_tone_5)

# Function to use in async context
async def play_waiting_tone_async(tone_func):
    while True:
        tone = tone_func()
        sd.play(tone, samplerate=44100)
        await asyncio.sleep(len(tone) / 44100)
        await asyncio.sleep(1.5)  # Gap between repeats