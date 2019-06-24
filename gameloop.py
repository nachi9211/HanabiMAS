
import random
import numpy as np

class Card:
    def __init__(self, color, number, id):
        self.color = color
        self.number = number
        self.id = id
        self.known_color = False
        self.known_number = False

class Player:
    def __init__(self, id, hand, otherplayers, commondicts, colors_all):
        self.id = id
        self.hand = hand
        self.otherplayers = otherplayers
        self.commondicts = commondicts
        self.known_hand = [('black',0),('black',0),('black',0),('black',0)] #0 is unknown, so is black
        self.colors_all = colors_all

    def update_info(self, otherplayers, commondicts):
        self.otherplayers = otherplayers
        self.commondicts = commondicts

# select what to do according to strategy
    def select_action(self,possibility_tables,playable_cards,possible_cards,dead_cards,hint_count,handstable):
        if not self.check_whether_playable_card(possibility_tables,playable_cards) == -1:
            return ['PLAY', self.check_whether_playable_card(possibility_tables,playable_cards)]
        elif (np.sum(playable_cards) + (50-np.sum(np.sum(possible_cards)))) < 5 and self.check_dead_card(possibility_tables,dead_cards) >= 0:
            return ['DISCARD UNDER 5', self.check_dead_card(possibility_tables,dead_cards)]
        elif hint_count > 0:
            return ['HINT']
        elif self.check_dead_card(possibility_tables,dead_cards) >= 0:
            return ['DISCARD DEAD CARD', self.check_dead_card(possibility_tables,dead_cards)]
        elif self.check_whether_card_known_duplicate(possibility_tables,handstable) !=-1:
            return ['DISCARD DUPLICATE', self.check_whether_card_known_duplicate(possibility_tables,handstable)]
        elif self.check_whether_dispensable_card_known(possibility_tables, possible_cards)!=-1:
            return ['DISCARD DISPENSABLE', self.check_whether_dispensable_card_known(possibility_tables, possible_cards)]
        else:
            return['DISCARD FIRST CARD',0]
        return action

# check whether one of the cards in the hand is playable, if so, return index of that card
    def check_whether_playable_card(self,possibility_tables,playable_cards):
        for card in range(0,4):
            possibly_playable = True
            for color in range(0,5):
                for value in range(0,5):
                    # if one of the possibilities is not playable card is not possibly playable
                    if possibility_tables[self.id,card,color,value] != 0:
                        if value != playable_cards[color]:
                            possibly_playable = False
            if possibly_playable:
                return card
        return -1


# check whether one of the cards in the hand is dead, if so, return index of that card
    def check_dead_card(self, possibility_tables, dead_cards):
        # check for each card whether all possibilities are dead
        for card in range(0,4):
            possibly_all_dead = True
            for color in range(0,5):
                for value in range(0,5):
                    if possibility_tables[self.id,card,color,value] != 0 and value > dead_cards[color]:
                        possibly_all_dead = False
                        break
                if not possibly_all_dead:
                    break
            if possibly_all_dead:
                return card
        return -1

# check whether one card is known to be a duplicate (in the hands of other players)
    def check_whether_card_known_duplicate(self,possibility_tables,handstable):
        for card in range(0,4):
            possible_duplicate = True
            for color in range(0,5):
                for value in range(0,5):
                    if possibility_tables[self.id,card,color,value] == 1:
                        card_dup = [self.colors_all[color],value]
                        if card_dup in handstable:
                            return card
        return -1


# check whether one card is known to be dispensable
    def check_whether_dispensable_card_known(self,possibility_tables,possible_cards):
        for card in range(0,4):
            possible_dispensable = True
            for color in range(0,5):
                for value in range(0,5):
                    if possibility_tables[self.id,card,color,value] == 1:
                        if possible_cards[color,value] < 2:
                            possible_dispensable = False
                            break
                if not possible_dispensable:
                    break
            if possible_dispensable:
                return card
        return -1




