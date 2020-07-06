#!/usr/bin/python2.7
# Tcp Chat server
 
import socket, select, sys, time,string, os

program="Mystic Relay Chat Server"
version="v1.1"
curdir=os.path.dirname(os.path.realpath(__file__))

# rooms_by_user.: key=user, value=room
# chatroom list, for LIST
rooms_by_user={}
# sites_by_scokets, for BBSES : key=socket, value=bbs name (from mrc_config.py)
sites_by_sockets={}
# bbs_by_user, for WHOON and USERS: key=user, value=bbs
bbs_by_user={}
# topics : key=room, value=topic
topics={}
loop=1
hosts={}
# chatrooms : key=room, value=user count
server=""
serverhost=""
serverport=""
actions={}
op_dir=os.getcwd()

allargs=list(sys.argv)
if len(sys.argv) < 2:
	print "Usage: %s <hostname:port> [hostname:port]" % allargs[0]
	sys.exit()
else:
	server=allargs[1]
	serverhost,serverport=server.split(":",2)

def loggit(text):
	ltime=time.asctime(time.localtime(time.time()))
	print "%s : %s" % (ltime,text.replace('\n',''))
	sys.stdout.flush()

def stripmci(text):
	ret=""
	if text.find("|") == -1:
		ret=text
	else:
		tx=text.split("|")
		for xt in tx:
			ret=ret+xt[2:]
	return ret 

def stripextra(txt):
	symbs=[]
	symbs.append(" ")
	symbs.append("(")
	symbs.append(")")
	symbs.append("/")
	symbs.append("\\")
	symbs.append("*")
	symbs.append("~")
	symbs.append("!")
	symbs.append("[")
	symbs.append("]")
	symbs.append("<")
	symbs.append(">")
	for s in symbs:
		if txt.find(s) == -1:
			txt=txt
		else:
			txt=txt.replace(s,"_")
	return txt
	

def broadcast_data (message):
	for socket in master_list:
 		if socket != mrc_server:
			try :
				socket.send(message)
			except :
				close_connection(socket)
	time.sleep(0.2)

def send_to_one(sock,message):
	for socket in master_list:
		if socket == sock and socket != mrc_server:
			try:
				socket.send(message)
			except:
				close_connection(socket)
	time.sleep(0.2)

def listrooms(sock,fromuser):
	lx=0
	chatrooms={}
	for userx,roomx in rooms_by_user.iteritems():
		if len(roomx) > lx:
			lx=len(roomx)
		if roomx in chatrooms.keys():
			chatrooms[roomx]+=1
		else:
			chatrooms[roomx]=1

	if lx < 3:
		lx=3

	data="SERVER~~~"+fromuser+"~~~|07-|16|00.|07%-*s |08%-5s |11%s\n" % (lx+1,"Room","Users","Topic")
	send_to_one(sock,data)
	time.sleep(0.1)
	for roomx in set(rooms_by_user.values()):
		if roomx in topics.keys():
			tp=topics[roomx]
		else:
			tp=""
		data="SERVER~~~"+fromuser+"~~~|07-|16|00.|07#%-*s |08%5d |11%s\n" %(lx,roomx,chatrooms[roomx],tp)
		time.sleep(0.1)
		send_to_one(sock,data)

def remove_empty_topics():
	trooms=[]
	trooms=set(topics.keys())
	for tr in trooms:
		if tr not in rooms_by_user.values():
			topics.pop(tr)

def logoff(fromuser,fromsite,fromroom):
	if fromuser in rooms_by_user.keys():
		rooms_by_user.pop(fromuser)
		loggit("User %s from %s has left MRC" % (fromuser,fromsite))
	if fromuser in bbs_by_user.keys():
		bbs_by_user.pop(fromuser)
	remove_empty_topics()

