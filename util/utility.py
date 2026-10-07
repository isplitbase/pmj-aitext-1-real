import os
import sys
import re
from pprint import pprint
import traceback

#import csv
import sqlite3

import datetime
import glob
import numpy as np
from util.defines import *

# デバッグ用
debug_file = sys.stdout                # デバッグprintのデフォルトはstdout

def debug_print(msg,level=0):

    if level >= DEBUG_PRINT_LEVEL:
        print(msg,file=debug_file)

def debug_print_end(msg,term,level=0):

    if level >= DEBUG_PRINT_LEVEL:
        print(msg,end=term,file=debug_file)

def debug_pprint(jsonData, width=40,level=0):

    if level >= DEBUG_PRINT_LEVEL:
        pprint(jsonData,width=width,stream=debug_file)

#charactersの文字は対象文字と合うかを判断する
#math：要求される最小合う比率例えば:0.8
#作成者：尚
def hikaku_characters(characters,target,math):
    i=0
    target_len=len(target)
    target_len_c=target_len+3
    #計算できた合う比率
    real_math=0
    for c in characters:
        #合計回数
        sub=0
        #今回の合う比率
        now_math=0
        dedmap={}
        for num in range(target_len_c):
            if i-num>-1 and characters[i-num]['text'] in target and dedmap.get(characters[i-num]['text']) is None:
                sub+=1
                dedmap[characters[i-num]['text']]=True
        now_math=sub/target_len
        if now_math>real_math :
            real_math=now_math
        i+=1
    if real_math>math :
        return True
    else : return False
#charactersから対象文字と合うか言葉の左上右下座標と文字高さを返す
#math：要求される最小合う比率例えば:0.8
#作成者：尚
def get_right_characters_count(characters,target,math,sumcount,count):
    i=0
    target_len=len(target)
    target_len_c=target_len+3
    #計算できた合う比率
    real_math=0
    codes=[]
    answer=[]

    ylist=[]
    for c in characters:
        addylistflag=True
        newy=0
        for y in ylist:
            if y+50>c['bounds'].rect[1] and y-50<c['bounds'].rect[1] :
                newy = y
                addylistflag=False
        if addylistflag :
            newy = c['bounds'].rect[1]
            ylist.append(c['bounds'].rect[1])
        codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3],newy])
    codes = sorted(codes,key=lambda x:(x[5],x[1]))
    for c in codes:
        #合計回数
        sub=0
        #今回の合う比率
        now_math=0
        #一番最初の文字位置
        first_num=None
        text=""
        for num in range(target_len_c):
            if i-num>-1 and codes[i-num][0] not in text and codes[i-num][0] in target and codes[i][0] == target[-1] :
                sub+=1
                first_num=i-num
                text+=codes[i-num][0]
        now_math=sub/target_len
        if now_math>math :
            answer.append([codes[first_num][1],codes[first_num][2],c[3],c[4],c[4]-c[2]])
        i+=1
    if len(answer)==sumcount :
      return answer[count][0],answer[count][1],answer[count][2],answer[count][3],answer[count][4]
    else :
      return None,None,None,None,None

#charactersから対象文字と合うか言葉の左上右下座標と文字高さを返す
#math：要求される最小合う比率例えば:0.8
#作成者：尚
def get_right_characters(characters,target,math):
    i=0
    target_len=len(target)
    target_len_c=target_len+3
    #計算できた合う比率
    real_math=0
    codes=[]
    ylist=[]
    for c in characters:
        if c['text']=="借" :
            aa=1
        addylistflag=True
        newy=0
        for y in ylist:
            if y+30>c['bounds'].rect[1] and y-30<c['bounds'].rect[1] :
                newy = y
                addylistflag=False
        if addylistflag :
            newy = c['bounds'].rect[1]
            ylist.append(c['bounds'].rect[1])
        codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3],newy])
    codes = sorted(codes,key=lambda x:(x[5],x[1]))
    text=""
    for c in codes:

        #合計回数
        sub=0
        #今回の合う比率
        now_math=0
        #一番最初の文字位置
        first_num=None
        text=""
        last_num=None
        if target == "雑収入" and (c[2]<1500 or c[2]>2500 or c[1]>700):
            text=""
        else :
            for num in range(target_len_c):
                if i-num>-1 and codes[i-num][0] not in text and codes[i-num][0] in target and (codes[i][0] == target[-1] or codes[i][0] == target[-2]) :
                    sub+=1
                    first_num=i-num
                    now_math=sub/target_len
                    last_num=i
                    text=codes[i-num][0]+text
                    if target == "雑収入" and text[0] == "入" and now_math>math :
                        text=""
                        now_math=0
                    else :
                        if now_math>math and num>=target_len-1 :
                            if codes[i][0] == target[-2] :
                                return text,codes[first_num][1],codes[first_num][2],c[3]+codes[first_num+1][1]-codes[first_num][1],c[4],c[3]-c[1]
                            else :
                                return text,codes[first_num][1],codes[first_num][2],c[3],c[4],c[3]-c[1]
        i+=1
        if now_math>math :
          if codes[last_num][0] == target[-2] :
            return text,codes[first_num][1],codes[first_num][2],c[3]+codes[first_num+1][1]-codes[first_num][1],c[4],c[3]-c[1]
          else :
            return text,codes[first_num][1],codes[first_num][2],c[3],c[4],c[3]-c[1]
    return None,None,None,None,None,None
#charactersから対象文字と合うか言葉の左上座標と文字高さを返す
#math：要求される最小合う比率例えば:0.8
#作成者：尚
def get_left_characters_nn(characters,target,math,nn):
    i=0
    c_len=len(characters)
    target_len=len(target)
    target_len_c=target_len+3
    #計算できた合う比率
    real_math=0

    codes=[]
    ylist=[]
    for c in characters:
        addylistflag=True
        newy=0
        for y in ylist:
            if y+50>c['bounds'].rect[1] and y-50<c['bounds'].rect[1] :
                newy = y
                addylistflag=False
        if addylistflag :
            newy = c['bounds'].rect[1]
            ylist.append(c['bounds'].rect[1])
        codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3],newy])
    codes = sorted(codes,key=lambda x:(x[5],x[1]))
    nn_=0
    for c in codes:
        #合計回数
        sub=0
        #今回の合う比率
        now_math=0
        #一番最後の文字位置
        last_num=None
        text=""
        for num in range(target_len_c):
            if i+num<c_len and codes[i+num][0] not in text and codes[i+num][0] in target and codes[i][0] == target[0] :
                sub+=1
                last_num=i+num
                now_math=sub/target_len
                text+=codes[i+num][0]
                if now_math>math and num>=target_len :
                  if nn_<nn :
                      nn_=nn_+1
                  else :
                    return c[1],c[2],codes[last_num][3],codes[last_num][4],c[3]-c[1]
        i+=1
        if now_math>math :
            if nn_<nn :
                nn_=nn_+1
            else :
                return codes[last_num][1],codes[last_num][2],c[3],c[4],c[3]-c[1]
    return None,None,None,None,None
#charactersから対象文字と合うか言葉の左上座標と文字高さを返す
#math：要求される最小合う比率例えば:0.8
#作成者：尚
def get_left_characters(characters,target,math):
    i=0
    c_len=len(characters)
    target_len=len(target)
    target_len_c=target_len+3
    #計算できた合う比率
    real_math=0

    codes=[]
    ylist=[]
    for c in characters:
        addylistflag=True
        newy=0
        for y in ylist:
            if y+50>c['bounds'].rect[1] and y-50<c['bounds'].rect[1] :
                newy = y
                addylistflag=False
        if addylistflag :
            newy = c['bounds'].rect[1]
            ylist.append(c['bounds'].rect[1])
        codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3],newy])
    codes = sorted(codes,key=lambda x:(x[5],x[1]))
    for c in codes:
        #合計回数
        sub=0
        #今回の合う比率
        now_math=0
        #一番最後の文字位置
        last_num=None
        text=""
        for num in range(target_len_c):
            if i+num<c_len and codes[i+num][0] not in text and codes[i+num][0] in target and codes[i][0] == target[0] :
                sub+=1
                last_num=i+num
                now_math=sub/target_len
                text+=codes[i+num][0]
                if now_math>math and num>=target_len :
                  return c[1],c[2],codes[last_num][3],codes[last_num][4],c[3]-c[1]
        i+=1
        if now_math>math :
          return codes[last_num][1],codes[last_num][2],c[3],c[4],c[3]-c[1]
    return None,None,None

