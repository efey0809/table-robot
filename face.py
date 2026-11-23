import math
import time
import pygame

from brain import FaceSnapshot


WIDTH, HEIGHT = 800, 480
FPS = 60

BG_COLOR = (10, 12, 16)

STATE_COLORS = {
    "normal": (0, 215, 255),
    "happy": (0, 235, 205),
    "surprised": (120, 240, 255),
    "sleepy": (0, 140, 185),
    "dizzy": (255, 175, 45),
    "listening": (40, 255, 175),
    "thinking": (145, 130, 255),
    "speaking": (0, 225, 255),
}


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class RobotFace:
    def __init__(self, fullscreen: bool = True):
        pygame.init()
        self.fullscreen = fullscreen
        self.screen = self._create_screen(fullscreen)
        pygame.display.set_caption("Table Robot")
        pygame.mouse.set_visible(not fullscreen)

        # Mevcut animasyon değerleri (lerp ile yumuşak geçiş)
        self.eye_w = 135.0
        self.eye_h = 165.0
        self.gaze_x = 0.0
        self.gaze_y = 0.0
        self.upper_lid = 0.0   # 0.0: açık, 0.5: yarı kapalı (sleepy)
        self.smile_arc = 0.0   # 0.0: düz, 1.0: mutlu yay (happy)
        self.color = list(STATE_COLORS["normal"])

    def _create_screen(self, fullscreen: bool) -> pygame.Surface:
        flags = pygame.FULLSCREEN if fullscreen else 0
        return pygame.display.set_mode((WIDTH, HEIGHT), flags)

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.screen = self._create_screen(self.fullscreen)
        pygame.mouse.set_visible(not self.fullscreen)

    def render(self, snap: FaceSnapshot) -> None:
        now = time.monotonic()

        # Duruma göre hedef geometri
        target_w = 135.0
        target_h = 165.0
        target_upper = 0.0
        target_smile = 0.0
        target_gx = snap.look_x * 55.0
        target_gy = snap.look_y * 35.0

        if snap.state == "happy":
            target_w, target_h = 150.0, 145.0
            target_smile = 1.0
        elif snap.state == "surprised":
            target_w, target_h = 155.0, 210.0
        elif snap.state == "sleepy":
            target_w, target_h = 140.0, 130.0
            target_upper = 0.55
        elif snap.state == "dizzy":
            target_w, target_h = 130.0, 130.0
            target_gx = math.cos(now * 9.0) * 28.0
            target_gy = math.sin(now * 9.0) * 18.0
        elif snap.state == "listening":
            pulse = math.sin(now * 5.0) * 8.0
            target_w, target_h = 150.0 + pulse, 185.0 + pulse
        elif snap.state == "thinking":
            target_w, target_h = 130.0, 150.0
            target_gx += math.sin(now * 3.0) * 18.0
            target_upper = 0.15
        elif snap.state == "speaking":
            level = snap.speech_level if snap.speech_level > 0.0 else (0.5 + 0.5 * math.sin(now * 14.0))
            target_w = 140.0 + level * 14.0
            target_h = 155.0 + level * 26.0

        # Göz kırpma aktifse yüksekliği hızla daralt
        if snap.blink > 0.5:
            target_h = 10.0

        # Yumuşak geçişler
        h_speed = 0.45 if snap.blink > 0.5 else 0.16
        self.eye_w = lerp(self.eye_w, target_w, 0.16)
        self.eye_h = lerp(self.eye_h, target_h, h_speed)
        self.gaze_x = lerp(self.gaze_x, target_gx, 0.14)
        self.gaze_y = lerp(self.gaze_y, target_gy, 0.14)
        self.upper_lid = lerp(self.upper_lid, target_upper, 0.12)
        self.smile_arc = lerp(self.smile_arc, target_smile, 0.18)

        target_rgb = STATE_COLORS.get(snap.state, STATE_COLORS["normal"])
        for i in range(3):
            self.color[i] = lerp(self.color[i], target_rgb[i], 0.10)

        eye_rgb = (int(self.color[0]), int(self.color[1]), int(self.color[2]))
        glow_rgb = (int(eye_rgb[0] * 0.35), int(eye_rgb[1] * 0.35), int(eye_rgb[2] * 0.35))

        # Ekranı temizle ve iki gözü çiz
        self.screen.fill(BG_COLOR)

        spacing = 240
        base_y = HEIGHT // 2 + self.gaze_y
        left_cx = (WIDTH // 2) - (spacing // 2) + self.gaze_x
        right_cx = (WIDTH // 2) + (spacing // 2) + self.gaze_x

        dizzy_offset = math.sin(now * 12.0) * 18.0 if snap.state == "dizzy" else 0.0

        self._draw_eye(left_cx, base_y - dizzy_offset, self.eye_w, self.eye_h, eye_rgb, glow_rgb)
        self._draw_eye(right_cx, base_y + dizzy_offset, self.eye_w, self.eye_h, eye_rgb, glow_rgb)

        pygame.display.flip()

    def _draw_eye(
        self,
        cx: float,
        cy: float,
        w: float,
        h: float,
        eye_rgb: tuple[int, int, int],
        glow_rgb: tuple[int, int, int],
    ) -> None:
        iw = max(8, int(w))
        ih = max(6, int(h))
        radius = max(4, int(min(iw, ih) * 0.30))

        # Dış parlama katmanı
        glow_rect = pygame.Rect(0, 0, iw + 18, ih + 18)
        glow_rect.center = (int(cx), int(cy))
        pygame.draw.rect(self.screen, glow_rgb, glow_rect, border_radius=radius + 6)

        # Ana göz gövdesi
        eye_rect = pygame.Rect(0, 0, iw, ih)
        eye_rect.center = (int(cx), int(cy))
        pygame.draw.rect(self.screen, eye_rgb, eye_rect, border_radius=radius)

        # Üst göz kapağı (sleepy / thinking)
        if self.upper_lid > 0.02 and ih > 20:
            lid_h = int(ih * self.upper_lid)
            lid_rect = pygame.Rect(glow_rect.left, glow_rect.top, glow_rect.width, lid_h + 10)
            pygame.draw.rect(self.screen, BG_COLOR, lid_rect)

        # Alt mutlu yay maskesi (happy)
        if self.smile_arc > 0.05 and ih > 30:
            cut_w = int(iw * 1.15)
            cut_h = int(ih * 0.95)
            cut_y = eye_rect.bottom - int(ih * 0.48 * self.smile_arc)
            cut_rect = pygame.Rect(0, 0, cut_w, cut_h)
            cut_rect.midtop = (int(cx), cut_y)
            pygame.draw.ellipse(self.screen, BG_COLOR, cut_rect)

    def close(self) -> None:
        pygame.quit()