import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from math import cos, pi, sin
from typing import Iterator
import pygame

from graphs import Graph
from parser import MapData

_FONT_CACHE: dict[tuple[str, int, bool], pygame.font.Font] = {}


def get_cached_font(name: str, size: int, bold: bool = True) -> pygame.font.Font:
    """Retrieves a cached Pygame Font instance or creates a new one."""
    key = (name, size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = pygame.font.SysFont(name, size, bold=bold)
    return _FONT_CACHE[key]


def draw_text_in_circle(
    screen: pygame.Surface,
    text: str,
    center: tuple[int, int],
    max_diameter: int,
    text_color: tuple[int, int, int] | str,
) -> None:
    if max_diameter <= 5:
        return

    font_size = max(6, int(max_diameter * 0.5))
    while font_size > 6:
        font = get_cached_font("Arial", font_size, bold=True)
        tw, th = font.size(text)
        if tw <= max_diameter - 4 and th <= max_diameter - 4:
            break
        font_size -= 1

    font = get_cached_font("Arial", font_size, bold=True)
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=center)
    screen.blit(text_surf, text_rect)


def to_screen_coords(
    x_graph: float,
    y_graph: float,
    window_height: int,
    scale: float = 20.0,
    offset_x: float = 50.0,
    offset_y: float = 50.0,
) -> tuple[int, int]:
    screen_x = int(x_graph * scale + offset_x)
    screen_y = int(window_height - (y_graph * scale + offset_y))
    return screen_x, screen_y


def hub_coords_on_screen(
    graph: Graph, zoom_modifier: float, camera_x: float, camera_y: float
) -> dict[str, tuple[int, int]]:
    hubs = graph.zones

    raw_xs = [hub.hub_cords[0] for hub in hubs.values()]
    raw_ys = [hub.hub_cords[1] for hub in hubs.values()]

    raw_min_x, raw_max_x = min(raw_xs), max(raw_xs)
    raw_min_y, raw_max_y = min(raw_ys), max(raw_ys)

    center_x = (raw_min_x + raw_max_x) / 2.0
    center_y = (raw_min_y + raw_max_y) / 2.0

    spacing_factor = 2.0

    scaled_coords: dict[str, tuple[float, float]] = {
        hub_name: (
            center_x + (hub.hub_cords[0] - center_x) * spacing_factor,
            center_y + (hub.hub_cords[1] - center_y) * spacing_factor,
        )
        for hub_name, hub in hubs.items()
    }

    xs = [coord[0] for coord in scaled_coords.values()]
    ys = [coord[1] for coord in scaled_coords.values()]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    graph_width = max_x - min_x if max_x != min_x else 1.0
    graph_height = max_y - min_y if max_y != min_y else 1.0

    padding = 50.0
    usable_width = 1280.0 - (2 * padding)
    usable_height = 720.0 - (2 * padding)

    scale_x = usable_width / graph_width
    scale_y = usable_height / graph_height
    scale = min(scale_x, scale_y) * zoom_modifier

    offset_x = (1280.0 / 2.0) - ((min_x + graph_width / 2.0) * scale) + camera_x
    offset_y = (720.0 / 2.0) - ((min_y + graph_height / 2.0) * scale) - camera_y

    return {
        hub_name: to_screen_coords(
            hx, hy, window_height=720, scale=scale, offset_x=offset_x, offset_y=offset_y
        )
        for hub_name, (hx, hy) in scaled_coords.items()
    }


def draw_hubs(
    graph: Graph,
    screen: pygame.Surface,
    coords_on_screen: dict[str, tuple[int, int]],
    zoom_modifier: float,
) -> None:
    for from_name, to_name in graph.connections.keys():
        if from_name in coords_on_screen and to_name in coords_on_screen:
            pygame.draw.line(
                screen,
                (120, 120, 120),
                coords_on_screen[from_name],
                coords_on_screen[to_name],
                3,
            )

    radius = max(5, int(12 * zoom_modifier))
    
    for hub_name, hub in graph.zones.items():
        if hub_name not in coords_on_screen:
            continue
            
        x, y = coords_on_screen[hub_name]
        color = hub.hub_meta_data.get("color", "white")
        if color == "rainbow":
            color = "royal blue"

        pygame.draw.circle(screen, (0, 0, 0), (x, y), radius + 2, 0)
        pygame.draw.circle(screen, color, (x, y), radius, 0)

        text_color: tuple[int, int, int] = (
            (255, 255, 255)
            if color in ["blue", "red", "black", "purple", "brown"]
            else (0, 0, 0)
        )
        draw_text_in_circle(screen, hub_name, (x, y), radius * 2, text_color)


def init_drones(nb_drones: int, start: str) -> dict[str, tuple[str, str, str]]:
    return {f"D{i}": (start, start, "stay") for i in range(1, nb_drones + 1)}


def render_drones(
    screen: pygame.Surface,
    size: int,
    center: tuple[float, float] | tuple[int, int],
    drone_id: str,
    color: tuple[int, int, int] = (100, 100, 100),
) -> None:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (0, 0, size, size))
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, size, size), 1)

    rotated_surf = pygame.transform.rotate(surf, 45)
    rect = rotated_surf.get_rect(center=(int(center[0]), int(center[1])))
    screen.blit(rotated_surf, rect)

    font = get_cached_font("Arial", 10, bold=True)
    text_surf = font.render(drone_id, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)


