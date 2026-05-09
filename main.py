import pygame
import sys
import enum
import warnings

warnings.filterwarnings("ignore") 

import config
import sprites
import ui_elements
import systems
import scoring

class GameState(enum.Enum):
    MAIN_MENU = 0
    DRAWING = 1
    DECIDING = 2
    SHOPPING = 3
    PACK_OPENING = 4 
    GAME_OVER = 5
    STATS = 6

class WarGame:
    def __init__(self):
        pygame.init()
        # Create the actual display, but use an off-screen Surface for all drawing
        self.real_display = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        
        # Pygbag Fix: Draw directly to the canvas in WebAssembly to avoid massive texture upload failures
        if sys.platform in ("emscripten", "wasi"):
            self.screen = self.real_display
        else:
            self.screen = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT)).convert()
        pygame.display.set_caption(config.SCREEN_TITLE)
        
        # Initialize UI fonts AFTER the display is created to prevent WASM invalidation
        ui_elements.init_fonts()
        self.clock = pygame.time.Clock()
        
        self.deck_manager = None
        self.shop_manager = systems.ShopManager()
        self.audio_manager = systems.AudioManager() 
        self.save_manager = systems.SaveManager()

        # Pygame Groups
        self.card_list = pygame.sprite.Group()
        self.hand_list = pygame.sprite.Group()
        self.joker_list = pygame.sprite.Group()
        self.shop_list = pygame.sprite.Group()
        self.pack_card_list = pygame.sprite.Group()
        self.animating_cards = pygame.sprite.Group() 
        self.drawn_card = None
        
        self.state = GameState.MAIN_MENU
        self.previous_state = None
        self.score_total = 0
        self.hands_played = 0
        self.hands_max = config.BASE_HANDS_TO_PLAY
        self.discards_left = config.MAX_DISCARDS
        self.target_score = config.BASE_TARGET_SCORE
        self.round_level = 1
        self.coins = 5 
        self.run_discards = 0 
        
        self.message = ""
        self.hand_details = [] 
        
        self.btn_action = None 
        self.btn_score = None
        self.btn_next_round = None
        self.btn_sell = ui_elements.TextButton(0, 0, 100, 40, "SELL", config.COLOR_BTN_SELL)
        self.btn_sell.visible = False
        self.shop_buttons = []
        
        self.btn_pack_skip = None
        self.btn_pack_mods = [] 
        self.pack_modifiers_offered = [] 
        
        self.hovered_joker = None 
        self.mouse_x = 0
        self.mouse_y = 0
        self.shop_focus_index = -1
        self.pack_focus_index = -1

        # Initialize the CRT overlay
        self.crt_overlay = ui_elements.CRTOverlay(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        
        self.volume_control = ui_elements.VolumeControl(config.SCREEN_WIDTH - 150, 40, width=100)

    def sync_save(self):
        if self.state not in [GameState.MAIN_MENU, GameState.STATS, GameState.GAME_OVER]:
            self.save_current_state()

    def _create_card(self, c_data):
        c = sprites.Card(c_data["suit"], c_data["rank"], config.CARD_SCALE)
        c.modifier = c_data["modifier"]
        return c

    def save_current_state(self):
        state_data = {
            "state": self.state.value,
            "score_total": self.score_total,
            "round_level": self.round_level,
            "target_score": self.target_score,
            "coins": self.coins,
            "run_discards": self.run_discards,
            "hands_played": self.hands_played,
            "hands_max": self.hands_max,
            "discards_left": self.discards_left,
            "jokers": [j.key for j in self.joker_list],
            "deck": [],
            "shop_items": [],
            "pack_indices": [],
            "pack_modifiers": []
        }
        
        master_deck_data = []
        for c in self.deck_manager.master_deck:
            loc = "master_only"
            if c in self.deck_manager.draw_pile: loc = "draw"
            elif c in self.deck_manager.discard_pile: loc = "discard"
            elif c in self.hand_list: loc = "hand"
            elif self.drawn_card and c == self.drawn_card: loc = "drawn"
            
            master_deck_data.append({
                "suit": c.suit, "rank": c.rank, "modifier": c.modifier, "location": loc
            })
        state_data["deck"] = master_deck_data

        if self.state == GameState.SHOPPING:
            for item in self.shop_list:
                if isinstance(item, sprites.Joker):
                    state_data["shop_items"].append({"type": "Joker", "key": item.key, "cost": item.cost})
                elif isinstance(item, sprites.Pack):
                    state_data["shop_items"].append({"type": "Pack", "cost": item.cost})
        elif self.state == GameState.PACK_OPENING:
            state_data["pack_indices"] = [self.deck_manager.master_deck.index(c) for c in self.pack_card_list if c in self.deck_manager.master_deck]
            state_data["pack_modifiers"] = self.pack_modifiers_offered

        self.save_manager.save_current_game(state_data)

    def load_current_state(self):
        data = self.save_manager.data.get("current_game")
        if not data: return False
        
        self.state = GameState(data["state"])
        self.score_total = data["score_total"]
        self.round_level = data["round_level"]
        self.target_score = data["target_score"]
        self.coins = data["coins"]
        self.run_discards = data["run_discards"]
        self.hands_played = data["hands_played"]
        self.hands_max = data["hands_max"]
        self.discards_left = data["discards_left"]
        
        self.joker_list.empty()
        for key in data["jokers"]:
            j = sprites.Joker(key, config.JOKER_SCALE)
            self.joker_list.add(j)
        self.reposition_jokers()

        self.deck_manager = systems.DeckManager()
        self.deck_manager.master_deck = []
        self.deck_manager.draw_pile = []
        self.deck_manager.discard_pile = []
        self.hand_list.empty()
        self.card_list.empty()
        self.drawn_card = None
        
        for c_data in data["deck"]:
            c = self._create_card(c_data)
            self.deck_manager.master_deck.append(c)
            loc = c_data["location"]
            if loc == "draw": self.deck_manager.draw_pile.append(c)
            elif loc == "discard": self.deck_manager.discard_pile.append(c)
            elif loc == "hand": self.hand_list.add(c)
            elif loc == "drawn": 
                self.drawn_card = c
                self.drawn_card._phys_x, self.drawn_card._phys_y = config.DRAWN_CARD_X, config.DRAWN_CARD_Y
                self.drawn_card.target_x, self.drawn_card.target_y = config.DRAWN_CARD_X, config.DRAWN_CARD_Y
                self.card_list.add(self.drawn_card)

        self.reposition_hand()
        
        self.btn_action = ui_elements.TextButton(config.SCREEN_WIDTH/2, config.SCREEN_HEIGHT - 320, 240, 50, "TAKE CARD", config.COLOR_BTN_ACTION)
        self.btn_score = ui_elements.TextButton(config.SCREEN_WIDTH - 150, config.SCREEN_HEIGHT - 150, 200, 60, "SCORE HAND", config.COLOR_BTN_SCORE)
        
        if self.state == GameState.SHOPPING:
            self.shop_list.empty()
            self.shop_buttons = []
            start_x = config.SCREEN_WIDTH / 2 - 200
            pos_y = config.SCREEN_HEIGHT / 2 - 50 
            for i, item_data in enumerate(data.get("shop_items", [])):
                pos_x = start_x + (i * 200)
                if item_data["type"] == "Joker":
                    item = sprites.Joker(item_data["key"], config.JOKER_SCALE)
                    item.cost = item_data["cost"]
                    item._phys_x, item._phys_y = pos_x, pos_y
                    item.target_x, item.target_y = pos_x, pos_y
                    self.shop_list.add(item)
                    btn = ui_elements.TextButton(pos_x, pos_y + 170, 120, 40, f"BUY ${item.cost}", config.COLOR_BTN_SHOP)
                    self.shop_buttons.append(btn)
                else:
                    item = sprites.Pack(config.JOKER_SCALE)
                    item.rect.center = (pos_x, pos_y)
                    self.shop_list.add(item)
                    btn = ui_elements.TextButton(pos_x, pos_y + 170, 120, 40, f"BUY ${item_data['cost']}", config.COLOR_PURPLE)
                    self.shop_buttons.append(btn)
            self.btn_next_round = ui_elements.TextButton(config.SCREEN_WIDTH - 150, config.SCREEN_HEIGHT - 150, 200, 60, "NEXT LEVEL >", config.COLOR_GREEN)
            self.update_shop_buttons()
        
        elif self.state == GameState.PACK_OPENING:
            self.pack_card_list.empty()
            self.btn_pack_mods = []
            start_x = config.SCREEN_WIDTH / 2 - 250
            start_y = config.SCREEN_HEIGHT / 2 - 100
            for i, idx in enumerate(data.get("pack_indices", [])):
                card = self.deck_manager.master_deck[idx]
                self.pack_card_list.add(card)
                row = i // 4
                col = i % 4
                tx = start_x + (col * (config.CARD_WIDTH + 20))
                ty = start_y + (row * (config.CARD_HEIGHT + 20))
                card._phys_x, card._phys_y = tx, ty
                card.target_x, card.target_y = tx, ty
            
            self.pack_modifiers_offered = data.get("pack_modifiers", [])
            bx = config.SCREEN_WIDTH / 2 - 100
            by = config.SCREEN_HEIGHT - 150 
            for i, mod_key in enumerate(self.pack_modifiers_offered):
                mod_d = config.MODIFIER_DATA[mod_key]
                btn = ui_elements.TextButton(bx + (i * 200), by, 180, 60, mod_d['name'], mod_d['color'])
                self.btn_pack_mods.append(btn)
            self.btn_pack_skip = ui_elements.TextButton(config.SCREEN_WIDTH - 150, config.SCREEN_HEIGHT - 150, 200, 60, "SKIP", config.COLOR_BTN_DEFAULT)
            
        self.audio_manager.start_bg_music()
        if self.state in [GameState.SHOPPING, GameState.PACK_OPENING]:
            self.audio_manager.enter_store()
            
        self.btn_main_continue.active = True
        return True

    def setup(self):
        self.state = GameState.MAIN_MENU
        self.btn_main_continue = ui_elements.TextButton(config.SCREEN_WIDTH/2, config.SCREEN_HEIGHT/2 - 50, 200, 60, "CONTINUE", config.COLOR_BTN_ACTION)
        self.btn_main_continue.active = (self.save_manager.data.get("current_game") is not None)
        self.btn_main_new_game = ui_elements.TextButton(config.SCREEN_WIDTH/2, config.SCREEN_HEIGHT/2 + 30, 200, 60, "NEW GAME", config.COLOR_GREEN)
        self.btn_main_stats = ui_elements.TextButton(config.SCREEN_WIDTH/2, config.SCREEN_HEIGHT/2 + 110, 200, 60, "STATS", config.COLOR_BTN_DEFAULT)
        self.btn_stats_back = ui_elements.TextButton(config.SCREEN_WIDTH/2, config.SCREEN_HEIGHT - 100, 200, 60, "BACK", config.COLOR_BTN_DEFAULT)
        
        self.audio_manager.start_bg_music() 

    def start_new_game(self):
        self.save_manager.clear_current_game()
        self.score_total = 0
        self.round_level = 1
        self.target_score = config.BASE_TARGET_SCORE
        self.coins = 15  
        self.run_discards = 0
        
        self.joker_list.empty()
        self.animating_cards.empty()
        self.deck_manager = systems.DeckManager()
        
        self.btn_main_continue.active = True
        
        self.start_new_round()

    def start_new_round(self):
        self.save_manager.update_highest_level(self.round_level)
        self.state = GameState.DRAWING
        self.card_list.empty()
        self.hand_list.empty()
        self.shop_list.empty()
        self.pack_card_list.empty()
        self.shop_buttons = []
        
        self.audio_manager.exit_store() 
        
        bonus_hands = sum(1 for j in self.joker_list if j.key == "helping_hand")
        bonus_discards = sum(1 for j in self.joker_list if j.key == "mulligan")
        
        self.hands_max = config.BASE_HANDS_TO_PLAY + bonus_hands
        self.discards_left = config.MAX_DISCARDS + bonus_discards
        
        self.hands_played = 0
        self.score_total = 0
        self.message = "" 
        self.hand_details = []
        
        self.deck_manager.start_round(self.card_list)

        self.btn_action = ui_elements.TextButton(config.SCREEN_WIDTH/2, config.SCREEN_HEIGHT - 320, 240, 50, "TAKE CARD", config.COLOR_BTN_ACTION)
        self.btn_score = ui_elements.TextButton(config.SCREEN_WIDTH - 150, config.SCREEN_HEIGHT - 150, 200, 60, "SCORE HAND", config.COLOR_BTN_SCORE)
        
        self.draw_new_card()
        self.sync_save()

    def draw_new_card(self):
        card = self.deck_manager.draw_card(self.card_list)
        
        if card:
            self.audio_manager.play_card_sound()
            
            start_x = config.SCREEN_WIDTH + 150
            start_y = config.DRAWN_CARD_Y
            card._phys_x, card._phys_y = start_x, start_y
            card.target_x = config.DRAWN_CARD_X
            card.target_y = config.DRAWN_CARD_Y
            
            self.drawn_card = card
            self.state = GameState.DECIDING
        else:
            self.drawn_card = None
            self.state = GameState.DECIDING
            if len(self.hand_list) == 0 and self.score_total < self.target_score:
                self.state = GameState.GAME_OVER
                self.audio_manager.enter_game_over()
                self.message = "lose: no cards in the deck"
                self.save_manager.clear_current_game()
            else:
                self.message = "DECK EMPTY!"
                
        if self.drawn_card is not None:
            self.sync_save()

    def enter_shop(self):
        self.state = GameState.SHOPPING
        self.message = "SHOP PHASE"
        
        self.audio_manager.enter_store()
        
        hands_left = max(0, self.hands_max - self.hands_played)
        reward = (hands_left * 2) + (self.discards_left * 1)
        self.coins += reward
        
        bonus_discards = sum(1 for j in self.joker_list if j.key == "mulligan")
        start_discards = config.MAX_DISCARDS + bonus_discards
        
        nr_bonus = 0
        if self.discards_left == start_discards:
            nr_count = sum(1 for j in self.joker_list if j.key == "national_reserve")
            if nr_count > 0:
                nr_bonus = nr_count * 3
                self.coins += nr_bonus
                
        harvest_count = sum(1 for j in self.joker_list if j.key == "the_harvest")
        harvest_bonus = harvest_count * 5
        if harvest_bonus > 0:
            self.coins += harvest_bonus

        self.message = f"Round Cleared!\nEarned ${reward}."
        if nr_bonus > 0: self.message += f"\n(Reserve: +${nr_bonus})"
        if harvest_bonus > 0: self.message += f"\n(Harvest: +${harvest_bonus})"

        self.shop_manager.generate_shop(self.shop_list, self.shop_buttons, self.joker_list)
        
        self.shop_focus_index = 0 if self.shop_buttons else -1

        self.btn_next_round = ui_elements.TextButton(config.SCREEN_WIDTH - 150, config.SCREEN_HEIGHT - 150, 200, 60, "NEXT LEVEL >", config.COLOR_GREEN)
        self.update_shop_buttons()
        self.sync_save()

    def update_shop_buttons(self):
        for i, item in enumerate(self.shop_list):
            if i < len(self.shop_buttons):
                btn = self.shop_buttons[i]
                if self.coins < item.cost:
                    btn.active = False
                    btn.text = f"Need ${item.cost}"
                else:
                    btn.active = True
                    btn.text = f"BUY ${item.cost}"

    def buy_shop_item(self, index):
        if index >= len(self.shop_list): return
        item = list(self.shop_list)[index]
        
        if self.coins >= item.cost:
            if isinstance(item, sprites.Joker):
                if len(self.joker_list) < config.MAX_JOKERS:
                    self.coins -= item.cost
                    item.kill()
                    self.joker_list.add(item)
                    self.reposition_jokers() 
                    self.shop_buttons.pop(index)
                    self.update_shop_buttons()
                    self.audio_manager.play_buy_joker_fx() 
                    self.sync_save()
                else:
                    self.message = "Inventory Full!"
            
            elif isinstance(item, sprites.Pack):
                self.coins -= item.cost
                item.kill()
                self.shop_buttons.pop(index)
                self.start_pack_opening()

    def start_pack_opening(self):
        self.state = GameState.PACK_OPENING
        self.message = "Select Cards then Choose Modifier"
        self.pack_card_list.empty()
        self.btn_pack_mods = []
        self.pack_focus_index = 0
        
        self.audio_manager.play_mod_fx() 
        
        chosen_cards = self.shop_manager.get_pack_cards(self.deck_manager.master_deck)
        
        start_x = config.SCREEN_WIDTH / 2 - 250
        start_y = config.SCREEN_HEIGHT / 2 - 100
        for i, card in enumerate(chosen_cards):
            self.pack_card_list.add(card)
            card.is_selected = False
            
            row = i // 4
            col = i % 4
            tx = start_x + (col * (config.CARD_WIDTH + 20))
            ty = start_y + (row * (config.CARD_HEIGHT + 20))
            
            card._phys_x, card._phys_y = config.SCREEN_WIDTH + 100, ty
            card.target_x, card.target_y = tx, ty

        self.pack_modifiers_offered = self.shop_manager.get_pack_modifiers()
        
        bx = config.SCREEN_WIDTH / 2 - 100
        by = config.SCREEN_HEIGHT - 150 
        for i, mod_key in enumerate(self.pack_modifiers_offered):
            data = config.MODIFIER_DATA[mod_key]
            btn = ui_elements.TextButton(bx + (i * 200), by, 180, 60, data['name'], data['color'])
            self.btn_pack_mods.append(btn)
            
        self.btn_pack_skip = ui_elements.TextButton(config.SCREEN_WIDTH - 150, config.SCREEN_HEIGHT - 150, 200, 60, "SKIP", config.COLOR_BTN_DEFAULT)
        self.sync_save()

    def apply_pack_modifier(self, mod_index):
        selected = [c for c in self.pack_card_list if c.is_selected]
        if not selected:
            self.message = "Select cards first!"
            return
            
        mod_key = self.pack_modifiers_offered[mod_index]
        self.audio_manager.play_mod_fx() 
        
        for card in selected:
            card.modifier = mod_key
            card.is_selected = False
            
            if mod_key == "destroy":
                card.is_spasming = True
            else:
                card.target_y = -400 
                card.should_despawn = True
            
            self.pack_card_list.remove(card)
            self.animating_cards.add(card)
            
        self.state = GameState.SHOPPING
        self.pack_card_list.empty() 
        self.message = "Applied!"
        self.sync_save()

    def score_hand(self):
        self.audio_manager.play_hand_fx()
        cards_in_deck = len(self.deck_manager.draw_pile)
        
        base, multi, desc, coin_bonus = scoring.calculate_hand_score(
            list(self.hand_list), list(self.joker_list), self.run_discards, cards_in_deck, self.coins
        )
        final_score = base * multi
        self.score_total += final_score
        
        hand_type = scoring.get_hand_type(list(self.hand_list))
        self.save_manager.update_hand_played(hand_type)
        self.save_manager.update_highest_hand(final_score)
        self.save_manager.update_highest_score(self.score_total)
        self.save_manager.update_highest_level(self.round_level)
        
        if coin_bonus > 0: self.coins += coin_bonus
        
        for card in list(self.hand_list): 
            self.hand_list.remove(card)
            self.deck_manager.discard_pile.append(card) 
            card.target_y = config.SCREEN_HEIGHT + 300 
            card.should_despawn = True
            self.animating_cards.add(card)
            
        if self.score_total >= self.target_score:
            self.enter_shop()
            return

        self.hands_played += 1
        if self.hands_played >= self.hands_max:
            self.state = GameState.GAME_OVER
            self.audio_manager.enter_game_over() 
            self.save_manager.clear_current_game()
        else:
            self.message = f"Scored {final_score}! ({base} x {multi})"
            if coin_bonus > 0: self.message += f" Earned ${coin_bonus}!"
            
            if self.drawn_card is None and len(self.deck_manager.draw_pile) == 0 and len(self.hand_list) == 0:
                self.state = GameState.GAME_OVER
                self.audio_manager.enter_game_over()
                self.message = "lose: no cards in the deck"
                self.save_manager.clear_current_game()
            else:
                self.sync_save()

    def process_swap(self):
        to_remove = [c for c in self.hand_list if c.is_selected]
        if len(to_remove) > 0:
            if self.discards_left > 0:
                self.discards_left -= 1
            else:
                return 
        
        self.run_discards += len(to_remove)

        sev_pack_count = sum(1 for j in self.joker_list if j.key == "severance_package")
        if sev_pack_count > 0:
            faces_discarded = sum(1 for c in to_remove if c.value in [11, 12, 13])
            if faces_discarded > 0:
                self.coins += faces_discarded * 2 * sev_pack_count

        for card in to_remove:
            self.hand_list.remove(card)
            self.deck_manager.discard_pile.append(card)
            card.target_y = config.SCREEN_HEIGHT + 300 
            card.should_despawn = True 
            self.animating_cards.add(card)
        
        if self.drawn_card:
            self.hand_list.add(self.drawn_card)
            self.card_list.remove(self.drawn_card)
            self.drawn_card = None
            self.reposition_hand()
            self.draw_new_card()
        else:
            self.reposition_hand()
            if len(self.hand_list) == 0 and len(self.deck_manager.draw_pile) == 0:
                if self.score_total < self.target_score:
                    self.state = GameState.GAME_OVER
                    self.audio_manager.enter_game_over()
                    self.message = "lose: no cards in the deck"
                    self.save_manager.clear_current_game()
        self.sync_save()

    def update_game_buttons(self):
        if self.state not in [GameState.DRAWING, GameState.DECIDING]:
            if self.btn_action: self.btn_action.visible = False
            if self.btn_score: self.btn_score.visible = False
            return
        
        self.btn_action.visible = True
        self.btn_score.visible = True

        num_selected = len([c for c in self.hand_list if c.is_selected])
        if num_selected > 0:
            self.btn_action.text = f"DISCARD ({num_selected}) & TAKE"
            self.btn_action.base_color = (220, 20, 60)
            self.btn_action.active = True
        else:
            self.btn_action.text = "TAKE CARD"
            self.btn_action.base_color = config.COLOR_BTN_ACTION
            if len(self.hand_list) >= config.MAX_HAND_SIZE:
                self.btn_action.active = False
                self.btn_action.text = "HAND FULL"
            else:
                self.btn_action.active = True

        if len(self.hand_list) > 0:
            cards_in_deck = len(self.deck_manager.draw_pile)
            s, m, desc, coin_bonus = scoring.calculate_hand_score(
                list(self.hand_list), list(self.joker_list), self.run_discards, cards_in_deck, self.coins
            )
            total = s * m
            self.btn_score.text = f"PLAY HAND\n{s} x {m} = {total}"
            if coin_bonus > 0: self.btn_score.text += f"\n(+${coin_bonus})"
            self.hand_details = desc
            self.btn_score.active = True
        else:
            self.btn_score.text = "PLAY HAND"
            self.hand_details = []
            self.btn_score.active = False

    def reposition_hand(self):
        sorted_hand = sorted(list(self.hand_list), key=lambda c: (c.value, c.suit))
        start_x = (config.SCREEN_WIDTH - (len(sorted_hand) * (config.CARD_WIDTH + 20))) / 2 + config.CARD_WIDTH / 2
        for i, card in enumerate(sorted_hand):
            card.target_x = start_x + i * (config.CARD_WIDTH + 20)
            card.target_y = config.HAND_Y
            card.is_selected = False

    def reposition_jokers(self):
        start_x = config.SCREEN_WIDTH - 100
        for i, joker in enumerate(self.joker_list):
            tx = start_x - (i * (config.JOKER_WIDTH + 50))
            joker.target_x = tx
            joker.target_y = config.JOKER_Y

    def sell_joker(self):
        to_sell = [j for j in self.joker_list if j.is_selected]
        for joker in to_sell:
            self.coins += joker.sell_price
            joker.kill()
        
        self.reposition_jokers()
        self.btn_sell.visible = False
        
        if self.state == GameState.SHOPPING:
            self.update_shop_buttons()
        self.sync_save()

    def run(self):
        try:
            while True:
                dt = self.clock.tick(60) / 1000.0
                
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    elif event.type == pygame.MOUSEMOTION:
                        self.mouse_x, self.mouse_y = event.pos
                        self.on_mouse_motion(self.mouse_x, self.mouse_y)
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1: 
                            self.on_mouse_press(*event.pos)
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if event.button == 1:
                            self.on_mouse_release(*event.pos)
                    elif event.type == pygame.KEYDOWN:
                        self.on_key_press(event.key)
                            
                self.on_update(dt)
                self.on_draw()
                pygame.display.flip()
        except Exception as e:
            import traceback
            self.real_display.fill((150, 0, 0)) # Red background for error
            font = pygame.font.SysFont(None, 24)
            y = 20
            for line in traceback.format_exc().split('\n'):
                self.real_display.blit(font.render(line, True, (255, 255, 255)), (20, y))
                y += 30
            pygame.display.flip()
            while True:
                pygame.time.wait(1000) 

    def on_mouse_motion(self, x, y):
        if self.volume_control.handle_mouse_motion(x, y):
            self.audio_manager.set_master_volume(self.volume_control.get_actual_volume())

        self.hovered_joker = None
        check_lists = [self.joker_list.sprites()]
        if self.state == GameState.SHOPPING: check_lists.append(self.shop_list.sprites())
            
        for sprite_list in check_lists:
            for sprite in sprite_list:
                if sprite.rect.collidepoint(x, y):
                    self.hovered_joker = sprite
                    break

        if self.state == GameState.SHOPPING:
            pass # This is now handled in on_update to combine mouse and keyboard focus
        elif self.state == GameState.PACK_OPENING:
            pass # Handled in on_update
        elif self.state == GameState.MAIN_MENU:
            if hasattr(self, 'btn_main_continue'):
                self.btn_main_continue.check_mouse_hover(x, y)
                self.btn_main_new_game.check_mouse_hover(x, y)
                self.btn_main_stats.check_mouse_hover(x, y)
        elif self.state == GameState.STATS:
            if hasattr(self, 'btn_stats_back'):
                self.btn_stats_back.check_mouse_hover(x, y)
        else:
            if self.btn_action: self.btn_action.check_mouse_hover(x, y)
            if self.btn_score: self.btn_score.check_mouse_hover(x, y)
        
        if self.btn_sell.visible: self.btn_sell.check_mouse_hover(x, y)

    def on_mouse_press(self, x, y):
        if self.volume_control.handle_mouse_down(x, y):
            self.audio_manager.set_master_volume(self.volume_control.get_actual_volume())
            return
            
        if self.state == GameState.MAIN_MENU:
            if hasattr(self, 'btn_main_continue') and self.btn_main_continue.is_clicked(x, y):
                if hasattr(self, 'previous_state') and self.previous_state:
                    self.state = self.previous_state
                else:
                    self.load_current_state()
            elif hasattr(self, 'btn_main_new_game') and self.btn_main_new_game.is_clicked(x, y):
                self.start_new_game()
            elif hasattr(self, 'btn_main_stats') and self.btn_main_stats.is_clicked(x, y):
                self.state = GameState.STATS
            return
            
        if self.state == GameState.STATS:
            if hasattr(self, 'btn_stats_back') and self.btn_stats_back.is_clicked(x, y):
                self.state = GameState.MAIN_MENU
            return

        if self.btn_sell.visible and self.btn_sell.is_clicked(x, y):
            self.sell_joker()
            return
        
        clicked_jokers = [j for j in self.joker_list if j.rect.collidepoint(x, y)]
        if clicked_jokers:
            for j in self.joker_list: j.is_selected = False
            clicked_jokers[-1].is_selected = True
            self.btn_sell.rect.center = (clicked_jokers[-1].rect.centerx, clicked_jokers[-1].rect.centery + 80)
            self.btn_sell.text = f"SELL ${clicked_jokers[-1].sell_price}"
            self.btn_sell.visible = True
            return
        else:
            for j in self.joker_list: j.is_selected = False
            self.btn_sell.visible = False

        if self.state == GameState.SHOPPING:
            for i, btn in enumerate(self.shop_buttons):
                if btn.is_clicked(x, y):
                    self.buy_shop_item(i)
                    return
            if self.btn_next_round and self.btn_next_round.is_clicked(x, y):
                self.round_level += 1
                self.target_score = int(self.target_score * 1.5)
                self.start_new_round()
                return

        elif self.state == GameState.PACK_OPENING:
            if self.btn_pack_skip.is_clicked(x, y):
                self.state = GameState.SHOPPING
                self.pack_card_list.empty()
                return
            for i, btn in enumerate(self.btn_pack_mods):
                if btn.is_clicked(x, y):
                    self.apply_pack_modifier(i)
                    return
            hit = [c for c in self.pack_card_list if c.rect.collidepoint(x, y)]
            if hit:
                card = hit[-1]
                if card.is_selected: card.is_selected = False
                else:
                    num_selected = len([c for c in self.pack_card_list if c.is_selected])
                    if num_selected < 2: card.is_selected = True
                    else: self.message = "Select only 2 cards!"

        elif self.state == GameState.GAME_OVER:
            self.state = GameState.MAIN_MENU
            self.btn_main_continue.active = False
            self.previous_state = None
            self.audio_manager.start_bg_music()
            return

        elif self.state in [GameState.DECIDING, GameState.DRAWING]:
            if self.btn_action and self.btn_action.is_clicked(x, y):
                self.process_swap()
                return
            if self.btn_score and self.btn_score.is_clicked(x, y):
                self.score_hand()
                return
            if self.state == GameState.DECIDING and self.discards_left > 0:
                cards_clicked = [c for c in self.hand_list if c.rect.collidepoint(x, y)]
                if cards_clicked: cards_clicked[-1].is_selected = not cards_clicked[-1].is_selected

    def on_mouse_release(self, x, y):
        if self.volume_control.handle_mouse_up(x, y):
            self.audio_manager.set_master_volume(self.volume_control.get_actual_volume())

    def on_key_press(self, key):
        if key == pygame.K_ESCAPE:
            if self.state in [GameState.DRAWING, GameState.DECIDING, GameState.SHOPPING, GameState.PACK_OPENING]:
                self.previous_state = self.state
                self.state = GameState.MAIN_MENU
                if hasattr(self, 'btn_main_continue'):
                    self.btn_main_continue.active = True
            elif self.state == GameState.MAIN_MENU and getattr(self, 'btn_main_continue', None) and self.btn_main_continue.active:
                if hasattr(self, 'previous_state') and self.previous_state:
                    self.state = self.previous_state
                else:
                    self.load_current_state()
            elif self.state == GameState.STATS:
                self.state = GameState.MAIN_MENU

        if self.state in [GameState.DECIDING, GameState.DRAWING]:
            if key == pygame.K_SPACE:
                if self.btn_action and self.btn_action.active and self.btn_action.visible:
                    self.process_swap()
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.btn_score and self.btn_score.active and self.btn_score.visible:
                    self.score_hand()
            elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                if self.state == GameState.DECIDING and self.discards_left > 0:
                    index = key - pygame.K_1
                    sorted_hand = sorted(list(self.hand_list), key=lambda c: (c.value, c.suit))
                    if index < len(sorted_hand):
                        card = sorted_hand[index]
                        card.is_selected = not card.is_selected
        
        elif self.state == GameState.SHOPPING:
            navigable_buttons = self.shop_buttons + ([self.btn_next_round] if self.btn_next_round else [])
            if not navigable_buttons: return

            if key == pygame.K_RIGHT:
                self.shop_focus_index = (self.shop_focus_index + 1) % len(navigable_buttons)
            elif key == pygame.K_LEFT:
                self.shop_focus_index = (self.shop_focus_index - 1) % len(navigable_buttons)
            elif key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.shop_focus_index != -1 and self.shop_focus_index < len(navigable_buttons):
                    focused_button = navigable_buttons[self.shop_focus_index]

                    if focused_button.active:
                        if focused_button in self.shop_buttons:
                            item_index = self.shop_buttons.index(focused_button)
                            self.buy_shop_item(item_index)
                        
                        elif focused_button == self.btn_next_round:
                            self.round_level += 1
                            self.target_score = int(self.target_score * 1.5)
                            self.start_new_round()
                            
        elif self.state == GameState.PACK_OPENING:
            navigable_items = list(self.pack_card_list) + self.btn_pack_mods + ([self.btn_pack_skip] if self.btn_pack_skip else [])
            if not navigable_items: return

            if key == pygame.K_RIGHT:
                self.pack_focus_index = (self.pack_focus_index + 1) % len(navigable_items)
            elif key == pygame.K_LEFT:
                self.pack_focus_index = (self.pack_focus_index - 1) % len(navigable_items)
            elif key == pygame.K_DOWN:
                num_cards = len(self.pack_card_list)
                if self.pack_focus_index < 4 and num_cards > 4:
                    self.pack_focus_index = min(self.pack_focus_index + 4, num_cards - 1)
                elif self.pack_focus_index < num_cards:
                    self.pack_focus_index = num_cards
            elif key == pygame.K_UP:
                num_cards = len(self.pack_card_list)
                if self.pack_focus_index >= num_cards:
                    self.pack_focus_index = num_cards - 1
                elif self.pack_focus_index >= 4:
                    self.pack_focus_index -= 4
            elif key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.pack_focus_index != -1 and self.pack_focus_index < len(navigable_items):
                    focused_item = navigable_items[self.pack_focus_index]
                    
                    if focused_item in self.pack_card_list:
                        if focused_item.is_selected: focused_item.is_selected = False
                        else:
                            num_selected = len([c for c in self.pack_card_list if c.is_selected])
                            if num_selected < 2: focused_item.is_selected = True
                            else: self.message = "Select only 2 cards!"
                    elif focused_item in self.btn_pack_mods:
                        mod_index = self.btn_pack_mods.index(focused_item)
                        self.apply_pack_modifier(mod_index)
                    elif focused_item == self.btn_pack_skip:
                        self.state = GameState.SHOPPING
                        self.pack_card_list.empty()

    def on_update(self, delta_time):
            self.audio_manager.update(delta_time)
            
            # NEW: Update the CRT animation
            self.crt_overlay.update(delta_time)
            
            self.card_list.update(delta_time)
            self.hand_list.update(delta_time) 
            self.joker_list.update(delta_time)
            self.shop_list.update(delta_time) 
            self.animating_cards.update(delta_time) 
            if self.state == GameState.PACK_OPENING:
                self.pack_card_list.update(delta_time)
            
            self.update_game_buttons()

            if self.state == GameState.SHOPPING:
                navigable_buttons = self.shop_buttons + ([self.btn_next_round] if self.btn_next_round else [])
                if navigable_buttons:
                    mouse_hover_index = -1
                    for i, btn in enumerate(navigable_buttons):
                        if btn.rect.collidepoint(self.mouse_x, self.mouse_y):
                            mouse_hover_index = i
                            break
                    
                    for btn in navigable_buttons:
                        btn.is_hovered = False

                    if mouse_hover_index != -1:
                        navigable_buttons[mouse_hover_index].is_hovered = True
                        self.shop_focus_index = mouse_hover_index
                    elif self.shop_focus_index != -1 and self.shop_focus_index < len(navigable_buttons):
                        navigable_buttons[self.shop_focus_index].is_hovered = True

            elif self.state == GameState.PACK_OPENING:
                navigable_items = list(self.pack_card_list) + self.btn_pack_mods + ([self.btn_pack_skip] if self.btn_pack_skip else [])
                if navigable_items:
                    mouse_hover_index = -1
                    for i, item in enumerate(navigable_items):
                        if item.rect.collidepoint(self.mouse_x, self.mouse_y):
                            mouse_hover_index = i
                            break
                    
                    for item in navigable_items:
                        item.is_hovered = False

                    if mouse_hover_index != -1:
                        navigable_items[mouse_hover_index].is_hovered = True
                        self.pack_focus_index = mouse_hover_index
                    elif self.pack_focus_index != -1 and self.pack_focus_index < len(navigable_items):
                        navigable_items[self.pack_focus_index].is_hovered = True



    def draw_game_world(self):
        if self.state in [GameState.MAIN_MENU, GameState.STATS]:
            return
            
        if self.state == GameState.SHOPPING:
            ui_elements.draw_shadows(self.screen, self.shop_list)
            self.shop_list.draw(self.screen)

        elif self.state == GameState.PACK_OPENING:
            ui_elements.draw_shadows(self.screen, self.pack_card_list)
            self.pack_card_list.draw(self.screen)
            for card in self.pack_card_list:
                card.draw_modifier(self.screen)
                if getattr(card, 'is_hovered', False):
                    pygame.draw.rect(self.screen, config.COLOR_GOLD, card.rect.inflate(8, 8), 2, border_radius=10)
                if card.is_selected:
                    pygame.draw.rect(self.screen, config.COLOR_GREEN, card.rect, 4, border_radius=8)

        elif self.state == GameState.GAME_OVER:
            pass 

        else: 
            # Draw the unified playmat background behind the cards
            playmat_color = (45, 105, 75) # Darker green than COLOR_BG
            start_x = (config.SCREEN_WIDTH - (config.MAX_HAND_SIZE * (config.CARD_WIDTH + 20))) / 2 + config.CARD_WIDTH / 2
            total_slots_width = (config.MAX_HAND_SIZE - 1) * (config.CARD_WIDTH + 20) + config.CARD_WIDTH
            pm_x = start_x - config.CARD_WIDTH / 2 - 20
            pm_y = config.HAND_Y - config.CARD_HEIGHT / 2 - 20
            pygame.draw.rect(self.screen, playmat_color, (pm_x, pm_y, total_slots_width + 40, config.CARD_HEIGHT + 40), border_radius=12)

            ui_elements.draw_shadows(self.screen, self.card_list)
            self.card_list.draw(self.screen)
            for card in self.card_list: card.draw_modifier(self.screen)
            
            ui_elements.draw_shadows(self.screen, self.hand_list)
            self.hand_list.draw(self.screen)
            
            for card in self.hand_list:
                card.draw_modifier(self.screen)
                if card.is_selected:
                    pygame.draw.rect(self.screen, config.COLOR_RED, card.rect, 4, border_radius=8)

        ui_elements.draw_shadows(self.screen, self.joker_list)
        self.joker_list.draw(self.screen)
        
        for joker in self.joker_list:
            if joker.is_selected:
                pygame.draw.rect(self.screen, config.COLOR_BTN_SELL, joker.rect, 2)
                
        ui_elements.draw_shadows(self.screen, self.animating_cards)
        self.animating_cards.draw(self.screen)
        for card in self.animating_cards: card.draw_modifier(self.screen)

    def draw_ui(self):
        if self.state == GameState.MAIN_MENU:
            title_surf = ui_elements.FONT_20.render(config.SCREEN_TITLE, True, config.COLOR_WHITE)
            self.screen.blit(title_surf, (config.SCREEN_WIDTH//2 - title_surf.get_width()//2, config.SCREEN_HEIGHT//4))
            self.btn_main_continue.draw(self.screen)
            self.btn_main_new_game.draw(self.screen)
            self.btn_main_stats.draw(self.screen)
            self.volume_control.draw(self.screen)
            return
            
        if self.state == GameState.STATS:
            title_surf = ui_elements.FONT_20.render("STATISTICS", True, config.COLOR_WHITE)
            self.screen.blit(title_surf, (config.SCREEN_WIDTH//2 - title_surf.get_width()//2, config.SCREEN_HEIGHT//4))
            
            stats = self.save_manager.data["stats"]
            stat_surf1 = ui_elements.FONT_16.render(f"Highest Level: {stats['highest_level']}", True, config.COLOR_WHITE)
            stat_surf2 = ui_elements.FONT_16.render(f"Highest Score: {stats['highest_score']}", True, config.COLOR_WHITE)
            stat_surf3 = ui_elements.FONT_16.render(f"Highest Single Hand: {stats['highest_hand_score']}", True, config.COLOR_WHITE)
            
            self.screen.blit(stat_surf1, (config.SCREEN_WIDTH//2 - stat_surf1.get_width()//2, config.SCREEN_HEIGHT//2 - 60))
            self.screen.blit(stat_surf2, (config.SCREEN_WIDTH//2 - stat_surf2.get_width()//2, config.SCREEN_HEIGHT//2 - 30))
            self.screen.blit(stat_surf3, (config.SCREEN_WIDTH//2 - stat_surf3.get_width()//2, config.SCREEN_HEIGHT//2))
            
            sy = config.SCREEN_HEIGHT//2 + 40
            if stats['hands_played']:
                for h_type, count in sorted(stats['hands_played'].items(), key=lambda x: x[1], reverse=True):
                    h_surf = ui_elements.FONT_14.render(f"{h_type}: {count}", True, config.COLOR_GOLD)
                    self.screen.blit(h_surf, (config.SCREEN_WIDTH//2 - h_surf.get_width()//2, sy))
                    sy += 20
            else:
                h_surf = ui_elements.FONT_14.render("No hands played yet.", True, config.COLOR_GOLD)
                self.screen.blit(h_surf, (config.SCREEN_WIDTH//2 - h_surf.get_width()//2, sy))
                
            self.btn_stats_back.draw(self.screen)
            self.volume_control.draw(self.screen)
            return

        pygame.draw.rect(self.screen, config.COLOR_UI_BG, (0, 0, config.SCREEN_WIDTH, 80))
        
        lvl_surf = ui_elements.FONT_16.render(f"Lvl: {self.round_level}", True, config.COLOR_WHITE)
        self.screen.blit(lvl_surf, (20, 30))
        
        target_surf = ui_elements.FONT_20.render(f"Target: {self.score_total} / {self.target_score}", True, config.COLOR_WHITE)
        self.screen.blit(target_surf, (150, 30))
        
        coin_surf = ui_elements.FONT_20.render(f"Coins: ${self.coins}", True, config.COLOR_GOLD)
        self.screen.blit(coin_surf, (config.SCREEN_WIDTH//2 - coin_surf.get_width()//2, 30))

        if self.state != GameState.GAME_OVER:
            hands_surf = ui_elements.FONT_16.render(f"Hands: {self.hands_max - self.hands_played}", True, config.COLOR_WHITE)
            self.screen.blit(hands_surf, (config.SCREEN_WIDTH - 320, 20))
            
            c_disc = config.COLOR_BTN_ACTION if self.discards_left > 0 else config.COLOR_RED
            disc_surf = ui_elements.FONT_16.render(f"Discards: {self.discards_left}", True, c_disc)
            self.screen.blit(disc_surf, (config.SCREEN_WIDTH - 320, 50))
            
        self.volume_control.draw(self.screen)

        if self.state == GameState.SHOPPING:
            msg_surf = ui_elements.FONT_20.render(self.message, True, config.COLOR_WHITE)
            self.screen.blit(msg_surf, (config.SCREEN_WIDTH//2 - msg_surf.get_width()//2, 150))
            for btn in self.shop_buttons: btn.draw(self.screen)
            if self.btn_next_round: self.btn_next_round.draw(self.screen)

        elif self.state == GameState.PACK_OPENING:
            msg_surf = ui_elements.FONT_20.render(self.message, True, config.COLOR_WHITE)
            self.screen.blit(msg_surf, (config.SCREEN_WIDTH//2 - msg_surf.get_width()//2, 120))
            for btn in self.btn_pack_mods: btn.draw(self.screen)
            self.btn_pack_skip.draw(self.screen)

        elif self.state == GameState.GAME_OVER:
            overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0,0))
            
            go_surf = ui_elements.FONT_20.render("GAME OVER", True, config.COLOR_RED)
            
            if self.message == "lose: no cards in the deck":
                fs_surf = ui_elements.FONT_20.render(self.message, True, config.COLOR_WHITE)
            else:
                fs_surf = ui_elements.FONT_20.render(f"Final Score: {self.score_total}", True, config.COLOR_WHITE)
            rs_surf = ui_elements.FONT_16.render("Click to Restart", True, (150, 150, 150))
            
            self.screen.blit(go_surf, (config.SCREEN_WIDTH//2 - go_surf.get_width()//2, config.SCREEN_HEIGHT//2 - 50))
            self.screen.blit(fs_surf, (config.SCREEN_WIDTH//2 - fs_surf.get_width()//2, config.SCREEN_HEIGHT//2))
            self.screen.blit(rs_surf, (config.SCREEN_WIDTH//2 - rs_surf.get_width()//2, config.SCREEN_HEIGHT//2 + 50))

        else: 
            if self.message:
                msg_surf = ui_elements.FONT_16.render(self.message, True, config.COLOR_WHITE)
                self.screen.blit(msg_surf, (config.SCREEN_WIDTH//2 - msg_surf.get_width()//2, config.DRAWN_CARD_Y - 100))
            
            cur_deck, total_deck = self.deck_manager.get_deck_counts()
            deck_surf = ui_elements.FONT_16.render(f"Deck: {cur_deck} / {total_deck}", True, config.COLOR_WHITE)
            self.screen.blit(deck_surf, (config.DRAWN_CARD_X - deck_surf.get_width()//2, config.DRAWN_CARD_Y + 130))

            start_y = config.SCREEN_HEIGHT - 300
            for i, line in enumerate(self.hand_details):
                line_surf = ui_elements.FONT_16.render(line, True, config.COLOR_GOLD)
                self.screen.blit(line_surf, (config.SCREEN_WIDTH - 200, start_y + (i * 25)))

            if self.state != GameState.GAME_OVER:
                pygame.draw.rect(self.screen, config.COLOR_WHITE, (config.DRAWN_CARD_X - config.CARD_WIDTH/2 - 5, config.DRAWN_CARD_Y - config.CARD_HEIGHT/2 - 5, config.CARD_WIDTH + 10, config.CARD_HEIGHT + 10), 2, border_radius=8)
                nc_surf = ui_elements.FONT_12.render("NEW CARD", True, config.COLOR_WHITE)
                self.screen.blit(nc_surf, (config.DRAWN_CARD_X - nc_surf.get_width()//2, config.DRAWN_CARD_Y - 120))

            if self.btn_action: self.btn_action.draw(self.screen)
            if self.btn_score: self.btn_score.draw(self.screen)

        if self.btn_sell.visible: self.btn_sell.draw(self.screen)

        ui_elements.draw_tooltip(self.screen, self.hovered_joker, self.mouse_x, self.mouse_y)

    def on_draw(self):
        self.screen.fill(config.COLOR_BG)
        
        # 1. Draw the game objects and background
        self.draw_game_world()
        
        # 2. Apply the CRT shader to the game world
        self.crt_overlay.draw(self.screen)
        
        # 3. Draw UI elements (Text, Buttons) over everything so they stay crisp
        self.draw_ui()
        
        # 4. Blit the fully rendered off-screen surface to the actual browser canvas
        if self.screen is not self.real_display:
            self.real_display.blit(self.screen, (0, 0))

def main():
    game = WarGame()
    game.setup()
    game.run()

if __name__ == "__main__":
    main()
    pygame.quit()