#右側から最初の数字列を取得する
#oo:Y座標の膨脹距離
#作成者：尚
#arg：平均距離をチェックする
def get_right_number(characters,x,y,line,oo,maxx,check,arg,kojin_tri):
    i=0
    #最初の1っ個数字
    first_x1=None;
    first_y1=None;
    first_x2=None;
    first_y2=None;
    text="";
    codes=[]
    #最初の1っ個数字
    last_x1=None;
    last_y1=None;
    last_x2=None;
    last_y2=None;
    answer=[]
    #同一Y座標のすべてのコードを取得
    for c in characters:
        if oo<0 :
            if c['bounds'].rect[1]>y+oo and c['bounds'].rect[3]<y-oo+25:
                codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3]])
        else :
            if c['bounds'].rect[1]<y+oo and c['bounds'].rect[3]>y-oo:
                codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3]])
    codes = sorted(codes,key=lambda x:(x[1]))
    breakflag=False
    #数値を取り出す
    #数字間隔
    lastx2=None
    lastnumber=""
    mondai=[]
    seikaku=25
    i=-1
    for c in codes:
      i = i+1
      if c[1]>x+line  and (((c[0].isdecimal() or c[0]==',') and c[3]-c[1]<maxx*4/3)  or c[0]=='-'):
        if c[0]!="1" and c[0]!="," and c[3]-c[1]+15<maxx*3/10 and check==False:
            continue
        if c[0]!="1" and c[0]!="," and c[3]-c[1]+4<maxx/5 and check:
            continue
        if c[0]!="," and c[4]-c[2]<maxx*1/5 :
            continue
        if c=="[" or c=="]" or c=="|" :
            xxxxxxx=0
        if lastx2 is None :
          if len(codes)>i+1 and ( codes[i+1][1]-c[1]< 28  and check==False ) and codes[i+1][0]!="," :
            continue
          if c[0]!="1" and len(codes)>i+1 and ( codes[i+1][1]-c[1]< 8  and check ) :
            continue
          lastx2=c[3]
          lastnumber=c[0]
          answer.append(c)
          breakflag=True
          if c[0]!="1" and c[0]!="2" :
            seikaku=c[3]-c[1]
          if c[3]-c[1]>maxx/3 and c[0]=="1" :
            mondai.insert(0,len(answer)-1)
        elif len(codes)>i+1 and ( codes[i+1][1]-c[1] > seikaku*2/3 or check or codes[i][3]-codes[i][1] > 3*seikaku or codes[i+1][3]-codes[i+1][1] > 3*seikaku) :
            lastx2=c[3]
            lastnumber=c[0]
            answer.append(c)
            breakflag=True
          
            if c[0]!="1" and c[0]!="2" and codes[i][3]-codes[i][1] < 3*seikaku :
              seikaku=c[3]-c[1]
            if c[3]-c[1]>maxx/3 and c[0]=="1" :
              mondai.insert(0,len(answer)-1)
        elif len(codes)==i+1:
            lastx2=c[3]
            lastnumber=c[0]
            answer.append(c)
            breakflag=True
          
            if c[0]!="1" and c[0]!="2" and codes[i][3]-codes[i][1] < 3*seikaku :
              seikaku=c[3]-c[1]
            if c[3]-c[1]>maxx/3 and c[0]=="1" :
              mondai.insert(0,len(answer)-1)
        else :
            continue
      elif breakflag :
        if c[0]!="[" and c[0]!="]" and c[0]!="|" and c[1]>lastx2+18 and c[4]-c[2]>30 :
          continue
    #print("240")
    #print(mondai)
    #print(answer)
    for c in mondai:
      if answer[c][3]-answer[c][1] > seikaku+20 :
        del answer[c]

    answer = sorted(answer,key=lambda x:(x[1]))
    #一数字しか識別できなかった場合
    if len(answer) == 1 :
        for c in answer:
            if c[4]-c[2]+7<maxx*2/5 :
                del answer[0]

    #平均文字距離
    #横長
    heikin=0
    v=0
    doheikin = True
    for c in answer:
        doheikin = True
        if c[0]=="," :
            doheikin = False
        if doheikin and (c[0]=="1" or c[0]=="2" or c[0]=="3") and v>1 and answer[v][1]-answer[v-1][1]<heikin*7/8:
            del answer[v]
            continue
        if v==0 :
            ak=0
        elif v==1 :
            heikin=answer[v][1]-answer[v-1][1]
        else :
            heikin=(heikin+answer[v][1]-answer[v-1][1])/2
        v=v+1
    v=0
    doheikin = True
    #縦長
    for c in answer:
        doheikin = True
        if c[0]=="," :
            doheikin = False
        if doheikin and v>1 and c[4]-c[2]<heikin*1/2:
            debug_print("del answer",level=DEBUG_ROWS_INFO)
            debug_print(str(c[0]),level=DEBUG_ROWS_INFO)
            debug_print(str(heikin),level=DEBUG_ROWS_INFO)
            del answer[v]
            continue
        if v==0 :
            heikin=0
        elif v==1 :
            heikin=c[4]-c[2]
        else :
            heikin=(heikin+c[4]-c[2])/2
        v=v+1
    if arg :
        v=0
        deleteindex=-1
        for c in answer:
            doheikin=True
            if c[0]==","  or v==0:
                doheikin = False
            if doheikin and v<len(answer)-1 and answer[v][1]-answer[v-1][1]>150 :
                deleteindex=v
            v=v+1
        v=0
        for c in answer:
            if v<deleteindex:
                del answer[v]
            v=v+1
        v=0
        #横平均距離を取得
        heikin=1000
        heikin_list=[]
        for c in answer:
            if v==0 :
                ak=0
            else:
                heikin_list.append(answer[v][1]-answer[v-1][1])
            v=v+1
        ld = sorted(heikin_list, reverse=True)
        ldsize=len(ld)/2
        v=0
        for c in ld:
            if v==0 :
                heikin=c
            elif v<ldsize :
                heikin=(heikin+c)/2
            v=v+1
        v=0
        todoflag=True
        for c in answer:
            doheikin=True
            if c[0]==","  or v==0:
                doheikin = False
            if doheikin and v<len(answer)-1 and answer[v][1]-answer[v-1][1]<heikin*7/10 and answer[v-1][3]-answer[v-1][1]<45 and answer[v][3]-answer[v][1]<45 and todoflag:
                del answer[v]
                todoflag=False
            else :
                todoflag=True
            v=v+1
    i=0
    for c in answer:
        if c[0]=="," :
            continue
        if i==0 :
            first_x1=c[1]
            first_y1=c[2]
        last_x2=c[3]
        last_y2=c[4]
        text+=c[0]
        i+=1
    if text=="" :
        text=None
    if text is not None and text!="" and first_x1 is not None and first_y1 is not None :
        for t in kojin_tri :
            if t[0]>first_x1-300 and t[0]<first_x1 and t[1]>first_y1-50 and t[1]<first_y1+50 :
                text="-"+text
    return text,first_x1,first_y1,last_x2,last_y2
def page_jyogai(source_texts,characters,text,fa):
    haveflag=False
    length=len(text)
    i=0
    totlen=len(characters)
    if totlen == 0 : 
        return source_texts,characters,haveflag
    deletindex=None;
    for i in range(totlen):
        targetText=text
        sum=0
        if(i+length<totlen) :
            for num in range(length):
                if characters[num+i]["text"] in targetText :
                    targetText.replace(characters[num+i]["text"], '')
                    sum=sum+1
                    if sum>=fa :
                        haveflag=True
                        deletindex=i
                        break
        if deletindex is not None :
            break
    if deletindex is not None :
        for num in range(totlen):
            if totlen-num-1>=deletindex :
                del characters[totlen-num-1]
        cnt = 0
        totlen=len(source_texts)
        cntindex=None
        for t in range(totlen):
            l = len(source_texts[t]['text'])
            if cnt+l>=deletindex :
                cntindex=t
                break
            cnt += l
        for num in range(totlen):
            if totlen-num-1>=cntindex :
                del source_texts[totlen-num-1]
    return source_texts,characters,haveflag
