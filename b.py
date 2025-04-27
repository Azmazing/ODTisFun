#Initial code was created to run 3 servo motors, with a neopixel and wifi service. It was enhanced using Gemini Pro 2.5 to integrate the WiFi services and connect it to HTML. 
# --- MicroPython Code for Card Shuffler/Dealer ---

import machine
import utime
import network
import socket
import neopixel
import urandom 

# --- 2. Configuration ---

# === Hardware Pins (CHANGE THESE!) ===
# Tell the brain which "nerves" connect to which part
NEOPIXEL_PIN = 26  
NUM_NEOPIXELS = 16

MOTOR1_PINS = (17, 5, 18, 19) 
MOTOR3_PINS = (13, 12, 14, 27)
MOTOR2_PINS = (16, 4, 2, 15)

# === Motor Settings ===
# How fast the motors turn (smaller number = faster, but might lose power)
MOTOR_DELAY_MS = 1
STEP_SEQUENCE = [
  [1, 0, 0, 0],
  [1, 1, 0, 0],
  [0, 1, 0, 0],
  [0, 1, 1, 0],
  [0, 0, 1, 0],
  [0, 0, 1, 1],
  [0, 0, 0, 1],
  [1, 0, 0, 1],
]
NUM_STEPS_IN_SEQUENCE = len(STEP_SEQUENCE)

STEPS_PER_CARD_RELEASE = 4000 # Example value, CALIBRATE!
# How many steps should the dealing motor turn to deal ~1 card?
STEPS_PER_CARD_DEAL = 4000    # Example value, CALIBRATE! Very unreliable!
# How many release actions should happen during shuffling?
SHUFFLE_MOVES = 5         # Example value, CALIBRATE! (e.g., 50 moves from each side)

# === Wi-Fi Settings (CHANGE THESE!) ===
WIFI_SSID = "Azmaz"
WIFI_PASSWORD = "password"

num_players = 0
cards_per_player = 0
machine_state = "INIT" 


# === NeoPixel Functions ===
np = neopixel.NeoPixel(machine.Pin(NEOPIXEL_PIN), NUM_NEOPIXELS)

def set_neopixel_color(color):
    """Sets all NeoPixels to the same color."""
    np.fill(color)
    np.write()

def clear_neopixels():
    """Turns all NeoPixels off."""
    set_neopixel_color((0, 0, 0))

def show_status_neopixel(state):
    """Update NeoPixels based on machine state."""
    print("Machine State:", state) # Print state to console for debugging
    if state == "IDLE":
        set_neopixel_color((0, 10, 0)) # Green
    elif state == "WAITING_INPUT":
         set_neopixel_color((0, 0, 10)) # Blue
    elif state == "SHUFFLING":
        set_neopixel_color((10, 5, 0)) # Orange/Yellow
    elif state == "DEALING":
        set_neopixel_color((0, 10, 10)) # Cyan
    elif state == "ERROR":
        set_neopixel_color((20, 0, 0)) # Red
    elif state == "INIT":
         set_neopixel_color((5, 5, 5)) # White
    else:
        clear_neopixels()

# === Basic Stepper Motor Control ===
# This is a simple way to control the ULN2003 steppers
# It remembers the current step position for each motor

motor_step_index = [0, 0, 0] # Current step index for Motor 1, 2, 3

