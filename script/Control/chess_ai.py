#!/usr/bin/env python
################################################################################
##
## MIT License
##
## Copyright (c) 2018 Team Roborex, NIT Rourkela
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.
##
################################################################################
################################################################################
##
## AUTHORS: Prabin Rath, Subham Sahoo,  Pabitra Dash
##
################################################################################
import rospy
import rospkg
import chess
import chess.uci
import chess.pgn
import time
import os
from std_msgs.msg import Int32,String,Bool
from chess_bot.msg import ui_data,feature

file_path=rospkg.RosPack().get_path('chess_bot')+"/files";
eng=chess.uci.popen_engine("stockfish") #initialize chess engine
brd=chess.Board() #global chess board declaration
game=chess.pgn.Game() #global game handle declaration
node=game.end() #global node variable for tracking variation heirarchy
dict1={'a':0,'b':1,'c':2,'d':3,'e':4,'f':5,'g':6,'h':7}
indata="" #input UCI string decoded
outdata="" #output UCI string from stockfish too be encoded
master=False #master falg for the game logic
turn=False #False for user and True for stockfish
value=1 #global move type determinant
respn="#" #respawn character
cur_fen="" #to store fen
illigal=True #for detecting illigal moves
rwait=True #flag for system to stall during stockfish respawn
quit_flag=False #flag to break the master loop
setBoardFlag=False #flag to send fen to BoardUI
setupUI=False #flag to setup InteractUI and BoardUI or scroll area in LoadGame
setupUI_flg=False #False to setup InteractUI and BoardUI and True to setup scroll area in LoadGame

################################### Helping Functions for PGN Handling and crash management
def logger(game,string): #logger function: here the game variable is local
	global file_path
	log=open(file_path+"/log.txt","a")
	log.write(game.headers["Event"]+','+game.headers["White"]+','+game.headers["Black"]+','+game.headers["Round"]+','+time.ctime()+','+string+'\n')
	log.close()

