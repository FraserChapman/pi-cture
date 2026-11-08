import pygame

# Rows are drawn and hit-tested from the same layout, so they can't drift apart
MENU_ITEMS = ("duration", "order", "folder", "transition", "close", "shutdown")
MENU_TOP = 20
ROW_HEIGHT = 70
TEXT_PADDING = 20

def menu_item_at(y):
    row = (y - MENU_TOP) // ROW_HEIGHT
    if y >= MENU_TOP and row < len(MENU_ITEMS):
        return MENU_ITEMS[row]
    return None

def draw_menu(screen, font, width, height, app_state):
    menu_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    menu_surface.fill((0, 0, 0, 220))

    order_str = "Random" if app_state.random_order else "Sequential"
    labels = {
        "duration": (f"Duration: {app_state.display_duration} seconds", (255, 255, 255)),
        "order": (f"Order: {order_str}", (255, 255, 255)),
        "folder": (f"Folder: {app_state.current_folder}", (255, 255, 255)),
        "transition": (f"Transition: {app_state.transition_type.title()}", (255, 255, 255)),
        "close": ("Close Menu", (100, 255, 100)),
        "shutdown": ("Shutdown Pi", (255, 100, 100)),
    }

    for row, item in enumerate(MENU_ITEMS):
        text, colour = labels[item]
        y = MENU_TOP + row * ROW_HEIGHT + TEXT_PADDING
        menu_surface.blit(font.render(text, True, colour), (50, y))

    rotated_menu = pygame.transform.rotate(menu_surface, 180)
    screen.blit(rotated_menu, (0, 0))
    pygame.display.flip()
