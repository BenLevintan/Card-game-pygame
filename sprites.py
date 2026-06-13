import pygame
import random
import math
import config

class Joker(pygame.sprite.Sprite):
    def __init__(self, key, scale=1.0):
        super().__init__()
        data = config.JOKER_DATA[key]
        
        self.key = key
        self.name = data['name']
        self.cost = data['cost']
        self.desc = data['desc']
        self.sell_price = self.cost // 2
        self.is_selected = False
        
        try:
            orig = pygame.image.load(data['file']).convert_alpha()
            w, h = orig.get_size()
            self.orig_image = pygame.transform.smoothscale(orig, (int(w*scale), int(h*scale)))
        except:
            self.orig_image = pygame.Surface((int(config.JOKER_WIDTH), int(350 * scale)), pygame.SRCALPHA)
            self.orig_image.fill((100, 0, 100))
            
        self.image = self.orig_image
        self.rect = self.image.get_rect()
        
        self.target_x = 0
        self.target_y = 0
        self.vel_x = 0
        self.vel_y = 0
        self._phys_x = 0
        self._phys_y = 0
        self.float_phase = random.uniform(0, 6.28)
        self.rot_phase = random.uniform(0, 6.28)
        self.timer = 0.0
        self.angle = 0

    def update(self, delta_time):
        self.timer += delta_time
        
        actual_target_y = self.target_y
        if self.is_selected:
            actual_target_y -= 30
            
        dx = self.target_x - self._phys_x
        dy = actual_target_y - self._phys_y
        self.vel_x = (self.vel_x + dx * config.STIFFNESS) * config.DAMPING
        self.vel_y = (self.vel_y + dy * config.STIFFNESS) * config.DAMPING
        self._phys_x += self.vel_x
        self._phys_y += self.vel_y
        
        if self.is_selected:
            float_offset = 0
            self.angle = 0
        else:
            float_offset = math.sin(self.timer * config.FLOAT_SPEED + self.float_phase) * config.FLOAT_RANGE
            self.angle = math.sin(self.timer * config.JOKER_ROT_SPEED + self.rot_phase) * config.JOKER_ROT_RANGE
        
        self.image = pygame.transform.rotate(self.orig_image, self.angle)
        self.rect = self.image.get_rect(center=(self._phys_x, self._phys_y + float_offset))

class Pack(pygame.sprite.Sprite):
    def __init__(self, scale=1.0):
        super().__init__()
        self.name = "Standard Pack"
        self.desc = "Choose 1 of 2 modifiers\nfor selected cards."
        self.cost = config.PACK_COST
        self.is_selected = False
        
        try:
            orig = pygame.image.load(config.PACK_IMAGE).convert_alpha()
            w, h = orig.get_size()
            self.orig_image = pygame.transform.smoothscale(orig, (int(w * scale), int(h * scale)))
        except Exception:
            self.orig_image = pygame.Surface((int(config.JOKER_WIDTH), int(350 * scale)), pygame.SRCALPHA)
            self.orig_image.fill((200, 50, 50))
            
        self.image = self.orig_image
        self.rect = self.image.get_rect()
        
        self.target_x = 0
        self.target_y = 0
        self.vel_x = 0
        self.vel_y = 0
        self._phys_x = 0
        self._phys_y = 0
        self.float_phase = random.uniform(0, 6.28)
        self.rot_phase = random.uniform(0, 6.28)
        self.timer = 0.0
        self.angle = 0

    def update(self, delta_time):
        self.timer += delta_time
        
        dx = self.target_x - self._phys_x
        dy = self.target_y - self._phys_y
        self.vel_x = (self.vel_x + dx * config.STIFFNESS) * config.DAMPING
        self.vel_y = (self.vel_y + dy * config.STIFFNESS) * config.DAMPING
        self._phys_x += self.vel_x
        self._phys_y += self.vel_y
        
        float_offset = math.sin(self.timer * config.FLOAT_SPEED + self.float_phase) * config.FLOAT_RANGE
        self.angle = math.sin(self.timer * config.JOKER_ROT_SPEED + self.rot_phase) * config.JOKER_ROT_RANGE
        
        self.image = pygame.transform.rotate(self.orig_image, self.angle)
        self.rect = self.image.get_rect(center=(self._phys_x, self._phys_y + float_offset))

