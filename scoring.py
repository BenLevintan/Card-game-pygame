import random
from collections import Counter

def get_hand_type(hand_list):
    """
    Analyzes the played cards and returns the best Poker Hand type info.
    Returns: hand_type_string
    """
    if not hand_list:
        return "Empty"

    # Basic Data
    ranks = [c.value for c in hand_list]
    suits = [c.suit for c in hand_list]
    
    # Counts (e.g., [3, 2] for Full House, [2, 2, 1] for Two Pair)
    rank_counts = Counter(ranks).values()
    sorted_counts = sorted(rank_counts, reverse=True)
    
    # Flush Check (5 cards minimum)
    is_flush = False
    if len(suits) >= 5:
        suit_counts = Counter(suits).values()
        if 5 in suit_counts:
            is_flush = True

    # Straight Check (5 cards minimum)
    is_straight = False
    if len(ranks) >= 5:
        unique_ranks = sorted(list(set(ranks)))
        # Check for 5 consecutive numbers
        if len(unique_ranks) >= 5:
            for i in range(len(unique_ranks) - 4):
                window = unique_ranks[i:i+5]
                if window[-1] - window[0] == 4:
                    is_straight = True
                    break
            # Ace Low Check (14, 2, 3, 4, 5) -> {2,3,4,5,14}
            if {14, 2, 3, 4, 5}.issubset(set(unique_ranks)):
                is_straight = True

    # --- DETERMINE HAND TYPE ---
    if is_straight and is_flush: return "Straight Flush"
    if 4 in sorted_counts: return "4 of a Kind"
    if sorted_counts == [3, 2]: return "Full House"
    if is_flush: return "Flush"
    if is_straight: return "Straight"
    if 3 in sorted_counts: return "3 of a Kind"
    if sorted_counts[:2] == [2, 2]: return "Two Pair"
    if 2 in sorted_counts: return "Pair"
    
    return "High Card"

