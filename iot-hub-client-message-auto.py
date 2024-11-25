from sense_hat import SenseHat
import time

# Initialize the Sense HAT
sense = SenseHat()


# Function to display "Hello" on the LED matrix
def display_hello():
    sense.show_message(
        "HIGH TEMPERATURE", text_colour=(255, 255, 0), back_colour=(0, 0, 0)
    )  # Yellow text on black background


# Main loop to check the temperature and display the message
while True:
    # Get the current temperature from the Sense HAT
    temperature = sense.get_temperature()

    # Check if the temperature is higher than 30°C
    if temperature > 30:
        display_hello()  # Display "Hello" if the temperature is higher than 30°C
    else:
        sense.clear()  # Clear the LED matrix if the temperature is not higher than 30°C

    # Wait for a while before checking again
    time.sleep(5)  # Check every 5 seconds
