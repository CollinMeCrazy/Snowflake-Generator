################################################################################################################
# osc.py       Version 1.74     27-Mar-2023     Taj Ballinger, David Johnson, and Bill Manaris

###########################################################################
#
# This library is made for Python Mode for Processing 3.x
# Based on the OSC library for JythonMusic by David Johnson and Bill Manaris
# This library allows a user in Processing to use Open Sound Control protocol
# using identical methods to those found in its sister JythonMusic library.
#
# Copyright (C) 2014-2023 Taj Ballinger, David Johnson, and Bill Manaris
#
#    Jython Music is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Jython Music is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Jython Music.  If not, see <http://www.gnu.org/licenses/>.
#
###########################################################################

#
# This module provides functionality for OSC communication between programs and OSC devices.
# To use this module, add it to
#     ' /Processing/libraries/site-packages '
# And import it in your Processing code with
#     ' from oscv1_74 import OscIn, OscMessage '
#
#
# REVISIONS:
#
#   1.74    27-Mar-2023 (tb) Added dispose() to close OscObjects between program runs, as in 1.2
#                       Known issues:
#                          -OscEvent uses an equivalence conditional that doesn't recognize regular expressions.
#                             Incoming messages must match their corresponding listener's functions EXACTLY,
#                             but this disables the default ALL_MESSAGES listener that's used to find incoming message addresses.
#                          -OscMessage's getArguments() seems to return an array of lists. It should just return the list.
#                          -OscIn prints an error on subsequent program runs using the same port #, but is otherwise functional. Watch this.
#
#   1.73    26-Mar-2023 (tb) Switched up OscIn implementation again.
#                       As noted in 1.72, LinkedListener is now ProcessingListener.
#                       ProcessingListener stores the desired oscAddress and checks before
#                       calling its registered functions.
#                       TODO: 
#                          1) Update ProcessingListener's check to allow regular expressions.
#                          2) Double check ProcessingListener's oscEvent unpacking. It should be returning a simple list of arguments.
#
#   1.72    26-Mar-2023 (tb) Overhauled OscIn implementation.
#                       OscIn holds a single OscP5 and LinkedListener object.
#                       When LinkedListener receives an input, it passes it back to OscIn.
#                       When OscIn receives the input, it checks the dictionary for a callback function and calls it.
#                       Problem is, LinkedListener has trouble finding OscIn from within it.
#                       Moreover, when the function call does work, it only calls one dictionary entry,
#                       even if multiple match (e.g. "/.*" and "/1/" should both trigger when "/1/fader1" is received).
#                       Might need to go back to multiple GenericListeners, but have them remember their Osc Address and check themselves.
#   
#   1.71    23-Mar-2023 (tb) Modified to provide compatibility with OscP5 and Processing.
#                       Still WIP. Known bugs:
#                          OscOut - OscP5 fails to connect to receiving port.
#                          OscIn  - Receives successfully, but doesn't discriminate by OscAddress.
#                                   Use plugs from OscP5 to implement illposed listener functionality
#
#   1.7     22-Mar-2023 (bm) Fixed problem with finding our own IP address.  Using gethostbyname(gethostname())
#                       does not work all the time.  So, now we use getaddrinfo(hostname, port), and a little more
#                       work to extract one or more real (i.e., external) IP addresses.
#
#   1.6     07-Mar-2018 (bm) Now, we allow mutliple callback functions to be associated with the same 
#                       incoming OSC address.  This is was introduced to be consistent with the MidiIn API.
#
#   1.5     11-Feb-2016 (dj) Update in how we get host IP address in OscIn object to fix Mac OSX problem.
#
#   1.4     07-Dec-2014 (bm) Changed OscIn object functionality to allow registering of only *one*
#                       callback function per address (to mirror the corresponding MidiIn's object's
#                       behavior in the midi.py library).  The goal is to promote consistency of behavior
#                       between the two libraries.  Also, added MidiIn showMessages() and hideMessages() 
#                       to turn on and off printing of incoming OSC messages.  This allows to easily explore
#                       what messages are being send by a particular device (so that they can be mapped to 
#                       different functions).
#
#   1.3     19-Nov-2014 (bm) Fixed bug in cleaning up objects after JEM's stop button is pressed -
#                       if list of active objects already exists, we do not redefine it - thus, we 
#                       do not lose older objects, and can still clean them up.
#
#   1.2     06-Nov-2014 (bm) Added functionality to stop osc objects via JEM's Stop button
#                       - see registerStopFunction().
#
#   1.1     02-Dec-2013 (bm) Updated iiposed.com import statement to fix import error under 
#                       some Windows / Java combinations.
#
#   1.0     11-May-2013 (dj, bm) First implementation.
#


