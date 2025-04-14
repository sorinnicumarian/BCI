# virtual_cursor.py

import pyautogui
import time

class VirtualCursor:
    def __init__(self):
        pyautogui.FAILSAFE = False  # Disable fail-safe for easier control

    def move_cursor(self, direction):
        screen_width, screen_height = pyautogui.size()
        current_pos = pyautogui.position()
        
        move_amount = 50  # Pixels to move per step
        
        if direction == 'left':
            new_pos = (current_pos[0] - move_amount, current_pos[1])
        elif direction == 'right':
            new_pos = (current_pos[0] + move_amount, current_pos[1])
        elif direction == 'up':
            new_pos = (current_pos[0], current_pos[1] - move_amount)
        elif direction == 'down':
            new_pos = (current_pos[0], current_pos[1] + move_amount)
        
        # Ensure new position is within screen bounds
        new_pos = (max(0, min(new_pos[0], screen_width-1)),
                   max(0, min(new_pos[1], screen_height-1)))
        
        pyautogui.moveTo(new_pos[0], new_pos[1])
    
    def click(self):
        pyautogui.click()
    
    def backspace(self):
        pyautogui.press('backspace')