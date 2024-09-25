'''
File: ping.py
Created Date: Wednesday, September 25th 2024, 6:27:38 pm
Author: alex-crouch

Project Ver 2024
'''

import numpy as np
import sounddevice as sd

def generate_phone_ping(freq1=1500, freq2=1800, duration=0.15, sample_rate=44100):
    """Generate a phone-like notification ping sound."""
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

def generate_wait_ping(freq1=1300, freq2=1500, duration=0.1, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate two sine waves
    tone1 = np.sin(2 * np.pi * freq1 * t)
    tone2 = np.sin(2 * np.pi * freq2 * t)
    
    # Combine the tones
    tone = tone1 + tone2
    
    # Normalize
    # tone = tone / np.max(np.abs(tone))
    
    # Apply an exponential decay envelope
    # envelope = np.exp(-t * 30)
     # Create ADSR envelope
    tone = apply_envelope(tone, attack=0.0006, decay=0.0005)
    tone = tone / np.max(np.abs(tone))
    # tone = tone * envelope
    
    return tone

import numpy as np
import sounddevice as sd
import time

def generate_sine_wave(freq, duration, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    return np.sin(2 * np.pi * freq * t)

def apply_envelope(tone, attack=0.01, decay=0.1):
    total_length = len(tone)
    attack_samples = int(attack * total_length)
    decay_samples = int(decay * total_length)
    
    envelope = np.ones_like(tone)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)
    
    return tone * envelope

def waiting_tone_1(duration=3.0, sample_rate=44100):
    """Gentle ascending pings"""
    tone = np.zeros(int(sample_rate * duration))
    for i, freq in enumerate([500, 600, 700, 800]):
        ping = apply_envelope(generate_sine_wave(freq, 0.1, sample_rate))
        start = int(i * 0.5 * sample_rate)
        tone[start:start+len(ping)] += ping
    return tone / np.max(np.abs(tone))

def waiting_tone_2(duration=3.0, sample_rate=44100):
    """Soft alternating high-low pings"""
    tone = np.zeros(int(sample_rate * duration))
    for i in range(6):
        freq = 800 if i % 2 == 0 else 600
        ping = apply_envelope(generate_sine_wave(freq, 0.05, sample_rate))
        start = int(i * 0.5 * sample_rate)
        tone[start:start+len(ping)] += ping
    return tone / np.max(np.abs(tone))

def waiting_tone_3(duration=3.0, sample_rate=44100):
    """Gentle descending triad"""
    tone = np.zeros(int(sample_rate * duration))
    for i, freq in enumerate([800, 600, 500]):
        ping = apply_envelope(generate_sine_wave(freq, 0.15, sample_rate))
        start = int(i * 0.2 * sample_rate)
        tone[start:start+len(ping)] += ping
    return tone / np.max(np.abs(tone))

def waiting_tone_4(duration=3.0, sample_rate=44100):
    """Soft pulsing tone"""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    carrier = np.sin(2 * np.pi * 600 * t)
    modulator = 0.5 + 0.5 * np.sin(2 * np.pi * 1 * t)
    tone = carrier * modulator
    return tone / np.max(np.abs(tone))

def waiting_tone_5(duration=3.0, sample_rate=44100):
    """Gentle rising bubbles"""
    tone = np.zeros(int(sample_rate * duration))
    for i in range(5):
        freq = 500 + i * 50
        ping = apply_envelope(generate_sine_wave(freq, 0.1, sample_rate), attack=0.02, decay=0.2)
        start = int(i * 0.4 * sample_rate)
        tone[start:start+len(ping)] += ping
    return tone / np.max(np.abs(tone))

def play_tone(tone_func):
    tone = tone_func()
    sd.play(tone, samplerate=44100)
    sd.wait()

def play_phone_ping():
    """Generate and play a phone-like ping sound."""
    ping = generate_phone_ping()
    sd.play(ping, samplerate=44100)
    sd.wait()

def play_wait_ping():
    """Generate and play a phone-like ping sound."""
    ping = generate_wait_ping()
    sd.play(ping, samplerate=44100)
    sd.wait()

if __name__ == "__main__":
    # print("Playing waiting tone 1")
    # play_tone(waiting_tone_1)
    # print("Playing waiting tone 2")
    # play_tone(waiting_tone_2)
    # print("Playing waiting tone 3")
    # play_tone(waiting_tone_3)
    # print("Playing waiting tone 4")
    # play_tone(waiting_tone_4)
    # print("Playing waiting tone 5")
    # play_tone(waiting_tone_5)
    play_wait_ping()
    time.sleep(2)
    play_wait_ping()


    # play_phone_ping()
    # time.sleep(2)
    # while True:
    #     play_phone_ping()
    #     time.sleep(0.16)
    #     play_phone_ping()
    #     time.sleep(1)
    # print("Phone notification ping played!")