add_library( 'oscP5' )
from oscP5 import OscEventListener, OscMessage, OscPacket, OscP5, OscNetManager
#from netP5 import NetAddress
#from java.net import InetAddress

## From JEM version. Not currently relevant in Processing
#from com.illposed.osc import OSCListener, OSCMessage, OSCPacket, OSCPort, OSCPortIn, OSCPortOut
#from com.illposed.osc import *
#from com.illposed.osc.utility import *
#import socket

### keep track of active osc objects, so we can stop them when the program ends
try:
   # already defined (from an earlier run, do nothing, as it already contains material)
   _ActiveOscInObjects_

except:
   # first run - define to hold active objects
   _ActiveOscInObjects_  = []   
#   _ActiveOscOutObjects_ = [] # not yet implemented


#################### OscIn ##############################
#
# OscIn is used to receive messages from OSC devices.
#
# This class may be instantiated several times to create different OSC input objects (servers)
# to receive and handle OSC messages.
#
# The constructor expects the port number (your choice) to listen for incoming messages.
#
# When instantiated, the OscIn object outputs (print out) its host IP number and its port 
# (for convenience).  Use this info to set up the OSC clients used to send messages here.
#
# NOTE:  To send messages here you may use objects of the OscOut class below, or another OSC client, 
# such as TouchOSC iPhone client (http://hexler.net/software/touchosc).  

# The latter is most enabling, as it allows programs to be driven by external devices, such as
# smart phones (iPhone/iPad/Android).  This way you may build arbitrary musical instruments and 
# artistic installations.
#
# Picking port numbers:
# 
# Each OscIn object requires its own port.  So, pick port numbers not used by other applications.  
# For example, TouchOSC (a mobile app for Android and iOS devices), defaults to 8000 for sending OSC messages,
# and 9000 for receiving messages.  In general, any port from 1024 to 65535 may be used, as long as no other 
# application is using it.  If you have trouble, try changing port numbers.  The best bet is a port in 
# the range 49152 to 65535 (which is reserved for custom purposes).
#
# For example:
#
# oscIn = OscIn( 57110 )          # create an OSC input device (OSC server) on port 57110
#
# def simple(message):            # define a simple message handler (function)
#    print "Hello world!"
#
# oscIn.onInput("/helloWorld", simple)   # if the incoming OSC address is "/helloWorld", 
#                                        # call this function.
#
# def complete(message):          # define a more complete message handler
#     address = message.getAddress()
#     args = message.getArguments()
#     print "\nOSC Event:"
#     print "OSC In - Address:", address,   # print the time and address         
#     for i in range( len(args) ):          # and any message arguments (all on the same line)
#        print ", Argument " + str(i) + ": " + str(args[i]),
#     print
#
# oscIn.onInput("/.*", complete)   # all OSC addresses call this function
#

### a useful OSC message constant
#   matches all possible OSC addresses
ALL_MESSAGES = "/.*"

