import pygame

def draw_menu(screen, font, width, height, app_state):
    menu_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    menu_surface.fill((0, 0, 0, 220))
    
    dur_text = font.render(f"Duration: {app_state.display_duration} seconds", True, (255, 255, 255))
    menu_surface.blit(dur_text, (50, 40))
    
    order_str = "Random" if app_state.random_order else "Sequential"
    ord_text = font.render(f"Order: {order_str}", True, (255, 255, 255))
    menu_surface.blit(ord_text, (50, 110))

    dir_text = font.render(f"Folder: {app_state.current_folder}", True, (255, 255, 255))
    menu_surface.blit(dir_text, (50, 180))

    trans_text = font.render(f"Transition: {app_state.transition_type.title()}", True, (255, 255, 255))
    menu_surface.blit(trans_text, (50, 250))

    close_text = font.render("Close Menu", True, (100, 255, 100))
    menu_surface.blit(close_text, (50, 320))

    shut_text = font.render("Shutdown Pi", True, (255, 100, 100))
    menu_surface.blit(shut_text, (50, 390))

    rotated_menu = pygame.transform.rotate(menu_surface, 180)
    screen.blit(rotated_menu, (0, 0))
    pygame.display.flip()