def page_jyogai2(source_texts,characters,text,fa):
    haveflag=False
    cont1=0
    cont2=0
    totlen=len(characters)
    if totlen == 0 : 
        return source_texts,characters,haveflag
    if text=="当期(首|末)残高" :
        deletindex=None;
        for i in range(totlen):
            if(i+5<totlen) :
                mototext=""
                for num in range(5):
                    mototext=mototext+characters[num+i]["text"]
                if mototext=="当期首残高" :
                    cont1=cont1+1
                    if deletindex == None :
                        deletindex=i
                if mototext=="当期末残高" :
                    cont2=cont2+1
                    if deletindex == None :
                        deletindex=i
                
            if deletindex is not None and cont1>=fa and cont2>=fa :
                haveflag=True
                break
        if deletindex is not None :
            for num in range(totlen):
                if totlen-num-1>=deletindex :
                    del characters[totlen-num-1]
            cnt = 0
            totlen=len(source_texts)
            cntindex=None
            for t in range(totlen):
                l = len(source_texts[t]['text'])
                if cnt+l>=deletindex :
                    cntindex=t
                    break
                cnt += l
            for num in range(totlen):
                if totlen-num-1>=cntindex :
                    del source_texts[totlen-num-1]
    else :
        return source_texts,characters,haveflag
    return source_texts,characters,haveflag

#右側から最初の数字を取得する
#oo:Y座標の膨脹距離
#作成者：尚
def get_right_number_endx(characters,x,y,line,end_x,oo,maxx,check,ALL,arg,kojin_tri):
    i=0
    #最初の1っ個数字
    first_x1=None;
    first_y1=None;
    first_x2=None;
    first_y2=None;
    text="";
    codes=[]
    #最初の1っ個数字
    last_x1=None;
    last_y1=None;
    last_x2=None;
    last_y2=None;
    answer=[]

    #同一Y座標のすべてのコードを取得
    for c in characters:
        if oo<0 :
            if c['bounds'].rect[1]>y+oo-10 and c['bounds'].rect[3]<y-oo+25:
                codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3]])
        else :
            if c['bounds'].rect[1]<y+oo and c['bounds'].rect[3]>y-oo:
                codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3]])
    codes = sorted(codes,key=lambda x:(x[1]))
    breakflag=False
    #数値を取り出す
    lastx2=None
    lastnumber=""
    mondai=[]
    seikaku=25
    i = -1
    for c in codes:
        i = i+1
        if c[1]>x+line and c[1]<end_x and (((c[0].isdecimal() or c[0]==','))  or c[0]=='-'):
          if ALL :
              answer.append(c)
              continue
          if len(answer)>0 and c[0].isdecimal()==False :
              continue
          #if c[0]!="1" and c[0]!="," and c[3]-c[1]+15<maxx*2/10 and check==False:
              #continue
          #if c[0]!="1" and c[0]!="," and c[3]-c[1]+4<maxx/5 and check:
              #continue
          if c[0]!="," and c[4]-c[2]<maxx*1/5 :
              continue
          #print("269>>>>>>"+c[0]+"_"+str(c[1])+"_"+str(y)+"_"+str(c[3]-c[1])+"_"+str(maxx))
          if lastx2 is None :
            if len(codes)>i+1 and ( codes[i+1][1]-c[1]< 28  and check==False ) and codes[i+1][0]!="," :
                continue
            if c[0]!="1" and len(codes)>i+1 and ( codes[i+1][1]-c[1]< 8  and check ) :
                continue
            lastx2=c[3]
            lastnumber=c[0]
            answer.append(c)
            breakflag=True

            if c[0]!="1" and c[0]!="2" :
              seikaku=c[3]-c[1]
            if c[3]-c[1]>maxx/3 and c[0]=="1" :
              mondai.insert(0,len(answer)-1)
          elif len(codes)>i+1 and ( codes[i+1][1]-c[1] > seikaku*2/3 or check or codes[i][3]-codes[i][1] > 3*seikaku or codes[i+1][3]-codes[i+1][1] > 3*seikaku) :
            lastx2=c[3]
            lastnumber=c[0]
            answer.append(c)
            breakflag=True
          
            if c[0]!="1" and c[0]!="2" and codes[i][3]-codes[i][1] < 3*seikaku :
              seikaku=c[3]-c[1]
            if c[3]-c[1]>maxx/3 and c[0]=="1" :
              mondai.insert(0,len(answer)-1)
          elif len(codes)==i+1:
            lastx2=c[3]
            lastnumber=c[0]
            answer.append(c)
            breakflag=True
          
            if c[0]!="1" and c[0]!="2" and codes[i][3]-codes[i][1] < 3*seikaku :
              seikaku=c[3]-c[1]
            if c[3]-c[1]>maxx/3 and c[0]=="1" :
              mondai.insert(0,len(answer)-1)
          else :
              continue
          """
          elif lastx2-12>c[1] :
            if c[0]=="1" and lastnumber!="1" :
              xxxxxxx=0
            else :
              answer.pop()
              lastx2=c[3]
              lastnumber=c[0]
              answer.append(c)
              breakflag=True

              if c[0]!="1" and c[0]!="2" :
                seikaku=c[3]-c[1]
              if c[3]-c[1]>maxx/3 and c[0]=="1" :
                mondai.insert(0,len(answer)-1)
          elif c[1]-lastx2<200 :
            lastx2=c[3]
            lastnumber=c[0]
            answer.append(c)
            breakflag=True
          
            if c[0]!="1" and c[0]!="2" :
              seikaku=c[3]-c[1]
            if c[3]-c[1]>maxx/3 and c[0]=="1" :
              mondai.insert(0,len(answer)-1)
          elif breakflag :
            continue
          """
        elif breakflag :
          if c[0]!="[" and c[0]!="]" and c[0]!="|" and c[1]>lastx2+18 and c[4]-c[2]>30 :
            continue

    for c in mondai:
      if answer[c][3]-answer[c][1] > seikaku+20 :
        del answer[c]



    answer = sorted(answer,key=lambda x:(x[1]))
    answer_len=len(answer);
    for o in range(answer_len):
        i=answer_len-o
        if i<=0 or i==answer_len :
            continue
        if answer[i][0]==answer[i-1][0] and abs(answer[i][1]-answer[i-1][1])<15 and abs(answer[i][2]-answer[i-1][2])<15 and abs(answer[i][3]-answer[i-1][3])<15 and abs(answer[i][4]-answer[i-1][4])<15:
            del answer[i]


    if arg : 
        #一数字しか識別できなかった場合
        if len(answer) == 1 :
            for c in answer:
                if c[4]-c[2]+7<maxx*1/5 :
                    del answer[0]               
        #平均文字距離
        heikin=0
        v=0
        doheikin = True
        
        for c in answer:
            if c[0]=="," :
                doheikin = False
            if doheikin and (c[0]=="1" or c[0]=="2" or c[0]=="3") and v>1 and answer[v][1]-answer[v-1][1]<heikin*5/8:
                debug_print("del answer",level=DEBUG_ROWS_INFO)
                debug_print(str(c[0]),level=DEBUG_ROWS_INFO)
                debug_print(str(heikin),level=DEBUG_ROWS_INFO)
                del answer[v]
                continue
            if v==0 :
                ak=0
            elif v==1 :
                heikin=answer[v][1]-answer[v-1][1]
            else :
                heikin=(heikin+answer[v][1]-answer[v-1][1])/2
            v=v+1
        #平均文字高さ
        heikin=0
        v=0
        doheikin = True
        
        for c in answer:
            if c[0]=="," :
                doheikin = False
            if doheikin and v>1 and c[4]-c[2]<heikin*1/2:
                debug_print("del answer",level=DEBUG_ROWS_INFO)
                debug_print(str(c[0]),level=DEBUG_ROWS_INFO)
                debug_print(str(heikin),level=DEBUG_ROWS_INFO)
                del answer[v]
                continue
            if v==0 :
                heikin=0
            elif v==1 :
                heikin=c[4]-c[2]
            else :
                heikin=(heikin+c[4]-c[2])/2
            v=v+1
        v=0
        #横平均距離を取得
        heikin=0
        for c in answer:
            if v==0 :
                heikin=0
            elif v==1 :
                heikin=c[3]-c[1]
            else :
                heikin=(heikin+c[3]-c[1])/2
            v=v+1

        v=0
        deleteindex=-1
        for c in answer:
            doheikin=True
            if c[0]==","  or v==0:
                doheikin = False
            if doheikin and v<len(answer)-1 and answer[v][1]-answer[v-1][1]>150 :
                deleteindex=v
            v=v+1
        v=0
        for c in answer:
            if v<deleteindex:
                del answer[v]
            v=v+1
        v=0
        #横平均距離を取得
        heikin=1000
        heikin_list=[]
        for c in answer:
            if v==0 :
                ak=0
            else:
                heikin_list.append(answer[v][1]-answer[v-1][1])
            v=v+1
        ld = sorted(heikin_list, reverse=True)
        ldsize=len(ld)/2
        v=0
        for c in ld:
            if v==0 :
                heikin=c
            elif v<ldsize :
                heikin=(heikin+c)/2
            v=v+1
        v=0
        todoflag=True
        for c in answer:
            doheikin=True
            if c[0]==","  or v==0:
                doheikin = False
            if doheikin and v<len(answer)-1 and answer[v][1]-answer[v-1][1]<heikin*7/10 and answer[v-1][3]-answer[v-1][1]<45 and answer[v][3]-answer[v][1]<45 and todoflag:
                del answer[v]
                todoflag=False
            else :
                todoflag=True
            v=v+1
            
    i=0
    for c in answer:
        if c[0]=="," :
            continue
        if i==0 :
            first_x1=c[1]
            first_y1=c[2]
        last_x2=c[3]
        last_y2=c[4]
        text+=c[0]
        i+=1 
    debug_print(str(text),level=DEBUG_ROWS_INFO)
    if text=="" :
        text=None
    if text=="2,243,,270" :
      print("359>>>>>>")
      codes=[]
      for c in characters:
            codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3]])
      codes = sorted(codes,key=lambda x:(x[1]))
      for c in answer:
        print(c)
    if text is not None and text!="" and first_x1 is not None and first_y1 is not None :
        for t in kojin_tri :
            y=(last_y2+first_y1)/2
            if int(t[0])>first_x1-300 and int(t[0])<first_x1 and int(t[1])<y and int(t[1])+int(t[3])>y :
                text="-"+text
    return text,first_x1,first_y1,last_x2,last_y2