class OscIn():

   def __init__(self, port = 57110):

      self.port  = port                     # holds port to listen to (for incoming events/messages)
      self.oscIn = OscP5( self, self.port ) # create port

      ### OscP5 prints receiving IP Address and Port number when instantiated

      ### create dictionary to hold registered callback functions, so that we can replace them
      #   when a new call to onInput() is made for a given address - the dictionary key is the
      #   address, and the dictionary value is the GenericListener created for this address,
      #   so that may update the callback function it is associated with.
      self.oscAddressHandlers = {}
      
      ### print all incoming OSC messages by default
      self.showIncomingMessages = True

      ### provide a default OSC message handler 
      #   prints out all incoming OSC messages (if desired - see showMessages() and hideMessages())
      self.onInput( ALL_MESSAGES, self. _printIncomingMessage_ )

      ### remember this OscIn object so that it can be closed when the program ends
      _ActiveOscInObjects_.append( self )


   def onInput( self, oscAddress, function ):
      """
      Associate callback function to an incoming oscAddress.
      oscAddresses are strings that resemble URLs (e.g. "/hello/world")
      """

      ### register callback function for oscAddress
      #   if oscAddress is already registered, append function to its entry
      if self.oscAddressHandlers.has_key( oscAddress ):
         self.oscAddressHandlers[oscAddress].addFunction( function )

      #   otherwise, add new entry for it
      else:
         ### create new listener
         eventHandler = ProcessingListener( oscAddress, function )
         ### register it
         self.oscAddressHandlers[oscAddress] = eventHandler
         ### activate it
         self.oscIn.addListener( eventHandler )


   def _printIncomingMessage_(self, message):
      """It prints out the incoming OSC message (if desired)."""

      ### don't do this if showIncomingMessages is disabled
      if self.showIncomingMessages:
      
         ### unpack message
         oscAddress    = message.getAddress()
         argumentList  = message.getArguments()

         ### print incoming address and arguments
         print "OSC In - Address:", '"' + str(oscAddress) + '"',       
         for i in range( len(argumentList) ):
            ### check for argument type
            if type(argumentList[i]) == unicode: # strings get double quotes
               print ", Argument " + str(i) + ': "' + argumentList[i] + '"',
            else: # everything else gets nothing
               print ", Argument " + str(i) + ": " + str(argumentList[i]),
         print


   def showMessages(self):
      """
      Turns on printing of incoming OSC messages (useful for exploring what OSC messages 
      are generated by a particular device).
      """
      self.showIncomingMessages = True


   def hideMessages(self):
      """
      Turns off printing of incoming OSC messages.
      """
      self.showIncomingMessages = False



############# helper classes for OscIn #################
class ProcessingListener( OscEventListener ):


   def __init__(self, oscAddress = None, function = None):
      self.oscAddress   = oscAddress
      self.functionList = [ function ]

   def oscEvent(self, message):
      """
      When an OSC message is received, check it against this Listener's assigned address.
      If it matches, call registered functions. Otherwise, do nothing.
      """

      ### unpack incoming message address
      incomingAddress = message.addrPattern()

      ### check against registered address
      if self.oscAddress == incomingAddress:

         ### unpack incoming message arguments
         #   messages come in as java arrays, so translate to python list
         oscArguments = message.arguments()
         # oscArgumentsList = []
         # for argument in oscArguments:
         #    oscArgumentsList.append( argument )

         ### repack into OSCMessage
         oscMessage   = OSCMessage( incomingAddress, oscArguments )

         ### call functions registered to oscAddress
         for function in self.functionList:
            function( oscMessage )

   def addFunction(self, function):
      self.functionList.append( function )

   def getAddress(self):
      return self.oscAddress

   def setAddress(self, newOscAddress):
      self.oscAddress = newOscAddress



class OSCMessage( OscPacket ):
   """
   This class mimics an OscP5 OscMessage with methods from illposed's similar-named OSCMessage.
   Users can use the same methods they would use in JEM to pack and unpack messages in Processing.
   """

   def __init__(self, oscAddress, *arguments):
      self.oscAddress = oscAddress
      self.arguments  = arguments

   def addArgument(self, newArgument):
      self.arguments.append( newArgument )

   def getAddress(self):
      return self.oscAddress

   def getArguments(self):
      return self.arguments

   def setAddress(self, newOscAddress):
      self.oscAddress = newOscAddress



#################### OscOut ##############################
#
# OscOut is used to send messages to OSC devices.
#
# This class may be instantiated several times to create different OSC output objects (clients)
# to send OSC messages.
#
# The constructor expects the IP address and port number of the OSC device to which we are sending messages.
#
# For example:
#
# oscOut = OscOut( "localhost", 57110 )   # connect to an OSC device (OSC server) on this computer listening on port 57110
#
# oscOut.sendMessage("/helloWorld")        # send a simple OSC message
#
# oscOut.sendMessage("/itsFullOfStars", 1, 2.3, "wow!", True)   # send a more detailed OSC message
#

## Not currently functional in Processing

# class OscOut():

#    def __init__( self, IPaddress = "localhost", port = 57110 ):
#       self.IPaddress = InetAddress.getByName(IPaddress).toString()    # holds IP address of OSC device to connect with
#       self.port = port                             # and its listening port
#       self.netAddress = NetAddress( self.IPaddress, self.port )
#       # self.portOut = OSCPortOut(self.IPaddress, self.port) # create the connection
#       self.oscPortOut = OscP5( this, self.IPaddress, self.port )


