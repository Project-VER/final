import soundfile as sf
import numpy as np
import pyaudio
import sys

class AudioStreamer:
    def __init__(self, file_path, speed_factor=1.0):
        self.file_path = file_path
        self.speed_factor = speed_factor
        self.data, self.samplerate = sf.read(file_path, dtype='float32')
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=self.data.shape[1] if len(self.data.shape) > 1 else 1,
            rate=int(self.samplerate),
            output=True
        )

    def play(self):
        # Calculate the indices of the samples to play
        indices = np.arange(0, len(self.data), self.speed_factor)
        # Ensures that the indices are integers
        indices = indices.astype(int)
        # Extract only the samples that need to be played
        sped_up_data = self.data[indices]

        # Stream the sped up data
        for i in range(0, len(sped_up_data), 1024):
            chunk_data = sped_up_data[i:i+1024]
            self.stream.write(chunk_data.tobytes(), num_frames=len(chunk_data))

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

def main(file_path, speed_factor):
    if speed_factor <= 0:
        print("Speed factor must be positive")
        return

    player = AudioStreamer(file_path, float(speed_factor))
    try:
        player.play()
    except KeyboardInterrupt:
        print("Playback interrupted")
    finally:
        player.close()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 audio_streamer.py <file_path> <speed_factor>")
        sys.exit(1)

    file_path = sys.argv[1]
    speed_factor = float(sys.argv[2])
    main(file_path, speed_factor)