#右側から最初の数字を取得する
#oo:Y座標の膨脹距離
#作成者：尚
def get_right_text_endx(characters,x,y,line,end_x,oo):
    i=0
    #最初の1っ個数字
    first_x1=None;
    first_y1=None;
    first_x2=None;
    first_y2=None;
    text="";
    codes=[]
    #最初の1っ個数字
    last_x1=None;
    last_y1=None;
    last_x2=None;
    last_y2=None;
    answer=[]

    #同一Y座標のすべてのコードを取得
    for c in characters:
        if oo<0 :
            if c['bounds'].rect[1]>y+oo and c['bounds'].rect[3]<y-oo:
                codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3]])
        else :
            if c['bounds'].rect[1]<y+oo and c['bounds'].rect[3]>y-oo:
                codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3]])
    codes = sorted(codes,key=lambda x:(x[1]))
    breakflag=False
    #数値を取り出す
    lastx2=None
    for c in codes:
        if c[1]>x+line and c[1]<end_x  and c[0].isdecimal()==False and c[0]!=',':
          if lastx2 is None :
            lastx2=c[3]
            answer.append(c)
            breakflag=True
          elif c[1]-lastx2<200 :
            lastx2=c[3]
            answer.append(c)
            breakflag=True
          elif breakflag :
            break
        elif breakflag :
            break
    answer = sorted(answer,key=lambda x:(x[1]))
    
    # 重複削除（x座標、y座標、文字が一致するものを除外）
    unique_answer = []
    seen = []

    tolerance_x = 30
    tolerance_y = 300

    for c in answer:
        char_text, cx, cy = c[0], c[1], c[2]
        is_duplicate = False
        for seen_char, seen_x, seen_y in seen:
            if (
                char_text == seen_char and
                abs(cx - seen_x) <= tolerance_x and
                abs(cy - seen_y) <= tolerance_y
            ):
                is_duplicate = True
                break
        if not is_duplicate:
            seen.append((char_text, cx, cy))
            unique_answer.append(c)    
    
    i=0
    for c in unique_answer:
        if i==0 :
            first_x1=c[1]
            first_y1=c[2]
        last_x2=c[3]
        last_y2=c[4]
        text+=c[0]
        i+=1 
    if text=="" :
        text=None
    return text,first_x1,first_y1,last_x2,last_y2
#販売費及び一般管理費内訳判断
def get_1_4_flag(characters):
    i=0
    c_len=len(characters)
    target="販売費及び一般管理費"
    target_len=len(target)
    target_len_c=target_len+3
    #計算できた合う比率
    real_math=0

    codes=[]
    ylist=[]
    for c in characters:
        addylistflag=True
        newy=0
        for y in ylist:
            if y+50>c['bounds'].rect[1] and y-50<c['bounds'].rect[1] :
                newy = y
                addylistflag=False
        if addylistflag :
            newy = c['bounds'].rect[1]
            ylist.append(c['bounds'].rect[1])
        codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3],newy])
    codes = sorted(codes,key=lambda x:(x[5],x[1]))
    for c in codes:
        #合計回数
        sub=0
        #今回の合う比率
        now_math=0
        #一番最後の文字位置
        last_num=None
        text=""
        for num in range(target_len_c):
            if i+num<c_len and codes[i+num][0] not in text and codes[i+num][0] in target and codes[i][0] == target[0] :
                sub+=1
                last_num=i+num
                now_math=sub/target_len
                text+=codes[i+num][0]
                if now_math>0.7 and num>=target_len and codes[i+num][2]<750 :
                    #内
                    uti=False
                    #訳
                    wake=False
                    for j in range(10):
                        if len(codes)> i+num+j and codes[i+num+j][0]=="内" :
                            uti=True
                        elif len(codes)> i+num+j and codes[i+num+j][0]=="訳" :
                            wake=True
                    if wake and uti :
                        return True
        i+=1
        if now_math>0.7 and codes[last_num][2]<750 :
            #内
            uti=False
            #訳
            wake=False
            for j in range(10):
                if len(codes)> last_num+j and codes[last_num+j][0]=="内" :
                    uti=True
                elif len(codes)> last_num+j and codes[last_num+j][0]=="訳" :
                    wake=True
            if wake and uti :
                return True
    return False
#正規表現　文字間のスペース
def regex_space(txt:str):

    regex = ''
    for c in txt.replace(' ','').replace('　',''): #既にある空白は削除
        regex += r'[\s　]*'
        #regex += r'(　|\s)*'
        #keyword += '( |　|\s)*'

        regex += re.escape(c)
        #if re.search('[\\\$\^\.\?\*\|\(\)\[\]\{\}]',c): #メタ文字をエスケープ
        #    regex += '\\'
        #regex += c

    if regex != '':
        regex += r'[\s　]*'
        #regex += r'(　|\s)*'
        #keyword += '( |　|\s)*'

    return regex

# グループ検索用　(文頭文末スペース無)
def regex_space2(txt:str):

    regex = ''
    for c in txt.replace(' ','').replace('　',''): #既にある空白は削除
        if regex != '':
            regex += r'[\s　]*'

        regex += re.escape(c)
        #if re.search('[\\\$\^\.\?\*\|\(\)\[\]\{\}]',c): #メタ文字をエスケープ
        #    regex += '\\'
        #regex += c

    return regex

address_regex = re.compile('(?![ -~０-９ａ-ｚＡ-Ｚ])(東京都|北海道|(?:京都|大阪)府|.{2,3}県)?((?:四日市|廿日市|野々市|臼杵|かすみがうら|つくばみらい|いちき串木野)市|(?:杵島郡大町|余市郡余市|高市郡高取)町|.{1,4}市.{1,4}区|.{1,3}区|.{1,5}市(?=.*市)|.{1,3}市|.{2,9}町(?=.*町)|.{2,9}町|.{3,8}村(?=.*村)|.{3,8}村)(.*)')
pref_regex = re.compile('[都道府県]')
pref_list = []      # 都道府県データ
city_regex = re.compile('市(?!区|町村|民|議)|(?<!市)区(?!別|域|分|画|民|議)|町(?!村|民|議)|(?<!町)村(?!民|議)')
#city_regex = re.compile('[市区町村]')
city_list = []      # 市区町村データ
# 住所検索用データの初期化
def init_address_data():

    global city_list
    global pref_list

    #dbname = 'address.db'
    dbname = os.path.join(os.path.dirname(__file__),'address.db')
    #print(dbname)
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    try:
        exe_str = 'SELECT pref_cd, name FROM city ORDER BY LENGTH(name) DESC'
        cur.execute(exe_str)
        for row in cur:
            city_list.append([row[0],row[1],re.compile('(.*?)('+regex_space(row[1])+')(.*)')])
            #city_list.append([row[0],row[1],re.compile('(.*?)('+row[1]+')(.*)')])

        #print(city_list)

        exe_str = 'SELECT pref_cd, name FROM pref'
        cur.execute(exe_str)
        #pref_list = cur.fetchall()
        for row in cur:
            pref_list.append([row[0],row[1],re.compile('(.*?)('+regex_space(row[1])+')(.*)')])

        #print(pref_list)

    except:
        None

    conn.close()

