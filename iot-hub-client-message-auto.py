from sense_hat import SenseHat

sense = SenseHat()

# Get the temperature from the Sense HAT
temperature = sense.get_temperature()

# Check if the temperature is higher than 30°C
if temperature > 30:
    sense.show_message("HIGH", text_colour=[255, 0, 0])  # Red text for emphasis
else:
    sense.show_message(f"TEMP: {temperature:.1f}C", text_colour=[0, 255, 0])  # Green text for normal temperature
