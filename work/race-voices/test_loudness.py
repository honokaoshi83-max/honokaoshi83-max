import unittest, subprocess, json, re
from pathlib import Path
import bridge

class LoudnessTests(unittest.TestCase):
    def test_real_voice_is_audible_and_peak_safe(self):
        import io, wave, math, struct
        stream=io.BytesIO()
        with wave.open(stream,'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(32000)
            w.writeframes(b''.join(struct.pack('<h',int(200*math.sin(2*math.pi*440*n/32000))) for n in range(96000)))
        source=stream.getvalue()
        normalize = getattr(bridge, 'normalize_audio', None)
        self.assertIsNotNone(normalize, 'Pure voice loudness normalization missing')
        result = normalize(source, 'mp3')
        def measure(audio):
            p = subprocess.run([str(bridge.FFMPEG), '-hide_banner', '-i', 'pipe:0', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json', '-f', 'null', 'NUL'], input=audio, capture_output=True, check=True)
            return json.loads(re.search(r'\{\s*"input_i".*?\}', p.stderr.decode(), re.S).group())
        before, after = measure(source), measure(result)
        self.assertGreater(float(after['input_i']), float(before['input_i']) + 3)
        self.assertLessEqual(float(after['input_tp']), -1)
        self.assertGreater(float(after['input_i']), -18)

if __name__ == '__main__': unittest.main()