#日付
#正規表現　パターンコンパイル
search_pat_date   = []
# 明治、大正、昭和、平成31年or令和元年12月31日
search_pat_date.append(re.compile(r'(.*)((?:令和|平成|昭和|大正|明治)\s*(?:\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*(?:(?:(?:\d{1,2}|末)\s*日)|(?:[初上中下]旬)))(.*)'))
#search_pat_date.append(re.compile(r'(.*)((?:令和|平成|昭和|大正|明治)\s*(?:\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*(?:\d{1,2}|末)\s*日)(.*)'))
#search_pat_date.append(re.compile(r'(.*)((?:令和|平成|昭和|大正|明治)\s*(?:\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)(.*)'))
#search_pat_date.append(re.compile(r'(令和|平成|昭和|大正|明治)\s*(\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
# M、T、S、H31年orR元年12月31日
search_pat_date.append(re.compile(r'(.*)((?:R|Ｒ|H|Ｈ|S|Ｓ|T|Ｔ|M|Ｍ)\s*(?:\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*(?:(?:(?:\d{1,2}|末)\s*日)|(?:[初上中下]旬)))(.*)',flags=re.IGNORECASE))
#search_pat_date.append(re.compile(r'(.*)((?:R|Ｒ|H|Ｈ|S|Ｓ|T|Ｔ|M|Ｍ)\s*(?:\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*(?:\d{1,2}|末)\s*日)(.*)',flags=re.IGNORECASE))
#search_pat_date.append(re.compile(r'(.*)((?:R|Ｒ|H|Ｈ|S|Ｓ|T|Ｔ|M|Ｍ)\s*(?:\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)(.*)',flags=re.IGNORECASE))
#search_pat_date.append(re.compile(r'(R|Ｒ|H|Ｈ|S|Ｓ|T|Ｔ|M|Ｍ)\s*(\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日',flags=re.IGNORECASE))
# 平成31年or令和元年12月31日
#search_pat_date.append(re.compile(r'(令和|平成)\s*(\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
#search_pat_date.append(re.compile(r'(令和|平成)\s*\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
# 令和元年12月31日
#search_pat_date.append(re.compile(r'令和\s*元\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
# [20]19年12月31日
#search_pat_date.append(re.compile(r'(.*)(\d{2,4}\s*年\s*(?:\(.*\))*\d{1,2}\s*月\s*\d{1,2}\s*日)(.*)'))
#search_pat_date.append(re.compile(r'(.*)(\d{2,4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)(.*)'))
search_pat_date.append(re.compile(r'(.*?)(\d{2,4}\s*年\s*(?:\(.*\))*s*\d{1,2}\s*月\s*(?:(?:(?:\d{1,2}|末)\s*日)|(?:[初上中下]旬)))(.*)'))
#search_pat_date.append(re.compile(r'(\D*)(\d{2,4}\s*年\s*(?:\(.*\))*s*\d{1,2}\s*月\s*(?:(?:(?:\d{1,2}|末)\s*日)|(?:[初上中下]旬)))(.*)'))
#search_pat_date.append(re.compile(r'(\D*)(\d{2,4}\s*年\s*(?:\(.*\))*s*\d{1,2}\s*月\s*(?:\d{1,2}|末)\s*日)(.*)'))
#search_pat_date.append(re.compile(r'(\D*)(\d{2,4}\s*年\s*(?:\(.*\))*s*\d{1,2}\s*月\s*\d{1,2}\s*日)(.*)'))
#search_pat_date.append(re.compile(r'\d{2,4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
#Jan,1,2019
search_pat_date.append(re.compile(r'(.*)((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*,\s*\d{1,2}\s*,\s*\d{2,4})(.*)',flags=re.IGNORECASE))
#search_pat_date.append(re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*,\s*\d{1,2}\s*,\s*\d{2,4}',flags=re.IGNORECASE))

# [20]19/12/31
# [20]19-12-31
# 上記パータン以外の文字列がある場合は対象外
search_pat_date.append(re.compile(r'(.*)(^[\s　]*\d{2,4}\s*[／/-]\s*\d{1,2}\s*[／/-]\s*\d{1,2}[\s　]*$)(.*)'))
#search_pat_date.append(re.compile(r'\d{2,4}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{1,2}'))

# 日付指定で　/／が　1 として読み込まれる時用のパターン
search_pat_date_revise_slash = re.compile(r'(\d{2,4})\s*[／/17]\s*(\d{1,2})\s*[／/17]\s*(\d{1,2})')
#search_pat_date_rep = re.compile(r'^[\s　]*\d{2,4}\s*[／/17]\s*\d{1,2}\s*[／/17]\s*\d{1,2}[\s　]*$')
# 未使用　RHSTM => 令和、平成... に変換する為のパターン (上の日付フォーマットと同じ)
#search_pat_date_revise_nengo  = re.compile(r'(R|Ｒ|H|Ｈ|S|Ｓ|T|Ｔ|M|Ｍ)\s*(\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*(?:\d{1,2}|末)\s*日',flags=re.IGNORECASE)

# 和yy年mm月dd日 => yy = 昭和 > 10 >= 令和 に変換する為のパターン
search_pat_date_reiwa_showa = re.compile(r'(.?\s*[昭令和])\s*(\d{1,2}|元)\s*年\s*(\d{1,2}\s*月)\s*((?:(?:\d{1,2}|末)\s*日)|(?:[初上中下]旬))')
# search_pat_date_reiwa_showa = re.compile(r'(.?\s*和)\s*(\d{1,2}|元)\s*年\s*(\d{1,2}\s*月)\s*((?:(?:\d{1,2}|末)\s*日)|(?:[初上中下]旬))')
#search_pat_date_reiwa_showa = re.compile(r'(.?\s*和)\s*(\d{1,2}|元)\s*年\s*(\d{1,2})\s*月\s*((?:\d{1,2}|末))\s*日')
#search_pat_date_reiwa_showa = re.compile(r'(令和|昭和|和)\s*(\d{1,2}|元)\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日')

search_pat_wareki_YMD = re.compile(r'([^0-9元]*)([0-9元]+)[^0-9]+([0-9]+)[^0-9]+([0-9]+)([^0-9]*)')

def search_date(txt:str):

    for pat in search_pat_date:
        ret = pat.search(txt)
        if ret:
            grp = ret.groups()
            return ret
            #return ret.group()

    return None
    #return ''

def search_date2(txt:str):

    ret2 = search_date(txt)
    if ret2:
        grp2 = ret2.groups()
        ret1 = search_date(grp2[0])
        if ret1:
            grp1 = ret1.groups()

            if '至' in grp1[2]:
                grps = [(grp1[0],grp1[1],''),(grp1[2],grp2[1],grp2[2])]
            else:
                grps = [grp1,('',grp2[1],grp2[2])]
        else:
            grps = [grp2]

        return grps
        # return ret2

    return None


# 日付 '/' -> '1' として認識した場合を想定して正しい日付に戻す
# RHSTM => 令和、平成... に変換する
def revise_date(txt:str):

    ret = search_pat_date_revise_slash.search(txt)

    if ret != None:
        try:
            gs = ret.groups()
            #g = ret.group()
            y = int(gs[0])
            m = int(gs[1])
            d = int(gs[2])
            #ret = None
            if y <= 99 or (y >= 1868 and y <= 2099):
                if m >= 1 and m <= 12:
                    if d >= 1 and d <= 31:
                        txt = str(y).zfill(len(gs[0])) + '/' + str(m).zfill(len(gs[1])) + '/' + str(d).zfill(len(gs[2]))
                        #ret = search_pat_date_revise.search(txt)
        except:
            None

    return txt

# 和yy年mm月dd日 => yy = 昭和 > 50 >= 令和 に変換する
def revise_date_nengo(txt:str, threshold=50):

    ret = search_pat_date_reiwa_showa.search(txt)

    if ret != None:
        try:
            gs = ret.groups()

            nengo = gs[0].replace(' ','').replace('　','') #空白は削除
            if nengo != '昭和' and nengo != '令和':
                if gs[1] == '元':
                    y = 0
                else:
                    y = int(gs[1])

                if nengo == '令':
                    nengo = '令和'
                elif nengo == '昭':
                    nengo = '昭和'
                else:
                    if y > threshold:
                        nengo = '昭和'
                    else:
                        nengo = '令和'

                # if y > threshold:
                #     pref = '昭'
                # else:
                #     pref = '令'

                st = ret.regs[1][0]
                ed = ret.regs[1][1]

                txt = txt[:ed-1] + nengo + txt[ed:] #'和'の前に挿入(ed = 必ず'和')
                # txt = txt[:ed-1] + pref + '和' + txt[ed:] #'和'の前に挿入(ed = 必ず'和')