def step_motor(motor_num, steps, direction):
    """
    Turns a specific motor a number of steps in a direction.
    motor_num: 1, 2, or 3
    steps: How many steps to turn
    direction: 1 for forward, -1 for backward
    """
    global motor_step_index
    
    if motor_num == 1:
        pins = [machine.Pin(p, machine.Pin.OUT) for p in MOTOR1_PINS]
    elif motor_num == 2:
        pins = [machine.Pin(p, machine.Pin.OUT) for p in MOTOR2_PINS]
    elif motor_num == 3:
        pins = [machine.Pin(p, machine.Pin.OUT) for p in MOTOR3_PINS]
    else:
        print("Error: Invalid motor number")
        return

    motor_idx = motor_num - 1 # List index is 0-based

    for _ in range(steps):
        # Calculate the next step index in the sequence
        motor_step_index[motor_idx] = (motor_step_index[motor_idx] + direction) % NUM_STEPS_IN_SEQUENCE
        
        # Get the pin pattern for the current step
        step_pattern = STEP_SEQUENCE[motor_step_index[motor_idx]]
        
        # Apply the pattern to the motor pins
        for i in range(len(pins)):
            pins[i].value(step_pattern[i])
            
        # Wait a tiny bit before the next step
        utime.sleep_ms(MOTOR_DELAY_MS)

    # Turn off motor pins to save power and reduce heat (optional)
    for pin in pins:
        pin.value(0)

# === Wi-Fi Connection ===
def connect_wifi():
    """Connects the ESP32 to the Wi-Fi network."""
    global machine_state
    sta_if = network.WLAN(network.STA_IF) # Station mode (connect to router)
    if not sta_if.isconnected():
        print('Connecting to network...')
        sta_if.active(True)
        sta_if.connect(WIFI_SSID, WIFI_PASSWORD)
        # Wait until connected, with a timeout
        max_wait = 10
        while not sta_if.isconnected() and max_wait > 0:
            print('.')
            max_wait -= 1
            utime.sleep(1)
            
    if sta_if.isconnected():
        print('Network config:', sta_if.ifconfig())
        return sta_if.ifconfig()[0] # Return IP address
    else:
        print('WiFi connection failed')
        machine_state = "ERROR"
        show_status_neopixel(machine_state)
        return None

# --- 5. Machine Logic Functions ---

def perform_shuffle():
    """Runs the shuffling sequence."""
    global machine_state
    machine_state = "SHUFFLING"
    show_status_neopixel(machine_state)
    print("Starting shuffle...")

    # Alternate between motor 1 and motor 2 randomly
    motor_choice = 1
    for i in range(SHUFFLE_MOVES):
        # Randomly choose which motor moves next (slightly biased to alternate)
        if urandom.randint(1, 10) > 3: # More likely to switch
            motor_choice = 3 - motor_choice # Switch between 1 and 2
        
        print(f"Shuffle move {i+1}/{SHUFFLE_MOVES}, Motor {motor_choice}")
        step_motor(motor_choice, STEPS_PER_CARD_RELEASE, 1) # Move forward
        utime.sleep_ms(50) # Small pause between moves

    print("Shuffle finished.")
    # Turn off motor pins just in case
    step_motor(1, 0, 1) 
    step_motor(2, 0, 1)


def deal_one_card():
    """Attempts to deal one card using Motor 3 (timed method)."""
    # !! This function's reliability depends heavily on CALIBRATION !!
    print("Dealing one card...")
    step_motor(3, STEPS_PER_CARD_DEAL, 1) # Move motor 3 forward
    utime.sleep_ms(100) # Small pause after dealing one card
    # Turn off motor pins
    step_motor(3, 0, 1)
    
def perform_deal():
    """Deals the specified number of cards to the players."""
    global machine_state, num_players, cards_per_player
    
    if num_players <= 0 or cards_per_player <= 0:
        print("Error: Invalid number of players or cards.")
        machine_state = "ERROR"
        show_status_neopixel(machine_state)
        utime.sleep(2)
        machine_state = "IDLE" # Return to IDLE after showing error
        show_status_neopixel(machine_state)
        return

    machine_state = "DEALING"
    show_status_neopixel(machine_state)
    print(f"Starting deal: {num_players} players, {cards_per_player} cards each.")

    total_cards_to_deal = num_players * cards_per_player
    
    for i in range(total_cards_to_deal):
        print(f"Dealing card {i+1}/{total_cards_to_deal}...")
        deal_one_card()
        # Add a small delay, maybe longer between "players"
        if (i + 1) % cards_per_player == 0:
            print("--- End of player's hand ---")
            utime.sleep_ms(1000) # Longer pause between players
        else:
             utime.sleep_ms(100) # Shorter pause between cards for same player
    print("Dealing finished.")
    machine_state = "IDLE" # Go back to idle when done
    show_status_neopixel(machine_state)