def kyle():
    	current_time=time.ctime()
    	parser={'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06','Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
    	ll=current_time.split()
    	return ll[-1]+':'+parser[ll[1]]+':'+ll[2]

def ui_list_initializer(game): #ui_list_initializer function: here the game variable is local
	global file_path
	new_text = open(file_path+"/uci_list.txt","w")
	if(game.headers["Black"]=="Stockfish"):
		tagA="0 ";tagB="1 ";
		new_text.write( game.headers["White"]+'\n' )
	else:
		tagA="1 ";tagB="0 ";
		new_text.write( game.headers["Black"]+'\n' )
	length=len(game.root().variations);
	if length>0:
		node = game.root().variations[0];
	node_ = game.end();
	if length>0:
		while(node.move.uci()!=node_.move.uci()):
			try:
				new_text.write( tagA+node.move.uci()+"\n" )
				node = node.variations[0]
				new_text.write( tagB+node.move.uci()+"\n" )
				node = node.variations[0]
			except:
				pass
	new_text.close()

def nth_retrival(event,round_,white,black): #load_game function
    global game,brd,turn,file_path,setupUI,setupUI_flg,setBoardFlag
    new_pgn=open(file_path+"/gamedata.pgn")
    i=0
    for i,headers in chess.pgn.scan_headers(new_pgn):
        if(headers["Event"]==event) and (headers["White"]==white) and (headers["Black"]==black) and (headers["Round"]==round_):
            game=chess.pgn.read_game(new_pgn)
            game.headers["Event"]=headers["Event"]
            game.headers["White"]=headers["White"]
            game.headers["Black"]=headers["Black"]
            game.headers["Round"]=headers["Round"]
            game.headers["Date" ]=headers["Date" ]
            print('Found saved game')
            brd=game.board()
            for move in game.main_line():
                brd.push(move)
    ui_list_initializer(game)
    setupUI_flg=False
    setupUI=True
    turn=False
    setBoardFlag=True
    logger(game,"Retrived")

def nth_deletion(event,round_,white,black): #delete_game function: here the game_ variable is local and is used for deletion action
    global file_path,setupUI,setupUI_flg
    new=open(file_path+"/gamedata.pgn")
    i=0
    game_data=open(file_path+"/tempo.pgn","w")
    for i,headers in chess.pgn.scan_headers(new):
        if(headers["Event"]==event) and (headers["White"]==white) and (headers["Black"]==black) and (headers["Round"]==round_):
            continue
        else:
            game_=chess.pgn.read_game(new)
            game_.headers["Event"]=headers["Event"]
            game_.headers["White"]=headers["White"]
            game_.headers["Black"]=headers["Black"]
            game_.headers["Round"]=headers["Round"]
            game_.headers["Date"]=headers["Date"]
            exporter=chess.pgn.FileExporter(game_data)
            game_.accept(exporter)
    game_data.close()
    os.remove(file_path+"/gamedata.pgn")
    os.rename(file_path+"/tempo.pgn",file_path+"/gamedata.pgn")
    setupUI_flg=True
    setupUI=True
    logger(game_,"Deleted")

def new_game(event,round_,white,black):
	global game,brd,turn,master,setupUI,setupUI_flg
	brd=chess.Board()
	game=chess.pgn.Game()
	game.headers["Event"]=event
	game.headers["White"]=white
	game.headers["Black"]=black
	game.headers["Round"]=round_
	game.headers["Date" ] =kyle()
	ui_list_initializer(game)
	setupUI_flg=False
	setupUI=True
	if white=="Stockfish":
		turn=True
		master=True
	logger(game,"New game")

def restart_game(choice):
	global game,brd,setBoardFlag,master,turn
	temp=chess.pgn.Game()
	temp.headers['Event']=game.headers['Event']
	if choice=='y':
		if game.headers['White']=='Stockfish':
			temp.headers['White']=game.headers['Black']
			temp.headers['Black']=game.headers['White']
		else:
			temp.headers['White']=game.headers['White']
			temp.headers['Black']=game.headers['Black']
	else:
		if game.headers['Black']=='Stockfish':
			temp.headers['White']=game.headers['Black']
			temp.headers['Black']=game.headers['White']
		else:
			temp.headers['White']=game.headers['White']
			temp.headers['Black']=game.headers['Black']
	temp.headers['Round']=str(int(game.headers['Round'])+1)
	temp.headers['Date']=kyle()
	game=temp
	brd=game.board()
	setBoardFlag=True
	if choice!='y':
		turn=True
		master=True
	logger(game,'Restart')

def save_game():
	global game,file_path
	if os.path.exists(file_path+"/gamedata.pgn"): #checking the presence of a previously saved game with equal parameters
		pgn_=open(file_path+"/gamedata.pgn")
		for i,headers in chess.pgn.scan_headers(pgn_):
			if(headers["Event"]==game.headers["Event"]) and (headers["White"]==game.headers["White"]) and (headers["Black"]==game.headers["Black"]) and (headers["Round"]==game.headers["Round"]):
				pgn_.close()
				nth_deletion(game.headers["Event"],game.headers["Round"],game.headers["White"],game.headers["Black"])
				break
		pgn_.close()
	pgn_=open(file_path+"/gamedata.pgn","a")
	exporter = chess.pgn.FileExporter(pgn_)
	game.accept(exporter)
	pgn_.close()
	logger(game,'Save')

def undo_move():
	global game,brd,node,setBoardFlag
	if len(game.variations)==1:
		node=game.end()
		node.parent.remove_variation(brd.pop())
		del node
		node=game.end()
		node.parent.remove_variation(brd.pop())
		del node
		node=game.end()
		setBoardFlag=True
		logger(game,'Undo')
	else:
		print('Nothing To Undo!')

def backup_game(move):
	global game,node,file_path
	pgn=open(file_path+"/temp.pgn","w")
	node=game.end()
	node = node.add_variation(chess.Move.from_uci(move))
	exporter = chess.pgn.FileExporter(pgn)
	game.accept(exporter)
	pgn.close()
	#logger(game,"Backup")

def manage_crash():
	global file_path,game,node,brd,setupUI,setupUI_flg,setBoardFlag
	if os.path.exists(file_path+"/temp.pgn"): #TODO:add turn setup after recovery
		print("Previous game crashed\n")
		new_pgn=open(file_path+"/temp.pgn")
		game=chess.pgn.read_game(new_pgn)
		node=game.end()
		brd=game.board()
		for move in game.main_line():
			brd.push(move)
		ui_list_initializer(game)
		setupUI_flg=False
		setupUI=True
		logger(game,"Crashed Game")
		'''
		if ' b ' in brd.fen():
		''' 

def quit_game():
	global game,eng,quit_flag,file_path
	if os.path.exists(file_path+"/temp.pgn"):
		os.remove(file_path+"/temp.pgn")
	eng.quit()
	logger(game,'Quit')
	quit_flag=True
################################################################################

############################### Helping Functions for control system and Arduino
def diff(s):
    global value,dict1,brd
    reil=''
    value=len(s)
    if value==2: #normal move #promotion
        a=s[0]
        b=s[1]
	row=int(a[1])-1
	col=dict1[a[0]]
	index=8*row+col
	piece=str(brd.piece_at(index))
        if a[0]+a[1]!=b[0]+b[1] and (a[1]=="7" ) and ( b[1]=="8") and (piece=='P' or piece=='p'):
            reil=a[0]+a[1]+b[0]+b[1]
	    value=5
        elif a[0]+a[1]!=b[0]+b[1] and (a[1]=="2" ) and ( b[1]=="1") and (piece=='P' or piece=='p'):
            reil=a[0]+a[1]+b[0]+b[1]
	    value=5
        elif a[0]+a[1]!=b[0]+b[1]:
            reil=a[0]+a[1]+b[0]+b[1]
    elif value==3: #normal kill #en-passant kill
        a=s[0]
        b=s[1]
        c=s[2]
	row=int(b[1])-1
	col=dict1[b[0]]
	index=8*row+col
	piece=str(brd.piece_at(index))
        gen_str=a[3]+a[4]+b[3]+b[4]+c[3]+c[4]
	if gen_str=="101001" and (((b[1]=="7" ) and ( c[1]=="8")) or ((b[1]=="2" ) and ( c[1]=="1"))) and (piece=='P' or piece=='p'):
            reil=b[0]+b[1]+c[0]+c[1]
	    value=5
        elif gen_str=="101001":
            reil=b[0]+b[1]+c[0]+c[1]
        elif gen_str=="100110":
            reil=a[0]+a[1]+b[0]+b[1]
    elif value==4: #castling
        a=s[0]
        b=s[1]
        reil=a[0]+a[1]+b[0]+b[1]
    if(reil==''):
        print("Blank String Generated Redo the Move")
    return reil

#arduino steps generation
def arduino_steps(string,flag):

        ret_string=""

        irow_8=8-int(string[1])
        icol_8=dict1[string[0]]
        frow_8=8-int(string[3])
        fcol_8=dict1[string[2]]
        irow_16=irow_8*2+1
        icol_16=icol_8*2+1
        frow_16=frow_8*2+1
        fcol_16=fcol_8*2+1

        r_diff=frow_16 - irow_16
        c_diff=fcol_16 - icol_16
        if flag==0:  #normal move
                ret_string+=normal_move(irow_16 - 7,icol_16 - 7);
                ret_string+=",1,"
                ret_string+= normal_move(r_diff,c_diff);
                ret_string+=",0,"
                ret_string+=normal_move(7-frow_16,7-fcol_16)

        if flag==1:  #killing move
                a=0
                b=0
                check_kill=-1
                check_kill1=-1
                check_kill2=-1
                ret_string+=normal_move(frow_16-7,fcol_16-7)+",1,"
                a,b=killing_move(frow_16,fcol_16)
                ret_string+=normal_move(a,b)+",0,"+normal_move( -1*(a+r_diff), -1*(b+c_diff) )+",1,"+normal_move(r_diff,c_diff)+",0,"+normal_move(7-frow_16,7-fcol_16)
        if flag==2:  #en passant
                ret_string+=normal_move(irow_16-7,fcol_16-7)+",1,"
                a,b=killing_move(irow_16,fcol_16)

                ret_string+=normal_move(a,b)+",0,"+normal_move( -1*(a), -1*(b+c_diff) )+",1,"+normal_move(r_diff,c_diff)+",0,"+normal_move(7-frow_16,7-fcol_16)

        if flag==3: #casling move
                ret_string+=normal_move(irow_16-7,icol_16-7)+",1,"
                if(fcol_8>icol_8):
                        ret_string+="x_4_1,0,x_2_1,1,"+normal_move(0,-4)+",0,"+normal_move(7-frow_16,5-icol_16)
                else:
                        ret_string+="x_4_0,0,x_4_0,1,"+normal_move(0,6)+",0,"+normal_move(7-frow_16,9-icol_16)
        ret_string=ret_string.replace('_','')
        ret_string=ret_string.replace(',1,','H')
        ret_string=ret_string.replace(',0,','L')
        ret_string=ret_string.replace(',','')
        return ret_string

def normal_move(r_diff,c_diff):
        ret_string=""
        check_row=-1
        check_col=-1
        if(r_diff==0):
                ret_string+="y_1_1"
                if(c_diff>0):
                        ret_string+=",x_"+str(c_diff)+"_1"
                else:
                        ret_string+=",x"+str(abs(c_diff))+"_0"
                ret_string+=",y_1_0";
        elif(c_diff==0):
                ret_string+="x_1_0"
                if(r_diff>0):
                        ret_string+=",y_"+str(r_diff)+"_0"
                else:
                        ret_string+=",y_"+str(abs(r_diff))+"_1"
                ret_string+="x_1_1"
        else:
                if(r_diff>0 and c_diff>0):
                        ret_string+="y_1_0"+",x_"+str(c_diff-1)+"_1"+",y_"+str(r_diff-1)+"_0"+",x_1_1"
                elif(r_diff>0 and c_diff<0):
                        ret_string+="y_1_0"+",x_"+str(abs(c_diff)-1)+"_0"+",y_"+str(r_diff-1)+"_0"+",x_1_0"
                elif(r_diff<0 and c_diff>0):
                        ret_string+="y_1_1"+",x_"+str(c_diff-1)+"_1"+",y_"+str(abs(r_diff)-1)+"_1"+",x_1_1"
                elif(r_diff<0 and c_diff<0):
                        ret_string+="y_1_1"+",x_"+str(abs(c_diff)-1)+"_0"+",y_"+str(abs(r_diff)-1)+"_1"+",x_1_0"
        return ret_string;

def killing_move(frow_16,fcol_16):
        t_row=15-frow_16   #to throw the piece nearest col
        t_col=15-fcol_16   #to throw the piece nearest row
        if(t_row>7):
                t_row=15-t_row
                check_kill1=0
        else:
                check_kill1=2

        if(t_col>7):
                t_col=15-t_col
                check_kill2=1
        else:
                check_kill2=3

        if(t_row>t_col):
                check_kill=check_kill2
        else:
                check_kill=check_kill1
        if(check_kill==0):
                a=-1-frow_16
                b=0
                #ret_string+=normal_move(-2-frow_16,0)+",0,"+normal_move()
        elif (check_kill==1):
                a=0
                b=-1-fcol_16
        elif (check_kill==2):
                a=17-frow_16
                b=0
        elif (check_kill==3):
                a=0
                b=17-fcol_16
        return a,b
#end arduino steps generation

def checking_(string_):
	global brd
	flag=99
    	if(brd.is_capture(string_)):
        	flag=1
    	if(brd.is_en_passant(string_)):
        	flag=2
    	if(brd.is_castling(string_)):
        	flag=3
    	if(flag==99):
        	flag=0
    	return flag
#########################################################

################################# ROS Suscriber Functions
def decode(mv):
	global indata,master
	indata=diff(mv.data.split(','))
	if(indata!=''):
		master=True

def uicall(uidat):
	global respn,illigal,rwait
	if uidat.type==1:
		rwait=False
	elif uidat.type==2:
		respn=uidat.sys
	elif uidat.type==3:
		illigal=False
		
def interact(income):
	if len(income.head)>1:
		data=income.head.split(',')
		if income.flag==1:
			new_game(data[0],data[1],data[2],data[3])
		elif income.flag==2:
			nth_retrival(data[0],data[1],data[2],data[3])
		elif income.flag==3:
			nth_deletion(data[0],data[1],data[2],data[3])
	else:
		if income.flag==1:
			save_game()
		elif income.flag==2:
			undo_move()
		elif income.flag==3:
			restart_game(income.head)
		elif income.flag==4:
			quit_game()
		elif income.flag==5:
			save_game()
			quit_game()
#########################################################

def main_():
	global master,turn,indata,cur_fen,respn,illigal,value,outdata,rwait,setBoardFlag,eng,game,brd,node,quit_flag,file_path,setupUI,setupUI_flg
	rospy.init_node('chess_ai') #all publishers are local to main
	flagpub = rospy.Publisher('turn_flag', Bool, queue_size=10)
	uipub = rospy.Publisher('ui_send', ui_data, queue_size=10)
	uiset = rospy.Publisher('ui_setup', feature, queue_size=10)
	fenpub = rospy.Publisher('fendata', String, queue_size=10)
	ardpub = rospy.Publisher('move_seq', String, queue_size=10)
	rospy.Subscriber('board_string', String, decode)
	rospy.Subscriber('ui_recv', ui_data, uicall)
	rospy.Subscriber('interactions', feature, interact)
	
	time.sleep(1)
	manage_crash()

	temp=ui_data()
	ui_setup_msg=feature()

	rate = rospy.Rate(20)
	while not rospy.is_shutdown():
		if quit_flag==True:
			break
		if setupUI==True:
			ui_setup_msg.head=""
			ui_setup_msg.flag=2
			if setupUI_flg==False:
				ui_setup_msg.flag=1
			print "publishing"
			uiset.publish(ui_setup_msg)
			print "published"
			if setupUI_flg==False:
				print "waiting"
				time.sleep(1);
			print "waited"
			setBoardFlag=True
			setupUI=False
		if master==True:
			flagpub.publish(turn)
			if turn==False: #user turn
				print('user turn')
				print(indata)
				if value==5: #for respawn move
					temp.type=2
					temp.sys="Enter the respawn character \nand press select"
					uipub.publish(temp)
					while respn=="#":
						time.sleep(0.01)
					indata=indata+respn
					respn="#"
				if chess.Move.from_uci(indata) in brd.legal_moves: #for legal move
					print('correct move')
					brd.push(chess.Move.from_uci(indata))
					backup_game(indata)
					temp.type=4
					temp.mo=indata
					uipub.publish(temp)
					if brd.is_stalemate():
						temp.type=5
						temp.sys="Game Over its a draw please \nrestart the game to play again"
						uipub.publish(temp)
						#quit_game()
					if brd.is_checkmate():
						temp.type=5
						temp.sys="Game over congratulations you won please \nrestart the game to play again"
						uipub.publish(temp)
						#quit_game()
					turn=True
				else: #for illigal move
					print('incorrect move')
					temp.type=3
					temp.sys="Illigal Move please correct the \nmove and press select"
					uipub.publish(temp)
					turn=True
					flagpub.publish(turn)
					while illigal==True:
						time.sleep(0.01)
					illigal=True
					turn=False
			elif turn==True: #stockfish turn
				print('stockfish turn')
				eng.position(brd)
				bst,pon=eng.go(movetime=30)
				move_flag=checking_(bst)
				brd.push(bst)
				outdata=bst.uci()
				print(outdata)
				backup_game(outdata)
				temp.type=4
				temp.mo=outdata
				uipub.publish(temp)
				yes_respn=False
				if len(outdata)==5:
					yes_respn=True
					temp.type=1
					temp.sys="Please replace "+outdata[2]+outdata[3]+" with "+outdata[4]+"\n and press select"
					uipub.publish(temp)
					outdata=outdata[0:4]
				###
				mystr=arduino_steps(outdata,move_flag)
				ardpub.publish(mystr)
				###
				if yes_respn==True:
					while rwait==True:
						time.sleep(0.01)
					rwait=True
				if brd.is_stalemate():
					temp.type=5
					temp.sys="Game Over its a draw please \nrestart the game to play again"
					uipub.publish(temp)
					quit_game()
				if brd.is_checkmate():
					temp.type=5
					temp.sys="Game Over Stockfish won please \nrestart the game to play again"
					uipub.publish(temp)
					quit_game()
				turn=False
			setBoardFlag=True
		if turn==False:
			master=False
		if setBoardFlag==True:
			print brd
			fenpub.publish(brd.fen())
			setBoardFlag=False
		
		rate.sleep()

if __name__ == '__main__':
    try:
        main_()
    except rospy.ROSInterruptException:
        pass