#                txt = txt[:st] + pref + '和' + txt[ed:]

        except:
            None

    return txt

# 和暦 -> 西暦
def revise_date_to_AD(txt:str):

    ret = search_pat_wareki_YMD.search(txt)
    if not ret:
        return None

    W   = ret.group(1)
    if ret.group(2) == '元':
        Y = 1
    else:
        Y   = int(ret.group(2))
    M   = int(ret.group(3))
    D   = int(ret.group(4))

    # 昭和:1926 - 平成:1989 - 令和:2019
    if '昭' in W: # 和は令和の可能性が高い
        Y += (1926-1)
    elif '平' in W or '成' in W:
        Y += (1989-1)
    elif '令' in W or '和' in W:
        Y += (2019-1)

    # ２桁の場合は西暦２桁とみなす
    if Y <= 50:
        Y += 2000
    elif Y <= 100: # 100はOKとする
    # elif Y <= 99:
        Y += 1900
    # else:
    elif Y <= 999: # 3桁はNG
        return None

    ad = f'{Y:4}/{M:02}/{D:02}'
    try:
        _ = datetime.datetime.strptime(ad, '%Y/%m/%d')
    except:
        ad = None

    return ad

#金額

#正規表現　パターンコンパイル
search_pat_cmm_yen   = re.compile(r'([^\\￥\$＄\-―△▽▲▼AＡへ\d]*)([\\￥\$＄\-―△▽▲▼AＡへ]?[0-9０-９,，.．、<>]+円)(.*)')
#search_pat_cmm_amount   = re.compile(r'([^\\￥\$＄\-―△▽▲▼AＡへ\d]*)([\\￥\$＄\-―△▽▲▼AＡへ]?[0-9０-９,，.．]+円?)(.*)')
#search_pat_cmm_amount   = re.compile(r'([^\\￥\$＄\-―△▲\d]*)([\\￥\$＄\-―△▲]?(?:(?:(?:[1-9]\d*)(?:[,\.]\d{3})*)|0)(?:\.\d+)?円?)(\D*)')

search_pat_cmm_mount = re.compile(r'([^\\￥\$＄\-―△▽▲▼AＡへ\d]*)([\\￥\$＄\-―△▽▲▼AＡへ]?[0-9０-９,，.．]+)(.*)')

search_pat_amount1      = re.compile(r'[￥＄][,.，．０-９0-9　\s￥＄]+')
search_pat_amount2      = re.compile(r'[０-９0-9]+')
#search_pat_amount       = []
#search_pat_amount.append(re.compile(r'[￥＄][,.\d　\s]+'))
#search_pat_amount.append(re.compile(r'[￥＄](　|\s)*\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*'))
#search_pat_amount.append(re.compile(r'[￥＄]?\b\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*(　|\s)*\b[円]?'))
#search_pat_amount.append(re.compile(r'[￥＄]\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*'))
#search_pat_amount.append(re.compile(r'\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*(　|\s)*[円]'))

#search_pat_amount       = re.compile(r'\b[¥著者至半\\￥\$＄]?\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*(　|\s)*(円)?\b')
search_pat_amount_sig    = re.compile(r'[￥＄]')
search_pat_amount_sig1   = re.compile(r'[¥著者至半\\]')
search_pat_amount_sig2   = re.compile(r'[\$]')

search_pat_number   = re.compile(r'([^\-\d]*)([\-]?[0-9０-９,，.．]+)(.*)')


#search_pat_number   = re.compile(r'([^\\￥\$＄\-―△▲\d\(]*)([\\￥\$＄\-―△▲]?[0-9０-９,，.．\-\(\)]+円?)(.*)')
#search_pat_number   = re.compile(r'([^\\￥\$＄\-―△▲\d\(]*)([\\￥\$＄\-―△▲]?[0-9０-９,，.．\-\(\)]+円?)(\D*)')

def replace_amount_sig(txt:str):
    ret = search_pat_amount_sig1.sub('￥', txt)
    ret = search_pat_amount_sig2.sub('＄', ret)

    return ret

def search_amount(txt:str):

    #txt = replace_amount_sig(txt)
    #txt = search_pat_amount_sig1.sub('￥', txt)
    #txt = search_pat_amount_sig2.sub('＄', txt)

    ret = search_pat_amount_sig.search(txt)
    if ret: # ￥＄があるのでその後ろを抽出
        ret = search_pat_amount1.search(txt)
        if ret:
            g = ret.group()
            ret2 = search_pat_amount2.search(g) # ￥＄の後ろに数字が無ければ除外
            if ret2:
                return ret

    return None
    #return ''

MINUS_SIG = '―△▽▲▼AＡへ'
def search_cmm_yen(txt:str):

    ret = search_pat_cmm_yen.search(txt)
    if ret:
        # ―△▽▲▼AＡへをマイナス(-)に変換
        grp = ret.groups()
        if grp[1][0] in MINUS_SIG:
            s = '-' + grp[1][1:]
            txt2 = grp[0] + s + grp[2]
            ret = search_pat_cmm_yen.search(txt2)

        return ret

    return None

def search_cmm_mount(txt:str):

    ret = search_pat_cmm_mount.search(txt)
    if ret:
        # ―△▽▲▼AＡへをマイナス(-)に変換
        grp = ret.groups()
        if grp[1][0] in MINUS_SIG:
            s = '-' + grp[1][1:]
            txt2 = grp[0] + s + grp[2]
            ret = search_pat_cmm_mount.search(txt2)

        return ret

    return None

def search_number(txt:str):

    ret = search_pat_number.search(txt)
    if ret:
        return ret

    return None

# 住所検索
def search_address(txt_src_org, chars=None): #, rm_head_word=True):

    found = False
    ret_address = None

    txt_src = txt_src_org
    #txt_src = txt_src_org.replace(' ','').replace('　','')
    #a1 = ''
    #a2 = ''
    #a3 = ''
    #a4 = ''

    ret = city_regex.search(txt_src)
    if ret: # 全てを検索すると重くなるので"市区町村"が含まれているのものだけ
        if chars: #
            # charsの情報がある場合は行内だけを検索対象とする
            serial_row = chars[ret.regs[0][0]]['row']['serial_row']
            txt_row = chars[ret.regs[0][0]]['row']['text']
            # aaaaaaaaaaaa = 0
            for i, city in enumerate(city_list):
                addr = city[2]
                ret = addr.search(txt_row)
                if ret:
                    ret = None
                    found = True
                    break
            else:
                found = False
        else:
            # charsの情報がない場合はtxt_srcを対象とする
            for i, city in enumerate(city_list):
                addr = city[2]
                ret = addr.search(txt_src)
                if ret:
                    found = True
                    break
            else:
                found = False

        if found:
            if ret == None:
                # 行内を対象とした場合は全体(txt_src)でもう一度検索
                ret = addr.search(txt_src)
            if ret:
                grps = ret.groups()

                a1 = ret.group(0) # 全体
                a2 = ret.group(1) # 前（都道府県とは限らない）
                a3 = ret.group(2) # 市区町村
                a4 = ret.group(3) # 後ろ

                if a2: # 都道府県以外の文字は取り除く
                    ret2 = pref_list[city[0]-1][2].search(a2)
                    if ret2:
                        grps = ret2.groups()
                        #a5 = ret2.group(3)
                        if ret2.group(2) == pref_list[city[0]-1][1] and ret2.group(3) == '':
                            a2 = ret2.group(2)
                        elif ret2.group(3) != '':
                            a2 = ''
                    else:
                        a2 = ''

                    #if pref_list[city[0]-1][1] in a2:
                    #    # 都道府県名が含まれていれば、それ以外のものを取り除く
                    #    a2 = pref_list[city[0]-1][1]
                    #elif rm_head_word:
                    #    a2 = ''
                    #rm_head_word==Falseの場合で含まれていなければそのまま

                else:
                    a2 = ''

                if chars and len(a4) > 0: # 行が変わったところを住所の終わりとする
                    a4 = ''
                    serial_row = chars[ret.regs[3][0]-1]['row']['serial_row']
                    for i in range(ret.regs[3][0],ret.regs[3][1]):
                        if serial_row != chars[i]['row']['serial_row']:
                            break
                        a4 += chars[i]['text']

                ret_address = a2 + a3 + a4
                #ret_address = ret_address.replace(' ','').replace('　','')

                regex = '(.*?)(' + regex_space2(ret_address) + ')(.*)'

                #ret2 =  re.search(regex,txt_src)
                #if ret2 == None:
                #    bbb = 0

                try:
                    ret =  re.search(regex,txt_src)
                    #if ret == None:
                    #    bbb = 0
                    grps = ret.groups()
                except:
                    print('ERROR:\n{}\n{}\n'.format(regex,txt_src), file=debug_file)
                    if DEBUG_PRINT_TO_FILE: # ファイル出力ならコンソールにも出力
                        print('ERROR:\n{}\n{}\n'.format(regex,txt_src))

                    traceback.print_exc(file=debug_file)
                    if DEBUG_PRINT_TO_FILE: # ファイル出力ならコンソールにも出力
                        traceback.print_exc()

                if DEBUG_BOUND_INFO >= DEBUG_PRINT_LEVEL:
                    debug_print(txt_src_org,level=DEBUG_BOUND_INFO)
                    if ret_address:
                        debug_print('{}\n{},{},{}\n\n{}'.format(a1,a2,a3,a4,ret_address),level=DEBUG_BOUND_INFO)
                    debug_print('--------------------\n',level=DEBUG_BOUND_INFO)

                found = True

            else:
                found = False # この行に来るのは文字化けの可能性もある
    else:
        found = False

    #if DEBUG_BOUND_INFO >= DEBUG_PRINT_LEVEL:
    #    debug_print(txt_src_org,level=DEBUG_BOUND_INFO)
    #    if ret_address:
    #        debug_print('{}\n{},{},{}\n\n{}'.format(a1,a2,a3,a4,ret_address),level=DEBUG_BOUND_INFO)
    #    debug_print('--------------------\n',level=DEBUG_BOUND_INFO)

    return ret if found == True else None