class Game:
    def __init__(self, nplayers, ncards, ncolors):
        self.colors_all = ['white', 'blue', 'red', 'green', 'yellow', 'orange']
        self.colors_all = self.colors_all[:ncolors]
        self.cardlist = [0,0,0,1,1,2,2,3,3,4]
        self.hint_count = 8
        self.mistake_count = 3
        self.score = 0
        self.play_token = 1
        self.nplayers = nplayers
        self.ncards = ncards
        self.ncolors = ncolors
        self.center = {}
        self.playable_cards = np.zeros((ncolors))
        self.dead_cards = np.zeros((ncolors)) -1
        self.discard_pile = []
        self.commondicts = {'center': self.center,
                            'discard_dict': self.discard_pile
                            }
        playerlist = self.create_players(self.nplayers, self.commondicts)
        self.playerlist = playerlist
        self.deck = self.create_deck(self.colors_all[0:self.ncolors+1], self.cardlist)
        self.possibility_tables = np.zeros((nplayers,ncards,ncolors,5)) + 1
        self.possible_cards = np.array([[3,2,2,2,1],[3,2,2,2,1],[3,2,2,2,1],[3,2,2,2,1],[3,2,2,2,1]])


# function that updates the number of cards still possible to have in your hand,
# for every card (i.e. not discarded or played)
    def update_possible_cards(self,card_color,card_value):
        self.possible_cards[card_color,card_value] -= 1
        # if the number of cards of this type becomes equal to 0, this is common
        # knowledge and this card is for no one possible to have in their hand
        if self.possible_cards[card_color, card_value] == 0:
            self.possibility_tables[:,:,card_color, card_value] = 0

# Hints also have to be incorporated wordly (the explicit meaning of the hings)
    def incorporate_hint_wordly(self,player,cards,value_color,color_hint):
        if color_hint:
            for color in range(0,self.ncolors):
                if color != value_color:
                    self.possibility_tables[player,cards,color,:] = 0
        else:
            for value in range(0,5):
                if value != value_color:
                    self.possibility_tables[player,cards,:, value] = 0

# what cards can the player see on the table now
    def cards_on_table_seen(self):
        handtotal = []
        for i in range(0,self.nplayers):
            if i != self.turn_token:
                handtotal += self.playerlist.get(i).hand
        return handtotal

# return the cards that are targeted this round
# calculates for all players the probability of all cards to be playable
# and targets the cards with highest probability per player
    def return_targeted_cards(self):
        targeted_cards = np.zeros((self.nplayers))
        for player in range(0,self.nplayers):
            cards = np.zeros((self.ncards))
            for card in range(0,self.ncards):
                ncards = 0
                nplayable_cards = 0
                for color in range(0,self.ncolors):
                    for value in range(0,5):
                        if self.possibility_tables[player,card,color,value] == 1:
                            ncards += self.possible_cards[color,value]
                            if self.playable_cards[color] == value:
                                nplayable_cards += self.possible_cards[color,value]
                if ncards!=0:
                    cards[card] = nplayable_cards/ncards

            targeted_cards[player] = int(np.argmax(cards))

        return targeted_cards


# create hint tables for all the targeted cards
    def targeted_cards_to_hints(self, targeted_cards):
# initialize them with 0's on dead cards, -1's on impossible cards and
# 1,2,3,4,5,6,7,7,7,7,7,7 etc.
        hint_tables = np.zeros((self.nplayers,self.ncolors,5))
        for player in range(0,self.nplayers):
            hint_table = self.possibility_tables[player,int(targeted_cards[player]),:,:] -1
            hintnum = 1
            for value in range(0,5):
                for color in range(0,self.ncolors):
                    if hint_table[color,value] == 0 and self.dead_cards[color] < value:
                        hint_table[color,value] = hintnum
                        if hintnum != 7:
                            hintnum += 1
            u, counts = np.unique(hint_table, return_counts = True)
            # make sure that no hint value occurs more than 8 times
            if len(counts) > 6:
                if counts[-1] > 8:
                    seven_surplus = counts[-1]-8
                    six_surplus = 0
                    if seven_surplus > 8:
                        six_surplus = seven_surplus-7
                        seven_surplus = 8
                    for value in range(0,5):
                        for color in range(0,self.ncolors):
                            if (hint_table[color,value] == 7 or hint_table[color,value] == 6) and six_surplus > 0:
                                hint_table[color,value] = 5
                                six_surplus -= 1
                            elif hint_table[color,value] == 7 and seven_surplus >0:
                                hint_table[color,value] = 6
                                seven_surplus -= 1
            hint_tables[player,:,:] = hint_table
        return hint_tables