def whoon(sock,fromuser):
	data="SERVER~~~"+fromuser+"~~~|07-|16|00.|13WhoOn: "
	for u,f in bbs_by_user.iteritems():
		data=data+"|04[|11"+u+"|07@"+f+"|04] "
	data=data+"\n"
	send_to_one(sock,data)

def showusers(sock,fromuser):
	data="SERVER~~~"+fromuser+"~~~|07-|16|00.|13Users: "
	for u,b in bbs_by_user.iteritems():
		data=data+"|04[|11"+u+"|04] "
	data=data+"\n"
	send_to_one(sock,data)

def showchannel(sock,fromuser,totoroom):
	data="SERVER~~~"+fromuser+"~~~|07-|16|00.|14#"+rooms_by_user[fromuser]+": "
	for u,r in rooms_by_user.iteritems():
		if r == rooms_by_user[fromuser]:
			data=data+"|06[|11"+u.rstrip()+"|06] "	
	data=data+"\n"
	send_to_one(sock,data)

def newroom(sock,fromuser,fromroom,message):
	oldr=message.split(":")[1]
	newr=message.split(":")[2]
	rooms_by_user[fromuser]=newr
	sendtopic(sock,fromuser,fromroom,newr)

def showconnected(socket,fromuser):
	data="SERVER~~~"+fromuser+"~~~|07-|16|00.|09BBSes: "
	bbsline=data
	for s,b in sites_by_sockets.iteritems():
		thisbbs="|01[|11"+b.rstrip()+"|01] "
		bbsline=data+thisbbs+"\n"
		send_to_one(sock,bbsline)

def showchatters(sock,fromuser):
	data="SERVER~~~"+fromuser+"~~~|07-|16|00.|12Chatters: "
	for occupant,roomname in rooms_by_user.iteritems():
		data=data+"|06[|11"+occupant+"|10#"+roomname+"|06] "
	data=data+"\n"
	send_to_one(sock,data)

def sendtopic(sock,fromuser,fromroom,room):
	if room in topics.keys():
		rtpc=topics[room]
	else:
		rtpc="No topic"
	data="SERVER~~~"+fromuser+"~~"+fromroom+"~ROOMTOPIC:"+room+':'+rtpc+"~\n"
	broadcast_data(data)

def newtopic(sock,fromuser,fromroom,message):
	croom=message.split(":")[1]
	rtopic=message.split(":")[2]
	topics[croom]=rtopic
	sendtopic(sock,fromuser,fromroom,croom)

def showmotd(sock,fromuser):
	data="SERVER~~~"+fromuser+"~~~|07-|16|00.|03MOTD: "
	sendtext=data+"Message of the Day\n"
	send_to_one(sock,sendtext)

	motdfile="%s%smotd.txt" % (curdir,os.sep)
	loggit(motdfile)
	fptr=open(motdfile,'r')
	for xyz in fptr:
		sendtext=data+xyz+"\n"
		send_to_one(sock,sendtext)
		loggit(sendtext)
		time.sleep(0.2)
	fptr.close()
	time.sleep(0.2)
	sendtext=data+"End MOTD\n"
	send_to_one(sock,sendtext)

def parse_data(sock,data):

		dt1=data.split("~")
		fromuser=dt1[0]
		fromsite=dt1[1]
		fromroom=dt1[2]
		totouser=dt1[3]
		totosite=dt1[4]
		totoroom=dt1[5]
		message=dt1[6]

		if totouser != "SERVER":
			broadcast_data(data)
		else:
			if message == "IAMHERE":
				if fromuser not in rooms_by_user.keys():
					rooms_by_user[fromuser]=fromroom
					loggit("User %s from %s is here" % (fromuser,fromsite))
				if fromuser not in bbs_by_user.keys():
					bbs_by_user[fromuser]=fromsite
			elif "IMALIVE" in message:
				bbsname=message.split(":")[1]
				bbsname.rstrip()
