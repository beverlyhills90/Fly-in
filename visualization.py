import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
from parser import MapData
from graphs import Graph
from math import sqrt, pi, cos, sin, degrees


def draw_text_in_circle(
    screen: pygame.Surface,
    text: str,
    center: tuple[int, int],
    max_diameter: int,
    text_color: tuple[int, int, int] | str,
) -> None:
    """Renders text inside a circular area, automatically shrinking font size to fit.

    Args:
        screen: Pygame surface to render onto.
        text: Label string to display.
        center: Coordinates (x, y) for the center of the circle.
        max_diameter: Maximum allowable diameter for text fitting.
        text_color: RGB tuple or Pygame color name for the text.
    """
    if max_diameter <= 5:
        return

    font_size = int(max_diameter * 0.5)
    while font_size > 6:
        font = pygame.font.SysFont("Arial", font_size, bold=True)
        text_surf = font.render(text, True, text_color)

        if (
            text_surf.get_width() <= max_diameter - 4
            and text_surf.get_height() <= max_diameter - 4
        ):
            break
        font_size -= 1

    font = pygame.font.SysFont("Arial", font_size, bold=True)
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
    """Converts 2D graph space coordinates into Pygame screen pixel coordinates.

    Args:
        x_graph: X coordinate in graph space.
        y_graph: Y coordinate in graph space.
        window_height: Height of the viewport/window in pixels.
        scale: Scaling multiplier.
        offset_x: Horizontal pixel shift.
        offset_y: Vertical pixel shift.

    Returns:
        A tuple (x, y) representing pixel positions on screen.
    """
    screen_x = int(x_graph * scale + offset_x)
    screen_y = int(window_height - (y_graph * scale + offset_y))
    return screen_x, screen_y


def hub_coords_on_screen(
    graph: Graph, zoom_modifier: float, camera_x: float, camera_y: float
) -> dict[str, tuple[int, int]]:
    """Calculates pixel coordinates for all graph hubs based on camera offset and zoom.

    Args:
        graph: Network topology graph.
        zoom_modifier: Zoom scale factor.
        camera_x: Horizontal camera displacement.
        camera_y: Vertical camera displacement.

    Returns:
        Mapping from hub names to their corresponding (x, y) screen coordinates.
    """
    hubs = graph.zones

    raw_xs = [hub.hub_cords[0] for hub in hubs.values()]
    raw_ys = [hub.hub_cords[1] for hub in hubs.values()]

    raw_min_x, raw_max_x = min(raw_xs), max(raw_xs)
    raw_min_y, raw_max_y = min(raw_ys), max(raw_ys)

    center_x = (raw_min_x + raw_max_x) / 2
    center_y = (raw_min_y + raw_max_y) / 2

    spacing_factor = 2.0

    scaled_coords: dict[str, tuple[float, float]] = {}
    for hub_name, hub in hubs.items():
        hx, hy = hub.hub_cords
        new_x = center_x + (hx - center_x) * spacing_factor
        new_y = center_y + (hy - center_y) * spacing_factor
        scaled_coords[hub_name] = (new_x, new_y)

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

    coords_on_screen: dict[str, tuple[int, int]] = {}
    for hub_name, (hx, hy) in scaled_coords.items():
        x, y = to_screen_coords(
            hx, hy, window_height=720, scale=scale, offset_x=offset_x, offset_y=offset_y
        )
        coords_on_screen[hub_name] = (x, y)

    return coords_on_screen