class Card(pygame.sprite.Sprite):
    def __init__(self, suit, rank, scale=1):
        super().__init__()
        self.suit = suit
        self.rank = rank
        
        if rank in ['J', 'Q', 'K', 'A']:
            if rank == 'J': self.value = 11
            elif rank == 'Q': self.value = 12
            elif rank == 'K': self.value = 13
            elif rank == 'A': self.value = 14
        else:
            self.value = int(rank)
            
        self.color_type = 'Red' if suit in ['Hearts', 'Diamonds'] else 'Black'
        self.is_selected = False
        self.modifier = None 
        
        self.is_hovered = False
        self.target_angle = 0.0
        self.current_angle = 0.0
        self.current_scale = 1.0
        
        width, height = int(config.CARD_WIDTH), int(config.CARD_HEIGHT)

        self.orig_image = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(self.orig_image, config.COLOR_BLACK, (0, 0, width, height), border_radius=12)
        pygame.draw.rect(self.orig_image, (255, 255, 255), (3, 3, width-6, height-6), border_radius=10)
        
        # Load fonts (using system fonts that support symbols)
        pygame.font.init()
        # Pygbag Fix: Requesting non-existent system fonts silently crashes WASM font rendering. Use default (None).
        font_small = pygame.font.SysFont(None, 28, bold=True)
        
        text_color = (220, 30, 30) if self.color_type == 'Red' else (30, 30, 30)
        
        # Render Text
        rank_surf = font_small.render(rank, True, text_color)
        
        # Draw Top-Left Corner
        self.orig_image.blit(rank_surf, (10, 8))
        self.draw_suit_symbol(self.orig_image, suit, 12, 34, 16, 16, text_color)
        
        # Draw Center Symbol
        self.draw_suit_symbol(self.orig_image, suit, width // 2 - 20, height // 2 - 20, 40, 40, text_color)
        
        # Draw Bottom-Right Corner (Flipped)
        br_surf = pygame.Surface((40, 60), pygame.SRCALPHA)
        br_surf.blit(rank_surf, (0, 0))
        self.draw_suit_symbol(br_surf, suit, 2, 26, 16, 16, text_color)
        br_surf = pygame.transform.rotate(br_surf, 180)
        self.orig_image.blit(br_surf, (width - br_surf.get_width() - 5, height - br_surf.get_height() - 5))
        # =========================================================

        self.image = self.orig_image
        self.rect = self.image.get_rect()
        
        self.target_x = 0
        self.target_y = 0
        self.vel_x = 0
        self.vel_y = 0
        self._phys_x = 0
        self._phys_y = 0
        self.should_despawn = False 
        self.is_spasming = False 
        self.float_phase = random.uniform(0, 6.28)
        self.timer = 0.0
        self.alpha = 255

    def draw_suit_symbol(self, surface, suit, x, y, w, h, color):
        if suit == 'Diamonds':
            points = [(x + w//2, y), (x + w, y + h//2), 
                      (x + w//2, y + h), (x, y + h//2)]
            pygame.draw.polygon(surface, color, points)
        elif suit == 'Hearts':
            r = w // 4
            pygame.draw.circle(surface, color, (x + r, y + r), r)
            pygame.draw.circle(surface, color, (x + w - r, y + r), r)
            points = [(x, y + r), (x + w, y + r), (x + w//2, y + h)]
            pygame.draw.polygon(surface, color, points)
        elif suit == 'Spades':
            r = w // 4
            pygame.draw.circle(surface, color, (x + r, y + int(h*0.6)), r)
            pygame.draw.circle(surface, color, (x + w - r, y + int(h*0.6)), r)
            points = [(x, y + int(h*0.6)), (x + w, y + int(h*0.6)), (x + w//2, y)]
            pygame.draw.polygon(surface, color, points)
            stem = [(x + w//2, y + int(h*0.5)), (x + w//2 - int(r*0.8), y + h), (x + w//2 + int(r*0.8), y + h)]
            pygame.draw.polygon(surface, color, stem)
        elif suit == 'Clubs':
            r = int(w * 0.24)
            pygame.draw.circle(surface, color, (x + w//2, y + r + 2), r)
            pygame.draw.circle(surface, color, (x + r + 1, y + int(h*0.6)), r)
            pygame.draw.circle(surface, color, (x + w - r - 1, y + int(h*0.6)), r)
            stem = [(x + w//2, y + int(h*0.5)), (x + w//2 - int(r*0.8), y + h), (x + w//2 + int(r*0.8), y + h)]
            pygame.draw.polygon(surface, color, stem)

    def update(self, delta_time):
        self.timer += delta_time
        
        if self.is_spasming:
            cx = self._phys_x + random.uniform(-15, 15)
            cy = self._phys_y + random.uniform(-15, 15)
            self.alpha = max(0, self.alpha - 255 * delta_time)
            
            self.image = self.orig_image.copy()
            self.image.set_alpha(int(self.alpha))
            self.rect = self.image.get_rect(center=(cx, cy))
            
            if self.alpha <= 0:
                self.kill()
                self.is_spasming = False
                self.alpha = 255
            return 

        target_scale = 1.15 if (self.is_hovered or self.is_selected) else 1.0
        self.current_scale += (target_scale - self.current_scale) * 15 * delta_time
        self.current_angle += (self.target_angle - self.current_angle) * 15 * delta_time

        actual_target_y = self.target_y
        if self.is_selected:
            actual_target_y -= 30
        elif self.is_hovered:
            actual_target_y -= 15

        dx = self.target_x - self._phys_x
        dy = actual_target_y - self._phys_y
        self.vel_x = (self.vel_x + dx * config.STIFFNESS) * config.DAMPING
        self.vel_y = (self.vel_y + dy * config.STIFFNESS) * config.DAMPING
        self._phys_x += self.vel_x
        self._phys_y += self.vel_y

        if self.should_despawn:
            self.rect.center = (self._phys_x, self._phys_y)
            if (self.rect.centery > config.SCREEN_HEIGHT + 200 or self.rect.centery < -200):
                self.kill()
        else:
            if self.is_selected:
                cy = self._phys_y
            else:
                float_offset = math.sin(self.timer * config.FLOAT_SPEED + self.float_phase) * config.FLOAT_RANGE
                cy = self._phys_y + float_offset
                
            if abs(self.current_scale - 1.0) > 0.01 or abs(self.current_angle) > 0.1:
                w, h = self.orig_image.get_size()
                scaled = pygame.transform.smoothscale(self.orig_image, (int(w * self.current_scale), int(h * self.current_scale)))
                if abs(self.current_angle) > 0.1:
                    self.image = pygame.transform.rotate(scaled, self.current_angle)
                else:
                    self.image = scaled
            else:
                self.image = self.orig_image
                
            self.rect = self.image.get_rect(center=(self._phys_x, cy))

    def draw_modifier(self, screen):
        if self.modifier:
            data = config.MODIFIER_DATA[self.modifier]
            pygame.draw.rect(screen, data['color'], self.rect, 4, border_radius=8)
            
            font = pygame.font.SysFont(None, 20, bold=True)
            text_surf = font.render(data['name'][:4], True, data['color'])
            
            # Add a slight dark background to the text so it's readable
            bg_rect = text_surf.get_rect(center=(self.rect.centerx, self.rect.centery + 40))
            pygame.draw.rect(screen, (20, 20, 20), bg_rect.inflate(8, 4), border_radius=3)
            screen.blit(text_surf, bg_rect)