from dataclasses import dataclass
import random
import threading
import time


VALID_STATES = {
    "normal",
    "happy",
    "surprised",
    "sleepy",
    "dizzy",
    "listening",
    "thinking",
    "speaking",
}


@dataclass(frozen=True)
class FaceSnapshot:
    """face.py tarafının sadece okuyacağı anlık durum paketi."""

    state: str
    look_x: float
    look_y: float
    blink: float
    speech_level: float


class RobotBrain:
    def __init__(self, sleepy_timeout: float = 45.0):
        self._lock = threading.Lock()
        now = time.monotonic()

        self._state = "normal"
        self._state_until = 0.0
        self._sleepy_timeout = sleepy_timeout
        self._last_interaction = now

        # Bakış yönü (-1.0 .. 1.0)
        self._look_x = 0.0
        self._look_y = 0.0
        self._next_saccade = now + random.uniform(2.0, 4.5)

        # Göz kırpma zamanlayıcısı
        self._next_blink = now + random.uniform(2.5, 5.5)
        self._blink_until = 0.0

        # İleride TTS ses şiddetini bağlamak için (0.0 .. 1.0)
        self._speech_level = 0.0

    def set_state(self, state: str, duration: float | None = None) -> None:
        """Dış modüllerden (dokunmatik, MPU6050, AI thread'i) güvenle çağrılır."""
        if state not in VALID_STATES:
            return

        now = time.monotonic()
        with self._lock:
            self._state = state
            self._state_until = (now + duration) if duration else 0.0
            self._last_interaction = now

            if state == "thinking":
                self._look_x, self._look_y = 0.45, -0.35
            elif state in ("listening", "speaking", "surprised"):
                self._look_x, self._look_y = 0.0, 0.0

    def set_speech_level(self, level: float) -> None:
        """Ses çıkışı sırasında göz nabzını kontrol etmek için."""
        clamped = max(0.0, min(1.0, level))
        with self._lock:
            self._speech_level = clamped

    def on_touch(self, norm_x: float, norm_y: float) -> None:
        """5 inç ekrana dokunulduğunda çağrılır."""
        now = time.monotonic()
        with self._lock:
            self._last_interaction = now
            self._look_x = max(-1.0, min(1.0, norm_x))
            self._look_y = max(-1.0, min(1.0, norm_y))

            # Aktif AI konuşması yoksa dokunmaya mutlu tepki ver
            if self._state in ("normal", "sleepy", "happy"):
                self._state = "happy"
                self._state_until = now + 2.5

    def on_drag(self, norm_x: float, norm_y: float) -> None:
        """Parmağı ekranda sürüklerken gözler parmağı takip eder."""
        now = time.monotonic()
        with self._lock:
            self._last_interaction = now
            self._look_x = max(-1.0, min(1.0, norm_x))
            self._look_y = max(-1.0, min(1.0, norm_y))

            if self._state == "sleepy":
                self._state = "normal"
                self._state_until = 0.0

    def on_shake(self) -> None:
        """İleride MPU6050 sarsıntı algıladığında tetiklenecek kanca."""
        self.set_state("dizzy", duration=3.5)

    def update(self) -> FaceSnapshot:
        """Her karede çağrılır; zamanlayıcıları günceller ve anlık kopya döner."""
        now = time.monotonic()

        with self._lock:
            # Süreli duygu bittiyse normale dön
            if self._state_until > 0.0 and now >= self._state_until:
                self._state = "normal"
                self._state_until = 0.0

            # Uzun süre etkileşim yoksa uykulu moda geç
            if self._state == "normal" and (now - self._last_interaction) > self._sleepy_timeout:
                self._state = "sleepy"
                self._look_x, self._look_y = 0.0, 0.25

            # Normal modda rastgele etrafa bakın (canlılık hissi)
            if self._state == "normal" and now >= self._next_saccade:
                if random.random() < 0.45:
                    self._look_x, self._look_y = 0.0, 0.0
                else:
                    self._look_x = random.uniform(-0.65, 0.65)
                    self._look_y = random.uniform(-0.35, 0.35)
                self._next_saccade = now + random.uniform(2.0, 5.0)

            # Göz kırpma kontrolü
            blink = 0.0
            if self._state not in ("happy", "dizzy"):
                if now >= self._next_blink:
                    self._blink_until = now + 0.14
                    interval = (4.5, 8.0) if self._state == "sleepy" else (2.5, 6.0)
                    self._next_blink = now + random.uniform(*interval)
                if now < self._blink_until:
                    blink = 1.0

            return FaceSnapshot(
                state=self._state,
                look_x=self._look_x,
                look_y=self._look_y,
                blink=blink,
                speech_level=self._speech_level,
            )