def draw_hubs(
    graph: Graph,
    screen: pygame.Surface,
    coords_on_screen: dict[str, tuple[int, int]],
    zoom_modifier: float,
) -> None:
    """Renders connection lines and hub circles on screen.

    Args:
        graph: Network topology containing connections and hubs.
        screen: Pygame surface to render onto.
        coords_on_screen: Calculated hub screen locations.
        zoom_modifier: Zoom multiplier affecting node sizes.
    """
    hubs = graph.zones
    for from_name, to_name in graph.connections.keys():
        if from_name in coords_on_screen and to_name in coords_on_screen:
            start_pos = coords_on_screen[from_name]
            end_pos = coords_on_screen[to_name]
            pygame.draw.line(screen, (120, 120, 120), start_pos, end_pos, 3)

    for hub_name, hub in hubs.items():
        x, y = coords_on_screen[hub_name]
        color = hub.hub_meta_data.get("color", "white")
        if color == "rainbow":
            color = "royal blue"

        radius = max(5, int(12 * zoom_modifier))
        pygame.draw.circle(screen, (0, 0, 0), (x, y), radius + 2, 0)
        pygame.draw.circle(screen, color, (x, y), radius, 0)

        text_color: tuple[int, int, int] = (
            (255, 255, 255) if color in ["blue", "red", "black"] else (0, 0, 0)
        )
        draw_text_in_circle(screen, hub_name, (x, y), radius * 2, text_color)


def init_drones(nb_drones: int, start: str) -> dict[str, tuple[str, str, str]]:
    """Initializes drone positioning dictionary.

    Args:
        nb_drones: Number of drones to spawn.
        start: Starting hub identifier.

    Returns:
        Mapping from drone ID to state tuple (from_zone, to_zone, path_type).
    """
    init: dict[str, tuple[str, str, str]] = {}
    for i in range(1, nb_drones + 1):
        init[f"D{i}"] = (start, start, "stay")
    return init


def render_drones(
    screen: pygame.Surface,
    size: int,
    center: tuple[float, float] | tuple[int, int],
    drone_id: str,
    color: tuple[int, int, int] = (100, 100, 100),
) -> None:
    """Draws a diamond-shaped icon representing a single drone.

    Args:
        screen: Pygame surface to render onto.
        size: Width and height of the bounding square before rotation.
        center: Coordinates (x, y) where the drone should be rendered.
        drone_id: Label text for the drone ID.
        color: Base color for the drone body.
    """
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (0, 0, size, size))
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, size, size), 1)

    rotated_surf = pygame.transform.rotate(surf, 45)
    rect = rotated_surf.get_rect(center=(int(center[0]), int(center[1])))
    screen.blit(rotated_surf, rect)

    font = pygame.font.SysFont("Arial", 10, bold=True)
    text_surf = font.render(drone_id, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)


def draw_a_bach(
    screen: pygame.Surface,
    draw_in_hub: dict[tuple[int, int], list[str]],
    zoom_modifier: float,
) -> None:
    """Renders groups of drones clustered at hub coordinates.

    Args:
        screen: Pygame surface to render onto.
        draw_in_hub: Map from coordinate tuples to lists of drone IDs present there.
        zoom_modifier: Zoom level controlling rendering offsets.
    """
    radius = max(5, int(12 * zoom_modifier))

    for cord, set_id in draw_in_hub.items():
        if len(set_id) == 1:
            render_drones(screen, radius, cord, set_id[0])
        else:
            for i, drone_id in enumerate(set_id):
                angle = (2 * pi / len(set_id)) * i
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
    """Calculates active drone positions and renders full simulation frame.

    Args:
        screen: Pygame surface to render onto.
        hub_coords_on_screen: Map of hub names to screen positions.
        drones_pos: Current movement states of active drones.
        zoom_modifier: Scaling factor.
        graph: Map graph topology.
    """
    draw_hubs(graph, screen, hub_coords_on_screen, zoom_modifier)

    draw_in_hub: dict[tuple[int, int], list[str]] = {}
    drone_state: dict[str, tuple[int, int]] = {}

    for drone_id, action in drones_pos.items():
        from_zone, to_zone, path = action
        if path == "half":
            x, y = hub_coords_on_screen[from_zone]
            target_x, target_y = hub_coords_on_screen[to_zone]
            mid_x = int((x + target_x) / 2)
            mid_y = int((y + target_y) / 2)
            drone_state[drone_id] = (mid_x, mid_y)
        else:
            drone_state[drone_id] = hub_coords_on_screen[to_zone]

    for drone_id, cords in drone_state.items():
        if cords in draw_in_hub:
            draw_in_hub[cords].append(drone_id)
        else:
            draw_in_hub[cords] = [drone_id]

    draw_a_bach(screen, draw_in_hub, zoom_modifier)


