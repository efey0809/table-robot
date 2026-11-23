import pygame

from brain import RobotBrain
from face import FPS, HEIGHT, WIDTH, RobotFace


KEY_STATE_MAP = {
    pygame.K_1: ("normal", None),
    pygame.K_2: ("happy", 3.0),
    pygame.K_3: ("surprised", 2.5),
    pygame.K_4: ("sleepy", None),
    pygame.K_5: ("dizzy", 3.5),
    pygame.K_6: ("listening", None),
    pygame.K_7: ("thinking", None),
    pygame.K_8: ("speaking", None),
}


def pixel_to_norm(pos: tuple[int, int]) -> tuple[float, float]:
    nx = (pos[0] / WIDTH) * 2.0 - 1.0
    ny = (pos[1] / HEIGHT) * 2.0 - 1.0
    return nx, ny


def main() -> None:
    brain = RobotBrain(sleepy_timeout=45.0)
    face = RobotFace(fullscreen=True)
    clock = pygame.time.Clock()
    running = True

    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_f:
                        face.toggle_fullscreen()
                    elif event.key in KEY_STATE_MAP:
                        state, duration = KEY_STATE_MAP[event.key]
                        brain.set_state(state, duration=duration)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    nx, ny = pixel_to_norm(event.pos)
                    brain.on_touch(nx, ny)
                elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
                    nx, ny = pixel_to_norm(event.pos)
                    brain.on_drag(nx, ny)

            snapshot = brain.update()
            face.render(snapshot)
            clock.tick(FPS)
    except KeyboardInterrupt:
        pass
    finally:
        face.close()


if __name__ == "__main__":
    main()