def draw_a_bach(
    screen: pygame.Surface,
    draw_in_hub: dict[tuple[int, int], list[str]],
    zoom_modifier: float,
) -> None:
    radius = max(5, int(12 * zoom_modifier))

    for cord, set_id in draw_in_hub.items():
        count = len(set_id)
        if count == 1:
            render_drones(screen, radius, cord, set_id[0])
        else:
            angle_step = 2 * pi / count
            for i, drone_id in enumerate(set_id):
                angle = angle_step * i
                drone_x = cord[0] + radius * cos(angle)
                drone_y = cord[1] + radius * sin(angle)
                render_drones(screen, radius, (drone_x, drone_y), drone_id)


def draw_sim(
    screen: pygame.Surface,
    hub_coords_on_screen: dict[str, tuple[int, int]],
    drones_pos: dict[str, tuple[str, str, str]],
    zoom_modifier: float,
    graph: Graph,
) -> None:
    draw_hubs(graph, screen, hub_coords_on_screen, zoom_modifier)

    draw_in_hub: dict[tuple[int, int], list[str]] = {}

    for drone_id, action in drones_pos.items():
        from_zone, to_zone, path = action
        if path == "half":
            x, y = hub_coords_on_screen[from_zone]
            target_x, target_y = hub_coords_on_screen[to_zone]
            cords = ((x + target_x) // 2, (y + target_y) // 2)
        else:
            cords = hub_coords_on_screen[to_zone]

        draw_in_hub.setdefault(cords, []).append(drone_id)

    draw_a_bach(screen, draw_in_hub, zoom_modifier)


def update_drones_cords(
    step: list[str],
    drones_pos: dict[str, tuple[str, str, str]],
    move_counter: int,
) -> None:
    RESET, GREEN, YELLOW = "\033[0m", "\033[32m", "\033[33m"

    doing: dict[str, tuple[str, str, str]] = {}
    print(f"===============\n{GREEN}Move:{move_counter}{RESET}")

    for log in step:
        print(f"{YELLOW}{log}{RESET}")
        log_split = log.split("-")
        drone_id = log_split[0]

        if len(log_split) == 3:
            prev_zone = drones_pos[drone_id][1]
            path_type = "half" if prev_zone != log_split[2] else "full"
            doing[drone_id] = (prev_zone, log_split[2], path_type)
        else:
            doing[drone_id] = (log_split[1], log_split[1], "full")

    drones_pos.update(doing)


def vizualizer(
    graph: Graph,
    solution_logs: list[list[str]],
    nb_drones: int,
    map_data: MapData,
) -> None:
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Drone Simulation Visualizer")
    clock = pygame.time.Clock()
    running = True

    zoom_modifier = 1.0
    camera_x = 0.0
    camera_y = 0.0
    is_dragging = False
    sim_activated = False
    freez = False

    drones_pos = init_drones(nb_drones, map_data.start_hub_name)
    logs: Iterator[list[str]] | None = None

    STEP_EVENT = pygame.USEREVENT + 1
    current_move: list[str] | None = []
    moves = 0

    pygame.time.set_timer(STEP_EVENT, 1000)
    
    font_ui = get_cached_font("Arial", 15, bold=True)
    controls_surface = font_ui.render(
        "Controls: [S] Start/Pause | [Scroll] Zoom | "
        "[LMB + Drag] Camera | [F] Freeze/Unfreeze | [Esc] Quit",
        True,
        (200, 200, 200),
    )

    panel_height = 60
    panel_rect = pygame.Rect(0, 720 - panel_height, 1280, panel_height)

    coords_on_screen = hub_coords_on_screen(graph, zoom_modifier, camera_x, camera_y)
    
    needs_recalc_coords = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif (
                event.type == STEP_EVENT
                and sim_activated
                and not freez
                and logs is not None
            ):
                current_move = next(logs, None)
                if current_move is not None:
                    moves += 1
                    update_drones_cords(current_move, drones_pos, moves)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    sim_activated = not sim_activated
                    moves = 0
                    if sim_activated:
                        logs = iter(solution_logs)
                        drones_pos = init_drones(nb_drones, map_data.start_hub_name)
                        current_move = []
                        pygame.time.set_timer(STEP_EVENT, 1000)
                elif event.key == pygame.K_f:
                    freez = not freez
                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    zoom_modifier += 0.1
                    needs_recalc_coords = True
                elif event.button == 5:
                    zoom_modifier = max(0.1, zoom_modifier - 0.1)
                    needs_recalc_coords = True
                elif event.button == 1:
                    is_dragging = True

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    is_dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if is_dragging:
                    camera_x += event.rel[0]
                    camera_y += event.rel[1]
                    needs_recalc_coords = True

        if needs_recalc_coords:
            coords_on_screen = hub_coords_on_screen(
                graph, zoom_modifier, camera_x, camera_y
            )
            needs_recalc_coords = False

        screen.fill((114, 206, 255))

        if sim_activated and current_move is not None:
            draw_sim(screen, coords_on_screen, drones_pos, zoom_modifier, graph)
        elif current_move is None or freez:
            draw_sim(screen, coords_on_screen, drones_pos, zoom_modifier, graph)
        else:
            draw_hubs(graph, screen, coords_on_screen, zoom_modifier)

        text_surface = font_ui.render(f"Moves: {moves}", True, (255, 255, 255))
        screen.blit(text_surface, (10, 10))

        pygame.draw.rect(screen, (30, 30, 35), panel_rect)
        pygame.draw.line(screen, (0, 200, 255), (0, 720 - panel_height), (1280, 720 - panel_height), 2)
        screen.blit(controls_surface, (20, 720 - panel_height + 25))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()