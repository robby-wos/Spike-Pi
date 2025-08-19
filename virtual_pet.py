    

import pygame
import os
import random
import time
from datetime import datetime, timedelta

pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((600, 400))
pygame.display.set_caption("Spike the SDR")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 14)

# Constants
DECAY_TO_ZERO_SECONDS = 3 * 24 * 60 * 60  # 3 days
FRAMES_PER_SECOND = 30
HUNGER_DECAY_PER_FRAME = 100 / (DECAY_TO_ZERO_SECONDS * FRAMES_PER_SECOND)

def load_animation_frames(folder_path):
    return [pygame.image.load(os.path.join(folder_path, f)).convert_alpha()
            for f in sorted(os.listdir(folder_path)) if f.endswith(".png")]

# Load animations
background_frames = load_animation_frames("background_frames")
idle_frames = load_animation_frames("pet_idle_frames")
feed_frames = load_animation_frames("pet_feed_frames")
sleeping_frames = load_animation_frames("pet_sleeping_frames")
falling_asleep_frames = load_animation_frames("pet_falling_asleep_frames")

# Load sounds
feed_sound = pygame.mixer.Sound("sounds/feed.wav")
sleep_sound = pygame.mixer.Sound("sounds/sleep.wav")
wake_sound = pygame.mixer.Sound("sounds/wake.wav")
mail_sound = pygame.mixer.Sound("sounds/mail.wav")

# States
health = 100
hunger = 100
meetings_booked = 0
last_meeting_date = datetime.now().date()
today_date = datetime.now().date()
feed_cooldown = 5
last_feed_time = 0

status_modes = ["Cold Calling", "Prospecting", "Reporting", "Beasting", "Crying", "Getting Yelled At",]
status_index = 0
last_status_change = time.time()
status_change_interval = 1800  # 30 minutes

# Tips
tips = [
    "COFFEES FOR CLOSERS",
    "Worst thing, you get an extra dollar.",
    "Help me",
    "Jack... nevermind",
    "Smile and dial",
    "Thank you for keeping me alive",
    "I <3 Echo Bunny Man",
    "Mr. Brightside",
    "GET BACK TO WORK SOLDIER",
    "Send another email, that'll help",
    "1 calendar invite and a dream",
    "Hang up on them instead",
    "Lets get that chedda",
    "Dont celebrate in the parking lot",
    "CAH A CAR AND A DEEA",
    "ABT",
    "Once you get the yes get out",
    "Never wear yout bag on your right arm",
    "Pete Knows Best",
    "NO SNEAKERS",
    "ECHO BRAVO MIKE",
    "JIMMY... watch that jargon mouth.",
    "Permission based email",
    ""
    
]
speech_override = None
speech_timer = 0
speech_duration = 3000
tips_sent_today = 0
max_daily_tips = random.randint(2, 3)
daily_tip_times = []
mail_flag = False


# Combo tracking
combo_counter = 0
last_combo_time = 0
combo_timeout = 5

# Animation frame trackers
current_frame = 0
frame_direction = 1
bg_frame_index = 0
bg_frame_timer = 0
bg_frame_delay = 5

# Action states
action_state = None  # 'feeding', 'sleeping', 'falling_asleep'
action_start_time = 0
action_duration = {
    "feeding": 5000,
    "falling_asleep": 1000,
    "sleeping": 5000
}

