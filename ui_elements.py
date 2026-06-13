import pygame
import config
import sys
import random

try:
    import moderngl
except ImportError:
    moderngl = None

FONT_14 = None
FONT_12 = None
FONT_16 = None
FONT_20 = None

def init_fonts():
    global FONT_14, FONT_12, FONT_16, FONT_20
    if FONT_14 is None:
        pygame.font.init()
        # For a true 16-bit pixel look, you would load a .ttf like "m6x11.ttf" here.
        # Using built-in bold as fallback for chunky retro aesthetic
        FONT_14 = pygame.font.SysFont(None, 24, bold=True)
        FONT_12 = pygame.font.SysFont(None, 20, bold=True)
        FONT_16 = pygame.font.SysFont(None, 28, bold=True)
        FONT_20 = pygame.font.SysFont(None, 34, bold=True)

_shadow_cache = {}

class TextButton:
    def __init__(self, cx, cy, width, height, text, text_color=config.COLOR_WHITE):
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (cx, cy)
        self.text = text 
        self.base_color = config.COLOR_BTN_DEFAULT
        self.highlight_color = config.COLOR_BTN_HOVER
        self.text_color = text_color
        self.is_hovered = False
        self.visible = True
        self.active = True
        self.is_winning_play = False
        self.sparks = []
        
        # Animation properties
        self.current_y_offset = 0.0
        self.velocity_y = 0.0
        self.last_time = pygame.time.get_ticks()

    def draw(self, surface):
        current_time = pygame.time.get_ticks()
        if not self.visible: 
            self.last_time = current_time
            return

        # Calculate delta time for animation
        dt = (current_time - self.last_time) / 1000.0
        self.last_time = current_time
        dt = min(dt, 0.05)  # Cap delta time to prevent physics explosions on lag spikes

        # Target offset: -6 when hovered/active, 0 otherwise
        target_y_offset = -6.0 if (self.is_hovered and self.active) else 0.0
        
        # Spring physics for overshoot and bounce
        stiffness = 250.0
        damping = 15.0
        
        acceleration = stiffness * (target_y_offset - self.current_y_offset) - damping * self.velocity_y
        self.velocity_y += acceleration * dt
        self.current_y_offset += self.velocity_y * dt

        # -- Sparks update and draw (drawn behind the button) --
        if self.is_winning_play and self.active:
            for _ in range(3):
                sx = self.rect.centerx + random.uniform(-self.rect.width/2.5, self.rect.width/2.5)
                sy = self.rect.centery + random.uniform(-self.rect.height/2.5, self.rect.height/2.5)
                vx = random.uniform(-150, 150)
                vy = random.uniform(-250, -50)
                lifetime = random.uniform(0.2, 0.6)
                self.sparks.append([sx, sy, vx, vy, lifetime, lifetime])

        new_sparks = []
        for spark in self.sparks:
            sx, sy, vx, vy, lt, max_lt = spark
            sx += vx * dt
            sy += vy * dt
            vy += 600 * dt # gravity
            lt -= dt
            if lt > 0:
                new_sparks.append([sx, sy, vx, vy, lt, max_lt])
                spark_color = (255, random.randint(150, 255), 0)
                pygame.draw.rect(surface, spark_color, (int(sx), int(sy), 4, 4))
        self.sparks = new_sparks

        if not self.active:
            draw_color = (100, 100, 100) 
        elif self.is_hovered:
            draw_color = self.highlight_color
        else:
            draw_color = self.base_color

        draw_rect = self.rect.copy()
        draw_rect.y += round(self.current_y_offset)
        
        if self.is_winning_play and self.active:
            draw_rect.x += random.randint(-4, 4)
            draw_rect.y += random.randint(-4, 4)

        # Retro Shadow
        size = (draw_rect.width, draw_rect.height)
        if size not in _shadow_cache:
            shadow_surf = pygame.Surface(size, pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 180)) # Darker drop shadow
            _shadow_cache[size] = shadow_surf
            
        shadow_surf = _shadow_cache[size]
        surface.blit(shadow_surf, (draw_rect.x + 6, draw_rect.y + 8))

        # Thick Pixel Outline
        pygame.draw.rect(surface, config.COLOR_BLACK, draw_rect, border_radius=8)
        inner_rect = draw_rect.inflate(-6, -6)
        pygame.draw.rect(surface, draw_color, inner_rect, border_radius=6)

        # Pygame Multiline centering
        lines = self.text.split('\n')
        line_height = FONT_14.get_linesize()
        start_y = draw_rect.centery - (len(lines) * line_height) / 2
        
        for i, line in enumerate(lines):
            # Heavy Text Drop Shadow
            text_surf_shadow = FONT_14.render(line, True, config.COLOR_BLACK)
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (2, 2)]:
                text_rect = text_surf_shadow.get_rect(center=(draw_rect.centerx + dx, start_y + (i * line_height) + line_height/2 + dy))
                surface.blit(text_surf_shadow, text_rect)
                
            text_surf = FONT_14.render(line, True, self.text_color)
            text_rect = text_surf.get_rect(center=(draw_rect.centerx, start_y + (i * line_height) + line_height/2))
            surface.blit(text_surf, text_rect)

    def check_mouse_hover(self, x, y):
        if not self.visible: return
        self.is_hovered = self.rect.collidepoint(x, y)

    def is_clicked(self, x, y):
        return self.visible and self.active and self.is_hovered

