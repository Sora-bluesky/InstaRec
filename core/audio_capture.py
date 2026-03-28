"""Audio capture: soundcard loopback / microphone -> WAV file."""

import threading
import logging

logger = logging.getLogger(__name__)

try:
    import soundcard as sc
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logger.warning("soundcard/soundfile not available; audio disabled")


def list_microphones() -> list[dict]:
    """Return available microphone devices as [{id, name}, ...].

    Falls back to empty list on error or if soundcard is unavailable.
    """
    if not AUDIO_AVAILABLE:
        return []
    try:
        mics = sc.all_microphones(include_loopback=False)
        return [{"id": m.id, "name": m.name} for m in mics]
    except Exception as e:
        logger.error(f"Failed to enumerate microphones: {e}")
        return []


class AudioCapture:
    """Records audio from a soundcard device to a WAV file.

    Supports both loopback (system audio) and microphone capture.

    Usage:
        cap = AudioCapture(output_path, loopback=True)
        cap.start()   # returns False if audio unavailable
        cap.stop()
    """

    SAMPLE_RATE = 48000
    BLOCK_SIZE = 1024

    def __init__(
        self,
        output_path: str,
        loopback: bool = False,
        device_id: str | None = None,
    ):
        self._output_path = output_path
        self._loopback = loopback
        self._device_id = device_id
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._error: Exception | None = None

    @property
    def had_error(self) -> bool:
        return self._error is not None

    def start(self) -> bool:
        """Start audio capture. Returns False if audio unavailable."""
        if not AUDIO_AVAILABLE:
            return False
        self._stop_event.clear()
        self._error = None
        label = "loopback" if self._loopback else "mic"
        self._thread = threading.Thread(
            target=self._record_loop,
            name=f"Audio-{label}",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self):
        """Signal stop and wait for thread to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _record_loop(self):
        try:
            device = self._get_device()
            if device is None:
                logger.warning(
                    f"Audio device not found "
                    f"(loopback={self._loopback}); skipping"
                )
                return

            with sf.SoundFile(
                self._output_path,
                mode="w",
                samplerate=self.SAMPLE_RATE,
                channels=2,
                format="WAV",
                subtype="FLOAT",
            ) as wav:
                with device.recorder(
                    samplerate=self.SAMPLE_RATE,
                    blocksize=self.BLOCK_SIZE,
                ) as rec:
                    while not self._stop_event.is_set():
                        data = rec.record(numframes=self.BLOCK_SIZE)
                        wav.write(data)

        except Exception as e:
            self._error = e
            logger.error(f"Audio capture error: {e}")

    def _get_device(self):
        """Resolve the target audio device."""
        try:
            if self._loopback:
                return self._find_loopback_device()
            else:
                return self._find_microphone()
        except Exception as e:
            logger.error(f"Device resolution error: {e}")
            return None

    @staticmethod
    def _find_loopback_device():
        """Find the default speaker's loopback device."""
        default_speaker = sc.default_speaker()
        loopbacks = sc.all_microphones(include_loopback=True)
        # Match loopback device to default speaker
        for lb in loopbacks:
            if lb.isloopback and default_speaker.name in lb.name:
                return lb
        # Fallback: first loopback device
        for lb in loopbacks:
            if lb.isloopback:
                return lb
        return None

    def _find_microphone(self):
        """Find specified or default microphone."""
        if self._device_id:
            mics = sc.all_microphones(include_loopback=False)
            for m in mics:
                if m.id == self._device_id:
                    return m
        return sc.default_microphone()