def find_address(txt_src_org):

    ret = search_address(txt_src_org)#,rm_head_word=False)
    if ret:
        return ret.group(2)

    return None

#(?:*)
#、、、、カ月、ヵ月、か月、ケ月、%、％、年
#　　　No.9999、ｎ項、（n) 、階、回、カ年、ヵ年、か年、ｹ年、n日


search_pat_unit_after    = re.compile(r'(.*?)([0-9０-９,，.．]+(?:項|回|%|％))(.*)')
#search_pat_unit_after    = re.compile(r'(.*?)([0-9０-９,，.．]+(?:項|階|F|Ｆ|回|%|％|号室))(.*)')
search_pat_unit_building    = re.compile(r'(.*?)([0-9０-９,，.．]+(?:階|F|Ｆ|号室))(.*)')

# search_pat_unit_after    = re.compile(r'(.*?)([0-9０-９,，.．]+[項|階|F|Ｆ|回|%|％|号室])(.*)')
#search_pat_unit_after    = re.compile(r'(\D*)([0-9０-９,，.．]+[項|階|F|Ｆ|回|%|％])(.*)')
#search_pat_unit_after    = re.compile(r'(\D*)([0-9０-９,，.．]+(?:平米|㎡|m|ｍ|坪|[カヵかヶケ]*[月年日]|項|階|回]))(.*)')
search_pat_unit_before   = re.compile(r'(.*(?!No.|NO.|no.|Ｎｏ.)?)((?:No.|NO.|no.|Ｎｏ.)[0-9０-９\-ー]+)(.*)')
#search_pat_unit_before   = re.compile(r'(.*)((?:[No|NO|no|Ｎｏ](?:\.．))[0-9０-９,，.．]+)(.*)')
#search_pat_unit   = re.compile(r'(\D*)([0-9０-９,，.．]+)((?:[平米|㎡|m|ｍ|坪|[カヵかヶケ]*[月年]|平方]).*)')

search_pat_unit   = []
search_pat_unit.append([ r'[\(（]' , r'[\)）]' ])
search_pat_unit.append([ '第?' , '条' ])
for pat in search_pat_unit:
    tt = r'({}[0-9０-９]+?{})'.format(pat[0],pat[1])
    # tt = r'({}?[0-9０-９]+?{})'.format(pat[0],pat[1])
    #tt = r'({}?[0-9０-９]{})'.format(pat[0],pat[1])
    pat.append(tt)
    pat.append(re.compile(tt))
    #article_regex = re.compile(r'(.*?)(第)([0-9０-９]+?)(条)(.*)')

#search_pat_unit.append(re.compile(r'(\([￥＄]'))

def search_unit(txt:str):

    #ret = re.search(r'(.*[^第])(第?[0-9０-９]条)(.*)', txt)
    #if ret:
    #    grp = ret.groups()
    #    a = 0

    # 単位
    a = 0
    # 前後: (n)|第ｎ条
    for pat in search_pat_unit:
        ret = pat[3].search(txt)
        if ret:
            t = ret.group(1).replace('(','\(').replace(')','\)')
            regex = r'(.*)({})(.*)'.format(t)
            ret = re.search(regex,txt)
            if ret:
                grp = ret.groups()
                return ret

    # 後: 項|回|%|％
    ret = search_pat_unit_after.search(txt)
    if ret:
        grp = ret.groups()
        return ret
    # 前: No.
    ret = search_pat_unit_before.search(txt)
    if ret:
        grp = ret.groups()
        return ret

    return None

# 第n条　FindItem()で使用
search_pat_unit_article_no    = re.compile(r'(第?[0-9０-９]+?条)')
def search_unit_article_no(txt:str):
    ret = search_pat_unit_article_no.search(txt)
    if ret:
        grp = ret.groups()
        return ret

    return None

def search_unit_building(txt:str):

    # 後: 階|F|Ｆ|号室
    ret = search_pat_unit_building.search(txt)
    if ret:
        grp = ret.groups()
        return ret

    return None


# 条文の終わり
article_term_pat = []
article_term_pat.append(re.compile(r'本証??書.+通を作成し'))
article_term_pat.append(re.compile(r'^以上$'))
#article_term_pat.append(re.compile(r'^[(（]??特約事項[)）]??$'))

def search_article_terminate(txt:str):

    for pat in article_term_pat:
        ret = pat.search(txt)
        if ret:
            return ret

    return None

# 面積
search_pat_unit_area    = re.compile(r'(.*?)([0-9０-９,，.．]+(?:平米|平方米|㎡|m|ｍ|坪))(.*)')
#search_pat_unit_area    = re.compile(r'(\D*)([0-9０-９,，.．]+(?:平米|㎡|m|ｍ|坪))(.*)')
#search_pat_unit_area    = re.compile(r'(\D*)([0-9０-９,，.．]+(?:平米|㎡|m|ｍ|坪))(.*)')
#search_pat_unit_area    = re.compile(r'(\D*)([0-9０-９,，.．]+(?:平米|平方米|㎡|m|ｍ|坪))(.*)')
def search_unit_area(txt:str):
    ret = search_pat_unit_area.search(txt)
    if ret:
        grp = ret.groups()
        return ret

    return None
#search_unit_area('件のうち賃貸面積約98.00m、賃料315,000円(共益費・税込)、契')

# 期間(年月)
search_pat_unit_term_year_month = re.compile(r'(.*?)([0-9０-９,，.．半]+(?:[カヵかヶケ箇]*[月年]間?前?))(.*)')
#search_pat_unit_term = re.compile(r'(\D*)([0-9０-９,，.．半]+(?:[カヵかヶケ箇]*[月年]間?前?))(.*)')
#search_pat_unit_term = re.compile(r'(\D*)([0-9０-９,，.．半]+(?:[カヵかヶケ箇]*[月年日]間?前?))(.*)')
def search_unit_term_year_month(txt:str):

    #ret = search_date(txt)
    #if ret: # 日付に該当する文字列がある場合は無効とする
    #    return None

    ret = search_pat_unit_term_year_month.search(txt)
    if ret:
        grp = ret.groups()
        return ret

    return None

#search_unit_term('(この契約解除申出)第25条乙の都合により本件契約を解除する場合は、その15ヶ月前にあらかじめ、甲指定の解約届書をもって通告しておかなければならない。乙が上記予告期間に違反して解約届を提出した場合、すなわち解約届日より明渡日までが14ヶ月未満の場合でも乙は甲に対し解約届日より12ヶ月間に相当する賃料もしくは賃料相当の損害金を支払わねばならない。甲が解約届書を受理した後には一切の変更は認めず、また乙は解約届書の各条項を避守することとする。')

# 期間(月)