running = True
while running:
    now = datetime.now()

    # Daily reset
    if now.date() != today_date:
        today_date = now.date()
        if today_date.weekday() <= 3:
            meetings_booked = 0
            tips_sent_today = 0
            max_daily_tips = random.randint(2, 3)
            daily_tip_times = sorted([
                datetime.combine(today_date, datetime.strptime(f"{random.randint(8, 14)}:{random.randint(30, 59)}", "%H:%M").time())
                for _ in range(max_daily_tips)
            ])

    current_time_str = now.strftime("%H:%M")

    # Auto wake
    if current_time_str == "08:30" and action_state == "sleeping":
        wake_sound.play()
        action_state = None
        speech_override = "Time to rise and book some meetings!"
        speech_timer = pygame.time.get_ticks()

    # Auto sleep
    if current_time_str == "15:45" and action_state not in ["sleeping", "falling_asleep"]:
        sleep_sound.play()
        action_state = "falling_asleep"
        action_start_time = pygame.time.get_ticks()

    # Status update every 30 min
    if today_date.weekday() <= 3 and time.time() - last_status_change >= status_change_interval:
        status_index = (status_index + 1) % len(status_modes)
        last_status_change = time.time()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f and time.time() - last_feed_time > feed_cooldown:
                feed_sound.play()
                last_feed_time = time.time()
                meetings_booked += 1
                last_meeting_date = today_date
                if time.time() - last_combo_time < combo_timeout:
                    combo_counter += 1
                else:
                    combo_counter = 1
                last_combo_time = time.time()
                action_state = "feeding"
                action_start_time = pygame.time.get_ticks()
            elif event.key == pygame.K_s:
                if action_state != "sleeping":
                    sleep_sound.play()
                    action_state = "falling_asleep"
                    action_start_time = pygame.time.get_ticks()
            elif event.key == pygame.K_z:
                sleep_sound.play()
                action_state = "sleeping"
                action_start_time = pygame.time.get_ticks()
            elif event.key == pygame.K_w:
                wake_sound.play()
                action_state = None
            elif event.key == pygame.K_t:
                speech_override = random.choice(tips)
                speech_timer = pygame.time.get_ticks()
                mail_flag = False

      # Speech timeout
    if speech_override and pygame.time.get_ticks() - speech_timer > speech_duration:
        speech_override = None

    # Deliver tips if scheduled
    if today_date.weekday() <= 3:
        if tips_sent_today < max_daily_tips and len(daily_tip_times) > tips_sent_today:
            if now >= daily_tip_times[tips_sent_today] and action_state not in ["sleeping", "falling_asleep"]:
                mail_sound.play()
                speech_override = random.choice(tips)
                speech_timer = pygame.time.get_ticks()
                mail_flag = True
                tips_sent_today += 1

    screen.blit(pygame.transform.scale(background_frames[bg_frame_index], (600, 400)), (0, 0))

    # Handle action animations
    if action_state == "feeding":
        elapsed = pygame.time.get_ticks() - action_start_time
        frame_index = int((elapsed / action_duration["feeding"]) * len(feed_frames))
        if frame_index < len(feed_frames):
            feed_frame_scaled = pygame.transform.scale(feed_frames[frame_index], (250, 250))
            feed_rect = feed_frame_scaled.get_rect(center=(300, 220))
            screen.blit(feed_frame_scaled, feed_rect)
        else:
            hunger = min(100, hunger + 10)
            action_state = None
            mail_flag = True

    elif action_state == "falling_asleep":
        elapsed = pygame.time.get_ticks() - action_start_time
        frame_index = int((elapsed / action_duration["falling_asleep"]) * len(falling_asleep_frames))
        if frame_index < len(falling_asleep_frames):
            fa_frame_scaled = pygame.transform.scale(falling_asleep_frames[frame_index], (250, 250))
            fa_rect = fa_frame_scaled.get_rect(center=(300, 220))
            screen.blit(fa_frame_scaled, fa_rect)
        else:
            action_state = "sleeping"
            action_start_time = pygame.time.get_ticks()

    elif action_state == "sleeping":
        elapsed = pygame.time.get_ticks() - action_start_time
        frame_index = int((elapsed / 300) % len(sleeping_frames))
        sleep_frame_scaled = pygame.transform.scale(sleeping_frames[frame_index], (250, 250))
        sleep_rect = sleep_frame_scaled.get_rect(center=(300, 220))
        screen.blit(sleep_frame_scaled, sleep_rect)
    else:
        # Idle pet animation
        current_frame += frame_direction
        if current_frame >= len(idle_frames) - 1 or current_frame <= 0:
         frame_direction *= -1   
        bg_frame_timer += 1
        if bg_frame_timer >= bg_frame_delay:
            bg_frame_index = (bg_frame_index + 1) % len(background_frames)
            bg_frame_timer = 0

        frame_scaled = pygame.transform.scale(idle_frames[current_frame], (250, 250))
        pet_rect = frame_scaled.get_rect(center=(300, 220))
        screen.blit(frame_scaled, pet_rect)

        # Hunger decay (only while idle on weekdays)
        if today_date.weekday() <= 3:
            hunger = max(0, hunger - HUNGER_DECAY_PER_FRAME)




    # HUD Elements
    pygame.draw.rect(screen, (0, 0, 0), (10, 10, 180, 80), border_radius=8)
    pygame.draw.rect(screen, (255, 255, 255), (10, 10, 180, 80), 2, border_radius=8)

    pygame.draw.rect(screen, (255, 0, 0), (20, 25, 100, 10))  # Health bar bg
    pygame.draw.rect(screen, (0, 255, 0), (20, 25, health, 10))  # Health value

    pygame.draw.rect(screen, (50, 50, 50), (20, 45, 100, 10))  # Hunger bar bg
    pygame.draw.rect(screen, (255, 165, 0), (20, 45, hunger, 10))  # Hunger value

    screen.blit(font.render("Health", True, (255, 255, 255)), (130, 22))
    screen.blit(font.render("Hunger", True, (255, 255, 255)), (130, 42))

    mood = "Dominating" if hunger > 80 else "Chill" if hunger > 50 else "Meh" if hunger > 30 else "Send help"
    screen.blit(font.render(f"Mood: {mood}", True, (255, 255, 255)), (20, 65))

    screen.blit(font.render(f"Meetings: {meetings_booked}", True, (255, 255, 255)), (400, 20))
    screen.blit(font.render(f"Status: {status_modes[status_index]}", True, (255, 255, 255)), (400, 40))

    if combo_counter > 1:
        screen.blit(font.render(f"Combo x{combo_counter}!", True, (255, 200, 0)), (400, 60))

    if mail_flag:
        screen.blit(font.render("New Tip!", True, (255, 255, 0)), (250, 10))

    now_time = datetime.now().strftime("%H:%M:%S")
    screen.blit(font.render(now_time, True, (255, 255, 255)), (500, 380))

    # Speech bubble
    if speech_override:
        text = font.render(speech_override, True, (20, 20, 20))
        bubble = pygame.Surface((text.get_width() + 20, 40), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (235, 230, 210, 240), bubble.get_rect(), border_radius=6)
        pygame.draw.rect(bubble, (70, 40, 20), bubble.get_rect(), 2, border_radius=6)
        bubble.blit(text, (10, 10))
        screen.blit(bubble, (300 - bubble.get_width() // 2, 100))

    pygame.display.update()
    clock.tick(FRAMES_PER_SECOND)

pygame.quit()








