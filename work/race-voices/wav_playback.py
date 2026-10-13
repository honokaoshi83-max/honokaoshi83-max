"""Finalize streamed PCM WAV lengths for Windows PlaySound."""
import io
import wave

def finalize_wav(data):
    with wave.open(io.BytesIO(data), 'rb') as source:
        params = source.getparams()
        samples = source.readframes(source.getnframes())
    alignment = params.nchannels * params.sampwidth
    if not samples or len(samples) % alignment:
        raise ValueError('语音音频为空或 PCM 数据不完整。')
    target = io.BytesIO()
    with wave.open(target, 'wb') as output:
        output.setnchannels(params.nchannels)
        output.setsampwidth(params.sampwidth)
        output.setframerate(params.framerate)
        output.writeframes(samples)
    return target.getvalue()
