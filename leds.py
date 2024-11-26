import time
from sense_hat import SenseHat

# Inicializar Sense HAT
sense = SenseHat()

# Colores
black = [0, 0, 0]
red = [255, 0, 0]
pink = [200, 85, 160]
white = [255, 255, 255]

# MAP JOYSTICK INPUT TO WINE TYPE
WINE_SELECTION = {
    "up": "Red Wine",
    "down": "White Wine",
    "right": "Rosé Wine",
}

# Patrones base para ondas
corchea_wave = [0, 1, 2, 3, 2, 1, 0, 0]
semicorchea_wave = [0, 1, 1, 2, 1, 1, 0, 0]
blanca_wave = [0, 2, 4, 6, 4, 2, 0, 0]

# Función para generar una matriz de onda
def generate_wave_matrix(wave_pattern, color):
    matrix = [[black for _ in range(8)] for _ in range(8)]
    for x in range(8):
        amplitude = wave_pattern[x]
        for y in range(7, 7 - amplitude, -1):
            matrix[y][x] = color
    return matrix

# Desplazar la onda hacia la izquierda
def shift_wave_left(wave_pattern):
    return wave_pattern[1:] + [wave_pattern[0]]

# Mostrar onda en el Sense HAT
def display_wave(wave_pattern, color):
    wave_matrix = generate_wave_matrix(wave_pattern, color)
    flattened_matrix = [pixel for row in wave_matrix for pixel in row]
    sense.set_pixels(flattened_matrix)

# Animar la onda en la matriz
def animate_wave(wave_pattern, color, duration=3):
    start_time = time.time()
    while time.time() - start_time < duration:
        display_wave(wave_pattern, color)
        wave_pattern = shift_wave_left(wave_pattern)
        time.sleep(0.2)

# Controlador principal
try:
    while True:
        print("Esperando selección del joystick...")
        events = sense.stick.get_events()
        for event in events:
            if event.action == "pressed":
                if event.direction in WINE_SELECTION:
                    wine = WINE_SELECTION[event.direction]
                    print(f"Seleccionado: {wine}")

                    if wine == "Red Wine":
                        animate_wave(corchea_wave, red)
                    elif wine == "Rosé Wine":
                        animate_wave(semicorchea_wave, pink)
                    elif wine == "White Wine":
                        animate_wave(blanca_wave, white)
                else:
                    print("Joystick movido en una dirección no configurada.")
except KeyboardInterrupt:
    sense.clear()
    print("Programa detenido.")
