from PIL import ImageGrab
from rgb_cie import Converter
import time

converter = Converter()


def tup_to_hex(rgb_tuple):
    """ convert an (R, G, B) tuple to #RRGGBB """
    hexcolor = '#%02x%02x%02x' % rgb_tuple

    return hexcolor


def screen_avg():
    """ Grabs screenshot of current window, returns avg RGB of all pixels """
    img = ImageGrab.grab()

    # Grab width and height
    width, height = img.size

    # Make list of all pixels
    pixels = img.load()
    data = []
    for x in range(width):
        for y in range(height):
            cpixel = pixels[x, y]
            data.append(cpixel)

    r = 0
    g = 0
    b = 0
    counter = 0

    # Loop through all pixels
    # If alpha is greater than 200/255 (non-transparent), add it to the average
    for x in range(len(data)):
        try:
            if data[x][3] > 200:
                r += data[x][0]
                g += data[x][1]
                b += data[x][2]
        except IndexError:
            r += data[x][0]
            g += data[x][1]
            b += data[x][2]

        counter += 1

    # Compute average RGB values
    r_avg = r / counter
    g_avg = g / counter
    b_avg = b / counter

    return r_avg, g_avg, b_avg

if __name__ == '__main__':
    while True:
        print 'Firing screen_avg()...'

        screen_color = screen_avg()
        screen_hex = tup_to_hex(screen_color)
        hue_color = converter.rgbToCIE1931(screen_color[0], screen_color[1], screen_color[2])

        print screen_color
        print screen_hex
        print hue_color
        time.sleep(1)