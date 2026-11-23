import random
import sys
import time
import pygame

# WaveShare 5" LCD doğal çözünürlüğü
WIDTH, HEIGHT = 800, 480
FPS = 60

BG_COLOR = (10, 12, 16)
EYE_COLOR = (0, 215, 255)      # Neon camgöbeği
EYE_GLOW = (0, 90, 120)        # Hafif dış parlama


def lerp(a, b, t):
    return a + (b - a) * t


class RobotFace:
    def __init__(self):
        self.state = "normal"
        self.state_until = 0.0

        # Temel göz boyutları
        self.base_w = 135.0
        self.base_h = 155.0
        self.eye_spacing = 240.0

        # Anlık (yumuşak geçişli) boyut ve bakış değerleri
        self.cur_w = self.base_w
        self.cur_h = self.base_h
        self.gaze_x = 0.0
        self.gaze_y = 0.0
        self.target_gaze_x = 0.0
        self.target_gaze_y = 0.0

        # İfade karışım ağırlıkları (0.0 -> 1.0 arası yumuşak geçiş)
        self.happy_val = 0.0
        self.angry_val = 0.0
        self.sleepy_val = 0.0

        # Göz kırpma zamanlayıcısı
        self.next_blink = time.time() + random.uniform(2.0, 4.5)
        self.blink_progress = 0.0
        self.is_blinking = False

        # Boşta etrafa bakınma ve sallanma
        self.last_mouse_move = 0.0
        self.next_wander = time.time() + 2.0
        self.shake_until = 0.0

    def set_state(self, state, duration=0.0):
        self.state = state
        self.state_until = time.time() + duration if duration > 0 else 0.0

    def trigger_shake(self):
        """MPU6050 sallanma simülasyonu"""
        self.shake_until = time.time() + 0.6
        self.set_state("angry", duration=2.2)

    def look_at(self, mx, my):
        """Gözleri fare (ileride dokunma/kamera) konumuna çevir"""
        nx = (mx - WIDTH / 2) / (WIDTH / 2)
        ny = (my - HEIGHT / 2) / (HEIGHT / 2)
        self.target_gaze_x = max(-1.0, min(1.0, nx)) * 55.0
        self.target_gaze_y = max(-1.0, min(1.0, ny)) * 35.0
        self.last_mouse_move = time.time()

    def update(self):
        now = time.time()

        # Süreli tepki bittiyse normale dön
        if self.state_until > 0 and now > self.state_until:
            self.state = "normal"
            self.state_until = 0.0

        # Fare 2.5 sn hareket etmezse kendi kendine etrafa bakın
        if now - self.last_mouse_move > 2.5 and now > self.next_wander:
            if self.state == "sleepy":
                self.target_gaze_x = 0.0
                self.target_gaze_y = 18.0
            else:
                self.target_gaze_x = random.uniform(-45.0, 45.0)
                self.target_gaze_y = random.uniform(-22.0, 22.0)
            self.next_wander = now + random.uniform(1.8, 4.0)

        # İfade hedeflerini belirle
        target_w = self.base_w
        target_h = self.base_h
        t_happy = 1.0 if self.state == "happy" else 0.0
        t_angry = 1.0 if self.state == "angry" else 0.0
        t_sleepy = 1.0 if self.state == "sleepy" else 0.0

        if self.state == "surprised":
            target_w = 160.0
            target_h = 185.0
        elif self.state == "sleepy":
            target_h = 130.0

        # Göz kırpma kontrolü
        if not self.is_blinking and now >= self.next_blink and self.state != "happy":
            self.is_blinking = True
            self.blink_progress = 0.0

        blink_scale = 1.0
        if self.is_blinking:
            self.blink_progress += 0.18
            if self.blink_progress < 1.0:
                blink_scale = max(0.06, 1.0 - self.blink_progress)
            elif self.blink_progress < 2.0:
                blink_scale = max(0.06, self.blink_progress - 1.0)
            else:
                self.is_blinking = False
                self.next_blink = now + random.uniform(2.5, 5.5)

        # Yumuşak geçişler (lerp)
        self.cur_w = lerp(self.cur_w, target_w, 0.16)
        self.cur_h = lerp(self.cur_h, target_h * blink_scale, 0.25 if self.is_blinking else 0.16)
        self.gaze_x = lerp(self.gaze_x, self.target_gaze_x, 0.12)
        self.gaze_y = lerp(self.gaze_y, self.target_gaze_y, 0.12)

        self.happy_val = lerp(self.happy_val, t_happy, 0.18)
        self.angry_val = lerp(self.angry_val, t_angry, 0.18)
        self.sleepy_val = lerp(self.sleepy_val, t_sleepy, 0.12)

    def draw_eye(self, surface, cx, cy, is_left):
        w, h = int(self.cur_w), int(self.cur_h)
        left = int(cx - w / 2)
        top = int(cy - h / 2)
        radius = min(38, max(4, min(w, h) // 2))

        # Hafif dış parlama + ana göz
        glow_rect = pygame.Rect(left - 6, top - 6, w + 12, h + 12)
        pygame.draw.rect(surface, EYE_GLOW, glow_rect, border_radius=radius + 4)

        eye_rect = pygame.Rect(left, top, w, h)
        pygame.draw.rect(surface, EYE_COLOR, eye_rect, border_radius=radius)

        # Mutlu maskesi (alttan yükselen gülümseme kavisi)
        if self.happy_val > 0.02:
            mask_w = int(w * 1.35)
            mask_h = int(h * 1.05)
            offset_y = lerp(h * 1.15, h * 0.22, self.happy_val)
            mask_rect = pygame.Rect(0, 0, mask_w, mask_h)
            mask_rect.center = (int(cx), int(cy + offset_y))
            pygame.draw.ellipse(surface, BG_COLOR, mask_rect)

        # Kızgın maskesi (üstten içe eğik göz kapakları)
        if self.angry_val > 0.02:
            inner_drop = h * 0.52 * self.angry_val
            outer_drop = h * 0.08 * self.angry_val
            if is_left:
                pts = [
                    (left - 10, top - 15),
                    (left + w + 10, top - 15),
                    (left + w + 10, top + inner_drop),
                    (left - 10, top + outer_drop),
                ]
            else:
                pts = [
                    (left - 10, top - 15),
                    (left + w + 10, top - 15),
                    (left + w + 10, top + outer_drop),
                    (left - 10, top + inner_drop),
                ]
            pygame.draw.polygon(surface, BG_COLOR, pts)

        # Uykulu maskesi (üstten düz inen göz kapakları)
        if self.sleepy_val > 0.02:
            lid_h = int(h * 0.58 * self.sleepy_val)
            lid_rect = pygame.Rect(left - 10, top - 10, w + 20, lid_h + 10)
            pygame.draw.rect(surface, BG_COLOR, lid_rect)

    def draw(self, surface):
        surface.fill(BG_COLOR)

        shake_x, shake_y = 0, 0
        if time.time() < self.shake_until:
            shake_x = random.randint(-14, 14)
            shake_y = random.randint(-10, 10)

        center_x = WIDTH / 2 + self.gaze_x + shake_x
        center_y = HEIGHT / 2 + self.gaze_y + shake_y

        self.draw_eye(surface, center_x - self.eye_spacing / 2, center_y, is_left=True)
        self.draw_eye(surface, center_x + self.eye_spacing / 2, center_y, is_left=False)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pi 5 Masa Robotu — 800x480 Prototip")
    clock = pygame.time.Clock()

    face = RobotFace()
    dragging = False
    drag_distance = 0.0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_1:
                    face.set_state("normal")
                elif event.key == pygame.K_2:
                    face.set_state("happy")
                elif event.key == pygame.K_3:
                    face.set_state("surprised")
                elif event.key == pygame.K_4:
                    face.set_state("angry")
                elif event.key == pygame.K_5:
                    face.set_state("sleepy")
                elif event.key == pygame.K_SPACE:
                    face.trigger_shake()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                drag_distance = 0.0
                face.look_at(*event.pos)

            elif event.type == pygame.MOUSEMOTION:
                face.look_at(*event.pos)
                if dragging:
                    dx, dy = event.rel
                    drag_distance += abs(dx) + abs(dy)
                    # Basılı tutup sürüklemek = kafasını okşama
                    if drag_distance > 45:
                        face.set_state("happy", duration=2.0)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                # Kısa tıklama = dürtme
                if drag_distance <= 45:
                    face.set_state("surprised", duration=1.5)
                dragging = False

        face.update()
        face.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()