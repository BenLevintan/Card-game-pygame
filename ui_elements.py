import pygame
import math
import config

pygame.font.init()
FONT_14 = pygame.font.SysFont(None, 24, bold=True)
FONT_12 = pygame.font.SysFont(None, 20)
FONT_16 = pygame.font.SysFont(None, 28)
FONT_20 = pygame.font.SysFont(None, 34, bold=True)

class TextButton:
    def __init__(self, cx, cy, width, height, text, color=config.COLOR_BTN_DEFAULT, text_color=config.COLOR_WHITE):
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (cx, cy)
        self.text = text 
        self.base_color = color
        self.highlight_color = config.COLOR_BTN_HOVER
        self.text_color = text_color
        self.is_hovered = False
        self.visible = True
        self.active = True

    def draw(self, surface):
        if not self.visible: return

        if not self.active:
            draw_color = (100, 100, 100) 
        elif self.is_hovered:
            draw_color = self.highlight_color
        else:
            draw_color = self.base_color

        pygame.draw.rect(surface, draw_color, self.rect)
        pygame.draw.rect(surface, config.COLOR_WHITE, self.rect, 2)

        # Pygame Multiline centering
        lines = self.text.split('\n')
        line_height = FONT_14.get_linesize()
        start_y = self.rect.centery - (len(lines) * line_height) / 2
        
        for i, line in enumerate(lines):
            text_surf = FONT_14.render(line, True, self.text_color)
            text_rect = text_surf.get_rect(center=(self.rect.centerx, start_y + (i * line_height) + line_height/2))
            surface.blit(text_surf, text_rect)

    def check_mouse_hover(self, x, y):
        if not self.visible: return
        self.is_hovered = self.rect.collidepoint(x, y)

    def is_clicked(self, x, y):
        return self.visible and self.active and self.is_hovered

def draw_shadows(surface, sprite_list):
    """ Simplified Pygame drop shadow """
    for sprite in sprite_list:
        shadow_rect = sprite.rect.copy()
        shadow_rect.x += 5
        shadow_rect.y += 5 # Shadow goes down in Pygame
        
        # Create shadow surface
        shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        shadow_surf.fill(config.COLOR_SHADOW)
        
        if hasattr(sprite, 'angle') and sprite.angle != 0:
            shadow_surf = pygame.transform.rotate(shadow_surf, sprite.angle)
            shadow_rect = shadow_surf.get_rect(center=shadow_rect.center)
            
        surface.blit(shadow_surf, shadow_rect)

def draw_tooltip(surface, hovered_joker, mouse_x, mouse_y):
    if not hovered_joker:
        return

    width, height = 240, 80
    tip_x = mouse_x + 20
    tip_y = mouse_y - 20

    if tip_x + width > config.SCREEN_WIDTH:
        tip_x = mouse_x - width - 20
    
    bg_rect = pygame.Rect(tip_x, tip_y - height, width, height)
    pygame.draw.rect(surface, config.COLOR_TOOLTIP_BG, bg_rect)
    pygame.draw.rect(surface, config.COLOR_WHITE, bg_rect, 1)
    
    name_surf = FONT_14.render(hovered_joker.name, True, config.COLOR_GOLD)
    surface.blit(name_surf, (tip_x + 10, tip_y - height + 10))
    
    desc_surf = FONT_12.render(hovered_joker.desc, True, config.COLOR_WHITE)
    surface.blit(desc_surf, (tip_x + 10, tip_y - height + 40))