def draw_shadows(surface, sprite_list):
    """ Simplified Pygame drop shadow """
    screen_rect = surface.get_rect().inflate(100, 100)
    
    # Create a single screen-sized surface to prevent alpha stacking
    shadow_layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    
    for sprite in sprite_list:
        if not screen_rect.colliderect(sprite.rect):
            continue
            
        shadow_rect = sprite.rect.copy()
        
        offset_x = 8
        offset_y = 12
        
        if getattr(sprite, 'is_selected', False):
            offset_x += 8
            offset_y += 24
            
        shadow_rect.x += offset_x
        shadow_rect.y += offset_y # Shadow goes down in Pygame
        
        # Optimize memory by reusing shadow surfaces
        size = (shadow_rect.width, shadow_rect.height)
        if size not in _shadow_cache:
            shadow_surf = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 255), shadow_surf.get_rect(), border_radius=12)
            _shadow_cache[size] = shadow_surf
            
        shadow_surf = _shadow_cache[size]
        
        angle = 0
        if hasattr(sprite, 'angle') and sprite.angle != 0:
            angle = sprite.angle
        elif hasattr(sprite, 'current_angle') and sprite.current_angle != 0:
            angle = sprite.current_angle
            
        if angle != 0:
            shadow_surf = pygame.transform.rotate(shadow_surf, angle)
            shadow_rect = shadow_surf.get_rect(center=shadow_rect.center)
            
        shadow_layer.blit(shadow_surf, shadow_rect)
        
    shadow_layer.set_alpha(160)
    surface.blit(shadow_layer, (0, 0))

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


import math

SHADER_VERTEX = """
#version 330
in vec2 in_position;
out vec2 uv;
void main() {
    uv = in_position;
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

SHADER_FRAGMENT = """
#version 330
in vec2 uv;
out vec4 fragColor;
uniform float time;
uniform vec2 resolution;
uniform vec3 color1;
uniform vec3 color2;
uniform vec3 color3;

