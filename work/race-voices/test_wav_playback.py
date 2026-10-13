import io,struct,unittest,wave
from wav_playback import finalize_wav

class WavPlaybackTests(unittest.TestCase):
    def test_streamed_ffmpeg_lengths_are_repaired_without_changing_samples(self):
        samples = struct.pack('<h', 1234) * 32000
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(32000); w.writeframes(samples)
        streamed = bytearray(buffer.getvalue())
        streamed[4:8] = b'\xff' * 4; streamed[40:44] = b'\xff' * 4
        repaired = finalize_wav(bytes(streamed))
        self.assertEqual(struct.unpack('<I', repaired[4:8])[0], len(repaired)-8)
        with wave.open(io.BytesIO(repaired), 'rb') as w:
            self.assertEqual(w.getnframes(), 32000)
            self.assertEqual(w.readframes(32000), samples)

if __name__ == '__main__': unittest.main()
