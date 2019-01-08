#!/usr/bin/python
# $Id$
#
# Date:	20-Feb-2018

__author__ = "Vakhramov"
__email__  = "megavad@mail.ru"

__name__ = "Embroidery"
__version__= "0.0.2"

from CNC import CNC,Block
from ToolsPage import Plugin

try:
	import tkMessageBox 
except ImportError:
	import tkinter.messagebox as tkMessageBox

import math
from bmath import Vector
from CNC import CW,CCW,CNC,Block


def getbit(b,pos):
	bit=(b>>pos)&1
	return bit
		
def decode_dx(b0, b1, b2):
	x=0
	x+= getbit(b2,2)*(+81)
	x+= getbit(b2,3)*(-81)
	x+= getbit(b1,2)*(+27)
	x+= getbit(b1,3)*(-27)
	x+= getbit(b0,2)*(+9)
	x+= getbit(b0,3)*(-9)
	x+= getbit(b1,0)*(+3)
	x+= getbit(b1,1)*(-3)
	x+= getbit(b0,0)*(+1)
	x+= getbit(b0,1)*(-1)
	return x
	
def decode_dy (b0, b1, b2):
	y=0
	y+= getbit(b2,5)*(+81)
	y+= getbit(b2,4)*(-81)
	y+= getbit(b1,5)*(+27)
	y+= getbit(b1,4)*(-27)
	y+= getbit(b0,5)*(+9)
	y+= getbit(b0,4)*(-9)
	y+= getbit(b1,7)*(+3)
	y+= getbit(b1,6)*(-3)
	y+= getbit(b0,7)*(+1)
	y+= getbit(b0,6)*(-1)
	return y
	

options = { 243 : CNC.grapid,#to be changed to zero func
           3 : CNC.gline,#normal stitch
           131 : CNC.grapid,# to jump - is not visible 
           195 : CNC.grapid#Change COLOR! and nothing else, in decode_flags
}	

colors = {0:"red", 
		  1:"green", 
		  2:"blue", 
		  3:"yellow",
		  4:"gray",
		  5:"brown",
		  6:"cyan",
		  7:"magenta"}




#==============================================================================
# Embroidery generates stitches at 2D
#==============================================================================
class Embroidery:
	
	def __init__(self, name="Embroidery",color = 0):
		self.name = name
		self.color = color
		#-----------------------


	def GetStitches(self, app, FileName ):
		try:
			from struct import *
		except:
			app.setStatus("Embroidery abort: no module named struct")
			return
		
		print(FileName)
		try:
			f = open(FileName,'rb')
		except:
			app.setStatus(" Embroidery abort: Can't read image file")
			return
		app.setStatus(" Embroidery: file %s sucsessfully opened"%f.name)
		#DST header struct checking - parsing
		format = "3s16sc3s7sc3s3sc3s5sc3s5sc3s5sc3s5sc3s6sc3s6sc"
		data=f.read(94)
		LAN,LA,C,STN,ST,C,CLN,CL,C,POSX,posx,C,NEGX,negx,C,POSY,posy,C,NEGY,negy,C,AX,ax,C,AY,ay,c=unpack(format, data) 
		CL=int(CL)
		ST=int(ST)
		
		if (LAN !='LA:'): 
			app.setStatus(" Embroidery abort: Not a DST")
		print (LA)
		print(" St count: %d color changes=%d"%(ST ,CL))
		f.seek(512);
		coordX=0;coordY=0;#initial coordinates to start sewing
		cnt=0;#just counter
		color = 0;#color code
		format="1b1b1b"# 3 unsigned bytes from data field
		prevCol=self.color
		i=0
		blocks = []
		for ColorCycles  in range (0 , CL+1): #color cycles
			
			block = Block(self.name)
			while prevCol==self.color:
				ff=f.read(3);#read 24 bits
				cnt+=1
				if  len(ff)<3: break
				b0,b1,b2=unpack(format, ff) #data field unpacked with "format" to b0 b1 b2
				dx = decode_dx(b0, b1, b2)
				dy = decode_dy(b0, b1, b2)
				coordX+=dx
				coordY+=dy
				block.color = colors[self.color]
				block.append(self.decode_flags( b2)(coordX,coordY))
				block.append(CNC.zsafe())#safe height
			prevCol = self.color
			print("Stitches read=: %d"%cnt)#counter		
			blocks.append(block)

		
		try:
			dx = float(self["dx"])
		except:
			dx = 0.0

		try:
			dy = float(self["dy"])
		except:
			dy = 0.0

		return blocks
	def decode_flags (self, b2) :
		if b2==243: return END
		if b2&195==195: 
			self.color = self.color+1
		return options[b2&195] 
		#================

		
class Tool(Plugin):
	__doc__ = _("Embroidery abstract")
	def __init__(self, master):
		Plugin.__init__(self, master,"Embroidery")
		self.name = "Embroidery"
		self.icon = "tile"
		self.group= "CAM"
		self.variables = [
			("name",      "db",    "", "Name"),
			("FileName",     "file",  "", "DST Tajima file"),
			("FeedMin"  ,  "int" ,     250, "Minimum feed"),
			("FeedMax"  ,  "int" ,    5000, "Maximum feed"),
			("LA",        "LA",  "", "name"),
			("ST",        "ST",  "", "Stitch count"),
			("CO:",        "CL",  "", "color changes"),
			("+X:",        "posx",  "", "maximum X extent"),
			("-X:",        "negx",  "", "minimum X extent"),
			("+Y:",        "posy",  "", "maximum Y extent"),
			("-Y:",        "negy",  "", "minimum Y extent"),
			("AX:",        "ax",  "", "needle end point X"),
			("AY:",        "ay",  "", "needle end point Y")
			
		]
		
		feedMax = self["FeedMax"]
		self.buttons.append("exe")


	# ----------------------------------------------------------------------
	def execute(self, app):
		# Select all code in editor
		n = self["name"]
		FileName = self["FileName"]
		print (FileName)
		print ("aaa")
		if not n or n=="default": n="Embroidery"
		embroidery = Embroidery(n)
		blocks = embroidery.GetStitches(app, FileName)

		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Create EMB")
		#		if len(blocks) > 0:
		app.refresh()



#some old stuff
		#self.buttons.append("Open Design")
		#pos = Vector(19, 100, 0)
		#block.append(block.append(CNC.gcode(0, zip("XY",pos[:2]))))
		#block.append(CNC.glinev(1, pos, 430))	
		#app.setStatus("Data 0 1 2 =: %d %d %d"%(b0,b1,b2))#debug message with bytes
		#app.setStatus("Data dx dy=: %d %d"%(dx, dy))#debug message with bits	

		