void main() {
    vec2 p = uv * 3.0;
    for(int i = 1; i < 5; i++) {
        vec2 newp = p;
        newp.x += 0.6 / float(i) * sin(float(i) * p.y + time + 0.3) + 1.0;
        newp.y += 0.6 / float(i) * cos(float(i) * p.x + time + 0.3) - 1.4;
        p = newp;
    }
    float f = 0.5 * sin(3.0 * p.x) + 0.5;
    float g = 0.8 * sin(3.0 * p.y) + 0.5;
    
    vec3 col = mix(color1, color2, f);
    col = mix(col, color3, g * 0.6);
    
    fragColor = vec4(col, 1.0);
}
"""

class MarbleBackground:
    PALETTES = {
        "default": ((0.0, 0.2, 0.1), (0.2, 0.8, 0.4), (0.1, 0.4, 0.2)),
        "shop": ((0.2, 0.05, 0.05), (0.8, 0.3, 0.1), (0.5, 0.1, 0.1)),
    }

    def __init__(self, width, height, ctx=None):
        self.width = width
        self.height = height
        self.time = 0.0
        self.ctx = ctx
        
        self.current_palette = list(self.PALETTES["default"])
        self.target_palette = list(self.PALETTES["default"])
        
        if self.ctx and moderngl:
            import struct
            self.prog = self.ctx.program(
                vertex_shader=SHADER_VERTEX,
                fragment_shader=SHADER_FRAGMENT
            )
            vertices = [
                -1.0, -1.0,
                 1.0, -1.0,
                -1.0,  1.0,
                 1.0,  1.0,
            ]
            self.vbo = self.ctx.buffer(struct.pack('8f', *vertices))
            self.vao = self.ctx.vertex_array(self.prog, [(self.vbo, '2f', 'in_position')])
        else:
            # Pygame fallback: pre-render a few swirling gradient circles
            self.layer1 = self._create_layer(600)
            self.layer2 = self._create_layer(500)
            self.layer3 = self._create_layer(400)

    def _create_layer(self, size):
        surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
        # Create concentric circles fading out to create a soft blob
        for r in range(size, 0, -10):
            alpha = int(255 * (1 - (r / size)**1.5))
            pygame.draw.circle(surf, (255, 255, 255, alpha), (size, size), r)
        return surf
        
    def set_state(self, state_name):
        if state_name == "shop":
            self.target_palette = list(self.PALETTES["shop"])
        elif state_name.startswith("level_"):
            lvl = int(state_name.split("_")[1])
            # Cycle level background palettes deterministically
            colors = [
                ((0.0, 0.2, 0.1), (0.2, 0.8, 0.4), (0.1, 0.4, 0.2)), # Green
                ((0.05, 0.1, 0.3), (0.2, 0.4, 0.8), (0.1, 0.2, 0.5)), # Blue
                ((0.2, 0.0, 0.2), (0.6, 0.2, 0.8), (0.4, 0.1, 0.5)), # Purple
                ((0.3, 0.05, 0.05), (0.9, 0.2, 0.2), (0.6, 0.1, 0.1)), # Red
                ((0.3, 0.2, 0.0), (0.9, 0.7, 0.1), (0.6, 0.4, 0.0)), # Gold
            ]
            self.target_palette = list(colors[(lvl - 1) % len(colors)])
        else:
            self.target_palette = list(self.PALETTES["default"])

    def update(self, delta_time):
        self.time += delta_time
        for i in range(3):
            self.current_palette[i] = tuple(
                c + (t - c) * 4.0 * delta_time 
                for c, t in zip(self.current_palette[i], self.target_palette[i])
            )

    def draw(self, screen=None):
        if self.ctx and moderngl:
            self.prog['time'].value = self.time
            if 'resolution' in self.prog:
                self.prog['resolution'].value = (self.width, self.height)
            if 'color1' in self.prog: self.prog['color1'].value = self.current_palette[0]
            if 'color2' in self.prog: self.prog['color2'].value = self.current_palette[1]
            if 'color3' in self.prog: self.prog['color3'].value = self.current_palette[2]
            self.vao.render(moderngl.TRIANGLE_STRIP)
        elif screen:
            bg_color = tuple(int(c * 255) for c in self.current_palette[0])
            screen.fill(bg_color)
            
            # Calculate moving orbits to simulate fluid swirl
            x1 = self.width / 2 + math.sin(self.time * 0.4) * (self.width / 3)
            y1 = self.height / 2 + math.cos(self.time * 0.5) * (self.height / 3)
            
            x2 = self.width / 2 + math.sin(self.time * 0.3 + 2.0) * (self.width / 2.5)
            y2 = self.height / 2 + math.cos(self.time * 0.6 + 1.0) * (self.height / 2.5)
            
            x3 = self.width / 2 + math.sin(self.time * 0.7 + 4.0) * (self.width / 4)
            y3 = self.height / 2 + math.cos(self.time * 0.2 + 3.0) * (self.height / 4)
            
            tint1 = tuple(int(c * 255) for c in self.current_palette[1])
            tint2 = tuple(int(c * 255) for c in self.current_palette[2])
            
            l1 = self.layer1.copy()
            l1.fill(tint1 + (255,), special_flags=pygame.BLEND_RGBA_MULT)
            l2 = self.layer2.copy()
            l2.fill(tint2 + (255,), special_flags=pygame.BLEND_RGBA_MULT)
            
            screen.blit(l1, (x1 - 600, y1 - 600), special_flags=pygame.BLEND_ADD)
            screen.blit(l2, (x2 - 500, y2 - 500), special_flags=pygame.BLEND_ADD)
            screen.blit(l1, (x3 - 400, y3 - 400), special_flags=pygame.BLEND_ADD)

class VolumeControl:
    def __init__(self, x, y, width=100, height=10, initial_vol=0.5):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        self.mute_rect = pygame.Rect(x, y - 10, 20, 20)
        self.slider_rect = pygame.Rect(x + 30, y - height//2, width, height)
        
        self.volume = initial_vol
        self.is_muted = False
        self.is_dragging = False

    def draw(self, surface):
        icon_color = config.COLOR_RED if self.is_muted else config.COLOR_WHITE
        pygame.draw.rect(surface, icon_color, self.mute_rect, 2, border_radius=4)
        
        pygame.draw.polygon(surface, icon_color, [(self.x+4, self.y), (self.x+8, self.y-5), (self.x+8, self.y+5)])
        if self.is_muted:
            pygame.draw.line(surface, config.COLOR_RED, (self.x+12, self.y-5), (self.x+18, self.y+5), 2)
            pygame.draw.line(surface, config.COLOR_RED, (self.x+18, self.y-5), (self.x+12, self.y+5), 2)
        else:
            pygame.draw.line(surface, icon_color, (self.x+12, self.y-3), (self.x+12, self.y+3), 2)
            pygame.draw.line(surface, icon_color, (self.x+16, self.y-6), (self.x+16, self.y+6), 2)

        pygame.draw.rect(surface, (50, 50, 50), self.slider_rect, border_radius=4)
        if not self.is_muted:
            fill_width = int(self.width * self.volume)
            fill_rect = pygame.Rect(self.slider_rect.x, self.slider_rect.y, fill_width, self.slider_rect.height)
            pygame.draw.rect(surface, config.COLOR_GREEN, fill_rect, border_radius=4)
            pygame.draw.circle(surface, config.COLOR_WHITE, (self.slider_rect.x + fill_width, self.slider_rect.centery), self.height)

    def update_volume_from_mouse(self, x):
        rel_x = x - self.slider_rect.x
        self.volume = max(0.0, min(1.0, rel_x / self.width))
        if self.volume > 0:
            self.is_muted = False
        elif self.volume == 0:
            self.is_muted = True

    def handle_mouse_down(self, x, y):
        if self.mute_rect.collidepoint(x, y):
            self.is_muted = not self.is_muted
            if not self.is_muted and self.volume == 0:
                self.volume = 0.5
            return True
        elif self.slider_rect.collidepoint(x, y) or self.slider_rect.inflate(0, 10).collidepoint(x, y):
            self.is_dragging = True
            self.update_volume_from_mouse(x)
            return True
        return False
        
    def handle_mouse_up(self, x, y):
        was_dragging = self.is_dragging
        self.is_dragging = False
        return was_dragging
        
    def handle_mouse_motion(self, x, y):
        if self.is_dragging:
            self.update_volume_from_mouse(x)
            return True
        return False
        
    def get_actual_volume(self):
        return 0.0 if self.is_muted else self.volume