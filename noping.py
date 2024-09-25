'''
File: noping.py
Created Date: Wednesday, September 25th 2024, 7:06:30 pm
Author: alex-crouch

Project Ver 2024
'''

import numpy as np
import sounddevice as sd
import time

def generate_click(duration=0.1, sample_rate=44100, attack=0.05, decay=0.02):
    """Generate a click sound with attack and decay."""
    num_samples = int(duration * sample_rate)
    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    
    # Create noise
    samples = np.random.uniform(-1, 1, num_samples)
    
    # Create ADSR envelope
    attack_envelope = np.linspace(0, 1, attack_samples)
    decay_envelope = np.exp(-np.linspace(0, 5, decay_samples))
    sustain_samples = num_samples - attack_samples - decay_samples
    if sustain_samples > 0:
        sustain_envelope = np.ones(sustain_samples) * decay_envelope[-1]
        envelope = np.concatenate([attack_envelope, decay_envelope, sustain_envelope])
    else:
        envelope = np.concatenate([attack_envelope, decay_envelope])[:num_samples]
    
    # Apply envelope
    click = samples * envelope
    
    # Normalize
    click = click / np.max(np.abs(click))
    
    return click.astype(np.float32)

def play_click():
    """Play the click sound."""
    click = generate_click()
    sd.play(click, samplerate=44100)
    sd.wait()  # Wait for the sound to finish playing

def simulate_processing(steps=5, delay=0.5):
    """Simulate a processing task with click sounds."""
    print("Processing...")
    for _ in range(steps):
        play_click()
        time.sleep(delay)
    print("Done!")

if __name__ == "__main__":
    # Ensure audio output is properly initialized
    with sd.Stream(samplerate=44100, channels=1):
        pass
    
    simulate_processing()