def update_drones_cords(
    step: list[str],
    drones_pos: dict[str, tuple[str, str, str]],
    move_counter: int,
) -> None:
    """Updates internal drone position states based on execution logs.

    Args:
        step: Log lines representing actions for the current step.
        drones_pos: Reference dictionary storing drone states.
        move_counter: Step iteration index for console reporting.
    """
    RESET = "\033[0m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"

    doing: dict[str, tuple[str, str, str]] = {}
    print("=" * 15)
    print(f"{GREEN}Move:{move_counter}{RESET}")

    for log in step:
        print(f"{YELLOW}{log}{RESET}")
        log_split = log.split("-")
        drone_id = log_split[0]

        if len(log_split) == 3:
            prev_zone = drones_pos[drone_id][1]
            if drones_pos[drone_id][1] != log_split[2]:
                doing[drone_id] = (prev_zone, log_split[2], "half")
            else:
                doing[drone_id] = (prev_zone, log_split[2], "full")
        else:
            doing[drone_id] = (log_split[1], log_split[1], "full")

    for drone_id, action in doing.items():
        drones_pos[drone_id] = action


def vizualizer(
    graph: Graph,
    solution_logs: list[list[str]],
    nb_drones: int,
    map_data: MapData,
) -> None:
    """Launches the Pygame interactive GUI visualizer.

    Args:
        graph: World network graph.
        solution_logs: Complete step-by-step resolution simulation output.
        nb_drones: Total number of active drones.
        map_data: Map parameters including starting point.
    """
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True

    zoom_modifier = 1.0
    camera_x = 0.0
    camera_y = 0.0
    is_dragging = False
    sim_activated = False
    freez = False

    drones_pos: dict[str, tuple[str, str, str]] = init_drones(
        nb_drones, map_data.start_hub_name
    )
    logs: Iterator[list[str]] | None = None

    STEP_EVENT = pygame.USEREVENT + 1
    current_move: list[str] | None = []
    moves = 0

    pygame.time.set_timer(STEP_EVENT, 1000)
    font = pygame.font.SysFont("Arial", 15, bold=True)

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
                elif event.button == 5:
                    zoom_modifier = max(0.1, zoom_modifier - 0.1)
                elif event.button == 1:
                    is_dragging = True

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    is_dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if is_dragging:
                    camera_x += event.rel[0]
                    camera_y += event.rel[1]

        screen.fill((114, 206, 255))
        text_surface = font.render(f"Moves: {moves}", True, (255, 255, 255))
        screen.blit(text_surface, (10, 10))

        coords_on_screen = hub_coords_on_screen(
            graph, zoom_modifier, camera_x, camera_y
        )

        if sim_activated and current_move is not None:
            draw_sim(
                screen,
                coords_on_screen,
                drones_pos,
                zoom_modifier,
                graph,
            )
        elif current_move is None or freez:
            draw_sim(screen, coords_on_screen, drones_pos, zoom_modifier, graph)
        else:
            draw_hubs(graph, screen, coords_on_screen, zoom_modifier)

        panel_height = 60
        panel_rect = pygame.Rect(0, 720 - panel_height, 1280, panel_height)
        pygame.draw.rect(screen, (30, 30, 35), panel_rect)
        pygame.draw.line(
            screen,
            (0, 200, 255),
            (0, 720 - panel_height),
            (1280, 720 - panel_height),
            2,
        )
        controls_surface = font.render(
            "Controls: [S] Start/Pause | [Scroll] Zoom | "
            "[LMB + Drag] Camera | [F] Freeze/Unfreeze | [Esc] Quit",
            True,
            (200, 200, 200),
        )
        screen.blit(controls_surface, (20, 720 - panel_height + 25))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