# decide which hint to give, making use of the hint tables
    def decide_hint(self, origin_player_id,targeted_cards,hint_tables):
        # decide on which hidden hint to play
        sum = 0
        for coplayers in range(0,self.nplayers):
            if coplayers != origin_player_id:
                hand = self.playerlist.get(coplayers).hand
                card_index = targeted_cards[coplayers]
                hint_table = hint_tables[coplayers,:,:]
                true_card = hand[int(card_index)]
                color_int = self.colors_all.index(true_card[0])
                val = true_card[1]
                sum += hint_table[color_int,val]
        hintval = sum%8
# convert this hidden hint value into a wordly hint
        hint = self.convert_val_to_hint(origin_player_id,hintval,targeted_cards)
        return hint

# make a wordly hint of the hint value
    def convert_val_to_hint(self,player,hintval,targeted_cards):
        # decode value to wordly hint
        hint_player = int((hintval%4 + player)%5)
        hint_color = True
        if hintval < 4:
            hint_color = False
        hand = self.playerlist.get(hint_player).hand
        tg = targeted_cards[int(hint_player)]
# decide on which cards to give hints about
# prioritize colors/values that occur more often
        if hint_color:
            indices = []
            colors = [hand[0][0],hand[1][0],hand[2][0],hand[3][0]]
            if len(colors) == len(list(set(colors))) + 1:
                if colors[0] == colors[1]:
                    indices += [0,1]
                if colors[0] == colors[2]:
                    indices += [0,2]
                if colors[0] == colors[3]:
                    indices += [0,3]
                if colors[1] == colors[2]:
                    indices += [1,2]
                if colors[2] == colors[3]:
                    indices += [2,3]
                if colors[1] == colors[3]:
                    indices += [1,3]
            elif len(colors) == len(list(set(colors))) + 2:
                if colors[0] == colors[1] == colors[2]:
                    indices += [0,1,2]
                if colors[3] == colors[1] == colors[2]:
                    indices += [3,1,2]
                if colors[0] == colors[1] == colors[3]:
                    indices += [0,1,3]
                if colors[0] == colors[2] == colors[3]:
                    indices += [0,3,2]
                if colors[0] == colors[1] and colors[2] == colors[3]:
                    indices += [2,3]
                if colors[0] == colors[2] and colors[1] == colors[3]:
                    indices += [1,3]
                if colors[0] == colors[3] and colors[1] == colors[2]:
                    indices += [1,2]
            elif len(list(set(colors))) == 1:
                indices += [0,1,2,3]
            else:

                reduce = 0
                indices = [1]

                for i in range(1,self.ncards):
                    ncards = np.sum(np.sum(self.possibility_tables[hint_player,i,:,:]))
                    ncardspercolor = np.sum(self.possibility_tables[hint_player,i,self.colors_all.index(hand[i][0]),:])
                    if ncards - ncardspercolor > reduce:
                        reduce = ncards - ncardspercolor
                        indices = [i]

            return [hint_player,indices,hand[indices[0]][0],hint_color]
        else:
            indices = []
            colors = [hand[0][1],hand[1][1],hand[2][1],hand[3][1]]
            if len(colors) == len(list(set(colors))) + 1:
                if colors[0] == colors[1]:
                    indices += [0,1]
                if colors[0] == colors[2]:
                    indices += [0,2]
                if colors[0] == colors[3]:
                    indices += [0,3]
                if colors[1] == colors[2]:
                    indices += [1,2]
                if colors[2] == colors[3]:
                    indices += [2,3]
                if colors[1] == colors[3]:
                    indices += [1,3]
            elif len(colors) == len(list(set(colors))) + 2:
                if colors[0] == colors[1] == colors[2]:
                    indices += [0,1,2]
                if colors[3] == colors[1] == colors[2]:
                    indices += [3,1,2]
                if colors[0] == colors[1] == colors[3]:
                    indices += [0,1,3]
                if colors[0] == colors[2] == colors[3]:
                    indices += [0,3,2]
                if colors[0] == colors[1] and colors[2] == colors[3]:
                    indices += [2,3]
                if colors[0] == colors[2] and colors[1] == colors[3]:
                    indices += [1,3]
                if colors[0] == colors[3] and colors[1] == colors[2]:
                    indices += [1,2]
            elif len(list(set(colors))) == 1:
                indices += [0,1,2,3]
            else:

                reduce = 0
                indices = [1]

                for i in range(1,self.ncards):
                    ncards = np.sum(np.sum(self.possibility_tables[hint_player,i,:,:]))
                    ncardspercolor = np.sum(self.possibility_tables[hint_player,i,:, hand[i][1]])
                    if ncards - ncardspercolor > reduce:
                        reduce = ncards - ncardspercolor
                        indices = [i]

            return [hint_player,indices,hand[indices[0]][1],hint_color]


    def convey_hidden_hint(self,hint, origin_player_id,targeted_cards,hint_tables):
        hint_player = (hint[0] + 5 - origin_player_id)%4
        if hint[3]:
            hint_player += 4
        # print("hint_player = "+str(hint_player))

        for coplayers in range(0, self.nplayers):
            if coplayers != origin_player_id:
                sum = 0
                for other in range(0, self.nplayers):
                    if other != coplayers and other != origin_player_id:
                        hand = self.playerlist.get(other).hand
                        # print ('Handsan:',[c for c in hand])
                        card_index = targeted_cards[other]
                        # print(card_index)
                        hint_table = hint_tables[other,:,:]
                        true_card = hand[int(card_index)]
                        color_int = self.colors_all.index(true_card[0])
                        val = true_card[1]
                        # print("other " + str(other) + str(hint_table[color_int,val]) + str(true_card))
                        sum += hint_table[color_int,val]
                # print("sum = " +str(sum))
                # print("hintval = " +str(sum%8) )
                # print("hint_player = "+str(hint_player))
                hintval = (sum + 8)%8
                hintval = (hint_player + 8 - hintval)%8
                # print("hv =" +str(hintval))
                for color in range(0,self.ncolors):
                    for value in range(0,5):
                        if hint_tables[coplayers,color,value] != hintval:
                            self.possibility_tables[coplayers,int(targeted_cards[coplayers]),color,value] =0



    def create_players(self, nplayers, commondicts):
        playerlist = {}
        pids = range(0,self.nplayers)
        for pid in pids:
            otherplayers = {}
            others = [p for p in pids if p is not pid]
            for other in others:
                otherplayers.update({other:[]})
            #print (otherplayers)
            playerlist.update({pid:Player(id=pid, hand=[], commondicts=commondicts, otherplayers=otherplayers, colors_all = self.colors_all)})
        return playerlist

    def create_deck(self, colors, cardlist):
        deck = []
        id = 1
        for c in colors:
            for n in cardlist:
                #newcard = Card(id = id, color=c, number=int(n))
                newcard = [c,n]
                deck.append(newcard)
                random.shuffle(deck)
                id+=1
        return deck

    def deal_initial(self):
        for i in range(1, self.ncards+1):
            pids = self.playerlist.keys()
            for j in pids:
                self.deal_card(pid=j)
        return True

    def deal_card(self, pid): #Currently being corrected
        if (len(self.playerlist.get(pid).hand) < self.ncards):
            card = self.deck.pop()
            playerinfo = self.playerlist.get(pid)
            h = playerinfo.hand.append(card)
        else:
            print ('Hand already full')

    def print_player_info(self):
        for id in self.playerlist.keys():
            print('Player ID: ',id)
            this_player = self.playerlist.get(id)
            #print ('Hand:',[[c.color,c.number] for c in this_player.hand])
            print ('Hand:',[c for c in this_player.hand])

    def update_player_info(self):
        commondicts = self.commondicts
        for pid in self.playerlist.keys():
            thisplayer = self.playerlist.get(pid)
            othersdict = {}
            others = [x for x in self.playerlist.keys() if x is not pid]
            for other in others:
                h = self.playerlist.get(other).hand
                othersdict.update({other:h})
            #print (othersdict)
            thisplayer.update_info(otherplayers=othersdict, commondicts=commondicts)



    def play_card(self, player_id, card_to_play):
        carddetails = self.playerlist.get(player_id).hand.pop(card_to_play)
        color = self.colors_all.index(carddetails[0])
        value = carddetails[1]
        self.dead_cards[color] += 1
        self.playable_cards[color] += 1
        self.update_possible_cards(color,value)
        for card in range(card_to_play,3):
            self.possibility_tables[player_id,card,:,:] = self.possibility_tables[player_id,card + 1,:,:]
        newcard = np.zeros((self.ncolors,5))
        newcard[np.where(self.possible_cards > 0)] = 1
        self.possibility_tables[player_id,3,:,:] = newcard

        self.deal_card(pid=player_id)
        self.score += 1

    def play_discard(self, player_id, card_index):
        # print(card_index)
        selected_card = self.playerlist.get(player_id).hand.pop(card_index)
        for card in range(card_index,3):
            self.possibility_tables[player_id,card,:,:] = self.possibility_tables[player_id,card + 1,:,:]
        newcard = np.zeros((self.ncolors,5))
        newcard[np.where(self.possible_cards > 0)] = 1
        self.possibility_tables[player_id,3,:,:] = newcard
        self.deal_card(player_id)
        self.discard_pile.append(selected_card)
        self.hint_count+=1
        #check if there are other variables that need updating when a card is discarded
        self.update_possible_cards(self.colors_all.index(selected_card[0]),selected_card[1])

    def play_game(self):
        #select player to start
        self.turn_token = 0 #randomize
        # self.incorporate_hint_wordly(2,3,1,True)
        # self.incorporate_hint_wordly(3,0,0,False)
        # self.incorporate_hint_wordly(1,2,3,True)
        # print(self.possibility_tables[4,0])
        tg = self.return_targeted_cards()
        # print(self.targeted_cards_to_hints(tg))
        #loop till you out of tokens
        last_turn = True
        player_last_turn = 0
        while self.mistake_count>=0 and self.score != 25 and sum(sum(self.possible_cards)) > self.nplayers * self.ncards and last_turn == True:
            # make sure every player gets one last turn before the game ends
            if sum(sum(self.possible_cards)) <= self.nplayers * self.ncards:
                player_last_turn += 1
                if player_last_turn == self.nplayers:
                    last_turn = False
            # print("mistake was made")
            #Update player info
            self.update_player_info()
            targeted_cards = self.return_targeted_cards()
            hint_tables = self.targeted_cards_to_hints(targeted_cards)
            #Call to player for action
            this_act = self.playerlist.get(self.turn_token).select_action(self.possibility_tables,self.playable_cards,self.possible_cards, self.dead_cards,self.hint_count,self.cards_on_table_seen())
            # perform action
            if this_act[0] == 'PLAY':
                self.play_card(self.turn_token, this_act[1])
            elif this_act[0] == 'HINT':
                # decide which hint to give
                hint = self.decide_hint(self.turn_token, targeted_cards,hint_tables)
                if hint[3]:
                    value_color =  int(self.colors_all.index(hint[2]))
                else:
                    value_color = hint[2]
                # convey the hidden meaning
                self.convey_hidden_hint(hint,self.turn_token,targeted_cards,hint_tables)
                # convey the wordly meaning
                self.incorporate_hint_wordly(int(hint[0]),hint[1],value_color,hint[3])
                self.hint_count = self.hint_count -1

            elif this_act[0].split()[0]=='DISCARD':
                self.play_discard(self.turn_token, this_act[1])
            # switch turns
            self.turn_token += 1
            if self.turn_token == self.nplayers:
                self.turn_token = 0
        print("Score = " + str(self.score))
        print("Num Cards Left = " + str(sum(sum(self.possible_cards))))
        return self.score


def gameloop():
    scores = []
    for i in range(0,1000):

        manager = Game(5,4,5)
        # print (manager.playerlist)
        manager.deal_initial()
        # manager.print_player_info()
        scores += [manager.play_game()]
    print(np.mean(scores))

    #get latest game elements
    #decide action
        #hint
        #discard
        #play
        #updates lie within action code
    #next turn

gameloop()
# manager = Game(5,4,5)
# print (manager.playerlist)
# manager.deal_initial()
# manager.print_player_info()
# manager.play_game()
