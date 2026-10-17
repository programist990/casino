import os
import math
import struct
import wave

SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sounds")
os.makedirs(SOUND_DIR, exist_ok=True)
SAMPLE_RATE = 22050

def write_wav(filename, samples):
    path = os.path.join(SOUND_DIR, filename)
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        data = bytearray()
        for s in samples:
            val = max(-32767, min(32767, int(s * 32767)))
            data.extend(struct.pack("<h", val))
        f.writeframes(data)
    print(f"Generated {filename}")

def gen_click():
    # Very short 30ms click
    samples = []
    duration = 0.04
    total = int(SAMPLE_RATE * duration)
    for i in range(total):
        t = i / SAMPLE_RATE
        freq = 1200 - 800 * (i / total)
        env = math.exp(-t * 80)
        s = math.sin(2 * math.pi * freq * t) * env * 0.7
        samples.append(s)
    write_wav("click.wav", samples)

def gen_stop():
    # Solid mechanical thud / snap
    samples = []
    duration = 0.08
    total = int(SAMPLE_RATE * duration)
    for i in range(total):
        t = i / SAMPLE_RATE
        freq = 280 * math.exp(-t * 20)
        env = math.exp(-t * 40)
        s = math.sin(2 * math.pi * freq * t) * env * 0.9
        samples.append(s)
    write_wav("stop.wav", samples)

def gen_spin():
    # Whirring mechanical roll
    samples = []
    duration = 0.15
    total = int(SAMPLE_RATE * duration)
    for i in range(total):
        t = i / SAMPLE_RATE
        s = 0.5 * math.sin(2 * math.pi * (160 + 40 * math.sin(2 * math.pi * 30 * t)) * t)
        env = math.sin(math.pi * (i / total))
        samples.append(s * env * 0.5)
    write_wav("spin.wav", samples)

def gen_bonus():
    # Rising triumphant arpeggio chime (C - E - G - C)
    samples = []
    notes = [523.25, 659.25, 783.99, 1046.50]
    note_dur = 0.12
    for note in notes:
        total = int(SAMPLE_RATE * note_dur)
        for i in range(total):
            t = i / SAMPLE_RATE
            env = math.exp(-t * 12)
            s = (math.sin(2 * math.pi * note * t) + 0.3 * math.sin(4 * math.pi * note * t)) * env * 0.6
            samples.append(s)
    write_wav("bonus.wav", samples)

def gen_crash():
    # Deep explosion / crash sound
    import random
    samples = []
    duration = 0.6
    total = int(SAMPLE_RATE * duration)
    for i in range(total):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 6)
        noise = random.uniform(-1, 1)
        sub = math.sin(2 * math.pi * (80 - 40 * (i / total)) * t)
        s = (noise * 0.7 + sub * 0.5) * env * 0.8
        samples.append(s)
    write_wav("crash.wav", samples)

if __name__ == "__main__":
    gen_click()
    gen_stop()
    gen_spin()
    gen_bonus()
    gen_crash()