#    def sendMessage( self, oscAddress, *args ):
#       """
#       Sends an OSC message consisting of the 'oscAddress' and corresponding 'args' to the OSC output device.
#       """

#       # HACK: For some reason, float OSC arguments do not work, unless they are explictly converted to Java Floats.
#       #       The following list comprehension does the trick.
#       from java.lang import Float
      
#       # for every argument, if it is a float cast it to a Java Float, otherwise leave unchanged
#       args = [Float(x) if isinstance(x, float) else x for x in args]
      
#       #print "sendMessage args = ", args
#       oscMessage = OscMessage( oscAddress, args )          # create OSC message from this OSC address and arguments
#       self.oscPortOut.send( oscMessage, self.netAddress )                        # and send it to the OSC device that's listening to us

#       # remember that this OscIn has been created and is active (so that it can be stopped/terminated by JEM, if desired)
#       _ActiveOscOutObjects_.append( self )
      

# TO DO??: Do we need a sendBundle() for time-stamped, bunded OSC messages?
#          To resolve - what does the timestamp mean?  When to execute?  
#          For answers, see - http://opensoundcontrol.org/spec-1_0
#
#   def sendBundle(self, timestamp, listOscAddresses, listArguments):
#      """
#      Sends a bundle of OSC messages 
#      """
#

###############################################################################
# Register function in Processing that stops everything when the program ends #
###############################################################################

def dispose():
   """Processing calls this function before shutting down.
   It cleans up any active OscIn or OscOut objects, freeing our ports."""

   ### stop OscIn objects
   for oscIn in _ActiveOscInObjects_:
      oscIn.stop()

   # ### stop OscOut objects
   # for oscOut in _ActiveOscOutObjects_:
   #    oscOut.stop()

   ### delete these objects
#   for oscObject in (_ActiveOscInObjects_ + _ActiveOscOutObjects_):
   for oscObject in _ActiveOscInObjects_:
      del oscObject

   ### and forget they existed
   _ActiveOscInObjects_  = []
#   _ActiveOscOutObjects_ = []



######################################################################################
# If running inside JEM, register function that stops everything, when the Stop button
# is pressed inside JEM.
######################################################################################

# # function to stop and clean-up all active Osc objects
# def _stopActiveOscObjects_():

#    global _ActiveOscInObjects_, _ActiveOscOutObjects_

#    # first, stop OscIn objects
#    for oscIn in _ActiveOscInObjects_:
#       oscIn.oscPortIn.stopListening()
#       oscIn.oscPortIn.close()

#    # now, stop OscOut objects
#    for oscOut in _ActiveOscOutObjects_:
#       oscOut.oscPortOut.close()

#    # then, delete all of them
#    for oscObject in (_ActiveOscInObjects_ + _ActiveOscOutObjects_):
#       del oscObject

#    # also empty list, so things can be garbage collected
#    _ActiveOscInObjects_ = []   # remove access to deleted items   
#    _ActiveOscInObjects_ = []   # remove access to deleted items   

# # now, register function with JEM (if possible)
# try:

#     # if we are inside JEM, registerStopFunction() will be available
#     registerStopFunction(_stopActiveOscObjects_)   # tell JEM which function to call when the Stop button is pressed

# except:  # otherwise (if we get an error), we are NOT inside JEM 

#     pass    # so, do nothing.

# #################### Unit Testing ##############################

# if __name__ == '__main__':

#    ###### create an OSC input object ######
#    oscIn = OscIn( 57110 )        # get input from OSC devices on port 57110

#    # define two message handlers (functions) for OSC input messages
#    def simple(message):      
#       print "Hello world!"

#    # tell OSC input object which functions to call for which OSC addresses
#    oscIn.onInput("/helloWorld", simple)   # if the incoming OSC message's address is "/helloWorld" call this function 



#    ###### create an OSC output object ######
#    oscOut = OscOut( "localhost", 57110 )    # send output to the OSC device on "localhost" listening at port 57110 
#                                             # (i.e., the above OSC input object)
   
#    # send a couple of messages
#    oscOut.sendMessage("/helloWorld")        # message without arguments
#    oscOut.sendMessage("/itsFullOfStars", 1, 2.35, "wow!", True)   # message with arguments
