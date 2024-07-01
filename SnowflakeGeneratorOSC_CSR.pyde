# SnowflakeGeneratorOSC-CSR.py
#
# Author:   Collins Ramsey
#
# Purpose: A remade program of Snowflake Generator by Lingdong Huang
# that has been translated from Java to Python. The output is of a 
# randomly generated snowflake and the color is controlled by TouchOSC.

# import osc library
add_library('oscP5')
from osc import OscIn, OscMessage

# important variables
symmetryParts    = 12   # number of symmetric parts, can be 2, 4, 6...
numberIterations = 2    # number of iterations each time the screen updates
maxFrames        = 500  # stopping number before too many iterations
petalSweep       = 1.0  # size of each petal between 0.0 and 1.0

# create the symmetric points on the screen
def symmetryPoints(v):
    
    # need a set size of a list made of empty PVectors
    points = [0] * symmetryParts
    
    # make it a whole snowflake
    points[0] = v
    points[1] = PVector(v.x, -v.y)
    
    # rotates the snowflake to be full
    for i in range(0, (symmetryParts / 2) - 1):
        
        # rotates the even iterations
        points[2 + i * 2] = points[i * 2].copy().rotate(PI * 4 / symmetryParts)
        
        # rotates the odd iterations
        points[2 + i * 2 + 1] = points[i * 2 + 1].copy().rotate(PI * 4 / symmetryParts)
        
    return points

# return true if point is out of bounds
def outOfBounds(x, y):
    return ((x < 0) or (x >= width) or (y < 0) or (y >= height))

# create body of snowflake
def iteration():
    
    # variables used for every iteration
    angleRange = PI / symmetryParts * 2   # spread/fan width of each snowflake arm
    angleMin   = (1 - petalSweep) / 2     # minimum of spread
    angleMax   = angleMin + petalSweep    # maximum of spread
    
    # variables used to calculate x and y which are coordinates of each pixel
    a = random(angleMin * angleRange, angleMax * angleRange)
    d = random(min(width / 2, height / 2))
    
    x = int((cos(a) * d) + width / 2)
    y = int((sin(a) * d) + height / 2)
    
    # here we plan out where to plot the points
    done = False
    while (not done):
        
        # make sure no points are out of bounds
        if (outOfBounds(x, y)):
            done = True
        
        # a "neighborhood" is made and neighbors are connected
        neighbors = [
                     [x - 1, y - 1], [x, y - 1], [x + 1, y - 1],
                     [x - 1, y],                 [x + 1, y],
                     [x - 1, y + 1], [x, y - 1], [x + 1, y + 1]]
        
        # check if a neighbor is "nextdoor" so they can connect
        for i in range(0, len(neighbors)):
            quantityX = neighbors[i][0]
            quantityY = neighbors[i][1]
            
            # if not outOfBounds and within a certain index then it is 
            # considered a neighbor
            if (not outOfBounds(quantityX, quantityY) and 
                    mapScreen[quantityY * width + quantityX]):
                v = PVector(x - width / 2, y - height / 2)
                
                # show the symmetric points as well
                # or waking up all neighbors on the street
                global points2
                points2 = symmetryPoints(v)
                for j in range(0, len(points2)):
                    pointX = int(points2[j].x + width / 2)
                    pointY = int(points2[j].y + height / 2)
                    if (not outOfBounds(pointX, pointY)):
                        mapScreen[pointY * width + pointX] = True
                        
                done = True
        
        # a flake pattern is chosen
        direction = int(random(8))
        if (direction == 0):
            x -= 1                 # create point to the left
        elif (direction == 1):
            x += 1                 # create point to the right 
        elif (direction == 2):
            y -= 1                 # create point down
        elif (direction == 3):
            y += 1                 # create point up
        elif (direction == 4):
            x -= 1                 # create point down left
            y -= 1
        elif (direction == 5):
            x += 1                 # create point down right
            y -= 1
        elif (direction == 6):
            x -= 1                 # create point up left
            y += 1
        elif (direction == 7):
            x += 1                 # create point up right
            y += 1
            
def setup():
    
    size(300, 300)
    
    # each color hue gets initialized
    global setColorR
    global setColorG
    global setColorB
    
    setColorR = 255
    setColorG = 255
    setColorB = 255
    
    # osc is listening for messages
    global oscInput
    oscInput = OscIn(57112)
    
    # holds all points
    global mapScreen
    mapScreen = [False] * (height * width)
    
    # probability loop, changes look of snowflake
    # change the 1 in random for a wider/tigher spread
    for i in range(width / 2 + width / 8, width - width / 16):
        if (random(1) < 0.25):
            mapScreen[height / 2 * width + i] = True
            
# changes the red hue of snowflake
def colorChangeR(message):
    global setColorR
    args = message.getArguments()
    value = args[0][0]
    setColorR = int(map(value, 0.0, 1.0, 0, 255))
    
# changes the green hue of snowflake
def colorChangeG(message):
    global setColorG
    args = message.getArguments()
    value = args[0][0]
    setColorG = int(map(value, 0.0, 1.0, 0, 255))
    
# changes the blue hue of snowflake
def colorChangeB(message):
    global setColorB
    args = message.getArguments()
    value = args[0][0]
    setColorB = int(map(value, 0.0, 1.0, 0, 255))
    
def draw():
    
    # on input, change color Red, Green, or Blue.
    # use the simple layout on TouchOsc and touch the first three
    # veritcal sliders, 1 for red, 2 for green, and 3 for blue
    oscInput.onInput("/1/fader1", colorChangeR)
    oscInput.onInput("/1/fader2", colorChangeG)
    oscInput.onInput("/1/fader3", colorChangeB)
    
    # let the snowflake commence!
    for i in range(0, numberIterations):
        iteration()
        
    # update canvas
    loadPixels()
    
    # choose black for bg and setColors for snowflake
    for i in range(0, len(pixels)):
        if (mapScreen[i]):
            pixels[i] = color(setColorR, setColorG, setColorB)
        else:
            pixels[i] = color(0, 0, 0)
            
    updatePixels()
    
    # dont go above the max frames
    if (frameCount > maxFrames):
        noLoop()
