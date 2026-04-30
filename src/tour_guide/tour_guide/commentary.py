"""Text-to-speech commentary for the tour guide.

Tries a series of TTS backends in order of preference and degrades gracefully
to a silent (log-only) speaker if none are available, so the tour will still
run on machines without TTS installed.
"""

import logging
import shutil
import subprocess
from typing import Callable, Optional


_LOG = logging.getLogger(__name__)


def _make_subprocess_speaker(cmd: str) -> Callable[[str], None]:
    def speak(text: str) -> None:
        try:
            subprocess.run([cmd, text], check=False, timeout=30)
        except (OSError, subprocess.SubprocessError) as e:
            _LOG.warning("TTS backend %s failed: %s", cmd, e)
    return speak


def _make_pyttsx3_speaker():
    try:
        import pyttsx3  # type: ignore
    except ImportError:
        return None
    engine = pyttsx3.init()

    def speak(text: str) -> None:
        engine.say(text)
        engine.runAndWait()
    return speak


def _silent_speaker(log_fn: Optional[Callable[[str], None]]) -> Callable[[str], None]:
    def speak(text: str) -> None:
        if log_fn is not None:
            log_fn(f"[silent TTS] {text}")
    return speak


def make_speaker(log_fn: Optional[Callable[[str], None]] = None) -> Callable[[str], None]:
    """Pick the best available TTS backend.

    Preference: espeak-ng > espeak > macOS `say` > pyttsx3 > silent.
    """
    for cmd in ("espeak-ng", "espeak", "say"):
        if shutil.which(cmd):
            return _make_subprocess_speaker(cmd)

    pyttsx = _make_pyttsx3_speaker()
    if pyttsx is not None:
        return pyttsx

    return _silent_speaker(log_fn)