#				bbsname=stripmci(bbsname)
#				bbsname.replace(" ","_")
#				bbsname=stripextra(bbsname)
#				while bbsname.find("__") != -1:
#					bbsname=string.replace(bbsname,"__","_")
				sites_by_sockets[sock]=bbsname
				loggit("BBS (%s) is alive." % (bbsname))
			elif "NEWTOPIC" in message:
				newtopic(sock,fromuser,fromroom,message)
			elif "NEWROOM" in message:
				newroom(sock,fromuser,fromroom,message)
				time.sleep(0.1)
				showchannel(sock,fromuser,totoroom)
			elif message == "LOGOFF":
				logoff(fromuser,fromsite,fromroom)
			elif message == "WHOON":
				whoon(sock,fromuser)
			elif message == "USERS":
				showusers(sock,fromuser)
			elif message == "CHANNEL":
				showchannel(sock,fromuser,totoroom)
			elif message == "CHATTERS":
				showchatters(sock,fromuser)
			elif message == "CONNECTED":
				showconnected(socket,fromuser)
			elif message == "LIST":
				listrooms(sock,fromuser)
			elif message == "MOTD":
				showmotd(sock,fromuser)
			elif message == "VERSION":
				data="SERVER~~~"+fromuser+"~~~|07- |09%s %s\n" % (program,version)
				send_to_one(sock,data)

def close_connection(deadsock):
	if deadsock in sites_by_sockets.keys():
		deadsite=sites_by_sockets.pop(deadsock)
		loggit("Client (%s) disconnected" % (deadsite))
		loggit("Removing %s from BBSES list." % (deadsite))
		for xuser, xsite in bbs_by_user.iteritems():
			if xsite==deadsite:
				if xuser in rooms_by_user.keys():
					xroom=rooms_by_user.pop(xuser)
					loggit("Removing %s from %s" % (xuser,xroom))

	for sock in master_list:
		if sock == deadsock and sock != mrc_server:
			master_list.remove(sock)
			sock.close()

def update_connections(sock,bip,data):
	bbs=data.split("~")[0]
#	bbs=string.replace(bbs," ","_")
#	bbs=stripextra(bbs)
#	while bbs.find("__") != -1:
#		bbs=string.replace(bbs,"__","_")
	sites_by_sockets[sock]=bbs
	master_list.append(sock)
	loggit("Client (%s) connected from %s" % (bbs,bip))

def poll_clients():
	for socket in master_list:
		try:
			socket.send("SERVER~~~CLIENT~~~ping~\n")
		except:
			if socket != mrc_server:
				close_connection(socket)	

def clear_lists():
	rooms_by_user.clear()
	bbs_by_user.clear()
	sites_by_sockets.clear()
 
if __name__ == "__main__":

	# List to keep track of socket descriptors
	master_list = []
	RECV_BUFFER =4096 
	PORT = int(serverport)
	textbuffer=""
	tada=""
    
	mrc_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	mrc_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	mrc_server.bind((serverhost, PORT))
	mrc_server.listen(20)

	# Add server socket to the list of readable connections
	master_list.append(mrc_server)

	loggit("Mystic Relat Chat server started on port " + str(PORT))

	running=1 
	while running:
		rsock,wsock,esock = select.select(master_list,[],master_list,0)

		for sock in rsock:
			if sock == mrc_server:
				sockfd, addr = mrc_server.accept()
				BIP,BPORT=(addr)
				data = sockfd.recv(RECV_BUFFER)
				if data:
					update_connections(sockfd,BIP,data)
			else:
				try:
					textbuffer=sock.recv(4096)
					if textbuffer:
						loggit(textbuffer)
						tada=textbuffer.split(os.linesep)
						for data in tada:
							if data:
								parse_data(sock,data)
					else:
						close_connection(sock)
				except:
						close_connection(sock)


		loop+=1

		if loop % 501 == 0:
			poll_clients()

		if loop > 999999 :
		#	clear_lists()
			loop=1

		time.sleep(0.25)
   	  