# --- 6. Web Server Setup ---
# This part creates the little web page on the ESP32

def start_web_server(ip):
    """Starts the simple web server."""
    # HTML for the web page
    html_page = """<!DOCTYPE html>
    <html>
    <head><title>Card Machine Control</title></head>
    <body>
      <h1>Card Shuffler & Dealer Control</h1>
      <form action="/setdeal">
        <label for="players">Number of Players:</label>
        <input type="number" id="players" name="players" min="1" value="{players_val}" required><br><br>
        <label for="cards">Cards per Player:</label>
        <input type="number" id="cards" name="cards" min="1" value="{cards_val}" required><br><br>
        <input type="submit" value="Set and Start">
      </form>
      <br>
      <p>Players set: {players_val}, Cards per player: {cards_val}</p>
    </body>
    </html>
    """

    # Open a "listening post" (socket) on the ESP32's IP address, port 80 (standard web)
    addr = socket.getaddrinfo(ip, 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow reusing address quickly
    s.bind(addr)
    s.listen(1) # Listen for 1 connection at a time
    print('Web server listening on', addr)

    # Main loop to handle incoming connections
    while True:
        try:
            conn, addr = s.accept() # Wait for someone to connect
            print('Got a connection from %s' % str(addr))
            request = conn.recv(1024) # Receive the browser's request (up to 1024 bytes)
            request = str(request)
            print('Content = %s' % request)

            # Check if the request includes "/setdeal?" which means the form was submitted
            setdeal_pos = request.find('/setdeal?')
            if setdeal_pos != -1:
                # Find the part of the request with the parameters
                params_str = request[setdeal_pos + len('/setdeal?'):request.find(' HTTP/')]
                params = params_str.split('&')
                temp_players = 0
                temp_cards = 0
                # Extract the values
                for param in params:
                    if param.startswith('players='):
                        temp_players = int(param.split('=')[1])
                    elif param.startswith('cards='):
                        temp_cards = int(param.split('=')[1])
                
                # Update global variables IF the machine is idle
                global num_players, cards_per_player, machine_state
                if machine_state == "IDLE" or machine_state == "WAITING_INPUT":
                     num_players = temp_players
                     cards_per_player = temp_cards
                     print(f"Received: Players={num_players}, Cards={cards_per_player}")
                     # --- Trigger Actions ---
                     perform_shuffle() # Shuffle first
                     perform_deal()    # Then deal
                     # Machine state is set to IDLE inside perform_deal() when finished
                else:
                    print("Machine busy, cannot start new task now.")


            # Send the HTML page back to the browser
            current_html = html_page.format(
                status=machine_state, 
                players_val=num_players, 
                cards_val=cards_per_player
            )
            conn.send('HTTP/1.1 200 OK\n')
            conn.send('Content-Type: text/html\n')
            conn.send('Connection: close\n\n')
            conn.sendall(current_html)
            conn.close() # Close the connection
            
        except OSError as e:
            conn.close()
            print('Connection closed due to OS Error:', e)
        except Exception as e:
             print("An error occurred in web server loop:", e)
             # Maybe try to close connection if it exists
             try: 
                 conn.close()
             except:
                 pass


# --- 7. Main Execution ---

# Turn off NeoPixels initially
clear_neopixels()
machine_state = "INIT"
show_status_neopixel(machine_state)

# Connect to Wi-Fi
ip_address = connect_wifi()

if ip_address:
    machine_state = "IDLE" # Ready for input via web page
    show_status_neopixel(machine_state)
    # Start the web server (this function runs forever)
    start_web_server(ip_address)
else:
    # Error state is set in connect_wifi()
    print("Could not connect to Wi-Fi. Halting.")
    # Loop forever showing error
    while True:
        show_status_neopixel("ERROR")
        utime.sleep(1)
        clear_neopixels()
        utime.sleep(1)