search_pat_unit_term_month = re.compile(r'(.*?)([0-9０-９,，.．]+(?:[カヵかヶケ箇]月(?!前)))(.*)')
#search_pat_unit_term_month = re.compile(r'(.*?)(\d{1,2}(?:[カヵかヶケ箇]月(?!前)))(.*)')
#search_pat_unit_term_month = re.compile(r'(.*)(\d{1,2}(?:[カヵかヶケ箇]月[^前]))(.*)')
#search_pat_unit_term_month = re.compile(r'(\D*)([0-9０-９,，.．]+(?:[カヵかヶケ箇]月(?!前)))(.*)')
def search_unit_term_month(txt:str):

    ret = search_pat_unit_term_month.search(txt)
    if ret:
        grp = ret.groups()
        return ret

    return None

#search_unit_term_month('(この契約解除申出)第25条乙の都合により本件契約を解除する場合は、その15ヶ月前にあらかじめ、甲指定の解約届書をもって通告しておかなければならない。乙が上記予告期間に違反して解約届を提出した場合、すなわち解約届日より明渡日までが14ヶ月未満の場合でも乙は甲に対し解約届日より12ヶ月間に相当する賃料もしくは賃料相当の損害金を支払わねばならない。甲が解約届書を受理した後には一切の変更は認めず、また乙は解約届書の各条項を避守することとする。')

# 期間(前)
search_pat_unit_term_prior = re.compile(r'(.*?)([0-9０-９,，.．]+(?:[カヵかヶケ箇]月前))(.*)')
#search_pat_unit_term_prior = re.compile(r'(.*?)(\d{1,2}(?:[カヵかヶケ箇]月前))(.*)')
def search_unit_term_prior(txt:str):

    ret = search_pat_unit_term_prior.search(txt)
    if ret:
        grp = ret.groups()
        return ret

    return None
#search_unit_term_prior('(この契約解除申出)第25条乙の都合により本件契約を解除する場合は、その15ヶ月前にあらかじめ、甲指定の解約届書をもって通告しておかなければならない。乙が上記予告期間に違反して解約届を提出した場合、すなわち解約届日より明渡日までが14ヶ月未満の場合でも乙は甲に対し解約届日より12ヶ月間に相当する賃料もしくは賃料相当の損害金を支払わねばならない。甲が解約届書を受理した後には一切の変更は認めず、また乙は解約届書の各条項を避守することとする。')
#search_unit_term_prior('にあらかじめ、甲指定の解約届書をもって通告しておかなければならない。乙が上記予告期間に違反して解約届を提出した場合、すなわち解約届日より明渡日までが14ヶ月未満の場合でも乙は甲に対し解約届日より12ヶ月間に相当する賃料もしくは賃料相当の損害金を支払わねばならない。甲が解約届書を受理した後には一切の変更は認めず、また乙は解約届書の各条項を避守することとする。')

    #       obj         self
    #     [0]  [2]    [0]  [2]
    #a  ? 10 - 50     49 - 100
    #b    10 - 50     51 - 100
    #c  ? 49 - 100    10 - 50
    #d    51 - 100    10 - 50

    def get_space(self,obj):
        #return self.rect[0] - obj.rect[2]
        #if self.rect[0] >= obj.rect[2] or obj.rect[2] >= self.rect[0]:  # a, b
        #    return self.rect[0] - obj.rect[2]
        #else:                                                           # c, d
        #    return obj.rect[0] - self.rect[2]

        if self.rect[0] >= obj.rect[2]:         # b
            return self.rect[0] - obj.rect[2]
        elif self.rect[2] >= obj.rect[0]:       # (a, b, c)
            if obj.rect[2] >= self.rect[0]:     # a
                return self.rect[0] - obj.rect[2]
            else:                               # c
                return obj.rect[0] - self.rect[2]
        else:                                   # d
            return obj.rect[0] - self.rect[2]

'''
#日付
#正規表現　パターンコンパイル
search_pat_date   = []
# 明治、大正、昭和、平成31年or令和元年12月31日
search_pat_date.append(re.compile(r'(令和|平成|昭和|大正|明治)\s*(\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
# M、T、S、H31年orR元年12月31日
search_pat_date.append(re.compile(r'(R|Ｒ|H|Ｈ|S|Ｓ|T|Ｔ|M|Ｍ)\s*(\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日',flags=re.IGNORECASE))
# 平成31年or令和元年12月31日
#search_pat_date.append(re.compile(r'(令和|平成)\s*(\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
#search_pat_date.append(re.compile(r'(令和|平成)\s*\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
# 令和元年12月31日
#search_pat_date.append(re.compile(r'令和\s*元\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
# [20]19年12月31日
search_pat_date.append(re.compile(r'\d{2,4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'))
#Jan,1,2019
search_pat_date.append(re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*,\s*\d{1,2}\s*,\s*\d{2,4}',flags=re.IGNORECASE))

# [20]19/12/31
# [20]19-12-31
# 上記パータン以外の文字列がある場合は対象外
search_pat_date.append(re.compile(r'^[\s　]*\d{2,4}\s*[／/-]\s*\d{1,2}\s*[／/-]\s*\d{1,2}[\s　]*$'))
#search_pat_date.append(re.compile(r'\d{2,4}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{1,2}'))

# 日付指定で　/／が　1 として読み込まれる時用のパターン
search_pat_date_revise_slash = re.compile(r'(\d{2,4})\s*[／/17]\s*(\d{1,2})\s*[／/17]\s*(\d{1,2})')
#search_pat_date_rep = re.compile(r'^[\s　]*\d{2,4}\s*[／/17]\s*\d{1,2}\s*[／/17]\s*\d{1,2}[\s　]*$')
# RHSTM => 令和、平成... に変換する為にパターン (上の日付フォーマットと同じ)
search_pat_date_revise_nengo  = re.compile(r'(R|Ｒ|H|Ｈ|S|Ｓ|T|Ｔ|M|Ｍ)\s*(\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日',flags=re.IGNORECASE)

def search_date(txt:str):

    for pat in search_pat_date:
        ret = pat.search(txt)
        if ret:
            return ret
            #return ret.group()

    return None
    #return ''

# 日付 '/' -> '1' として認識した場合を想定して正しい日付に戻す
# RHSTM => 令和、平成... に変換する
def revise_date(txt:str):

    ret = search_pat_date_revise_slash.search(txt)

    if ret != None:
        try:
            gs = ret.groups()
            g = ret.group()
            y = int(gs[0])
            m = int(gs[1])
            d = int(gs[2])
            #ret = None
            if y <= 99 or (y >= 1868 and y <= 2099):
                if m >= 1 and m <= 12:
                    if d >= 1 and d <= 31:
                        txt = str(y).zfill(len(gs[0])) + '/' + str(m).zfill(len(gs[1])) + '/' + str(d).zfill(len(gs[2]))
                        #ret = search_pat_date_revise.search(txt)
        except:
            None

    return txt

#金額

#正規表現　パターンコンパイル
search_pat_amount1      = re.compile(r'[￥＄][,.，．０-９0-9　\s￥＄]+')
search_pat_amount2      = re.compile(r'[０-９0-9]+')
#search_pat_amount       = []
#search_pat_amount.append(re.compile(r'[￥＄][,.\d　\s]+'))
#search_pat_amount.append(re.compile(r'[￥＄](　|\s)*\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*'))
#search_pat_amount.append(re.compile(r'[￥＄]?\b\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*(　|\s)*\b[円]?'))
#search_pat_amount.append(re.compile(r'[￥＄]\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*'))
#search_pat_amount.append(re.compile(r'\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*(　|\s)*[円]'))

#search_pat_amount       = re.compile(r'\b[¥著者至半\\￥\$＄]?\d(　|\s)*\d?(　|\s)*\d?(　|\s)*(,(　|\s)*\d(　|\s)*\d(　|\s)*\d(　|\s)*)*(　|\s)*(円)?\b')
search_pat_amount_sig    = re.compile(r'[￥＄]')
search_pat_amount_sig1   = re.compile(r'[¥著者至半\\]')
search_pat_amount_sig2   = re.compile(r'[\$]')

def replace_amount_sig(txt:str):
    ret = search_pat_amount_sig1.sub('￥', txt)
    ret = search_pat_amount_sig2.sub('＄', ret)

    return ret

def search_amount(txt:str):

    #txt = replace_amount_sig(txt)
    #txt = search_pat_amount_sig1.sub('￥', txt)
    #txt = search_pat_amount_sig2.sub('＄', txt)

    ret = search_pat_amount_sig.search(txt)
    if ret: # ￥＄があるのでその後ろを抽出
        ret = search_pat_amount1.search(txt)
        if ret:
            g = ret.group()
            ret2 = search_pat_amount2.search(g) # ￥＄の後ろに数字が無ければ除外
            if ret2:
                return ret

    return None
    #return ''

'''