# --- UPDATED: Added current_coins to arguments ---
def calculate_hand_score(hand_list, joker_list, run_discards, cards_in_deck, current_coins):
    if not hand_list: 
        return 0, 1, [], 0

    base_sum = sum(c.value for c in hand_list)
    additive_mult = 1
    final_multiplier = 1
    coin_bonus = 0 
    bonus_points = 0
    breakdown = []

    # 1. Identify Hand Type
    hand_type = get_hand_type(hand_list)
    
    # 2. Apply Base Scoring for Hand Type
    if hand_type == "Straight Flush":
        base_sum += 100; additive_mult += 8; breakdown.append("StrFlush")
    elif hand_type == "4 of a Kind":
        base_sum += 60; additive_mult += 7; breakdown.append("4-Kind")
    elif hand_type == "Full House":
        base_sum += 40; additive_mult += 4; breakdown.append("FullHouse")
    elif hand_type == "Flush":
        base_sum += 35; additive_mult += 4; breakdown.append("Flush")
    elif hand_type == "Straight":
        base_sum += 30; additive_mult += 4; breakdown.append("Straight")
    elif hand_type == "3 of a Kind":
        base_sum += 30; additive_mult += 3; breakdown.append("3-Kind")
    elif hand_type == "Two Pair":
        base_sum += 20; additive_mult += 2; breakdown.append("TwoPair")
    elif hand_type == "Pair":
        base_sum += 10; additive_mult += 2; breakdown.append("Pair")
    else:
        base_sum += 5; additive_mult += 1

    # 3. Card Modifiers
    for card in hand_list:
        if card.modifier == "bonus_chips":
            bonus_points += 10
            breakdown.append("Bonus(+10)")
        elif card.modifier == "mult_plus":
            additive_mult += 4
            breakdown.append("Mult(+4)")

    # 4. Joker Effects
    for joker in joker_list:
        
        # --- HAND TYPE TRIGGERS ---
        if joker.key == "pear_up" and hand_type in ("Pair", "Two Pair", "Full House" ,"3 of a Kind", "4 of a Kind"):
            additive_mult += 8
            breakdown.append("Pear(+8)")
            
        if joker.key == "triple_treat" and hand_type in ["3 of a Kind", "Full House", "4 of a Kind"]:
            additive_mult += 12
            breakdown.append("TripTrt(+12)")
            
        if joker.key == "double_trouble" and hand_type in ("Two Pair", "Full House"):
            final_multiplier *= 2
            breakdown.append("DblTrbl(x2)")

        # --- SPECIAL LOGIC ---
        if joker.key == "rainbow_trout":
            unique_suits = set(c.suit for c in hand_list)
            if len(unique_suits) == 4:
                final_multiplier *= 2
                breakdown.append("Trout(x2)")

        if joker.key == "national_reserve":
            if cards_in_deck > 0:
                bonus = cards_in_deck * 10
                bonus_points += bonus
                breakdown.append(f"Reserve(+{bonus})")

        if joker.key == "multi_python":
            sorted_ranks = sorted(list(set(c.value for c in hand_list)))
            has_3_straight = False
            consecutive = 0
            for i in range(len(sorted_ranks) - 1):
                if sorted_ranks[i+1] == sorted_ranks[i] + 1:
                    consecutive += 1
                    if consecutive >= 2: has_3_straight = True
                else: consecutive = 0
            if {14, 2, 3}.issubset(set(sorted_ranks)): has_3_straight = True
            
            if has_3_straight:
                final_multiplier *= 2
                breakdown.append("Python(x2)")

        # --- CONDITION TRIGGERS ---
        if joker.key == "inflation" and len(hand_list) <= 4:
            additive_mult += 12
            breakdown.append("Inflation(+12)")
            
        # NEW: Petty Cash (+$3 Chips per $1)
        if joker.key == "petty_cash":
            if current_coins > 0:
                bonus = current_coins * 3
                bonus_points += bonus
                breakdown.append(f"Petty(+{bonus})")
                
        # NEW: Capital Gains (x1 mult per $10)
        if joker.key == "capital_gains":
            mult_factor = current_coins // 10
            if mult_factor > 1: # Values of 0 and 1 don't change the multiplier mathematically
                final_multiplier *= mult_factor
                breakdown.append(f"Gains(x{mult_factor})")

        # --- CARD PROPERTY TRIGGERS ---
        if joker.key == "diamond_geezer":
            count = sum(1 for c in hand_list if c.suit == "Diamonds")
            if count > 0:
                bonus = count * 4
                additive_mult += bonus
                breakdown.append(f"Geezer(+{bonus})")
                
        if joker.key == "club_sandwich":
            count = sum(1 for c in hand_list if c.suit == "Clubs")
            if count > 0:
                bonus = count * 20
                bonus_points += bonus
                breakdown.append(f"Club(+{bonus})")
                
        if joker.key == "face_value":
            count = sum(1 for c in hand_list if c.value in [11, 12, 13])
            if count > 0:
                bonus = count * 4
                additive_mult += bonus
                breakdown.append(f"FaceVal(+{bonus})")
        
        if joker.key == "odd_todd":
            count = sum(1 for c in hand_list if c.value in [14, 3, 5, 7, 9])
            if count > 0:
                bonus = count * 30
                bonus_points += bonus
                breakdown.append(f"OddTodd(+{bonus})")
                
        if joker.key == "wishing_well":
            count = sum(1 for c in hand_list if c.value in [14, 2, 3])
            if count > 0:
                coin_bonus += count
                breakdown.append(f"Wish(+${count})")

        # --- STATE TRIGGERS ---
        if joker.key == "waste_management":
            wm_bonus = run_discards // 3
            if wm_bonus > 0:
                additive_mult += wm_bonus
                breakdown.append(f"Waste(+{wm_bonus})")
                
        if joker.key == "the_regular":
            additive_mult += 4
            breakdown.append("Regular(+4)")
            
        if joker.key == "potato_chip":
            bonus_points += 50
            breakdown.append("Potato(+50)")

    total_mult = additive_mult * final_multiplier
    total_base = base_sum + bonus_points
    
    return total_base, total_mult, breakdown, coin_bonus