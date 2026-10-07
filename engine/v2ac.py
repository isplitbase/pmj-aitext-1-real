'''
会計帳票
'''
ENGINE_VERSION = '093-v2ac-20230921'

# from http.client import NON_AUTHORITATIVE_INFORMATION
import  io, os
import csv
import re
import copy
import json
import difflib
from difflib import SequenceMatcher
from unicodedata import numeric
import datetime

import cv2 # opencv-python:4.1.2.30 -> 4.6.0.66
import numpy as np
# import matplotlib.pyplot as plt
# import pandas as pd


from operator import itemgetter

from pkg_resources import UnknownExtra
from .engine2 import engine2

import util.defines
from util.defines import *
from util.utility import *
from util.coordinate import Point, Bound

from enum import Enum, IntEnum
import sqlite3

# from .pre_process_image import del_line_str_right
import engine.pre_process_image as pre_process_image

# DEBUG
from PIL import Image, ImageDraw, ImageFont
def pil2cv(imgPIL):
    imgCV_RGB = np.array(imgPIL, dtype = np.uint8)
    imgCV_BGR = np.array(imgPIL)[:, :, ::-1]
    return imgCV_BGR

def cv2pil(imgCV):
    imgCV_RGB = imgCV[:, :, ::-1]
    imgPIL = Image.fromarray(imgCV_RGB)
    return imgPIL

def plot_labeling_box(img, labeling_box):
    RectColorRGB = (0, 255, 0)

    for i, lb in enumerate(labeling_box):
        aaa = 0
        for j, b in enumerate(lb):
            cv2.rectangle(img,(int(b[1]), int(b[2])),(int(b[1]+b[3]), int(b[2]+b[4])), RectColorRGB ,thickness=2)
            cv2.putText(img, f'{i}', (int(b[1])-8, int(b[2])+20), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(img, f'{j}', (int(b[1])-8, int(b[2])+44), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2, cv2.LINE_AA)



def plot_source_characters(img, source_characters, after=False):
    RectColorRGB = (0, 255, 0)
    textColorRGB = (255, 0, 0)
    if after:
        for c in source_characters:
            if 'dist' in c:
                cv2.rectangle(img,(int(c['bounds'].rect[0]), int(c['bounds'].rect[1])),(int(c['bounds'].rect[2]), int(c['bounds'].rect[3])), RectColorRGB ,thickness=2)
            else:
                cv2.rectangle(img,(int(c['bounds'].rect[0]), int(c['bounds'].rect[1])),(int(c['bounds'].rect[2]), int(c['bounds'].rect[3])), (255,0,0) ,thickness=4)

    else:
        for c in source_characters:
            cv2.rectangle(img,(int(c['bounds'].rect[0]), int(c['bounds'].rect[1])),(int(c['bounds'].rect[2]), int(c['bounds'].rect[3])),RectColorRGB,thickness=2)

    imgPIL = cv2pil(img)
    draw = ImageDraw.Draw(imgPIL)
    font_path = os.path.join(os.path.dirname(__file__),'meiryo.ttc')
    fontPIL_S = ImageFont.truetype(font_path, 20)
    fontPIL_M = ImageFont.truetype(font_path, 24)
    fontPIL_L = ImageFont.truetype(font_path, 32)

    if after:
        for c in source_characters:
            if 'dist' in c:
                w, h = draw.textsize(c['text'], font = fontPIL_S)
                # draw.text(xy = (int(c['bounds'].rect[0])-8, int(c['bounds'].rect[1])-h+8), text = '{}\n{},{}'.format(c['text'],c['dist'][0]['i'],c['dist'][0]['j']), fill = textColorRGB, font = fontPIL_S)
                draw.text(xy = (int(c['bounds'].rect[0])-8, int(c['bounds'].rect[1])-h+8), text = '{}'.format(c['text']), fill = textColorRGB, font = fontPIL_S)
                draw.text(xy = (int(c['bounds'].rect[0])-8, int(c['bounds'].rect[1])-h+28), text = '{}'.format(c['dist'][0]['i']), fill = textColorRGB, font = fontPIL_S)
                draw.text(xy = (int(c['bounds'].rect[0])-8, int(c['bounds'].rect[1])-h+44), text = '{}'.format(c['dist'][0]['j']), fill = textColorRGB, font = fontPIL_S)
            else:
                w, h = draw.textsize(c['text'], font = fontPIL_L)
                draw.text(xy = (int(c['bounds'].rect[0])-8, int(c['bounds'].rect[1])-h+8), text = '{}'.format(c['text']), fill = (0, 255, 255), font = fontPIL_L)
                aaa = 0
    else:
        for c in source_characters:
            w, h = draw.textsize(c['text'], font = fontPIL_M)
            draw.text(xy = (int(c['bounds'].rect[0])-8, int(c['bounds'].rect[1])-h+8), text = c['text'], fill = textColorRGB, font = fontPIL_M)

    imgCV = pil2cv(imgPIL)
    return imgCV



# 正規表現で補正
REGEX_REVISE = '__REGEX_REVISE__'

# 列を揃えた
COL_ALIGN    = '__COL_ALIGN__'

remove_brackets = re.compile(r'[(（\[<【]?([^)）\]>】]+)[)）\]>】]*')
# 勘定科目DB
class account_DB(object):

    COMBINE_CODE         = '{:02}{:03}{:02}{:02}'      # ORDER:FAMILY:GENUS:SPECIES
    to_def_code_WO_order =       (999,  99,  99, 999)  #       FAMILY:GENUS:SPECIES:VARIETY
    blank_code_dict = {'order':-1, 'family':-1, 'genus':-1, 'species':-1, 'variety':-1, 'property':-1, 'variety_name':''}
    # 対象外のテーブルタイトル(仮) -> DBへ移行予定
    except_table_subject = [
            '棚卸資産の計算内訳',
            '製造原価報告書',
            'たな卸資産の計算内訳',
            '株主資本変動計算書'
    ]


    class Order(IntEnum):
        NON = 0
        PL  = 1
        BS  = 2
        MAX = 10

    class Code(IntEnum):
        ORDER   = 0
        FAMILY  = 1
        GENUS   = 2
        SPECIES = 3
        VARIETY = 4
        PROPERTY = 5
        MAX = 6
    class table_type(object):

        def __init__(self, type, end, keyword, score) -> None:
            self.order   = type
            self.end     = end
            self.keyword = keyword
            self.score   = score

    def __init__(self) -> None:

        self.order = ()
        self.family = ()
        self.genus = ()
        self.species = ()
        self.variety = ()
        self.variety_code = ()

        self.order_title = ()
        self.family_title = ()
        self.genus_title = ()
        self.species_title = ()
        self.variety_title = ()

        self.variety_title_alphabet = ()

        # キャッシュを保存 get_variety_title_list()
        self.cache_variety_title_list = ()
        self.cache_variety_title_list_code = (-999,)
        self.cache_variety_title_list_between = (-999,)

        self.table_keyword = (
            # PLの開始判定用	[損益計算書,売上高,売上高合計,売上原価]
            account_DB.table_type( account_DB.Order.PL, 0, '損益計算書',      1),
            account_DB.table_type( account_DB.Order.PL, 0, '売上高',          1),#
            account_DB.table_type( account_DB.Order.PL, 0, '売上高合計',      1),
            account_DB.table_type( account_DB.Order.PL, 0, '売上原価',        1),

            # PLの終了判定用	[当期利益,当期純利益,法人税,税引前当期純利益,税引前当期純損失]
            account_DB.table_type( account_DB.Order.PL, 1, '税引前当期純利益',1),
            account_DB.table_type( account_DB.Order.PL, 1, '税引前当期純損失',1),
            account_DB.table_type( account_DB.Order.PL, 1, '当期純利益',     1),
            account_DB.table_type( account_DB.Order.PL, 1, '当期利益',       1),
            account_DB.table_type( account_DB.Order.PL, 1, '法人税',         1),#

            # BSの開始判定用	[貸借対照表,流動資産,現金,預金,売掛金]
            account_DB.table_type( account_DB.Order.BS, 0, '貸借対照表',      1),
            account_DB.table_type( account_DB.Order.BS, 0, '流動資産',        1),
            account_DB.table_type( account_DB.Order.BS, 0, '売掛金',          1),
            account_DB.table_type( account_DB.Order.BS, 0, '現金',            1),#
            account_DB.table_type( account_DB.Order.BS, 0, '預金',            1),

            # BSの終了判定用	[負債純資産,負債・純資産,負債及び純資産,純資産,利益剰余金,利益準備金,資本剰余金,資本金]
            account_DB.table_type( account_DB.Order.BS, 1, '負債及び純資産', 1),
            account_DB.table_type( account_DB.Order.BS, 1, '負債・純資産',   1),
            account_DB.table_type( account_DB.Order.BS, 1, '負債純資産',     1),
            account_DB.table_type( account_DB.Order.BS, 1, '利益剰余金',     1),
            account_DB.table_type( account_DB.Order.BS, 1, '利益準備金',     1),
            account_DB.table_type( account_DB.Order.BS, 1, '資本剰余金',     1),
            account_DB.table_type( account_DB.Order.BS, 1, '純資産',         1),
            account_DB.table_type( account_DB.Order.BS, 1, '資本金',         1),
        )

        try:

            # マスターJSONファイルの読み込み
            master_json = []
            # 勘定科目マスター
            kanjo_master_path = os.path.join(os.path.dirname(__file__),'../v2ac_kanjo_master.json')
            with open(kanjo_master_path, 'r', encoding='utf_8') as f:
                master_json = json.load(f)

            dt = datetime.datetime.fromtimestamp(os.path.getmtime(kanjo_master_path))

            debug_print( f'Kanjo master:<{dt}> {kanjo_master_path}', level=DEBUG_ROWS_INFO)

            # タイトル(order=3)はCSVから読み込んで追加する
            # title_csv_path = os.path.join(os.path.dirname(__file__),'v2ac_title.csv')
            # with open(title_csv_path, 'r', encoding='utf_8', errors='', newline='') as f:
            #     data = csv.reader(f, delimiter=',', doublequote=True, lineterminator='\r\n', quotechar='"', skipinitialspace=True)
            #     for r in data:
            #         item = {"order":int(r[0]),"order_name":r[1],"family":int(r[2]),"family_name":r[3],"genus":int(r[4]),"genus_name":r[5],"variety":int(r[6]),"variety_name":r[7],"property":int(r[8]) }
            #         master_json['kanjo_master'].append(item)

            order   = []
            family  = []
            genus   = []
            species = []
            variety = []

            for item in master_json['kanjo_master']:
                order.append((int(item['order']),item['order_name']))
                # order.append((int(item['order']), item['order_name']))
                family.append((int(item['order']), int(item['family']), item['family_name']))
                genus.append((int(item['order']), int(item['family']), int(item['genus']), item['genus_name']))

                if 'species' not in item:
                    aaa = 0
                species.append((int(item['order']), int(item['family']), int(item['genus']), int(item['species']), item['species_name']))
                variety.append((int(item['order']), int(item['family']), int(item['genus']), int(item['species']), int(item['variety']), int(item['property']), item['variety_name']))
                if '＊' in item['variety_name']: # *(半角)も登録
                    variety_name = item['variety_name'].replace('＊','*')
                    variety.append((int(item['order']), int(item['family']), int(item['genus']), int(item['species']), int(item['variety']), int(item['property']), variety_name))

            # タイトルはCSVから読み込んで追加する
            # title_csv_path = os.path.join(os.path.dirname(__file__),'v2ac_title.csv')
            # with open(title_csv_path, 'r', encoding='utf_8', errors='', newline='') as f:
            #     data = csv.reader(f, delimiter=',', doublequote=True, lineterminator='\r\n', quotechar='"', skipinitialspace=True)
            #     for r in data:
            #         item = {"order":int(r[0]),"order_name":r[1],"family":int(r[2]),"family_name":r[3],"genus":int(r[4]),"genus_name":r[5],"variety":int(r[6]),"variety_name":r[7],"property":int(r[8]) }
            #         order.append((int(item['order']),item['order_name']))
            #         family.append((int(item['order']), int(item['family']), item['family_name']))
            #         genus.append((int(item['order']), int(item['family']), int(item['genus']), item['genus_name']))
            #         variety.append((int(item['order']), int(item['family']), int(item['genus']), int(item['variety']), int(item['property']), item['variety_name']))

            def unique_list(seq, unique=True):
                if unique:
                    # 重複を削除
                    uni = []
                    data1 = [x for x in seq if x not in uni and not uni.append(x)]
                else:
                    data1 = seq

                data2 = [x[-1] for x in data1]

                return tuple(data1), tuple(data2)

            self.order,   self.order_title   = unique_list(order)
            self.family,  self.family_title  = unique_list(family)
            self.genus,   self.genus_title   = unique_list(genus)
            self.species, self.species_title = unique_list(species)
            self.variety, self.variety_title = unique_list(variety,False)

            variety_code = []
            variety_title_alphabet = []
            alphabet_regex = re.compile(r'(^[A-Za-zＡ-Ｚａ-ｚ]+)(.*)')

            for t in self.variety:
                # FAMILY->3ケタ
                code_val   = int(account_DB.COMBINE_CODE.format(  t[account_DB.Code.ORDER],  t[account_DB.Code.FAMILY],  t[account_DB.Code.GENUS],  t[account_DB.Code.SPECIES]))
                # code_val   = int('{:02}{:02}{:02}{:03}'.format(  t[account_DB.Code.ORDER],  t[account_DB.Code.FAMILY],  t[account_DB.Code.GENUS],  t[account_DB.Code.SPECIES]))
                variety_code.append(code_val)

                ret = alphabet_regex.search(t[-1])
                if ret:
                    # variety_title_alphabet.append(t[-1])
                    # variety_title_alphabet.append({'text':t[-1], 'alphabet':ret.group(1)})
                    variety_title_alphabet.append((ret.group(0),ret.group(1),ret.group(2)))

            self.variety_code = tuple(variety_code)
            self.variety_title_alphabet = tuple(variety_title_alphabet)

            # 会社マスター
            company_master_path = os.path.join(os.path.dirname(__file__),'../v2ac_company_master.json')
            with open(company_master_path, 'r', encoding='utf_8') as f:
                master_json = json.load(f)

            company = []
            company_title = []
            for item in master_json['company_master']:
                company.append((item['code'], item['name']))
                company_title.append((item['name']))
            company = tuple(company)
            company_title = tuple(company_title)

            # # マスターDBの読み込み
            # self.dbname = os.path.join(os.path.dirname(__file__),'v2ac.db')
            # conn = sqlite3.connect(self.dbname)
            # cur = conn.cursor()

            # def load(table_name):
            #     cur.execute(f'SELECT * FROM {table_name};')
            #     data1 = cur.fetchall()

            #     cur.execute(f'SELECT item FROM {table_name};')
            #     data2 = []
            #     for i in cur:
            #         data2.append(i[0])

            #     # data2.sort(key=lambda x: len(x), reverse=True) # ソートしても結果に変化なし

            #     return tuple(data1), tuple(data2)

            # self.order,    self.order_title =    load('type')
            # self.family,  self.family_title =  load('family')
            # self.genus,   self.genus_title =   load('genus')
            # # self.species, self.species_title = load('species')
            # self.variety, self.variety_title = load('variety')
            aaa = 0
        except:
            traceback.print_exc(file=util.utility.debug_file)
            if DEBUG_PRINT_TO_FILE: # ファイル出力ならコンソールにも出力
                traceback.print_exc()
            pass

        # "v2ac_subject"シートを ファイルの種類:CSV UTF-8(コンマ区切り)(*.csv) でエクスポート
        # 勘定科目置き換え(とりあえずCSVの読み込み)
        self.revise_subject_path = os.path.join(os.path.dirname(__file__),'v2ac_subject.csv')
        self.revise_subject_list = []
        try:
            # csv_file = open( self.revise_subject_path, 'r', encoding='cp932', errors='', newline='' )
            # csv_file = open( self.revise_subject_path, 'r', encoding='utf_8_sig', errors='', newline='' )
            csv_file = open( self.revise_subject_path, 'r', encoding='utf_8', errors='', newline='' )
            #リスト形式
            data = csv.reader(csv_file, delimiter=',', doublequote=True, lineterminator='\r\n', quotechar='"', skipinitialspace=True)

            for r in data:
                # r[0] = re.escape(r[0]) # 正規表現で指定するのでエスケープは不要
                self.revise_subject_list.append(r)
                aaa = 0

            self.revise_subject_list.sort(key=lambda x: len(x[0]), reverse=True)

            csv_file.close()
        except:
            pass

        aaa = 0

    # 勘定科目置き換え UNKNOWN
    def revise_subject(self, text):
        if not text:
            return None

        # 勘定科目置き換えリストと照合
        def search_revise_subject_list(t):
            for r in self.revise_subject_list:
                f = re.search(r[0], t)
                if f is not None:
                    return r

            return None

        ret = search_revise_subject_list(text)
        if ret:
            return ret

        # 全角以外を取り除く
        # not_zen = re.compile(f'[^{ZENKAKU}]')
        # f = not_zen.search(text)
        # if f:
        #     text2 = not_zen.sub('',text)
        #     if text == text2:
        #         return None

        #     ret = search_revise_subject_list(text2)
        #     if ret:
        #         # revise_subject_listにあれば返す
        #         return ret

        #     return [text, text2]

        return None

    def search_type(self, texts, ratio=0.7):

        for txt in texts:
            close = difflib.get_close_matches(txt, self.order_title,cutoff=ratio)
            if close:
                for r in self.order:
                    if r[1] == close[0]:
                        return r[0]

        return account_DB.Order.NON

    def search_type_title(self, title, ratio=0.7):

        close = difflib.get_close_matches( title, self.order_title,cutoff=ratio)

        return close
    def search_variety_title_syou(self, title, ratio=0.3, code=(), between=()):
        if title == '資産計io':
            aaa = 0
        # title = symbol.sub('',title) # 記号を削除 -> 削除すると精度が下がる可能性

        # title2 = begin_symbol.sub('',title) # 先頭のa-z0-9を削除
        # if title != title2:
        #     aaa = 0

        # 検索範囲を絞り込む
        title_list = self.get_variety_title_list(code, between)
        # title_list = self.get_variety_title_list(())

        title = begin_symbol.sub('',title) # 先頭のa-z0-9を削除

        # title1 = title
        # close1 = difflib.get_close_matches( title, title_list, cutoff=ratio)
        ## close1 = difflib.get_close_matches( title, self.variety_title,cutoff=ratio)

        l1 = len(title)

        title = remove_brackets.sub(r'\1', title) # カッコで囲まれている（精度下がる？？？）
        l2 = len(title)

        close = difflib.get_close_matches( title, title_list, n=40, cutoff=ratio)
        # close = difflib.get_close_matches( title, self.variety_title,cutoff=ratio)

        close=list(dict.fromkeys(close))
        
        for i, x in enumerate(close):
            if title==x :
                close[0], close[i] = close[i], close[0]

        if l1 != l2 and close:
            aaa = 0

        return close

    def search_variety_title(self, title, ratio=0.7, code=(), between=()):
        if title == '資産計io':
            aaa = 0
        # title = symbol.sub('',title) # 記号を削除 -> 削除すると精度が下がる可能性

        # title2 = begin_symbol.sub('',title) # 先頭のa-z0-9を削除
        # if title != title2:
        #     aaa = 0

        # 検索範囲を絞り込む
        title_list = self.get_variety_title_list(code, between)
        # title_list = self.get_variety_title_list(())

        title = begin_symbol.sub('',title) # 先頭のa-z0-9を削除

        # title1 = title
        # close1 = difflib.get_close_matches( title, title_list, cutoff=ratio)
        ## close1 = difflib.get_close_matches( title, self.variety_title,cutoff=ratio)

        l1 = len(title)

        title = remove_brackets.sub(r'\1', title) # カッコで囲まれている（精度下がる？？？）
        l2 = len(title)

        close = difflib.get_close_matches( title, title_list, cutoff=ratio)
        # close = difflib.get_close_matches( title, self.variety_title,cutoff=ratio)

        if l1 != l2 and close:
            aaa = 0

        return close

    # titleと勘定科目が"完全一致"
    def search_variety_code(self, title, code=(), between=()):
        code_len = len(code)
        between_len = len(between)

        if between_len == 0:
            for t in self.variety:
                if code == t[:code_len]:
                    if t[-1] == title:
                        return t[0:account_DB.Code.MAX]
        else:
            from_code  = code + ((0,) * (account_DB.Code.VARIETY+1-code_len))
            to_code = between + account_DB.to_def_code_WO_order[(between_len-1):]
            # to_code = between + ((0,) * (account_DB.Code.VARIETY+1-between_len))

            # FAMILY->3ケタ
            form_code_val = int(account_DB.COMBINE_CODE.format(from_code[account_DB.Code.ORDER],from_code[account_DB.Code.FAMILY],from_code[account_DB.Code.GENUS],from_code[account_DB.Code.SPECIES]))
            to_code_val   = int(account_DB.COMBINE_CODE.format(  to_code[account_DB.Code.ORDER],  to_code[account_DB.Code.FAMILY],  to_code[account_DB.Code.GENUS],  to_code[account_DB.Code.SPECIES]))
            # form_code_val = int('{:02}{:02}{:02}{:03}'.format(from_code[account_DB.Code.ORDER],from_code[account_DB.Code.FAMILY],from_code[account_DB.Code.GENUS],from_code[account_DB.Code.SPECIES]))
            # to_code_val   = int('{:02}{:02}{:02}{:03}'.format(  to_code[account_DB.Code.ORDER],  to_code[account_DB.Code.FAMILY],  to_code[account_DB.Code.GENUS],  to_code[account_DB.Code.SPECIES]))

            for i, c in enumerate(self.variety_code):
                if form_code_val <= c <= to_code_val:
                    if self.variety[i][-1] == title:
                        return self.variety[i][0:account_DB.Code.MAX]

        return () #[]
    def search_variety_codes(self, title, code=(), between=()):
        code_len = len(code)
        between_len = len(between)
        re=[]
        if between_len == 0:
            for t in self.variety:
                if code == t[:code_len]:
                    if t[-1] == title:
                        re.append(t[0:account_DB.Code.MAX])

        else:
            from_code  = code + ((0,) * (account_DB.Code.VARIETY+1-code_len))
            to_code = between + account_DB.to_def_code_WO_order[(between_len-1):]
            # to_code = between + ((0,) * (account_DB.Code.VARIETY+1-between_len))

            # FAMILY->3ケタ
            form_code_val = int(account_DB.COMBINE_CODE.format(from_code[account_DB.Code.ORDER],from_code[account_DB.Code.FAMILY],from_code[account_DB.Code.GENUS],from_code[account_DB.Code.SPECIES]))
            to_code_val   = int(account_DB.COMBINE_CODE.format(  to_code[account_DB.Code.ORDER],  to_code[account_DB.Code.FAMILY],  to_code[account_DB.Code.GENUS],  to_code[account_DB.Code.SPECIES]))
            # form_code_val = int('{:02}{:02}{:02}{:03}'.format(from_code[account_DB.Code.ORDER],from_code[account_DB.Code.FAMILY],from_code[account_DB.Code.GENUS],from_code[account_DB.Code.SPECIES]))
            # to_code_val   = int('{:02}{:02}{:02}{:03}'.format(  to_code[account_DB.Code.ORDER],  to_code[account_DB.Code.FAMILY],  to_code[account_DB.Code.GENUS],  to_code[account_DB.Code.SPECIES]))
            for i, c in enumerate(self.variety_code):
                if form_code_val <= c <= to_code_val:
                    if self.variety[i][-1] == title:
                        re.append(self.variety[i][0:account_DB.Code.MAX])

        return re

    # titleに勘定科目が"含まれる"
    def search_in_variety_code(self, title, ratio=0.7):

        for t in self.variety:
            if t[-1] in title:
                return t[0:account_DB.Code.MAX]

    # def search_variety_code(self, title, code=()):
    #     code_len = len(code)
    #     for t in self.variety:
    #         if code == t[:code_len]:
    #             if t[-1] == title:
    #                 return t[0:account_DB.Code.MAX]
    #                 # return t[0:4]
    #                 # return '{:01d}:{:02d}:{:02d}:{:03d}'.format(t[0],t[1],t[2],t[3])

    #     return () #[]

    # betweenを指定する場合はcodeは必須で長さも同じにする
    def get_variety_title_list(self, code=(), between=()):

        # 同じものが繰り返される可能性があるのでキャッシュしておく
        if code == self.cache_variety_title_list_code and between == self.cache_variety_title_list_between:
            data = self.cache_variety_title_list
        else:
            code_len = len(code)
            if code_len == 0:
                data = self.variety_title
            else:
                data = []
                between_len = len(between)
                if between_len == 0 or code_len != between_len:
                    # code だけで検索
                    for t in self.variety:
                        if code == t[:code_len]:
                            data.append(t[-1])
                else:
                    from_code  = code + ((0,) * (account_DB.Code.VARIETY+1-code_len))
                    # to_code = between + ((999,) * (account_DB.Code.VARIETY+1-between_len))
                    # FAMILY->3ケタ
                    # to_def_code = (999,99,99,999)
                    to_code = between + account_DB.to_def_code_WO_order[(between_len-1):]

                    # to_code = between + ((0,) * (account_DB.Code.VARIETY+1-between_len))

                    form_code_val = int(account_DB.COMBINE_CODE.format(from_code[account_DB.Code.ORDER],from_code[account_DB.Code.FAMILY],from_code[account_DB.Code.GENUS],from_code[account_DB.Code.SPECIES]))
                    to_code_val   = int(account_DB.COMBINE_CODE.format(  to_code[account_DB.Code.ORDER],  to_code[account_DB.Code.FAMILY],  to_code[account_DB.Code.GENUS],  to_code[account_DB.Code.SPECIES]))
                    # form_code_val = int('{:02}{:02}{:02}{:03}'.format(from_code[account_DB.Code.ORDER],from_code[account_DB.Code.FAMILY],from_code[account_DB.Code.GENUS],from_code[account_DB.Code.SPECIES]))
                    # to_code_val   = int('{:02}{:02}{:02}{:03}'.format(  to_code[account_DB.Code.ORDER],  to_code[account_DB.Code.FAMILY],  to_code[account_DB.Code.GENUS],  to_code[account_DB.Code.SPECIES]))

                    for i, c in enumerate(self.variety_code):
                        if form_code_val <= c <= to_code_val:
                            data.append(self.variety[i][-1])

                data = tuple(data)
            # キャッシュ
            self.cache_variety_title_list = data
            self.cache_variety_title_list_code = code
            self.cache_variety_title_list_between = between

        return data

    # def get_variety_title_list(self, code=()):

    #     # 同じものが繰り返される可能性があるのでキャッシュしておく
    #     if code == self.cache_variety_title_list_code:
    #         data = self.cache_variety_title_list
    #     else:
    #         code_len = len(code)
    #         if code_len == 0:
    #             data = self.variety_title
    #         else:
    #             data = []
    #             for t in self.variety:
    #                 if code == t[:code_len]:
    #                     data.append(t[-1])

    #             data = tuple(data)
    #         # キャッシュ
    #         self.cache_variety_title_list = data
    #         self.cache_variety_title_list_code = code

    #     return data

    # def search_variety_code(self, title):

    #     for t in self.variety:
    #         if t[-1] == title:
    #             return t[0:4]
    #             # return '{:01d}:{:02d}:{:02d}:{:03d}'.format(t[0],t[1],t[2],t[3])

    #     return []

    NO_REGISTRATION = '未登録'
    def code_to_title(self, code, data):

        code_len = len(code)
        for t in data:
            if t[:code_len] == code:
                return t[-1]

        return self.NO_REGISTRATION

    def code_to_variety_property(self, code):

        for t in self.variety:
            if t[:account_DB.Code.VARIETY+1] == code[:account_DB.Code.VARIETY+1]:
                return t[-2]

        return 0

    def code_to_title_list(self, code, data):

        title_list = []
        code_len = len(code)
        for t in data:
            if t[:code_len] == code:
                title_list.append(t[-1])

        return title_list

    def search_close_title(self, code, title, ratio=0.7):

        title_list = self.code_to_title_list(code, self.variety)

        close = difflib.get_close_matches( title, title_list,cutoff=ratio)

        return close

    # def type_to_title(self, code):

    #     for t in self.code:
    #         if t[0] == code[0]:
    #             return t[-1]

    #     return self.NO_REGISTRATION

    # def family_to_title(self, code):

    #     for t in self.family:
    #         if t[0] == code[0] and t[1] == code[2]:
    #             return t[-1]

    #     return self.NO_REGISTRATION

    # def family_to_title(self, code):

    #     for t in self.family:
    #         if t[0] == code[0] and t[1] == code[2]:
    #             return t[-1]

    #     return self.NO_REGISTRATION

    # def genus_to_title(self, code):

    #     for t in self.genus:
    #         if t[0] == code[0] and t[1] == code[2]:
    #             return t[-1]

    #     return self.NO_REGISTRATION

    def to_title_csv(self, code):

        title_csv = []

        code_len = len(code)

        if code_len >= account_DB.Code.ORDER+1:
            title = [code[account_DB.Code.ORDER], self.code_to_title(code[:account_DB.Code.ORDER+1], self.order)]
            title_csv += title
        if code_len >= account_DB.Code.FAMILY+1:
            title = [code[account_DB.Code.FAMILY], self.code_to_title(code[:account_DB.Code.FAMILY+1], self.family)]
            title_csv += title
        if code_len >= account_DB.Code.GENUS+1:
            title = [code[account_DB.Code.GENUS], self.code_to_title(code[:account_DB.Code.GENUS+1], self.genus)]
            title_csv += title
        if code_len >= account_DB.Code.SPECIES+1:
            title = [code[account_DB.Code.SPECIES], self.code_to_title(code[:account_DB.Code.SPECIES+1], self.species)]
            title_csv += title
        if code_len >= account_DB.Code.VARIETY+1:
            title = [code[account_DB.Code.VARIETY], self.code_to_title(code[:account_DB.Code.VARIETY+1], self.variety)]
            title_csv += title

        return title_csv

    def to_title_text(self, code):

        title_text = ''

        code_len = len(code)

        if code_len >= account_DB.Code.ORDER+1:
            title = '{}[{}]'.format(code[account_DB.Code.ORDER], self.code_to_title(code[:account_DB.Code.ORDER+1], self.order))
            title_text += title
        if code_len >= account_DB.Code.FAMILY+1:
            title = ':{}[{}]'.format(code[account_DB.Code.FAMILY], self.code_to_title(code[:account_DB.Code.FAMILY+1], self.family))
            title_text += title
        if code_len >= account_DB.Code.GENUS+1:
            title = ':{}[{}]'.format(code[account_DB.Code.GENUS], self.code_to_title(code[:account_DB.Code.GENUS+1], self.genus))
            title_text += title
        if code_len >= account_DB.Code.SPECIES+1:
            title = ':{}[{}]'.format(code[account_DB.Code.SPECIES], self.code_to_title(code[:account_DB.Code.SPECIES+1], self.species))
            title_text += title
        if code_len >= account_DB.Code.VARIETY+1:
            title = ':{}[{}]'.format(code[account_DB.Code.VARIETY], self.code_to_title(code[:account_DB.Code.VARIETY+1], self.variety))
            title_text += title

        return title_text

    # table_keywordの検索
    def search_table_keyword(self, row_txt):
        tks = []
        for tk in self.table_keyword:
            if tk.keyword in row_txt:
                tks.append(tk)
                # return tk

        return tks
        # return None

    # table_keywordの各要素のカウント
    def count_table_keyword(self):
        count = [0] * 4
        for tk in self.table_keyword:
            count[(tk.order-1)*2+tk.end] += 1
        return count

#account_db = account_DB()


minus_sign = r'\-ー△▽▲▼'
amount_sign = minus_sign+r',.、/'
# amount_sign = r'-▲△,.、/'

amount_num  = r'0-9０-９'
amount_char = amount_sign+amount_num

triangle_minus_sign = re.compile(f'[{minus_sign}]')
# triangle_minus_sign = re.compile(r'[-▲△]')

error_head_minus_sign = re.compile(r'[AＡへ]$') # マイナス、△の誤認識 s['revise'][0] | d['data'][k-1]['val]

### 不採用(意図しない分割)
# table_row_pat = re.compile(f'[^年月日 {minus_sign}~✔{amount_num}.,]+[{minus_sign}{amount_num}.,]+')
# table_row_pat = re.compile(f'[^{amount_char}年月日 ~✔]+[{amount_char}]+')

table_row_pat = re.compile(r'[^年月日 -△▽▲▼~✔\[\]【】0-9０-９.,]+[-△▽▲▼\[\]【】0-9０-９.,]+')
# table_row_pat = re.compile(r'[^年月日 -△▽▲▼~✔0-9０-９.,]+[-△▽▲▼0-9０-９.,]+')
# table_row_pat = re.compile(r'([^年月日 -~✔0-9０-９]+)[0-9０-９]+')
# table_row_pat = re.compile(r'[^年月日 -~✔0-9０-９]+[0-9０-９]+')

# table_row_pat = re.compile(r'[^年月日 \-ー△▲~✔0-9０-９.,]+[\-ー△▲0-9０-９.,]+')
# table_row_pat = re.compile('[^年月日 ~✔\-△▽▲▼,.、0-9０-９]+[\-△▽▲▼,.、0-9０-９]+')
# table_row_pat = re.compile(r'[^年月日 -~0-9０-９]+[0-9０-９-,.]+')

# amount_pat = '0-9０-９-▲,.'
# amount_pat = '0-9０-９-▲△,.'
# 金額が無くて勘定科目だけのパターンも想定
# subject_amount_pat = re.compile(f'([^{amount_pat}]+)([{amount_pat}]*)')
# ([-▲△]*[0-9０-９,.、/]'

braces_char = r'\(\)【】\|' # r'()【】|' ???
subject_amount_pat = re.compile(f'([^{minus_sign}{amount_num}]+)([{amount_char}]*)')
# subject_amount_pat = re.compile(f'([^0-9０-９-▲△]+)([{amount_char}]*)')

subject_amount_other_pat = re.compile(f'([^{minus_sign}{amount_num}]+)([{amount_char}]*)(.*)')
# subject_amount_other_pat = re.compile(f'([^0-9０-９-▲△]+)([{amount_char}]*)(.*)')

one_subject_amount_pat = re.compile(f'([^{minus_sign}{amount_num}]+)([{amount_char}{braces_char}]+)')
# one_subject_amount_pat = re.compile(f'([^0-9０-９-▲△]+)([{amount_char}{braces_char}]+)')

braces_pat = re.compile(f'([{braces_char}])')
# subject_amount_pat = re.compile(r'([^0-9０-９-▲△]+)([-▲△0-9０-９,.、/]*)')
# subject_amount_pat = re.compile(r'([^0-9０-９-▲△]+)([-▲△0-9０-９,.、]*)')

amount_pat = re.compile(f'([{amount_char}]+)')
# amount_pat = re.compile(r'([-▲△0-9０-９,.、/]+)')
# amount_pat = re.compile(r'([-▲△0-9０-９,.、]+)')

amount_split_pat = re.compile(f'([^{amount_char}]*)([{amount_char}]+)(.*)')
# amount_split_pat = re.compile(r'([^-▲△0-9０-９,.、/]*)([-▲△0-9０-９,.、/]+)(.*)')

num_pat = re.compile(f'([{amount_num}]+)')

symbol_char = r' -/:-@\[-~！”＃＄％＆’（）＝～｜‘｛＋＊｝＜＞？＿－＾￥＠「；：」、。・【】《》'
symbol = re.compile(f'[{symbol_char}]')
# symbol = re.compile(f'[{symbol_char}]')
not_symbol = re.compile(f'[^{symbol_char}]')
# symbol = re.compile(r'[ -/:-@\[-~！”＃＄％＆’（）＝～｜‘｛＋＊｝＜＞？＿－＾￥＠「；：」、。・【】《》]')

begin_symbol = re.compile(r'^[0-9a-zA-Z]*')
# begin_symbol = re.compile(r'^[0-9a-zA-Z\[\]\(\)]*')

version_sign = re.compile(r'ver', re.IGNORECASE)

ZENKAKU = r'\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002EBEF\u3041-\u309F\u30A1-\u30FF\uFF66-\uFF9F'
# ZENKAKU = r'[\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002EBEF\u3041-\u309F\u30A1-\u30FF\uFF66-\uFF9F]'

class v2ac(engine2):
    class Type(IntEnum):
        UNKNOWN     = 0
        SUBJECT     = 0x01
        AMOUNT      = 0x02
        SUBJECT_AMOUNT = (SUBJECT|AMOUNT)
        DATE        = 0x04
        TITLE       = 0x08
        REMOVE      = 0x80

    # 前期 今期(当期)の並び
    class PeriodOrder(IntEnum):
        NON = 0
        PREV_X_CURRENT_X  = 1 # 前期 X 今期 X
        PREV_CURRENT      = 1 # 前期 今期 (2列)

        CURRENT_PREV_X_X  = 2 # 今期 前期 X X
        CURRENT_PREV      = 2 # 今期 前期 (2列)

    def __init__(self, inData, start_date, main_version='', version=ENGINE_VERSION, id='non', debug_suffix=''):

        # DBは都度読み込む
        self.account_db = account_DB()

        super().__init__(inData, start_date, main_version, version, id, debug_suffix)

        # self.find_rows_scale = [0.3,0.3]

        self.find_rows_scale = [0.25,0.30]

        # self.find_rows_scale = [0.3,DEFAULT_FIND_ROWS_SCALE]

        # self.table_block = []
        self.table_type = account_DB.Order.NON
        self.col_list = []

        self.result_data = []
        self.result_data_param = []

        # 前期 今期(当期)の並び
        self.period_order = v2ac.PeriodOrder.NON

        # 割合の列
        self.ratio_column = False

        # 現在処理中のタイプを保存 find_table_typeで使用
        self.cur_table_order = account_DB.Order.NON

        # 縦線区切り情報
        self.stats_v = {}

    def keyword_param(self):
        # ※従来のリクエストと形式が一部違うので注意
        # v2ac のconditions_id=100は 'col_id'等、指定されないが他のエンジンと共通の処理が必要なので項目だけ追加する
        for col in self.format_cols:
            if 'col_id' not in col:
                col['col_id'] = ''
                col['col_name'] = ''
                col['itask_form_id'] = ''

            for cond in col['col_conditions']:
                if 'conditions_sort_number' not in cond:
                    cond['conditions_sort_number'] = ''
                if 'itask_col_conditions_parameter' not in cond:
                    cond['itask_col_conditions_parameter'] = [{}]

        super().keyword_param()

    def load_keyword(self):
        keyword = super().load_keyword()

        keyword['keyword'].append({ 'title': '現金売上高' })
        keyword['keyword'].append({ 'title': '掛売上高' })
        keyword['keyword'].append({ 'title': '営業利益金額' })
        keyword['keyword'].append({ 'title': '経常利益金額' })
        keyword['keyword'].append({ 'title': '税引前当期純利益金額' })
        keyword['keyword'].append({ 'title': '当期純利益金額' })
        keyword['keyword'].append({ 'title': '有形固定資産合計' })
        keyword['keyword'].append({ 'title': '無形固定資産合計' })
        keyword['keyword'].append({ 'title': '投資その他の資産' })
        keyword['keyword'].append({ 'title': '資産の部合計' })
        keyword['keyword'].append({ 'title': '負債の部合計' })
        keyword['keyword'].append({ 'title': '純資産の部合計' })
        keyword['keyword'].append({ 'title': '負債・純資産の部合計' })
        keyword['keyword'].append({ 'title': 'その他利益剰余金' })

        return keyword

    # 傾き補正(※コメントしておく)
    # def revise_tilt(self, img, filename=None):
    #     return img, None, 0.0, None
    # v2ac専用：黄色除去したが画像で回転角を取得して元画像を回転する為
    def revise_tilt(self, img, filename=None):
        # 黄色除去
        Y_img = pre_process_image.del_yellow(img)
        # 黄色除去画像で回転角取得
        _, contours, angle, table_bound = super().revise_tilt(Y_img)

        # 元画像を回転
        img = self.rotate_image(img,angle,None,filename)

        return img, contours, angle, table_bound

    def preprocess_loaded_image(self, img, filename=None):
        img = pre_process_image.preprocess_loaded_image_v2ac(img)

        return img

    # VisionAPI直前のイメージ前処理
    def preprocess_image(self, img_org, filename=None):
        return img_org
        # return img_org
        # ノイズ除去など基本処理
        img = super().preproccess_image(img_org)
        # img = img_org #super().preproccess_image(img_org)

        return img

        # img2 = None
        try:
            # カラー -> モノクロ変換
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # 適応的しきい値処理
            img2 = cv2.adaptiveThreshold(gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY, 41, 15)
        except:
            img2 = None # エラーの場合はオリジナルを使う

        if filename is not None and img2 is not None:
            # 変換した画像を保存
            filename2 = filename+ADJUST_FILE
            cv2.imwrite(filename2, img2)
            os.chmod(filename2, FILE_PARMITION)

        # 変換できたらグレースケール画像を返す
        return img2 if img2 is not None else img_org

    # 右寄せされた文字を元の位置に戻す
    def restore_position_detection_text(self, source_characters, src_pos, dest_pos):

        row_rect = [None] * len(dest_pos)
        for i, dp in enumerate(dest_pos):
            aaa = 0
            for j, d in enumerate(dp):
                p = Bound(left=d[1],top=d[2],right=d[1]+d[3],bottom=d[2]+d[4])
                # if row_rect[i] is None:
                #     row_rect[i] = p
                # else:
                #     row_rect[i].expand(p)

                cnt = 0
                for c in source_characters:
                    if p.is_included(c['bounds'],True):
                    # if p.is_center_included(c['bounds']):

                        if i < len(src_pos) and j < len(src_pos[i]):
                            s = src_pos[i][j]
                            sp = Bound(left=s[1],top=s[2],right=s[1]+s[3],bottom=s[2]+s[4])
                            if 'dist' in c:
                                c['dist'].append({'src':sp, 'dest':p, 'i':i, 'j':j})
                            else:
                                c['dist'] = [{'src':sp, 'dest':p, 'i':i, 'j':j}]
                        else:
                            aaa = 0
                    # else:
                    #   print('source+',c)
        aaa = 0

        for c in source_characters:
            if c['text'] == '諸':
                aaa = 0
            if 'dist' in c:
                if len(c['dist']) > 1:
                    for d in c['dist']:
                        _ = d['dest'].get_overlap_area(c['bounds'])
                        # _ = d['dest'].get_x_overlap(c['bounds'])
                        # _ = d['dest'].get_center_distance(c['bounds'])
                        aaa = 0
                    aaa = 0
                    c['dist'].sort(key=lambda x: x['dest'].dist, reverse=True)
                    # c['dist'].sort(key=lambda x: x['dest'].dist)

                    aaa = 0
                d = c['dist'][0]['src'].center[0] - c['dist'][0]['dest'].center[0]
                # d2 = c['dist2'][0]['src'].center[0] - c['dist2'][0]['dest'].center[0]
                # if d != d2:
                #     aaa = 0
                c['bounds'].offset(d,0)
                aaa = 0
            else:
                aaa = 0
        aaa = 0
        return source_characters
    def get_text_detection(self, no, _img, file_name, client, def_cache_data=None, force_detection=False):

        # まず通常処理を行う
        #source_texts, source_characters, response, cache_data, img2, _ = super().get_text_detection(no, _img, file_name, client, def_cache_data={'rotate':None})
        # img2 = None : 基底のget_text_detectionはimgを変更しない
        filename2 = file_name+TILT_FILE
        cv2.imwrite(filename2, _img)
        r_flags=None
        #if cache_data:
        #    r_flags  = cache_data['rotate']
        #else:
        #    r_flags  = None
        #
        ## r_flags = -1 # TILT DEBUG こことる
        #
        #if r_flags is not None:
        #    # キャッシュがあって画像が回転されている
        #    if r_flags != -1:
        #        _img2_2 = cv2.rotate(_img, r_flags) # ブロック解析では元画像を使う
        #
        #        # 回転した画像を保存
        #        filename2 = file_name+TILT_FILE
        #        cv2.imwrite(filename2, _img2_2)
        #        os.chmod(filename2, FILE_PARMITION)
        #
        #        if 'img_bk' in locals() : del img_bk
        #        _img2, img_bk = pre_process_image.preprocess_image_v2ac(_img2_2)
        #        if '_img2_2' in locals() : del _img2_2
        #        if 'newimg' in locals() : del newimg
        #        newimg,img_line,rs2_ascend,rs3_ascend,stats_v,triangle_xy=pre_process_image.del_line_str_right(_img2, img_bk)
        #        source_texts, source_characters, response, cache_data, img2, _ = super().get_text_detection(no, newimg, file_name, client, def_cache_data={'rotate':r_flags}, force_detection=True)
        #else:#こちらは廃棄しました
        #    # キャッシュが無い(初めての読み込み)場合は用紙の向きを確認する
        #    p = re.compile('[\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002EBEF]+')
        #    cnt = 0
        #    #20220923 mizuno------>
        #    flg = 0
        #    checkwords=["貸借","損益","販売","青色","収支","負債","株式","売上","利益","株主","会社"]
        #
        #    for t in source_texts:
        #      l = len(t['text'])
        #      if l == 2 and p.fullmatch(t['text']) and flg ==0:
        #        for w in checkwords:
        #          if t['text']==w:
        #            flg = 1
        #            b1 = source_characters[cnt]['bounds'].rect
        #            b2 = source_characters[cnt+1]['bounds'].rect
        #            break
        #      cnt += l
        #    #checkwordsに当てはまらなかった場合の処理
        #    cnt = 0
        #    if flg ==0:
        #      for t in source_texts:
        #          l = len(t['text'])
        #          if l == 2 and p.fullmatch(t['text']):
        #              b1 = source_characters[cnt]['bounds'].rect
        #              b2 = source_characters[cnt+1]['bounds'].rect
        #              break
        #          cnt += l
        #      else:
        #          b1 = b2 = None
        #    #<--------------20220923 mizuno
        #
        #    if b1 and b2:
        #        x1 ,y1, x2, y2 = int(b1[0]),int(b1[1]),int(b2[0]),int(b2[1])
        #        a, b = abs(x2-x1), abs(y2-y1)
        #
        #        if a > b and x2-x1 > 0:
        #            r_flags = -1 # None
        #        elif a < b and y2-y1 > 0:
        #            r_flags = cv2.ROTATE_90_COUNTERCLOCKWISE
        #        elif a > b and x2-x1 < 0:
        #            r_flags = cv2.ROTATE_180
        #        elif a < b and y2-y1 < 0:
        #            r_flags = cv2.ROTATE_90_CLOCKWISE
        #        else:
        #            r_flags = None
        #
        #        if r_flags is not None:
        #            if r_flags != -1:
        #                img3_2 = cv2.rotate(_img, r_flags)
        #                # 回転した画像を保存
        #                filename2 = file_name+TILT_FILE
        #                cv2.imwrite(filename2, img3_2)
        #                os.chmod(filename2, FILE_PARMITION)
        #
        #                if 'img_bk' in locals() : del img_bk
        #                _img2, img_bk = pre_process_image.preprocess_image_v2ac(img3_2)
        #                if 'img3_2' in locals() : del img3_2
        #                if 'newimg' in locals() : del newimg
        #                newimg,img_line,rs2_ascend,rs3_ascend,stats_v,triangle_xy=pre_process_image.del_line_str_right(_img2,img_bk)
        #                # 回転した画像でもう一度VisionAPIを呼ぶ
        #                source_texts, source_characters, response, cache_data, img2, _ = super().get_text_detection(no, newimg, file_name, client, def_cache_data={'rotate':r_flags}, force_detection=True)
        #
        #            else:
        #                vsn_file = self.get_cache_file_name(file_name)
        #                self.cache_write(vsn_file, response, {'rotate':r_flags})

        if 'newimg' not in locals() :
            _img2, img_bk = pre_process_image.preprocess_image_v2ac(_img)
            source_texts, source_characters, response, cache_data, img2, _ = super().get_text_detection(no, _img2, file_name, client, def_cache_data={'rotate':None}, force_detection=True)
            leftmost_characters=9999
            for i in range(len(source_characters))[::-1]:
                if source_characters[i]['bounds'].get_height() >= 300: # 縦に大きな文字
                    debug_print( 'H[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size),level=DEBUG_ROWS_INFO)
                    # print( 'H[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size))
                    del source_characters[i]
                elif source_characters[i]['bounds'].get_height() <= 12: # 縦に小さな文字
                    debug_print( 'S[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size),level=DEBUG_ROWS_INFO)
                    # print( 'S[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size))
                    del source_characters[i]
                elif source_characters[i]['bounds'].get_width() >= 300: # 横に大きな文字
                    debug_print( 'W[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size),level=DEBUG_ROWS_INFO)
                    # print( 'W[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size))
                    del source_characters[i]
                #最も左の文字の位置を抽出
                try:
                    if source_characters[i]['bounds'].get_left() >0 :
                        if(leftmost_characters>source_characters[i]['bounds'].get_left()):
                            leftmost_characters=source_characters[i]['bounds'].get_left()
                except:
                    leftmost_characters=9999


            newimg,img_line,rs2_ascend,rs3_ascend,stats_v,triangle_xy=pre_process_image.del_line_str_right(_img2, img_bk,leftmost_characters)

            # 縦線区切り情報
            height, width = _img2.shape[0], _img2.shape[1]
            self.stats_v[no] = []

            debug_print( f'stats_v:{no} -> x座標, y座標, 幅, 高さ, 面積 [{width},{height}]', level=DEBUG_ROWS_INFO)
            if height > 0:
                # 縦を繋げる
                stats_vs = sorted(stats_v, key=lambda x:(x[0],x[1])) #, reverse=True)
                stats_vv = []
                i = 0
                max = len(stats_vs)
                while True:
                    if i >= max:
                        break
                    col = stats_vs[i]
                    i += 1

                    vv = [col]

                    # 同じ縦線をまとめる
                    for j in range(i, max):
                        i = j
                        col2 = stats_vs[j]
                        # 別の縦線？
                        # Xが離れている
                        if (col2[0] - col[0]) >= 20: # 別の線とみなすX閾値
                            break

                        vv.append(col2)

                    # Y順でソート
                    vv.sort(key=lambda x:(x[1]))

                    # Yが繋がっている線を合わせる
                    vv2 = []
                    cv = None
                    for c in vv:
                        if cv is None:
                            cv = c
                            vv2.append(c)
                        else:
                            ey = cv[1] + cv[3]
                            # Y(上側の線の下端と下側の線の上端)が離れている
                            if (c[1] - ey) >= 100: # 繋がっているとみなすY閾値
                                cv = None
                            else:
                                cv[3] = c[1] + c[3] - cv[1]

                                # 現状は使わない
                                # if c[2] > cv[2]:
                                #     cv[2] = c[2]

                    stats_vv += vv2

                # まとめたものに入れ替え
                for col in stats_v:
                    debug_print( '{}({}):{}'.format(col, col[1]+col[3], int(col[3]/height*100)), level=DEBUG_ROWS_INFO)
                debug_print( ' --->', level=DEBUG_ROWS_INFO)
                for col in stats_vv:

                    # 上から下までの場合
                    # col[1] = 0
                    # col[3] = height
                    # 上から下までを採用する場合は短い線を使わない様にする処理が必要

                    debug_print( '{}({}):{}'.format(col, col[1]+col[3], int(col[3]/height*100)), level=DEBUG_ROWS_INFO)

                stats_v = stats_vv #DEBUG

                for col in stats_v:
                    # debug_print( '{}({}):{}'.format(col, col[1]+col[3], int(col[3]/height*100)), level=DEBUG_ROWS_INFO)

                    # if col[3] >= 0: # 高さに対して割合が少ないものは除外
                    if col[0] >= 200 and col[3] >= 100: # 高さに対して割合が少ないものは除外
                    # if col[0] >= 200 and col[3]/height >= 0.25: # 高さに対して割合が少ないものは除外
                        self.stats_v[no].append(col)

                if len(self.stats_v[no]) >= 1: # 一番右側として用紙幅を追加
                    self.stats_v[no].append([width,0,1,height,height])

            source_texts, source_characters, response, cache_data, img2, _ = super().get_text_detection(no, newimg, file_name, client, def_cache_data={'rotate':None}, force_detection=True)


        # 認識文字書き出し(確認用)
        filename2 = file_name+'.D_1.jpg'
        cv2.imwrite(filename2, img_line)
        os.chmod(filename2, FILE_PARMITION)

        img_chk = newimg.copy()
        plot_labeling_box(img_chk, rs3_ascend)
        filename2 = file_name+'.B_2.jpg'
        cv2.imwrite(filename2, img_chk)
        os.chmod(filename2, FILE_PARMITION)
        del img_chk

        img_chk = _img2.copy() if img2 is None else img2.copy()        # img_chk = _img.copy()
        plot_labeling_box(img_chk, rs2_ascend)
        filename2 = file_name+'.B_3.jpg'
        cv2.imwrite(filename2, img_chk)
        os.chmod(filename2, FILE_PARMITION)
        del img_chk

        img_chk = plot_source_characters(newimg, source_characters)
        # img_chk_2 = newimg.copy()
        # img_chk = plot_source_characters(img_chk_2, source_characters)
        # if 'img_chk_2' in locals() : del img_chk_2
        filename2 = file_name+'.D_2.jpg'
        cv2.imwrite(filename2, img_chk)
        os.chmod(filename2, FILE_PARMITION)
        del img_chk

        self.restore_position_detection_text(source_characters,rs2_ascend,rs3_ascend)

        # 大きな文字、小さな文字を取り除く (現状はsource_textsに対して何もしていない)
        debug_print( f'remove_sized_char:{no} -->',level=DEBUG_ROWS_INFO)
        # print( f'remove_sized_char:{no} -->')
        for i in range(len(source_characters))[::-1]:
            if source_characters[i]['bounds'].get_height() >= 300: # 縦に大きな文字
                debug_print( 'H[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size),level=DEBUG_ROWS_INFO)
                # print( 'H[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size))
                del source_characters[i]
            elif source_characters[i]['bounds'].get_height() <= 12: # 縦に小さな文字
                debug_print( 'S[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size),level=DEBUG_ROWS_INFO)
                # print( 'S[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size))
                del source_characters[i]
            elif source_characters[i]['bounds'].get_width() >= 300: # 横に大きな文字
                debug_print( 'W[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size),level=DEBUG_ROWS_INFO)
                # print( 'W[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size))
                del source_characters[i]
        debug_print( f'<-- remove_sized_char:{no}',level=DEBUG_ROWS_INFO)
        # print( f'<-- remove_sized_char:{no}')

        # [△]
        # 抜いた'△'を一旦元の位置に戻す 数字の前への移動はmove_triangle_char
        for d in triangle_xy:
        # for d in triangle_xy[:2]:
            c = {'text':'△', 'bounds':Bound(left=d[0],top=d[1],right=d[0]+d[2],bottom=d[1]+d[3])}
            source_characters.append(c)
        source_characters.sort(key=lambda x: (x['bounds'].rect[1],x['bounds'].rect[0]))

        # 認識文字書き出し(確認用)
        img_chk = plot_source_characters(_img2 if img2 is None else img2, source_characters, True)
        # img_chk_2 = _img2.copy() if img2 is None else img2.copy()        # img_chk = _img.copy()
        # img_chk = plot_source_characters(img_chk_2, source_characters, True)
        # if 'img_chk_2' in locals() : del img_chk_2
        filename2 = file_name+'.D_3.jpg'
        cv2.imwrite(filename2, img_chk)
        os.chmod(filename2, FILE_PARMITION)
        del img_chk


        # remove_symbol_charsで必要になるのでsource_charactersにシーケンシャル番号を振る(v2ac独自)
        for i, c in enumerate(source_characters):
            c['no'] = i

        debug_print( f'rs2_ascend:{no} -->',level=DEBUG_ROWS_INFO)
        for i, r in enumerate(rs2_ascend):
            for j, d in enumerate(r):
                debug_print( '{},{}:{}'.format(i,j,d),level=DEBUG_ROWS_INFO)
        debug_print( f'<-- rs2_ascend:{no}',level=DEBUG_ROWS_INFO)

        debug_print( f'rs3_ascend:{no} -->',level=DEBUG_ROWS_INFO)
        for i, r in enumerate(rs3_ascend):
            for j, d in enumerate(r):
                debug_print( '{},{}:{}'.format(i,j,d),level=DEBUG_ROWS_INFO)
        debug_print( f'<-- rs3_ascend:{no}',level=DEBUG_ROWS_INFO)
        # 大きな文字、小さな文字を取り除く (現状はsource_textsに対して何もしていない)
        debug_print( f'remove_sized_char:{no} -->',level=DEBUG_ROWS_INFO)
        # print( f'remove_sized_char:{no} -->')

        # tilt用
        if r_flags and r_flags == -1:
            r_flags = None
        if '_img' in locals() : del _img
        if 'img_bk' in locals() : del img_bk
        if 'newimg' in locals() : del newimg
        if '_img2' in locals() : del _img2
        if 'img2_2' in locals() : del img2_2
        return source_texts, source_characters, response, cache_data, img2, r_flags

    # VisionAPIからのデータを元に用紙の向きを確認して補正する(※PDFは考慮していない)
    # get_text_detectionは一番最初の処理
    def get_text_detection_kojin(self, no, _img, file_name, client, def_cache_data=None, force_detection=False):
        b1=False
        b2=False

        if '_img2' in locals() : del _img2
        if 'img_bk' in locals() : del img_bk
        if self.document_judgment_flag == "kojin" or 'konjin' in self.document_judgment_flag :
            _img2 = _img.copy()
            img_bk = _img.copy()
            newimg = _img.copy()
        filename2 = file_name+TILT_FILE
        cv2.imwrite(filename2, _img)
        r_flags=None

        #個人の場合実行しない
        if self.document_judgment_flag != "kojin" and 'konjin' not in self.document_judgment_flag :
            if 'newimg' not in locals() :
                # 回転した画像を保存
                filename2 = file_name+TILT_FILE
                cv2.imwrite(filename2, _img)
                os.chmod(filename2, FILE_PARMITION)
                _img2, img_bk = pre_process_image.preprocess_image_v2ac(_img)
                newimg,img_line,rs2_ascend,rs3_ascend,stats_v,triangle_xy=pre_process_image.del_line_str_right(_img2, img_bk)
                source_texts, source_characters, response, cache_data, img2, _ = super().get_text_detection(no, newimg, file_name, client, def_cache_data={'rotate':r_flags}, force_detection=True)

            filename2 = file_name+'.D_1.jpg'
            cv2.imwrite(filename2, img_line)
            os.chmod(filename2, FILE_PARMITION)

            img_chk = newimg.copy()
            plot_labeling_box(img_chk, rs3_ascend)
            print('rs3_ascend',rs3_ascend)
            filename2 = file_name+'.B_2.jpg'
            cv2.imwrite(filename2, img_chk)
            os.chmod(filename2, FILE_PARMITION)
            del img_chk

            img_chk = _img2.copy() if img2 is None else img2.copy()        # img_chk = _img.copy()
            plot_labeling_box(img_chk, rs2_ascend)
            filename2 = file_name+'.B_3.jpg'
            cv2.imwrite(filename2, img_chk)
            os.chmod(filename2, FILE_PARMITION)
            del img_chk

            img_chk = newimg.copy()
            img_chk = plot_source_characters(img_chk, source_characters)
            filename2 = file_name+'.D_2.jpg'
            cv2.imwrite(filename2, img_chk)
            os.chmod(filename2, FILE_PARMITION)
            del img_chk
            self.restore_position_detection_text(source_characters,rs2_ascend,rs3_ascend)
        else :
            filename2 = file_name+'.S_2_0.jpg'
            cv2.imwrite(filename2, newimg)
            os.chmod(filename2, FILE_PARMITION)
            source_texts, source_characters, response, cache_data, img2, _ = super().get_text_detection(no, newimg, file_name, client, def_cache_data={'rotate':r_flags}, force_detection=True)
            img_chk = newimg.copy()
            img_chk = plot_source_characters(img_chk, source_characters)
            filename2 = file_name+'.S_2.jpg'
            cv2.imwrite(filename2, img_chk)
            os.chmod(filename2, FILE_PARMITION)
            del img_chk
        # 大きな文字、小さな文字を取り除く (現状はsource_textsに対して何もしていない)
        debug_print( f'remove_sized_char:{no} -->',level=DEBUG_ROWS_INFO)
        # print( f'remove_sized_char:{no} -->')
        for i in range(len(source_characters))[::-1]:
            if source_characters[i]['bounds'].get_height() >= 300: # 縦に大きな文字
                debug_print( 'H[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size),level=DEBUG_ROWS_INFO)
                # print( 'H[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size))
                del source_characters[i]
            elif source_characters[i]['bounds'].get_height() <= 12: # 縦に小さな文字
                debug_print( 'S[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size),level=DEBUG_ROWS_INFO)
                # print( 'S[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size))
                del source_characters[i]
            elif source_characters[i]['bounds'].get_width() >= 300: # 横に大きな文字
                debug_print( 'W[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size),level=DEBUG_ROWS_INFO)
                # print( 'W[{}]{}:{}'.format(source_characters[i]['text'],source_characters[i]['bounds'].rect,source_characters[i]['bounds'].size))
                del source_characters[i]
        #個人の場合実行しない
        if self.document_judgment_flag != "kojin" and 'konjin' not in self.document_judgment_flag  :
            debug_print( f'<-- remove_sized_char:{no}',level=DEBUG_ROWS_INFO)
            # print( f'<-- remove_sized_char:{no}')
            # [△]
            # 抜いた'△'を一旦元の位置に戻す 数字の前への移動はmove_triangle_char
            debug_print( triangle_xy,level=DEBUG_ROWS_INFO)
            for d in triangle_xy:
            # for d in triangle_xy[:2]:
                c = {'text':'△', 'bounds':Bound(left=d[0],top=d[1],right=d[0]+d[2],bottom=d[1]+d[3])}
                source_characters.append(c)
            source_characters.sort(key=lambda x: (x['bounds'].rect[1],x['bounds'].rect[0]))

            # 認識文字書き出し(確認用)
            img_chk = _img2.copy() if img2 is None else img2.copy()        # img_chk = _img.copy()

            img_chk = plot_source_characters(img_chk, source_characters, True)
            filename2 = file_name+'.D_3.jpg'
            cv2.imwrite(filename2, img_chk)
            os.chmod(filename2, FILE_PARMITION)
            del img_chk

        if 'newimg' in locals() : del newimg
        if 'img_bk' in locals() : del img_bk
        # remove_symbol_charsで必要になるのでsource_charactersにシーケンシャル番号を振る(v2ac独自)
        for i, c in enumerate(source_characters):
            c['no'] = i
        debug_print( f'rs2_ascend:{no} -->',level=DEBUG_ROWS_INFO)
        #個人の場合実行しない
        if self.document_judgment_flag != "kojin" and 'konjin' not in self.document_judgment_flag :
            for i, r in enumerate(rs2_ascend):
                for j, d in enumerate(r):
                    debug_print( '{},{}:{}'.format(i,j,d),level=DEBUG_ROWS_INFO)
            debug_print( f'<-- rs2_ascend:{no}',level=DEBUG_ROWS_INFO)

            debug_print( f'rs3_ascend:{no} -->',level=DEBUG_ROWS_INFO)
            for i, r in enumerate(rs3_ascend):
                for j, d in enumerate(r):
                    debug_print( '{},{}:{}'.format(i,j,d),level=DEBUG_ROWS_INFO)
            debug_print( f'<-- rs3_ascend:{no}',level=DEBUG_ROWS_INFO)

        # tilt用
        if r_flags and r_flags == -1:
            r_flags = None
        return source_texts, source_characters, response, cache_data, _img2, r_flags

    def find_vline(self, img_org, path):
        img = img_org.copy()
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = img.shape[0], img.shape[1]
        minlength = height * 0.3
        gap = 5
        judge_img = cv2.bitwise_not(img)

        lines = []
        lines = cv2.HoughLinesP(judge_img, rho=1, theta=np.pi/360, threshold=100, minLineLength=minlength, maxLineGap=gap)

        line_list = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # /* 傾きを3px以内と判断 */
            if abs(x1 - x2) < 8:
                whiteline = 3
                lineadd_img = cv2.line(judge_img, (line[0][0], line[0][1]), (line[0][2], line[0][3]), (255, 255, 255), whiteline)
                x1 = line[0][0]
                y1 = line[0][1]
                x2 = line[0][2]
                y2 = line[0][3]
                line = (x1, y1, x2, y2)
                line_list.append(line)

        line_list.sort(key=itemgetter(0, 1, 2, 3))

        vtl_line = 0
        vt_line_list = []
        x1 = 0
        for line in line_list:
            judge_x1 = line[0]
            if abs(judge_x1 - x1) < 2 and vt_line_list !=[]:
                x1 = judge_x1
            else:
                x1 = judge_x1
                vtl_line = vtl_line + 1
                vt_line_list.append(line)

        img = img_org.copy()
        for l in line_list:
            img = cv2.line(img,(l[0],l[1]),(l[2],l[3]),(0,255,0),5)

        cv2.imwrite(path+'.vline.jpg', img)
        os.chmod(path+'.vline.jpg', FILE_PARMITION)

        # print('VT_line:' + str(vtl_line))
        # line_list = pd.DataFrame(line_list)



        aaa = 0

    def clear_char_area(self, chars, img_org, path=None):
        if img_org is None:
            return None
        img = img_org.copy()
        for c in chars:
            cv2.rectangle(img, (c['bounds'].rect[0], c['bounds'].rect[1]), (c['bounds'].rect[2], c['bounds'].rect[3]), (255, 255, 255), thickness=-1)
            # cv2.rectangle(img, (c['bounds'].rect[0], c['bounds'].rect[1]), (c['bounds'].rect[2], c['bounds'].rect[3]), (0, 255, 0))

        if path is not None:
            cv2.imwrite(path+'.clear.jpg', img)
            os.chmod(path+'.clear.jpg', FILE_PARMITION)

        return img

    def copy_image_area(self, src_img, dest_img, src, dest=None):

        if dest is None:
            dest = src

        img = src_img[src.rect[1]:src.rect[3], src.rect[0]:src.rect[2]]
        dest_img[dest.rect[1]:dest.rect[3], dest.rect[0]:dest.rect[2]] = img

    # 文字のX位置の間隔が離れている文字列を分割
    def split_word_by_gap(self, row, x_span=5):

        words = []
        if not row['chars']:
            return words

        text = row['chars'][0]['text']
        # text = copy.copy(row['chars'][0]['text'])
        # x = row['chars'][0]['bounds'].get_right()  # 文字の右
        prev_ch = row['chars'][0]
        for i, ch in enumerate(row['chars'][1:]):
            # 数字は接近している前提で小さい数字の幅を優先
            # if prev_ch['text'].isdigit():
            #     w = prev_ch['bounds'].get_width()
            # else:
            #     w = ch['bounds'].get_width()

            w = ch['bounds'].get_height() # 高さを使う
            w *= x_span
            # w = ch['bounds'].get_width() * x_span
            c = ch['text']
            diff = ch['bounds'].get_left() - prev_ch['bounds'].get_right() # 前の文字との距離
            # diff = ch['bounds'].get_left() - x # 前の文字との距離
            d = c.isdigit()
            if diff >= w:
                words.append(text)
                text = ''

            # x = ch['bounds'].get_right()  # 文字の右
            text += ch['text']

            prev_ch = ch

        if text:
            words.append(text)

        return words

    # 文字のX位置から勘定科目と金額に分割
    def split_subject_amount_list(self, row):
    # def split_subject_amount_list_by_gap(self, row, x_span=5):

        word_list = []

        # start = 0
        ret = list(subject_amount_pat.finditer(row['text']))
        if len(ret) >= 2:
            close = [self.account_db.search_variety_title(ret[0].group(1)), self.account_db.search_variety_title(ret[1].group(1))]
            if close[0] and close[1]:
                # 同じ行に2個の勘定科目
                subject = ret[0].group(1)
                amount  = ret[0].group(2)
                if amount:
                    f = not_symbol.search(subject)
                    start = 0 if f is None else f.start()
                    end = len(subject)+len(amount)
                    word_list.append({'start':start, 'end':end-1, 'subject':subject, 'amount':amount})

                    subject = ret[1].group(1)
                    amount  = ret[1].group(2)
                    f = not_symbol.search(subject)
                    start = 0 if f is None else f.start()
                    start = end + start
                    end += len(subject)+len(amount)
                    word_list.append({'start':start, 'end':end-1, 'subject':subject, 'amount':amount})
            aaa = 0

        # words = self.split_word_by_gap(row, x_span)

        # word_list = []

        # subject = amount  = ''
        # start = 0
        # for word in words:
        #     found = amount_pat.search(word)
        #     # found = list(amount_pat.finditer(word))
        #     if found is None:
        #         subject += word
        #     else:
        #         amount = word
        #         if subject and amount:
        #             word_list.append({'end':start+len(amount)-1, 'subject':subject, 'amount':amount})
        #         subject = amount  = ''

        #     start += len(word)

        # if subject and amount:
        #     word_list.append([subject, amount])

            # f = amount_pat.search(word)

        #     if any(c.isdigit() for c in word):

        #     subject = ''
        #     for w in words[:-1]:
        #         subject += w

        #     return subject, amount

        return word_list

    # 文字のX位置から勘定科目と金額に分割
    def split_subject_amount_by_gap(self, row, x_span=2, check_digit=True):
    # def split_subject_amount_by_gap(self, row, x_span=5, check_digit=True):

        words = self.split_word_by_gap(row, x_span)
        if len(words) >= 2:
            for i in range(1,len(words)):
                if any(c.isdigit() for c in words[i]):
                    if check_digit and any(c.isdigit() for c in words[i-1]):
                        break # 前も数字 i=1しか無い

                    amount = words[i]

                    subject = ''
                    for w in words[:i]:
                        subject += w

                    return subject, amount

        return row['text'], ''

    # def split_subject_amount_by_gap(self, row, x_span=5):

    #     words = self.split_word_by_gap(row, x_span)
    #     if len(words) >= 2 and any(c.isdigit() for c in words[-1]):
    #         amount = words[-1]

    #         subject = ''
    #         for w in words[:-1]:
    #             subject += w

    #         return subject, amount

    #     return row['text'], ''

    def find_table_blocks(self, org_rows, chars, no, org_img, path):

        xw = 32.0 #16.0
        tables = []
        clear_img = None
        on_table = False
        height, width = org_img.shape[0], org_img.shape[1]

        debug_print( f'VLINE({no}) -->',level=DEBUG_ROWS_INFO)
        # self.clear_char_area(self.papers[page_no]['texts'],self.papers[page_no]['image'],self.papers[page_no]['path'])
        # clear_img = self.clear_char_area(chars, org_img, path)
        if clear_img is None:
            clear_img = org_img.copy() # ここに入ることは無いはず

            # #縦線強化用カーネル
            # kernel = np.array([[0,1,0],[0,1,0],[0,1,0]], dtype=np.uint8)

            # #縦線強化
            # clear_img = cv2.erode(clear_img,kernel,iterations = 3)

            # #縦線強化用カーネル
            # kernel = np.array([[0,1,0],[1,1,1],[0,1,0]], dtype=np.uint8)

            # #縦線強化
            # clear_img = cv2.erode(clear_img,kernel,iterations = 1)

            # # clear_img = org_img # ここに入ることは無いはず

        table = {'page':None, 'sy':None, 'ey':None, 'row':[], 'col':[], 'total':0}
        on_table = False

        table_type = account_DB.Order.NON
        rows = []
        for row in org_rows:
            if len(row['text']) == 1: # 一文字は高さが十分では無い可能性
                if row['text'].isascii(): #.isalnum(): # .isascii():
                    continue
            rows.append(row)

            if table_type == account_DB.Order.NON:
                texts = self.split_word_by_gap(row)
                table_type = self.account_db.search_type(texts)

        # if type != account_DB.Order.NON:
        #     # 別テーブルなのでリセット
        #     self.col_list = []

        # stats_v からYの重なりを探して　vline作成
        def find_vertical_line_by_stats_v(bounds):
            vline = []
            for col in self.stats_v[no]:
                if col[1] > bounds.get_bottom() or (col[1]+col[3]) < bounds.get_top(): # 線の上端 > 文字範囲の下 or 線の下端 < 文字範囲の上
                # if col[0] > bounds.get_right() or col[1] > bounds.get_bottom() or (col[0]+col[2]) < bounds.get_left() or (col[1]+col[3]) < bounds.get_top(): # 線の上端 < 文字範囲の下 or 線の下端 < 文字範囲の上
                    continue
                vline.append(col[0])

                # if col[1] >= bounds.get_right() and (col[0]+col[2]) >= bounds.get_left() and col[1] >= bounds.get_bottom() and (col[1]+col[3]) >= bounds.get_top(): # 線の上端 >= 文字範囲の下 and 線の下端 >= 文字範囲の上
                    # vline.append(col[0])

            return vline

        # 行を上下に半分づつずらして縦線をみる(stats_vも同時に評価)
        vrows = []
        vrows_stats_v = [] # stats_v用
        rows_max = len(rows)
        for i, row in enumerate(rows):
            b = [
                copy.deepcopy(row['bounds']),
                copy.deepcopy(row['bounds'])
            ]

            b[0].offset(0,int(-b[0].get_height()/2))
            b[1].offset(0,int(b[1].get_height()/2))

            for j in range(2):
                b[j].expand_wh(0,int(b[j].get_height()*0.2))
                b[j].revise_height(0,height)

            # debug_print( '{} {}:{}'.format(vline,row['page'],row['text']),level=DEBUG_ROWS_INFO)

            vline = self.find_vertical_line('{}_{:02}-1'.format(path,i), clear_img, b[0], img_width=True)
            vline2 = self.find_vertical_line('{}_{:02}-2'.format(path,i), clear_img, b[1], img_width=True)
            vline3 = find_vertical_line_by_stats_v(row['bounds'])
            #if b[0].get_height() <= 32 or b[1].get_height() <= 32:
            #    vline = []
            #    vline2 = []

            vrows.append({'no':i, 'row':row, 'vline':[vline,vline2], 'row_block':-1})
            vrows_stats_v.append({'no':i, 'row':row, 'vline':[vline3,vline3], 'row_block':-1})

        debug_print( f'<table_blocks[A]>:{no}',level=DEBUG_ROWS_INFO)
        for r in vrows:
            debug_print( '{}({}):{} {}:{}'.format(r['no'], r['row_block'], r['vline'], r['row']['bounds'].to_string(), r['row']['text']), level=DEBUG_ROWS_INFO)
        debug_print( f'<---table_blocks[A]:{no}',level=DEBUG_ROWS_INFO)

        # stats_vがある場合は使用する(3本以上あれば有効)
        use_stats_v = False #DEBUG
        # use_stats_v = len(self.stats_v[no]) >= 3
        if use_stats_v:
            vrows = vrows_stats_v

        debug_print( f'stats_v:{no}[{use_stats_v}]',level=DEBUG_ROWS_INFO)
        for col in self.stats_v[no]:
            debug_print( '{}({}):{}'.format(col, col[1]+col[3], int(col[3]/height*100)), level=DEBUG_ROWS_INFO)
        debug_print( '<table_blocks[A-2]>',level=DEBUG_ROWS_INFO)
        for r in vrows_stats_v:
            debug_print( '{}({}):{} {}:{}'.format(r['no'], r['row_block'], r['vline'], r['row']['bounds'].to_string(), r['row']['text']), level=DEBUG_ROWS_INFO)
        debug_print( f'<---table_blocks[A-2]:{no}',level=DEBUG_ROWS_INFO)

        # 勘定科目の始まりと終わりを探す
        blank = 0
        start_table_row = None
        end_table_row = None
        except_table_subject_row = None
        alph_sym = re.compile(f'([A-Za-zＡ-Ｚａ-ｚⅠ-ⅹ.]+)')
        # except_table = False
        for j in range(len(vrows))[::-1]:
            r = vrows[j]
            # if r['row']['page'] == '5' and r['row']['row_no'] == 1:
            #     aaa = 0

            # 日付が含まれる行は除外
            f = search_date(r['row']['text'])
            if f:
                continue

            # if '売上高' in r['row']['text']:
            #     aaa = 0

            # gapで分ける
            # subject, amount = self.split_subject_amount_by_gap(r['row'])
            subject, amount = self.split_subject_amount_by_gap(r['row'], check_digit=False)

            # アルファベット+余計な文字を取り除く
            ret = list(alph_sym.finditer(subject))
            aaa = 0
            for f in ret[::-1]:
                for a in self.account_db.variety_title_alphabet:
                    s1 = SequenceMatcher(None, f.group(0), a[0])
                    r1 = s1.ratio()
                    if r1 > 0.5:
                        break
                else:
                    subject = subject[:f.start(0)] + subject[f.end(0):]

            # 対象外のテーブルタイトルがあるか確認
            for ts in account_DB.except_table_subject:
                if subject == ts:
                # if subject in ts:
                    # except_table = True
                    start_table_row = None
                    blank = 0
                    end_table_row = None

                    except_table_subject_row = r
                    break
            else:
                # 対象外のテーブルタイトルでは無い
                aaa = 0

                if subject and any(c.isdigit() for c in amount):
                    close = self.account_db.search_variety_title(subject, ratio=0.6, code=(1,), between=(2,))
                    if close:
                        close = self.account_db.search_variety_title(subject, ratio=0.7, code=(3,))
                        if close:
                        # code = self.account_db.search_variety_code(close[0],code=(3,))
                        # if code:
                            if any(c.isdigit() for c in amount):
                                # txt = revise_date_nengo(amount)
                                # f = search_date(txt)
                                # if f is None:
                                    # start_table_row = r

                                blank = 0
                            else:
                                blank += 1
                        else:
                            if blank >= 2 or not end_table_row:
                            # if except_table == False and (blank >= 2 or not end_table_row):
                                end_table_row = r

                            start_table_row = r
                            blank = 0
                    else:
                        blank += 1

                # if start_table_row and blank >= 3:
                #     break

        start_table_row_no = 0
        if start_table_row:
            # start_table_row_no = start_table_row['row']['row_no']
            start_table_row_no = start_table_row['no']
        end_table_row_no = len(vrows)
        if end_table_row:
            # end_table_row_no = end_table_row['row']['row_no']+1
            end_table_row_no = end_table_row['no']+1

        # BS T?
        BS_T_table = False
        for r in vrows:
            if r['no'] < start_table_row_no:
                continue # 始まりより前

            ret = list(subject_amount_pat.finditer(r['row']['text']))
            if len(ret) == 2:
                close = [self.account_db.search_variety_title(ret[0].group(1)), self.account_db.search_variety_title(ret[1].group(1))]
                if close[0] and close[1]:
                    # 同じ行に2個の勘定科目
                    BS_T_table = True
                    break

        aaa = 0

        # 縦のラインでまとめる
        total = 0
        row_total = 0
        col_list = []
        for r in vrows:
            if r['no'] < start_table_row_no:
                continue # 始まりより前
            row_total += 1
            for j in range(2):
                if r['vline'][j]:
                    r['vline'][j].insert(0,0)
                    total += 1

                for v in r['vline'][j]:
                    for col in col_list:
                        if (col['x']-xw) <= v <= (col['x']+xw):
                            col['cnt'] += 1
                            if col['max'] < v:
                                col['max'] = v
                            if col['min'] > v:
                                col['min'] = v
                            col['x'] = int((col['max']+col['min'])/2)
                            # col['x'] = int((col['x']+v)/2)
                            # col['x'] = int(col['col']/col['cnt'])
                            break
                    else:
                        col_list.append({'x':(v), 'max':(v), 'min':(v), 'cnt':1, 'flags':0})

        col_list.sort(key=lambda x: x['x'])

        debug_print( f'COL[1]:{total},{row_total}', level=DEBUG_ROWS_INFO)
        for col in col_list:
            debug_print( col, level=DEBUG_ROWS_INFO)

        total = row_total

        def remove_empty_col_block(total):
            # 文字が無いブロックを除外して全体の列情報を確定
            half_total = int(total/2)   # カウントが1/2以下は除外
            if len(col_list) > 1:
                if col_list[0]['flags'] != -1:
                    col_list[0]['flags'] = 1
                new_col = [col_list[0]]
                x = 0
                for i, col in enumerate(col_list[1:]):
                    if half_total <= col['cnt']: # totalの半分以下は除外
                        b = Bound(left=x, top=0, right=col['x'], bottom=height)
                        x = col['x']+1
                        # b = Bound(left=col_list[i]['x'], top=0, right=col['x'], bottom=height)
                        for row in vrows:
                            if row['no'] < start_table_row_no:
                                continue # 始まりより前

                            in_cnt = 0
                            for c in row['row']['chars']: # 一文字づつで確認
                                if b.is_included(c['bounds'], True):
                                    in_cnt += 1
                                    if in_cnt > 1:
                                        break

                            if in_cnt > 1:
                            # if b.is_included(row['row']['bounds'], True): # 行全体で確認
                                if col['flags'] != -1:
                                    col['flags'] = 1
                                new_col.append(col)
                                break
                        else:
                            if col == col_list[-1]:
                                # 最後は一つ前を削除して右端(幅)をセット
                                if len(new_col) > 1:
                                    del new_col[-1]
                                    # new_col[-1]['flags'] = 0
                                if col_list[-1]['flags'] != -1:
                                    col_list[-1]['flags'] = 1
                                new_col.append(col_list[-1])

                            aaa = 0

                # col_list[-1]['flags'] = 1
                # new_col.append(col_list[-1])

                # for i, col in enumerate(col_list[1:-1]):
                #     if half_total <= col['cnt']: # totalの半分以下は除外
                #         b = Bound(left=col_list[i]['x'], top=0, right=col['x'], bottom=height)
                #         for row in vrows:
                #             if b.is_included(row['row']['bounds'], True):
                #                 col['flags'] = 1
                #                 new_col.append(col)
                #                 break
                #         else:
                #             aaa = 0

                # col_list[-1]['flags'] = 1
                # new_col.append(col_list[-1])

            else:
                new_col = []

            if not new_col or len(new_col) == 1:
                # 何もなければ両端
                new_col = [
                        {'x':0, 'max':0, 'min':0, 'cnt':total, 'flags':1},
                        {'x':width, 'max':width, 'min':width, 'cnt':total, 'flags':1}
                        # {'x':0, 'col':0, 'cnt':total, 'flags':1},
                        # {'x':width, 'col':0, 'cnt':total, 'flags':1}
                ]
            else:
                if new_col[0]['min'] < new_col[0]['x']:
                    new_col[0]['x'] = new_col[0]['min']
                if new_col[-1]['max'] > new_col[-1]['x']:
                    new_col[-1]['x'] = new_col[-1]['max']

            return new_col

        # # 文字が無いブロックを除外して全体の列情報を確定
        # half_total = int(total/2)   # カウントが1/2以下は除外
        # if len(col_list) > 1:
        #     col_list[0]['flags'] = 1
        #     new_col = [col_list[0]]
        #     x = 0
        #     for i, col in enumerate(col_list[1:]):
        #         if half_total <= col['cnt']: # totalの半分以下は除外
        #             b = Bound(left=x, top=0, right=col['x'], bottom=height)
        #             x = col['x']+1
        #             # b = Bound(left=col_list[i]['x'], top=0, right=col['x'], bottom=height)
        #             for row in vrows:

        #                 in_cnt = 0
        #                 for c in row['row']['chars']: # 一文字づつで確認
        #                     if b.is_included(c['bounds'], True):
        #                         in_cnt += 1
        #                         if in_cnt > 1:
        #                             break

        #                 if in_cnt > 1:
        #                 # if b.is_included(row['row']['bounds'], True): # 行全体で確認
        #                     col['flags'] = 1
        #                     new_col.append(col)
        #                     break
        #             else:
        #                 if col == col_list[-1]:
        #                     # 最後は一つ前を削除して右端(幅)をセット
        #                     if len(new_col) > 1:
        #                         del new_col[-1]
        #                         # new_col[-1]['flags'] = 0
        #                     col_list[-1]['flags'] = 1
        #                     new_col.append(col_list[-1])

        #                 aaa = 0

        #     # col_list[-1]['flags'] = 1
        #     # new_col.append(col_list[-1])

        #     # for i, col in enumerate(col_list[1:-1]):
        #     #     if half_total <= col['cnt']: # totalの半分以下は除外
        #     #         b = Bound(left=col_list[i]['x'], top=0, right=col['x'], bottom=height)
        #     #         for row in vrows:
        #     #             if b.is_included(row['row']['bounds'], True):
        #     #                 col['flags'] = 1
        #     #                 new_col.append(col)
        #     #                 break
        #     #         else:
        #     #             aaa = 0

        #     # col_list[-1]['flags'] = 1
        #     # new_col.append(col_list[-1])

        # else:
        #     new_col = []

        # if not new_col:
        #     # 何もなければ両端
        #     new_col = [
        #             {'x':0, 'max':0, 'min':0, 'cnt':total, 'flags':1},
        #             {'x':width, 'max':width, 'min':width, 'cnt':total, 'flags':1}
        #             # {'x':0, 'col':0, 'cnt':total, 'flags':1},
        #             # {'x':width, 'col':0, 'cnt':total, 'flags':1}
        #     ]
        # else:
        #     if new_col[0]['min'] < new_col[0]['x']:
        #         new_col[0]['x'] = new_col[0]['min']
        #     if new_col[-1]['max'] > new_col[-1]['x']:
        #         new_col[-1]['x'] = new_col[-1]['max']

        new_col = remove_empty_col_block(row_total)
        # new_col = remove_empty_col_block(total)
        col_list = new_col

        debug_print( f'COL[2]:{total}', level=DEBUG_ROWS_INFO)
        for col in col_list:
            debug_print( col, level=DEBUG_ROWS_INFO)

        # stats_col_list = []
        # debug_print( f'stats_v:{no} -> x座標, y座標, 幅, 高さ, 面積 [{width},{height}]', level=DEBUG_ROWS_INFO)
        # for col in self.stats_v[no]:
        #     # debug_print( str(col) + ':{}'.format(col[3]/height), level=DEBUG_ROWS_INFO)
        #     debug_print( '{}:{}'.format(col, int(col[3]/height*100)), level=DEBUG_ROWS_INFO)

        #     if col[3]/height < 0.25:
        #         continue

        #     stats_col_list.append({'x':col[0], 'max':-1, 'min':-1, 'cnt':-1, 'flags':1})

        # col_list = stats_col_list
        # debug_print( f'COL[2.5]:{total}', level=DEBUG_ROWS_INFO)
        # for col in col_list:
        #     debug_print( col, level=DEBUG_ROWS_INFO)

        # use_stats_v = len(stats_col_list) > 1

        aaa = 0
        # 貸借対照表の場合に勘定科目と金額の間の線を取り除く
        # 現金 | 123,456 | 買掛金 | 654,321 -> 現金   123,456 | 買掛金   654,321
        for r in vrows:
            if r['no'] < start_table_row_no:
                continue # 始まりより前
            if '(△)' in r['row']['text']:
                aaa = 0

            ret = list(subject_amount_pat.finditer(r['row']['text']))
            if len(ret) == 2:
                close = [self.account_db.search_variety_title(ret[0].group(1)), self.account_db.search_variety_title(ret[1].group(1))]
                if close[0] and close[1]:
                    # 同じ行に2個の勘定科目
                    amount  = [ret[0].group(2), ret[1].group(2)]

                    # 勘定科目と金額の間にある縦線を探す
                    for i in range(2):
                        st1 = ret[i].start(1)
                        ed1 = ret[i].end(1)
                        st2 = ret[i].start(2)
                        ed2 = ret[i].end(2)
                        if st1 == ed1 or st2 == ed2:
                            continue

                        x1 = r['row']['chars'][ed1-1]['bounds'].get_right() # 勘定科目の後
                        x2 = r['row']['chars'][st2]['bounds'].get_left()  # 金額の前
                        cx = int((x1+x2)/2)

                        # 縦線を探す
                        for col in col_list:
                            # if (col['x']-xw) <= cx <= (col['x']+xw): # 間が狭すぎてダメ
                            if x1 < col['x'] < x2:
                                # あった
                                aaa = 0

                                col['flags'] -= 1 # 削除カウント
                                # col['flags'] = -1 # 削除

                                # col['flags'] = 0 # 削除
                                break
                        aaa = 0

                    aaa = 0
            aaa = 0

        # 削除カウントが2行以上
        for col in col_list:
            if col['flags'] <= -1:
                col['flags'] = -1
            else:
                col['flags'] = 1

        debug_print( f'COL[3]:{total}', level=DEBUG_ROWS_INFO)
        for col in col_list:
            debug_print( col, level=DEBUG_ROWS_INFO)


        # 縦線が無い帳票で左右に分れている項目
        # 現金  123,456  買掛金  654,321 -> 現金  123,456 | 買掛金  654,321

        if BS_T_table:
        # if len(col_list) <= 2:
            table_on = -1

            for i, r in enumerate(vrows):
                if r['no'] < start_table_row_no:
                    continue # 始まりより前
                if 'その他利益余剰金' in r['row']['text']:
                    aaa = 0
                found = self.split_subject_amount_list(r['row'])
                # found = self.split_subject_amount_list_by_gap(r['row'])
                if len(found) == 2: # [科目 金額  科目 金額]の並び
                    if table_on == -1:
                        table_on = i

                    ed = found[0]['end']
                    # if not r['row']['chars'][ed]['text'].isdigit():
                    #     ed -= 1

                    st = found[1]['start']
                    # st = ed + 1

                    # 左右に1文字分を広げる(2023/01/06)
                    x1 = r['row']['chars'][ed]['bounds'].get_left()   # 金額の後
                    x2 = r['row']['chars'][st]['bounds'].get_right()  # 勘定科目の前
                    # x1 = r['row']['chars'][ed]['bounds'].get_right() # 金額の後
                    # x2 = r['row']['chars'][st]['bounds'].get_left()  # 勘定科目の前
                    px = int((x1+x2)/2)
                    # px = x1 # int((x1+x2)/2)

                    # xw2 = xw*2
                    # 縦線を探す
                    for col in col_list:
                        if x1 <= col['x'] <= x2:
                        # if (col['x']-xw2) <= px <= (col['x']+xw2):
                        # if x1 < col['x'] < x2:
                            # あった
                            col['cnt'] += 1
                            if col['min'] > px:
                                col['min'] = px
                            if col['max'] < px:
                                col['max'] = px
                            # if col['min'] > x1:
                            #     col['min'] = x1
                            # if col['max'] < x2:
                            #     col['max'] = x2
                            break
                    else:
                        on = False
                        for col in col_list:
                            if col['flags'] == 2: # 文字が欠落する時があるので勘定科目と金額の間の線は右側優先
                                if col['x'] < px:
                                    # 右ある
                                    col['x'] = px
                                    col['max'] = px
                                col['cnt'] += 1
                                on = True
                                break

                        if not on:
                            # 無いのでcol情報に追加
                            # とりあえず先頭に挿入
                            col_list.insert(0, {'x':px, 'max':px, 'min':px, 'cnt':total, 'flags':2})
                            if table_on == -1:
                                table_on = i

            if table_on != -1:
                # 追加したcol情報を再評価
                new_col_list = []
                for k, col in enumerate(col_list):
                    if col['flags'] == 2:
                        for col2 in col_list[k+1:]:
                            if col['min'] <= col2['x'] <= col['max']:
                                break
                        else:
                            new_col_list.append(col)
                    else:
                        new_col_list.append(col)

                col_list = new_col_list
                col_list.sort(key=lambda x: x['x']) # とりあえず先頭に入れたものを正しい位置

                # if self.table_type == table_type and self.col_list:
                #     # 前のページと同じタイプのテーブル
                #     col_list = self.col_list

                # 各列の右側を調整
                vline = []
                for col in col_list:
                    if col['x'] == 0 or col['x'] == width:
                        vline.append(col['x'])
                        continue

                    if col['max']+xw > width:
                        col['x'] = width
                    # else:
                    #     col['x'] = col['max']+(xw/2)
                    vline.append(col['x'])

                aaa = 0
                # vlineに追加
                st = table_on
                # table_on = False
                for r in vrows[table_on:]:

                    # found = list(subject_amount_pat.finditer(r['row']['text']))
                    # for f in found:
                    #     # 勘定科目がある
                    #     close = self.account_db.search_variety_title(f.group(1))
                    #     if close:
                    #         break
                    # else:
                    #         aaa = 0 # 勘定科目は無い

                    r['vline'] = [vline,vline]

                    # if not table_on:
                    #     close = self.account_db.search_variety_title(r['row']['text'])
                    #     if close:
                    #         table_on = True

                    # if table_on:
                    #     r['vline'] = [vline,vline]

                    aaa = 0
            aaa = 0

        col_list.sort(key=lambda x: x['x']) # ソート
        debug_print( f'COL[4]:{total}', level=DEBUG_ROWS_INFO)
        for col in col_list:
            debug_print( col, level=DEBUG_ROWS_INFO)


        # 縦線が無い帳票で分れている項目
        # 現金  123,456  654,321 789,000 -> 現金 | 123,456 | 654,321 | 789,000
        # 現金  123,456                  -> 現金 | 123,456 |
        # 現金           654,321         -> 現金 |         | 654,321 |
        # 現金           654,321 789,000 -> 現金 |         | 654,321 | 789,000

        # BS_T_table = True
        # use_stats_v = False #DEBUG
        if not BS_T_table and use_stats_v == False:
        # if len(col_list) <= 2:

            max = 0
            table_on = -1
            # cols = []
            for i, r in enumerate(vrows):
                if r['no'] < start_table_row_no:
                    continue # 始まりより前

                # if r['no'] == 23:
                #     aaa = 0

                if '車両' in r['row']['text']:
                    aaa = 0
                # if '賞与31当金' in r['row']['text']:
                #     aaa = 0

                # BS_T_table=False は同じ行に1個の勘定科目しか無いのでコメントアウト
                # found = list(one_subject_amount_pat.finditer(r['row']['text']))
                # if len(found) == 1:
                    # 同じ行に1個の勘定科目

                if True:
                    # subject, amount = self.split_subject_amount_by_gap(r['row'])
                    subject, amount = self.split_subject_amount_by_gap(r['row'], check_digit=False,x_span=3)

                    close = self.account_db.search_variety_title(subject)
                    # close = self.account_db.search_variety_title(found[0].group(1))

                    def search_not_braces(chars, step=1):
                        for j, c in enumerate(chars[::step]):
                            if braces_pat.search(c['text']) is None:
                                return j * step
                        return 0

                    if True: #close:
                        if any(c.isdigit() for c in amount) and version_sign.search(amount) == None:
                            st = len(subject)
                            prev = st-1
                        # if any(c.isdigit() for c in found[0].group(2)):
                        #     st = found[0].start(2)

                            # p = search_not_braces(r['row']['chars'][:st-1], -1)
                            # prev = st-1-p

                            # n = search_not_braces(r['row']['chars'][st:])
                            # st += n

                            for j, ch in enumerate(r['row']['chars'][st:]):

                            # x = r['row']['chars'][st]['bounds'].get_right()  # 金額の後
                            # for ch in r['row']['chars'][st+1:]:
                                if braces_pat.search(ch['text']) is not None:
                                    continue
                                h = ch['bounds'].get_height()
                                c = ch['text']
                                x1 = r['row']['chars'][prev]['bounds'].get_right()  # 勘定科目の最後
                                x2 = ch['bounds'].get_left()
                                diff = x2 - x1 # 金額の前
                                d = c.isdigit()
                                if diff >= h: # 幅であるが高さを閾に使う
                                    if not close:
                                        # 金額か?
                                        f = amount_pat.search(r['row']['text'][st+j:])
                                        if not f:
                                            # 勘定科目:金額ではない
                                            continue

                                    # prev = st+j-1
                                    # pc = r['row']['chars'][prev]['text']

                                    px = x1+16 #int((x1+x2)/2) #26変更
                                    # px = x1 #int((x1+x2)/2)

                                    # px = int(r['row']['chars'][prev]['bounds'].get_right())
                                    # col.append({'text':pc, 'x':px})
                                    # col.append({'no':prev, 'text':pc, 'x':px})

                                    # if px == 2951:
                                    #     aaa = 0

                                    max += 1
                                    if j == 0: # 勘定科目と金額の間は1つだけ
                                        on = False
                                        for col in col_list:
                                            if col['flags'] == 10: # == 2: # 文字が欠落する時があるので勘定科目と金額の間の線は右側優先
                                                aaa = 0
                                                if px < col['next']:
                                                    # 金額より前になる
                                                    if col['x'] < px:
                                                        # 右ある
                                                        col['x'] = px
                                                        col['max'] = px
                                                    col['cnt'] += 1


                                                    if col['x'] < x2: ##############
                                                        if col['next'] > x2:
                                                            # 金額の左側が右にある
                                                            col['next'] = x2

                                                on = True
                                                break
                                    else:
                                        on = False
                                        for col in col_list:
                                            if (x1 <= col['x'] <= x2) or (col['min'] <= px <= col['max']):
                                                if col['flags'] == 35:
                                                    aaa = 0
                                            # if x1 < col['x'] < x2:
                                                # あった
                                                col['cnt'] += 1
                                                if col['min'] > px:
                                                    col['min'] = px
                                                if col['max'] < px:
                                                    col['max'] = px
                                                # col['x'] = col['max'] #26
                                                col['x'] = int((col['min']+col['max'])/2)
                                                on = True
                                                break
                                    if not on:
                                        # 無いのでcol情報に追加
                                        # とりあえず先頭に挿入
                                        if j == 1:
                                            aaa = 0
                                        col_list.insert(0, {'x':px, 'max':px, 'min':px, 'cnt':total, 'flags':10+j, 'next':x2})
                                        # if table_on == -1:
                                        #     table_on = i
                                        aaa = 0
                                    aaa = 0

                                if table_on == -1:
                                    table_on = i

                                prev = st+j
                                # x = ch['bounds'].get_right()  # 金額の後

                            # 行の最後
                            px = r['row']['chars'][-1]['bounds'].get_right()+1 # +1 ???
                            for col in col_list:
                                # if px <= col['x']:
                                if (col['x']-xw) <= px <= (col['x']+xw):
                                    col['cnt'] += 1
                                    if col['min'] > px:
                                        col['min'] = px
                                    if col['max'] < px:
                                        col['max'] = px

                                    col['x'] = int((col['min']+col['max'])/2)
                                    break
                            else:
                                col_list.insert(0, {'x':px, 'max':px, 'min':px, 'cnt':total, 'flags':3})

                            # col.append(r['row']['text'])
                            # cols.append(col)
            if table_on != -1:
                col_list.sort(key=lambda x: x['x']) # とりあえず先頭に入れたものを正しい位置

                # if self.table_type == table_type and self.col_list:
                #     # 前のページと同じタイプのテーブル
                #     col_list = self.col_list

                # 各列の右側を調整
                vline = []
                for col in col_list:
                    if col['x'] == 0 or col['x'] == width:
                        vline.append(col['x'])
                        continue

                    if col['max']+xw > width:
                        col['x'] = width
                    else:
                        col['x'] = col['max']
                    #     col['x'] = col['max']+xw
                    vline.append(col['x'])

                vline.sort(key=lambda x: x)
                aaa = 0
                # vlineに追加
                st = table_on
                # table_on = False
                for r in vrows[table_on:]:

                    # found = list(subject_amount_pat.finditer(r['row']['text']))
                    # for f in found:
                    #     # 勘定科目がある
                    #     close = self.account_db.search_variety_title(f.group(1))
                    #     if close:
                    #         break
                    # else:
                    #         aaa = 0 # 勘定科目は無い

                    r['vline'] = [vline,vline]

                    # if not table_on:
                    #     close = self.account_db.search_variety_title(r['row']['text'])
                    #     if close:
                    #         table_on = True

                    # if table_on:
                    #     r['vline'] = [vline,vline]

                    aaa = 0
            aaa = 0

        # new_col2 = remove_empty_col_block(total)

        col_list.sort(key=lambda x: x['x']) #

        debug_print( f'COL[5]:{total}', level=DEBUG_ROWS_INFO)
        for col in col_list:
            debug_print( col, level=DEBUG_ROWS_INFO)

        # blank = 0
        # start_table_row = None
        # for j in range(len(vrows))[::-1]:
        #     r = vrows[j]
        #     if r['row']['page'] == '5' and r['row']['row_no'] == 1:
        #         aaa = 0
        #     subject, amount = self.split_subject_amount_by_gap(r['row'])
        #     if subject and any(c.isdigit() for c in amount):
        #         close = self.account_db.search_variety_title(subject, ratio=0.7, code=(1,), between=(2,))
        #         if close:
        #             close = self.account_db.search_variety_title(subject, ratio=0.7, code=(3,))
        #             if close:
        #             # code = self.account_db.search_variety_code(close[0],code=(3,))
        #             # if code:
        #                 if any(c.isdigit() for c in amount):
        #                     blank = 0
        #                 else:
        #                     blank += 1
        #             else:
        #                 if blank >= 2:
        #                     aaa = 0
        #                 start_table_row = r
        #                 blank = 0
        #         else:
        #             blank += 1

        #     # if start_table_row and blank >= 3:
        #     #     break

        # if start_table_row:
        #     aaa = 0

        # for r in vrows[1:]: # 数行スキップ
        #     subject, amount = self.split_subject_amount_by_gap(r['row'])
        #     if subject:
        #         close = self.account_db.search_variety_title(subject, ratio=0.8, code=(1,), between=(2,))
        #         if close:
        #             code = self.account_db.search_variety_code(close[0],code=(3,))
        #             if code:
        #                 aaa = 0
        #             else:
        #                 start_table_row = r
        #                 break
        # if start_table_row:
        #     aaa = 0

        aaa = 0
        # 連続した漢字のブロック、文字がないブロックの線は消す
        col_list_tmp = []
        for c in col_list:
            if c['flags'] >= 0:
                col_list_tmp.append(c)

        if start_table_row and len(col_list_tmp) > 1:
            # 0:全ての文字
            # 1:数字
            # 2:行数
            # 3:線の前後が両方数字では無い列数(勘定科目の可能性)
            # 4:列の最大文字数
            k_col_cnt = [[0 for j in range(5)] for i in range(len(col_list_tmp)-1)]
            # k_col_cnt = [[0 for j in range(4)] for i in range(len(col_list_tmp)-1)]
            for j in range(len(col_list_tmp)-1):
                v1 = col_list_tmp[j]['x']
                v2 = col_list_tmp[j+1]['x']
                del_flag = False
                for r in vrows:
                    if r['no'] >= end_table_row_no:
                    # if r['no'] >= end_table_row_no:
                        break
                    if r['no'] < start_table_row['no']:
                        continue

                    # 線の前後の文字
                    bc = None
                    bc_diff = 99999
                    ac = None
                    ac_diff = 99999

                    col_len = 0
                    chars = r['row']['chars']
                    for c in chars:
                        # if c['text'] == '△':
                        #     aaa = 0

                        # （１列テーブル用）
                        if v1 <= c['bounds'].rect[0] <= v2:
                            col_len += 1 # 列の文字数
                            if k_col_cnt[j][4] < col_len:
                                k_col_cnt[j][4] = col_len

                            k_col_cnt[j][0] += 1
                            if c['text'].isdigit():
                                k_col_cnt[j][1] += 1
                            else:
                                aaa = 0

                        # 前後（２列テーブル用）
                        if v2-c['bounds'].rect[0] < 0:
                            # 後
                            dif = c['bounds'].rect[0]-v2
                            if dif < ac_diff:
                                ac_diff = dif
                                ac = c
                        else:
                            # 前
                            dif = v2 - c['bounds'].rect[0]
                            if dif < bc_diff:
                                bc_diff = dif
                                bc = c

                    k_col_cnt[j][2] += 1
                    if ac and bc:
                        if not ac['text'].isdigit() and not bc['text'].isdigit():
                            k_col_cnt[j][3] += 1

                    aaa = 0

            # print(f'k_col_cnt:{no}')
            debug_print( f'k_col_cnt:{no}',level=DEBUG_ROWS_INFO)
            for j in range(len(k_col_cnt)):
                # print(f'{j}:{k_col_cnt[j]}')
                debug_print( f'{j}:{k_col_cnt[j]}',level=DEBUG_ROWS_INFO)

            aaa = 0
            if BS_T_table:
                # ２列テーブル
                aaa = 0
                for j in range(len(k_col_cnt)-1):
                    ratio = 0.5
                    if k_col_cnt[j][2] == 0 or (k_col_cnt[j][3] / k_col_cnt[j][2] >= ratio):
                            col_list_tmp[j+1]['flags'] = -3
                bbb = 0
            else:
                # １列テーブル
                # 列情報から連続した漢字列を調べる
                for j in range(len(k_col_cnt)-1):
                    # 何も無い列は消す
                    if k_col_cnt[j][0] == 0:
                        col_list_tmp[j]['flags'] = -10
                        continue

                    # ブロックの最大桁数が1 かつ 2行以下
                    if k_col_cnt[j][4] == 1 and k_col_cnt[j][0] <= 2:
                        w = col_list_tmp[j+1]['x'] - col_list_tmp[j]['x']
                        if w <= xw*2: # 列幅が64以下
                            col_list_tmp[j]['flags'] = -8 # 前側
                            # col_list_tmp[j+1]['flags'] = -8 # 後側
                            continue

                    # if k_col_cnt[j][0] < 5 or k_col_cnt[j+1][0] < 5:
                    #     # 判定する文字数が少ないので除外
                    #     continue

                    # 連続した漢字の領域の線は消す
                    # 列が０ か 線の前後が両方数字では無い/列数(文字列の間を通る)の割合が0.5以上
                    ratio = 0.5
                    if k_col_cnt[j][0] == 0 or (k_col_cnt[j][1] / k_col_cnt[j][0] < ratio):
                        if k_col_cnt[j+1][0] == 0 or (k_col_cnt[j+1][1] / k_col_cnt[j+1][0] < ratio):
                            col_list_tmp[j+1]['flags'] = -2

                for j in range(len(col_list_tmp)-1):
                    if col_list_tmp[j]['flags'] < 3: # 完全では無いので3だけを対象にする
                    # if col_list_tmp[j]['flags'] != 3: # 完全では無いので3だけを対象にする
                    # if col_list_tmp[j]['flags'] < 0:
                        continue

                    v = col_list_tmp[j]['x']
                    # 文字の上にある線を消す
                    for r in vrows:
                        if r['no'] >= end_table_row_no:
                            break
                        if r['no'] < start_table_row['no']:
                            continue

                        if v == 2984.0:
                            aaa = 0

                        chars = r['row']['chars']
                        for k, c in enumerate(chars):
                            aaa = 0
                            # f = amount_pat.search(c['text'])
                            # if not f: # 数字、記号の制限をかける必要があるか？
                            # # if not c['text'].isdigit(): # 数字では無い
                            #     continue
                            xww = int(xw*1.1)
                            vxw = int(v+xww)
                            if v <= c['bounds'].rect[2] <= vxw:
                                aaa = 0

                            if (c['text'].isdigit() and
                                (v <= c['bounds'].rect[0] <= vxw or v <= c['bounds'].rect[2] <= vxw)):
                                # 区切りから右側vxw以内に数字がある場合
                                if k > 0:
                                    gap = c['bounds'].rect[0] - chars[k-1]['bounds'].rect[2]
                                    # 線の前後文字間がxwwより小さい場合は前後は続いているものとする
                                    if gap < xww:
                                        aaa = 1
                                        col_list_tmp[j]['flags'] = -7
                                        break
                                    else:
                                        aaa = 0
                            elif c['bounds'].rect[0] < v < c['bounds'].rect[2]:
                                # 見出しタイトル？
                                subject, amount = self.split_subject_amount_by_gap(r['row'], check_digit=False)
                                s_len = len(subject)
                                if s_len > 0 and len(amount) == 0:
                                    if not (chars[0]['bounds'].rect[0] < v < chars[s_len-1]['bounds'].rect[2]):
                                        col_list_tmp[j]['flags'] = -5 #-3
                                        break
                                else:
                                    col_list_tmp[j]['flags'] = -3
                                    break
                        if col_list_tmp[j]['flags'] < 0:
                            break

                    aaa = 0
        aaa = 0

##################################################
        # if start_table_row and len(col_list) > 1:
        # # if not BS_T_table and start_table_row and len(col_list) > 1:
        #     # 列内の数字の文字数を数える
        #     k_col_cnt = [[0 for j in range(2)] for i in range(len(col_list)-1)]
        #     for j in range(len(col_list)-1):
        #         v1 = col_list[j]['x']
        #         v2 = col_list[j+1]['x']
        #         del_flag = False
        #         for r in vrows:
        #             if r['no'] >= end_table_row_no:
        #                 break
        #             if r['no'] < start_table_row['no']:
        #                 continue
        #             chars = r['row']['chars']
        #             for c in chars:
        #                 if v1 <= c['bounds'].rect[0] <= v2:
        #                     k_col_cnt[j][0] += 1
        #                     if c['text'].isdigit():
        #                         k_col_cnt[j][1] += 1
        #     aaa = 0
        #     if not BS_T_table:
        #         # 列情報から連続した漢字列を調べる
        #         for j in range(len(k_col_cnt)-1):
        #             # 何も無い列は消す
        #             if k_col_cnt[j][0] == 0:
        #                 col_list[j]['flags'] = -10
        #                 continue

        #             # if k_col_cnt[j][0] < 5 or k_col_cnt[j+1][0] < 5:
        #             #     # 判定する文字数が少ないので除外
        #             #     continue

        #             # 連続した漢字の領域の線は消す
        #             ratio = 0.5
        #             if k_col_cnt[j][0] == 0 or (k_col_cnt[j][1] / k_col_cnt[j][0] < ratio):
        #                 if k_col_cnt[j+1][0] == 0 or (k_col_cnt[j+1][1] / k_col_cnt[j+1][0] < ratio):
        #                     col_list[j+1]['flags'] = -2
        # aaa = 0
##################################################
        # ※うまくとれないので不採用
        # 区切りではなく文字列の中を通る線を削除
        # 123|456789
        # if start_table_row:
        #     for j in range(len(col_list))[::-1]:
        #         v = col_list[j]['x']
        #         del_flag = False
        #         for r in vrows:
        #             if r['no'] < start_table_row['no']:
        #                 continue
        #             chars = r['row']['chars']
        #             for c in chars:
        #                 if c['bounds'].rect[0] < v <= c['bounds'].rect[2]:
        #                     del col_list[j]
        #                     del_flag = True
        #                     break
        #             # for k in range(len(chars)-1):
        #             #     if chars[k]['bounds'].rect[0] < v < chars[k+1]['bounds'].rect[2]:
        #             #         if (chars[k]['bounds'].rect[2] > v - xw) and (chars[k+1]['bounds'].rect[0] < v + xw):
        #             #             del col_list[j]
        #             #             del_flag = True
        #             #             break
        #             if del_flag:
        #                 break

        # 除外された列情報を基に各行のvlineを書き換え
        aaa = 0
        for r in vrows:
            aaa = 0
            for j in range(2):
                for k in range(len(r['vline'][j]))[::-1]:
                    v = r['vline'][j][k]
                    if 0 < v <= xw: # 1-32
                        # ごみの可能性大
                        del r['vline'][j][k]
                    else:
                        for col in col_list:
                            if col['flags'] <= -2:
                            # if col['flags'] <= -3:
                            # if col['flags'] <= -10:
                                if col['x'] == v:
                                    del r['vline'][j][k]
                                    break
                            else:
                                if (col['x']-xw) <= v <= (col['x']+xw):
                                    if col['flags'] <= 0:
                                    # if col['flags'] == 0:
                                        del r['vline'][j][k]
                                    break
                        else:
                            del r['vline'][j][k]
                    # for col in col_list:
                    #     if col['flags'] >= 1:
                    #         continue
                    #     if (col['x']-xw) <= v <= (col['x']+xw):
                    #         del r['vline'][j][k]
                    #         break

                if not r['vline'][j] or len(r['vline'][j]) < 2: # [width]の場合もある
                # if not r['vline'][j]:
                    # ブロック無し
                    r['vline'][j] = [0,width]

        # for r in vrows:
        #     debug_print( '{}({}):{} {}:{}'.format(r['no'], r['flags'], r['vline'], r['row']['bounds'].to_string(), r['row']['text']), level=DEBUG_ROWS_INFO)

        debug_print( f'<table_blocks[B]>:{no}',level=DEBUG_ROWS_INFO)
        for r in vrows:
            debug_print( '{}.{:02}-1:{} {}'.format(no, r['no'], r['vline'][0], r['row']['text']), level=DEBUG_ROWS_INFO)
            debug_print( '{}.{:02}-2:{}'.format(no, r['no'], r['vline'][1]), level=DEBUG_ROWS_INFO)

        # col_list = new_col

        debug_print( f'COL:{total}', level=DEBUG_ROWS_INFO)
        for col in col_list:
            debug_print( col, level=DEBUG_ROWS_INFO)

        # 行ブロックの検出(現)
        def make_row_list():
            if True:
            ##############現
                debug_print( f'<table_blocks[C]>:{no}',level=DEBUG_ROWS_INFO)
                prev_row = None
                row_block = 0
                cur_row_block = -1
                table = False
                block_sy = 0
                row_list = []
                up_down = 0 # 上
                # up_down = 1 # 下
                for r in vrows:
                    # if not row_list or prev_row['row']['row_block'] != row_block:
                    if not row_list or row_list[-1]['row_block'] != row_block:
                        # tableの変わり目
                        row = r
                        if row_list:
                            if up_down == 1:
                                row = prev_row
                                prev_row['row']['block'] = row_block
                                prev_row['row']['row_block'] = row_block
                                prev_row['row_block'] = row_block

                            block_sy = row['row']['bounds'].get_top()

                            # if prev_row is not None:
                            #     block_sy = prev_row['row']['bounds'].get_top()
                            # else:
                            #     block_sy = 0
                            row_list[-1]['ey'] = block_sy-1

                        row_list.append({'row_block':row_block, 'up_down':up_down, 'row':row, 'sy':block_sy, 'ey':height})
                        # row_list.append({'row_block':row_block, 'up_down':up_down, 'row':prev_row if prev_row is not None else r, 'sy':block_sy, 'ey':height})

                    cur_row_block = row_block
                    if not table:
                        if len(r['vline'][0]) > 2:
                            # ON:1 下
                            table = True
                            row_block += 1
                            cur_row_block = row_block
                            up_down = 1
                        elif len(r['vline'][1]) > 2:
                            # ON:2 下
                            table = True
                            row_block += 1
                            cur_row_block = row_block
                            up_down = 1
                    else:
                        len0 = len(r['vline'][0])
                        len1 = len(r['vline'][1])
                        if len0 == 2:
                            # OFF:1 下
                            if len(r['vline'][1]) == 2: # 次のtableの始まりの場合はTrueのままにする
                                table = False
                            row_block += 1
                            cur_row_block = row_block
                            up_down = 1
                        elif len1 == 2:
                            # OFF:2 上
                            table = False
                            row_block += 1
                            up_down = 0
                        else:
                            # 検討
                            if prev_row is not None and len0 != len(prev_row['vline'][1]):
                                # 前行下と現行上が違う
                                # DIFF:1 上
                                row_block += 1
                                up_down = 1 #0
                            elif len0 != len1:
                            # if len0 != len1:
                                # 現行下と現行上が違う
                                # DIFF:2 下
                                row_block += 1
                                cur_row_block = row_block
                                up_down = 1

                    r['row']['block'] = cur_row_block
                    r['row']['row_block'] = cur_row_block
                    r['row_block'] = cur_row_block
                    prev_row = r

                if prev_row is not None and vrows[-1]['row_block'] == row_block and (not row_list or row_list[-1]['row_block'] != row_block):
                    # tableの変わり目でループを抜けた
                    # vrows[-1] != prev_row
                    if row_list:
                        block_sy = prev_row['row']['bounds'].get_top()
                        row_list[-1]['ey'] = block_sy-1
                    row_list.append({'row_block':row_block, 'up_down':up_down, 'row':prev_row, 'sy':block_sy, 'ey':height})
            ##############
            else:
            #########試
                debug_print( f'<table_blocks[C]>:{no}',level=DEBUG_ROWS_INFO)
                prev_row = None
                row_block = 0
                cur_row_block = -1
                table = False
                block_sy = 0
                row_list = []
                up_down = 0 # 上
                # up_down = 1 # 下
                for r in vrows:
                    cur_row_block = row_block
                    if not table:
                        if len(r['vline'][0]) > 2:
                            # ON:1 下
                            table = True
                            row_block += 1
                            cur_row_block = row_block
                            up_down = 1
                        elif len(r['vline'][1]) > 2:
                            # ON:2 下
                            table = True
                            row_block += 1
                            cur_row_block = row_block
                            up_down = 1
                    else:
                        len0 = len(r['vline'][0])
                        len1 = len(r['vline'][1])
                        if len0 == 2:
                            # OFF:1 下
                            if len(r['vline'][1]) == 2: # 次のtableの始まりの場合はTrueのままにする
                                table = False
                            row_block += 1
                            cur_row_block = row_block
                            up_down = 1
                        elif len1 == 2:
                            # OFF:2 上
                            table = False
                            row_block += 1
                            up_down = 0
                        else:
                            # if prev_row is not None and len0 != len(prev_row['vline'][1]):
                            #     # 前行下と現行上が違う
                            #     # DIFF:1 上
                            #     row_block += 1
                            #     up_down = 0
                            # elif len0 != len1:
                            if len0 != len1:
                                # 現行下と現行上が違う
                                # DIFF:2 下
                                row_block += 1
                                cur_row_block = row_block
                                up_down = 1

                    r['row']['block'] = cur_row_block
                    r['row']['row_block'] = cur_row_block
                    r['row_block'] = cur_row_block

                    # if not row_list or prev_row['row']['row_block'] != row_block:
                    if not row_list or row_list[-1]['row_block'] != row_block:
                        # tableの変わり目
                        row = r
                        if row_list:
                            if up_down == 1:
                                row = prev_row

                            block_sy = row['row']['bounds'].get_top()

                            # if prev_row is not None:
                            #     block_sy = prev_row['row']['bounds'].get_top()
                            # else:
                            #     block_sy = 0
                            row_list[-1]['ey'] = block_sy-1

                        row_list.append({'row_block':row_block, 'up_down':up_down, 'row':row, 'sy':block_sy, 'ey':height})
                        # row_list.append({'row_block':row_block, 'up_down':up_down, 'row':prev_row if prev_row is not None else r, 'sy':block_sy, 'ey':height})

                    prev_row = r

                if prev_row is not None and vrows[-1]['row_block'] == row_block and (not row_list or row_list[-1]['row_block'] != row_block):
                    # tableの変わり目でループを抜けた
                    # vrows[-1] != prev_row
                    if row_list:
                        block_sy = prev_row['row']['bounds'].get_top()
                        row_list[-1]['ey'] = block_sy-1
                    row_list.append({'row_block':row_block, 'up_down':up_down, 'row':prev_row, 'sy':block_sy, 'ey':height})

        ##############

        # 行ブロックの検出(試)
        def make_row_list2():
            if len(vrows) == 0:
                return []

            row_list = [{'row_block':0, 'up_down':0, 'row':vrows[0], 'sy':0, 'ey':height}]
            if start_table_row_no > 0:
                block_sy = vrows[start_table_row_no]['row']['bounds'].get_top()
                row_list[0]['ey'] = block_sy - 1
                row_list.append({'row_block':1, 'up_down':0, 'row':vrows[start_table_row_no], 'sy':block_sy, 'ey':height})

            row_list_len = len(row_list)
            for j, r in enumerate(vrows):
                cur_row_block = 1 if start_table_row_no <= j and row_list_len > 1 else 0
                r['row']['block'] = cur_row_block
                r['row']['row_block'] = cur_row_block
                r['row_block'] = cur_row_block

            return row_list

        row_list = make_row_list2()

        for r in vrows:
            debug_print( '{}.{:02}-1:{}:{} {}'.format(no, r['no'], r['row_block'], r['vline'][0], r['row']['text']), level=DEBUG_ROWS_INFO)
            debug_print( '{}.{:02}-2:{}:{}'.format(no, r['no'], r['row_block'], r['vline'][1]), level=DEBUG_ROWS_INFO)

        debug_print( f'ROW:{no}',level=DEBUG_ROWS_INFO)
        for row in row_list:
            debug_print( '{},{}:{}:{}'.format(row['sy'], row['ey'], row['up_down'], row['row']), level=DEBUG_ROWS_INFO)

        debug_print( f'<table_blocks>:{no}',level=DEBUG_ROWS_INFO)
        block_no = 0
        table_blocks = []
        for j, row in enumerate(row_list):
            vline = row['row']['vline'][row['up_down']]
            # if vline[0] != 0:
            #     vline.insert(0,0)
            table_blocks.append({'row':row['row'], 'sy':row['sy'], 'ey':row['ey'], 'st':block_no, 'ed':block_no+len(vline)-1, 'blocks':vline, 'count':0, 'total':0, 'ratio':0})
            debug_print( '{},{} : {}-{}[{}]'.format(row['sy'], row['ey'], block_no, block_no+len(vline)-1, vline), level=DEBUG_ROWS_INFO)
            block_no += (len(vline)-1)

        if len(table_blocks) == 0: # ページにはなにも無い（白紙対応）
            table_blocks.append({'row':{'row_block':-1}, 'st':0, 'ed':0, 'blocks':[], 'count':0, 'total':0, 'ratio':0})
            # table_blocks.append({'row':{'row_block':-1, 'blocks':[]}, 'sy':0, 'ey':0, 'st':0, 'ed':0, 'blocks':[], 'count':0, 'total':0, 'ratio':0})

        debug_print( f'VLINE({no}) <--',level=DEBUG_ROWS_INFO)

        return table_blocks, vrows, table_type, col_list, [start_table_row,end_table_row,except_table_subject_row], BS_T_table


    def find_blocks(self, chars, no, paper):
        # blocks = super().find_blocks(chars, no, paper)

        # self.find_vline(paper['image'], paper['path'])

        # blocks = super().find_rows(chars, no, blocks)
        blocks = [0,paper['width']]
        return [{'row':0, 'sy':0, 'ey':paper['height'], 'blocks':blocks}]
        # return blocks

    def find_keyword_title(self, txt1, txt2):

        close1 = self.account_db.search_variety_title(txt1)
        # close1 = difflib.get_close_matches(txt1,self.keyword_title)#,cutoff=ratio)
        if close1:
            aaa = 0
        close2 = self.account_db.search_variety_title(txt2)
        # close2 = difflib.get_close_matches(txt2,self.keyword_title)#,cutoff=ratio)
        if close2:
            aaa = 0

        for t in self.keyword_title:
            if t in txt1 or t in txt2:
                return t

        return None

    def find_table_row(self, rows_org, rows_block, table_block, chars, vrows):

        # XXX 999,999 のペアが同一行内何個あるか？
        # ２個は貸借対照表 左ブロック上から下、右ブロック上から下の順で読む
        # 現金 123,456  買掛金 654,321

        # 縦線がある帳票もある
        # 現金 | 123,456 | 買掛金 | 654,321


        # １個は上から下、ブロックが複数ある場合の縦線はセパレータとして使う
        # 現金 123,456
        # 現金 | 123,456 | 100.0 | 456,123 | 100.0

        cnt = 0 # ペアのある行数
        for r in rows_org:

            r['cols'] = [] # セパレータとして分けた時のために
            for c in r['chars']:
                c['row'] = r

            # ペアがある可能性？
            ret = table_row_pat.findall(r['text'])
            if len(ret) >= 2:
                cnt += 1
                if 'row_block' in r:
                    m = self.find_keyword_title(ret[0],ret[1])
                    # m = self.find_keyword_title(r['text'])
                    # if m is not None:
                    #     table_block[r['row_block']]['count'] += 1
                    table_block[r['row_block']]['count'] += 1

                    table_block[r['row_block']]['total'] += 1
            else:
                if 'row_block' in r and len(table_block) > r['row_block']:
                    table_block[r['row_block']]['total'] += 1

        ratio = cnt / len(rows_org) if len(rows_org) >= 1 else 0
        for t in table_block:
            if t['total'] > 0:
                t['ratio'] = t['count'] / t['total']

            if t['total'] <= 3 and t['ratio'] > 0 and t['ratio'] <= 0.7:
                # 数が少ない時の調整
                t['ratio'] = 0

        aaa = 0
        # ブロック分けした行を再構成するための情報
        for r in rows_block:
            # if not r['chars'] or not 'row' in r['chars'][0]:
            if not 'row' in r['chars'][0]:
                continue

            r['row'] = r['chars'][0]['row']
            # r['row_block'] = r['row']['block']
            for c in r['chars']:
                c['rows_block'] = r

                if 'row' in c and r not in c['row']['cols']:
                    c['row']['cols'].append(r) # 元の行情報

        # 文字左上があるブロックを取得
        def get_table_block_no(table_block, bounds):
            aaa = 0
            for i, tb in enumerate(table_block):
                if 'sy' in tb and tb['sy'] <= bounds.rect[1] <= tb['ey']:
                    for j, v in enumerate(tb['blocks'][1:]):
                        if bounds.rect[0] <= v:
                            return [i, j]

            return None

        aaa = 0
        # 数字の前に移動した'△'が移動前とブロックが違う時は削除
        for c in chars:
            if 'origin' in c:
                org_block = get_table_block_no(table_block,c['origin'])
                dts_block = get_table_block_no(table_block,c['bounds'])

                if org_block is not None and dts_block is not None:
                    if org_block != dts_block:
                        aaa = 0
                        # 元の位置に戻す
                        c['bounds'] = c['origin']
                        for j in range(len(c['rows_block'])):
                            if c['no'] == c['rows_block']['chars'][j]['no']:
                                c['rows_block']['text'] = c['rows_block']['text'][:j] + c['rows_block']['text'][j+1:]
                                del c['rows_block']['chars'][j]

                                for r in rows_block:
                                    if c['rows_block']['row']['page'] == r['row']['page']:
                                        if c['rows_block']['row']['row_no'] == r['row']['row_no']:
                                            r['text'] += c['text']
                                            r['chars'].append(c)
                                            break

                                break
                aaa = 0

        return rows_block

    # [△]
    # 離れた△を数字の前に移動する
    def move_triangle_char(self, rows, chars):

        sym1 = re.compile(f'([△▲])[0-9０-９]+')

        for r in rows:
            ret = list(sym1.finditer(r['text']))
            if ret:
                aaa = 0
                for f in ret:
                    st = f.start(1)
                    if st+1 < len(r['text']):
                        b = r['chars'][st+1]['bounds']

                        if 'origin' not in r['chars'][st]:
                            r['chars'][st]['origin'] = copy.deepcopy(r['chars'][st]['bounds']) # 元の座標を保存
                        r['chars'][st]['bounds'] = Bound(left=b.get_left()-b.get_width()-4, top=b.get_top(), right=b.get_left()-2, bottom=b.get_bottom())

                    # x = r['chars'][st+1]['bounds'].get_left() - r['chars'][st]['bounds'].get_right() - 1
                    # r['chars'][st]['bounds'].offset(x, 0)


    # 不用の文字、置き換え文字の処理
    def preprocess_chars(self, rows, chars):
    # def remove_head_symbols(self, rows, chars):

        head_sym1 = re.compile(f'([\(\[【][1-１-９]{{1}}[\)\]】])([{ZENKAKU}]+)')
        head_sym2 = re.compile(f'([1-9１-９]{{1}}[\.．,、])([{ZENKAKU}]+)')
        head_sym2_2 = re.compile(f'^([0-9０-９]{{0,2}}[\.．,、]?)([{ZENKAKU}]+)') # 0桁も含む .勘定科目
        # head_sym2 = re.compile(f'([1-9１-９]{{1}}[\.．,、】])([{ZENKAKU}]+)')
        head_sym3 = re.compile(f'([A-Za-zＡ-Ｚａ-ｚⅠ-ⅹ・]+)([{ZENKAKU}]+)')
        # head_sym1 = re.compile(r'([\(\[（【][0-9０-９]{1}[\)\]）】][\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002EBEF]+?)')

        braces_sym = re.compile(r'([\(\)\[\]（）【】\{\}<>＜＞★_])')
        # triangle_sym = re.compile(r'(△{2,})')

        replace_chars = [
                {'regex':re.compile('(;)'), 'char':','},
                {'regex':re.compile('(/)'), 'char':','},
                {'regex':re.compile('(:)'), 'char':','}
        ]

        # ※01
        tail_num_sym = re.compile(r'.*[※＊\*]([0-9０-９]{1,2})$')

        # ['text'] ['chars'] 内の対象文字を削除
        def remove_symbol_chars(r, chars, st, ed):
        # def remove_symbol_chars(r, chars, f):
            rrr = r['text']
            t1 = r['text'][:st]
            t2 = r['text'][ed:]
            r['text'] = t1 + t2
            # r['text'] = r['text'][f.start(2):f.end(2)]


            for i in range(ed-1,st-1,-1):
                no = r['chars'][i]['no']
                end = len(chars)-1 if no >= len(chars)-1 else no # loopする回数をへらす為
                # if no >= len(chars)-1: # loopする回数をへらす為
                #     end = len(chars)-1
                # else:
                #     end = no

                for j in range(end,-1,-1):
                # for j, c in enumerate(chars):
                    if chars[j]['no'] == no:
                        del chars[j]
                        break

                del r['chars'][i]

        def replace_char(r, chars, f, c):
            rrr = r['text']
            t1 = r['text'][:f.start(1)]
            t2 = r['text'][f.end(1):]
            r['text'] = t1 + c + t2

            for i in range(f.end(1)-1,f.start(1)-1,-1):
                no = r['chars'][i]['no']
                end = len(chars)-1 if no >= len(chars)-1 else no # loopする回数をへらす為
                # if no >= len(chars)-1: # loopする回数をへらす為
                #     end = len(chars)-1
                # else:
                #     end = no

                for j in range(end,-1,-1):
                # for j, c in enumerate(chars):
                    if chars[j]['no'] == no:
                        chars[j]['text'] = c
                        break

                r['chars'][i]['text'] = c

        for r in rows:
            # ギャップで判定
            words = self.split_word_by_gap(r)
            w_len = 0
            for j in range(len(words))[::-1]:
                w = words[j]
                f = tail_num_sym.search(w)
                if f:
                    w_len = 0
                    for k in range(j):
                        w_len += len(words[k])

                    remove_symbol_chars(r,chars,f.start(1)+w_len,f.end(1)+w_len)
                    # aaa = 0

            # subject, amount = self.split_subject_amount_by_gap(r, check_digit=False)

            # (n)全角 を削除
            ret = list(head_sym1.finditer(r['text']))
            if ret:
                aaa = 0
                for f in ret[::-1]:
                    # st = f.start(1)
                    # ed = f.end(1)
                    # g0 = f.group(0)
                    # g1 = f.group(1)
                    # g2 = f.group(2)
                    # close0 = self.account_db.search_variety_title(g0)
                    # close2 = self.account_db.search_variety_title(g2)
                    # aaa = 0

                    remove_symbol_chars(r,chars,f.start(1),f.end(1))

            # n.全角 を削除
            ret = list(head_sym2.finditer(r['text']))
            if ret:
                aaa = 0
                for f in ret[::-1]:
                    st = f.start(1)
                    ed = f.end(1)
                    # g0 = f.group(0)
                    # g1 = f.group(1)
                    # g2 = f.group(2)
                    # close0 = self.account_db.search_variety_title(g0)
                    # close2 = self.account_db.search_variety_title(g2)
                    # aaa = 0

                    # 前の文字とのギャップを確認
                    remove_char = True
                    if st > 0:
                        pc = r['chars'][st-1]
                        cc = r['chars'][st]
                        x1 = pc['bounds'].get_right() # 前の文字の右側
                        x2 = cc['bounds'].get_left()   # 文字の左側
                        h  = cc['bounds'].get_height()
                        diff = x2 - x1
                        if pc['text'].isdigit() and diff < h: # 前が数字で近い
                        # if diff < h:
                            remove_char = False
                    if remove_char:
                        remove_symbol_chars(r,chars,f.start(1),f.end(1))
                    else:
                        aaa = 0

            # 先頭の nn.全角 を削除
            f = head_sym2_2.search(r['text']) # 先頭なので必ず１つ
            if f:
                remove_symbol_chars(r,chars,f.start(1),f.end(1))
            # ret = list(head_sym2_2.finditer(r['text']))
            # if ret:
            #     aaa = 0
            #     for f in ret[::-1]:
            #         remove_symbol_chars(r,chars,f)

            # A-Z全角 を削除
            ret = list(head_sym3.finditer(r['text']))
            if ret:
                aaa = 0
                for f in ret[::-1]:
                    for a in self.account_db.variety_title_alphabet:
                        s1 = SequenceMatcher(None, f.group(0), a[0])
                        r1 = s1.ratio()
                        if r1 > 0.5:
                            break
                    else:
                        # 一致しないので削除
                        # g0 = f.group(0)
                        # g1 = f.group(1)
                        # g2 = f.group(2)

                        remove_symbol_chars(r,chars,f.start(1),f.end(1))

            # カッコを削除
            ret = list(braces_sym.finditer(r['text']))
            if ret:
                aaa=0
                for f in ret[::-1]:
                    remove_symbol_chars(r,chars,f.start(1),f.end(1))

            # # ２個以上の△を１個にする
            # ret = list(triangle_sym.finditer(r['text']))
            # if ret:
            #     aaa = 0
            #     for f in ret[::-1]:
            #         remove_symbol_chars(r,chars,f.start(1)+1,f.end(1))

            # 文字置き換え
            for c in replace_chars:
                ret = list(c['regex'].finditer(r['text']))
                if ret:
                    aaa = 0
                    for f in ret:
                        replace_char(r,chars,f,c['char'])

        # 不要文字を削除したことで行がなくなったので行ごと削除 --? 043-v2ac
        for i in range(len(rows))[::-1]:
            if not rows[i]['text']:
                del rows[i]

    # v2acエンジンはテーブルを検出するために違う条件でsuper().find_rows()を2回呼ぶ
    def find_rows(self, chars, no, blocks, paper):

        # スケール変えて通常処理
        find_rows_scale = self.find_rows_scale
        self.find_rows_scale = [0.2,0.25]#[0.25,0.25]

        extacted_rows_org = super().find_rows(chars, no, blocks, paper)
        self.find_rows_scale = find_rows_scale

        # 頭の(1) 1. IXV 等を取り除く
        self.preprocess_chars(extacted_rows_org, chars)
        # self.remove_head_symbols(extacted_rows_org, chars)
        # 離れた△を一旦数字の前に移動
        self.move_triangle_char(extacted_rows_org, chars)

        # 帳票の種類
        table_order, _ = self.find_table_order(extacted_rows_org)

        # ブロック検出
        table_block, vrows, table_type, col_list, start_table_row, BS_T_table = self.find_table_blocks(extacted_rows_org, chars, no, paper['image'], paper['path'])
        paper['table_type'] = table_type # ページ毎

        self.table_type = table_type
        self.col_list = col_list

        rows_block = super().find_rows(chars, no, table_block, paper)
        # 頭の(1) 1. IXV 等を取り除く
        self.preprocess_chars(rows_block, chars)
        # self.remove_head_symbols(rows_block, chars)

        # # 離れた△を数字の前に移動
        # self.move_triangle_char(rows_block, chars)

        extacted_rows = self.find_table_row(extacted_rows_org, rows_block, table_block, chars, vrows)

        debug_print( 'table_block:ratio<{}> -->'.format(no),level=DEBUG_ROWS_INFO)
        for tb in table_block:
            if 'row' in tb and 'row' in tb['row']:
                t = tb['row']['row']['text']
            else:
                t = None
            debug_print( '{}={}/{} : <{}>'.format(tb['ratio'],tb['count'],tb['total'],t), level=DEBUG_ROWS_INFO)
        debug_print( 'table_block:ratio<{}> <--'.format(no),level=DEBUG_ROWS_INFO)


        # v2ac固有データをpaper毎に保存
        paper['rows_org'] = extacted_rows_org
        paper['table_block'] = table_block

        paper['table_order'] = table_order

        paper['table_row_range'] = start_table_row

        # 勘定科目が１行に２列ある
        paper['BS_T_table'] = BS_T_table

        return extacted_rows

    def find_article_rows(self):
        # self.find_table_blocks()

        article_rows = super().find_article_rows()
        return article_rows

    def split_words(self, words, no, loop):
        # return super().split_words(words, no, loop)
        # 分割せずにそのまま返す
        return 0, words

    # 帳票の種類を検索
    def find_table_order(self, rows):
        cmax = 4
        count = [0] * 4
        info = []

        # 先ずはキーワードから帳票の種類を調べる
        for r in rows:
            tks = self.account_db.search_table_keyword(r['text'])
            if tks:
                for tk in tks:
                    count[(tk.order-1)*2+tk.end] += 1
                    info.append({'order':tk.order, 'end':tk.end, 'kw':tk.keyword, 'row':r})
                    # info.append({'tk':tk, 'row':r})

        max = self.account_db.count_table_keyword()
        ret = [0] * 4
        for no in range(4):
            ret[no] = {'no':no, 'ratio':count[no] / max[no]}

        # debug用
        ratio = [ret[0]['ratio'],ret[1]['ratio'],ret[2]['ratio'],ret[3]['ratio']]

        order =  self.account_db.Order.NON
        if count == [0] * 4:
            pass
        elif (ret[0]['ratio']+ret[1]['ratio']) < (ret[2]['ratio']+ret[3]['ratio']):
            order = self.account_db.Order.BS
        elif (ret[0]['ratio']+ret[1]['ratio']) == (ret[2]['ratio']+ret[3]['ratio']):
            order = self.cur_table_order
        else:
            order = self.account_db.Order.PL

        ret2 = sorted(ret, key=lambda x:x['ratio'], reverse=True)
        end2 = ret2[0]['no'] % 2

        begin = None
        end   = None
        for i in info:
            if i['order'] == order:
                if i['end'] == 0: # begin
                    if not begin:
                        begin = i
                else:             # end
                    if not end or end['row']['row_no'] <= i['row']['row_no']:
                        end = i

        aaa = 0

        if order == self.account_db.Order.NON:
            # キーワードが見つからないので勘定科目のORDERを調べる
            count = [0] * account_DB.Order.MAX

            for r in rows:
                # code2 = self.account_db.search_in_variety_code(r['text'])
                # if code2:
                #     aaa = 0

                close = None
                ret = list(subject_amount_pat.finditer(r['text']))
                if len(ret) >= 1:
                    close = self.account_db.search_variety_title(ret[0].group(1),ratio=0.5)
                    if not close and len(ret) >= 2:
                        close = self.account_db.search_variety_title(ret[1].group(1),ratio=0.5)

                if close:
                    if close[0] != '合計': # 合計は判定には使えない
                        code = self.account_db.search_variety_code(close[0])
                        if code:
                            if code[0] < account_DB.Order.MAX:
                                count[code[0]] += 1

            if count[self.account_db.Order.PL] != count[self.account_db.Order.BS]: # 両方とも同じ場合はNONとする(両方とも0も含む)
                if count[self.account_db.Order.PL] < count[self.account_db.Order.BS]:
                    order = self.account_db.Order.BS
                else:
                    order = self.account_db.Order.PL

        self.cur_table_order = order

        return order, ret

    # def make_csv_file(func):
    def make_csv_file(tag):
        def _make_csv_file(func):
            def wrapper(self, writer=None):
            # def wrapper(self, *args, **kwargs):
                # print(f'--start--:{tag}')
                if writer is None:
                    f = io.StringIO()
                    w = csv.writer(f,
                                #    quotechar='"',
                                #    lineterminator='\n',
                                #    quoting=csv.QUOTE_NONNUMERIC,
                                #    quoting=csv.QUOTE_ALL,
                                    delimiter=',')
                    writer = w

                func(self, writer)

                # func(self, *args, **kwargs)
                # print('--end--')

                all_csv = f.getvalue()
                f.close()

                # debug_file.txt と合わせるためにdebug_suffix付きファイル名で保存
                if self.debug_suffix:
                    fname = self.debug_suffix
                    path = f'{DEBUG_PRINT_FILE_PATH}{fname}{tag}.csv'.encode('utf-8')
                else:
                    fname = self.start_date.strftime('%Y-%m-%d+%H-%M-%S.%f')+"@=>"+self.inData["filenam"]
                    path = f'{DEBUG_PRINT_FILE_NAME}.{fname}{tag}.csv'.encode('utf-8')

                with open(path, mode='w', encoding='cp932', errors='replace') as f: # Excelがcp932しか読めない
                # with open(path, mode='w', encoding=util.defines.CSV_CHAR_CODE) as f:
                    f.write(all_csv)

            return wrapper
        return _make_csv_file

    @make_csv_file('')
    def to_csv(self, writer=None):
    # def to_csv(self):
        if writer is None:
            return

        for d in self.result_data:
            writer.writerow(d[2:])

    @make_csv_file('.param')
    def to_param_csv(self, writer=None):
        if writer is None:
            return

        aaa = 0
        for d in self.result_data_param:
            for s in d['data']:
                if s['type'] == v2ac.Type.SUBJECT:
                    writer.writerow([s['code_title'] if 'code_title' in s and s['code_title'] else '-1[未登録]'])

                r = [s['val']]
                # r = [d['page'],d['block'],s['type'],s['val']]
                if 'revise' in s:
                    try:
                        if s['type'] == v2ac.Type.UNKNOWN:
                            r += s['revise']
                        elif s['type'] == v2ac.Type.DATE:
                            r += s['revise'][1:2]
                        elif s['type'] == v2ac.Type.SUBJECT:
                            r += s['revise'][0:1]
                        elif s['type'] == v2ac.Type.AMOUNT:
                            r += s['revise'][1:2]
                    except:
                        pass

                writer.writerow(r)

    @make_csv_file('.cd')
    def to_cd_csv(self, writer=None):
        if writer is None:
            return

        aaa = 0
        for d in self.result_data_param:
            for s in d['data']:
                if s['type'] == v2ac.Type.SUBJECT:
                    if 'code' in s and s['code']:
                        writer.writerow((d['page'],)+s['code'])
                    else:
                        writer.writerow((d['page'],)+(-1,-1,-1,-1,-1)) # CODE注意
                        # writer.writerow((d['page'],)+(-1,-1,-1,-1)) # CODE注意

                    break

    @make_csv_file('')
    def to_result_csv(self, writer=None):
        if writer is None:
            return

        aaa = 0
        prev_code = (-1,-1,-1,-1,-1,-1) # CODE注意
        # prev_code = (-1,-1,-1,-1,-1)
        for d in self.result_data_param:
            if d['type'] & v2ac.Type.REMOVE:
                continue

            r = []
            a = []
            deb = ['>>>']

            on_data = False
            for s in d['data']:
                if s['OK'] == '-':
                    continue

                if s['type'] == v2ac.Type.SUBJECT:
                    db = 'FALSE'
                    ratio = 0.0
                    r = [d['page']]
                    if 'code' in s and s['code']:
                        prev_code = s['code']
                        r += s['code']
                        r += [s['revise'][0]]

                        db = 'TRUE'
                        # if len(s['revise']) >= 2:
                        #     if REGEX_REVISE not in s['revise'][1]:
                        #         db = 'TRUE'
                        #     else:
                        #         aaa = 0

                        # sm = SequenceMatcher(None, remove_brackets.sub(r'\1',s['val']), s['revise'][0])
                        # ratio = sm.ratio()

                        # if len(s['revise']) >= 2:
                        #     sm = SequenceMatcher(None, s['val'], s['revise'][1])
                        #     ratio += [sm.ratio()]
                        # else:
                        #     ratio += [-1]

                    else:
                        r += prev_code[:account_DB.Code.GENUS]
                        r += ['','','']
                        if s['revise']:
                            r += [s['revise'][0]]
                        else:
                            r += ['***']

                        # ratio = 0.0

                    ratio = s['ratio']
                    r += [f'{ratio:.02f}']
                    # r += [f'{ratio:.02f}']
                    # deb += ratio
                    if 'tabindex' in d:
                        deb += str(d['tabindex'])
                    else:
                        deb += str(-1)

                    deb += [s['val']]
                    deb += s['revise']

                    # r += [db]

                    aaa= 0

                elif s['type'] == v2ac.Type.AMOUNT:
                    if len(s['revise']) >= 2:
                        v = s['revise'][1]
                        if s['revise'][0] != COL_ALIGN:
                            on_data = True
                    else:
                        v = s['val'].translate(NORMALIZE_DICTIONARY)

                    if not v:
                        v = '0'
                    a += [v]

                    aaa = 0

            if on_data and r and a:
                ll = len(r+a)
                if ll <= 15:
                    deb_s = [''] * (15 - ll)
                else:
                    deb_s = ['']

                writer.writerow(r+a+deb_s+deb)

            aaa = 0

    # def to_csv(self):

    #     # デバッグ用CSV
    #     f = io.StringIO()
    #     w = csv.writer(f,
    #                 #    quotechar='"',
    #                 #    lineterminator='\n',
    #                 #    quoting=csv.QUOTE_NONNUMERIC,
    #                 #    quoting=csv.QUOTE_ALL,
    #                     delimiter=',')

    #     for d in self.result_data:
    #         w.writerow(d[2:])

    #     all_csv = f.getvalue()
    #     f.close()

    #     # debug_file.txt と合わせるためにdebug_suffix付きファイル名で保存
    #     fname = self.start_date.strftime('%Y-%m-%d+%H-%M-%S.%f')
    #     path = f'{DEBUG_PRINT_FILE_NAME}.{fname}{self.debug_suffix}.csv'.encode('utf-8')

    #     with open(path, mode='w', encoding='cp932', errors='replace') as f: # Excelがcp932しか読めない
    #     # with open(path, mode='w', encoding=util.defines.CSV_CHAR_CODE) as f:
    #         f.write(all_csv)

    #     return

    def to_json(self):

        # 日付
        if self.closing_date:
            closing_date = {'date': self.closing_date['date'], 'page':self.closing_date['page'], 'start_x': int(self.closing_date['bounds'].rect[0]), 'start_y': int(self.closing_date['bounds'].rect[1]), 'end_x': int(self.closing_date['bounds'].rect[2]), 'end_y': int(self.closing_date['bounds'].rect[3])}
            # closing_date = {'date': '{:4}/{:02}/{:02}'.format(2021, 3, 31), 'page':0, 'start_x': 1522, 'start_y': 390, 'end_x': 1891, 'end_y': 443}

        # 会社情報
        company = {'candidate': [], 'page':0, 'start_x': 0, 'start_y': 0, 'end_x': 0, 'end_y': 0}
        # company = {'candidate': [], 'page':0, 'start_x': 551, 'start_y': 469, 'end_x': 1100, 'end_y': 525}
        # company['candidate'].append({'code':'128-02240', 'name':'株式会社サイトウ電器'})

        # 勘定科目
        data = []
        prev_code = (-1,-1,-1,-1,-1,-1) # CODE注意
        # prev_code = (-1,-1,-1,-1,-1)
        req_code_candidate = None

        org_data = []
        #当期利益
        toukirieki_flg      = False
        #負債・純資産
        husaijunsisan_flg   = False

        page = -1

        print('--> to_json')
        debug_print('--> to_json',level=DEBUG_ROWS_INFO)

        for i, d in enumerate(self.result_data_param):
            #debug_print( 'v2ac 3816 [{}]'.format(d['data'][0]['val']), level=DEBUG_ROWS_INFO)
            search_order = self.get_table_order(d['page'])

            if page != int(d['page']):
                page = int(d['page'])

                if self.ratio_column:
                    aaa = 0

                if self.papers[page]['BS_T_table']:
                    aaa = 0

                if self.period_order == v2ac.PeriodOrder.CURRENT_PREV_X_X:
                    aaa = 0

                print( '{}:[{}]{},{},{}'.format(page, d['amount_cnt'], self.ratio_column, self.papers[page]['BS_T_table'], self.period_order))
                debug_print('{}:[{}]{},{},{}'.format(page, d['amount_cnt'], self.ratio_column, self.papers[page]['BS_T_table'], self.period_order),level=DEBUG_ROWS_INFO)

                aaa = 0

            # pre_year_col  = -1
            # # pre_year_col  = 0
            # # this_year_col = 2
            # # 前期今期の並び、比率列によって採用する列を替える

            pre_year_col, this_year_col = self.get_period_col(d)
            if d['type'] & v2ac.Type.REMOVE:
                continue

            col = {
                'candidate': [], # {'order': '', 'family': '', 'genus': '', 'variety': '', 'property': '', 'variety_name':''}
                'amount_pre_year': '',
                'amount_this_year': '',
                'db_exist': '',
                'page': '',
                'start_x': 0,
                'start_y': 0,
                'end_x': 0,
                'end_y': 0,
            }

            on_data = False
            for s in d['data']:
                if s['OK'] == '-':
                    continue

                if s['type'] == v2ac.Type.SUBJECT:

                    # if s['val'] == '流動負憤':
                    #     aaa = 0
                    #debug_print( 'v2ac 3966 [{}@{}@{}]'.format(s['val'],husaijunsisan_flg,have_hanbaihi_flag), level=DEBUG_ROWS_INFO)

                    # 第１候補 (候補がある)
                    if 'code' in s and s['code']:
                        # code2 = self.account_db.search_variety_code(s['revise'][0], prev_code[:account_DB.Code.VARIETY])
                        # if not code2:
                        #     code2 = self.account_db.search_variety_code(s['revise'][0], prev_code[:account_DB.Code.SPECIES])
                        #     if not code2:
                        #         code2 = self.account_db.search_variety_code(s['revise'][0], prev_code[:account_DB.Code.GENUS])

                        # if code2 and s['code'] != code2:
                        #     s['code'] = code2
                        #     code_title = self.account_db.to_title_text(s['code'][:account_DB.Code.VARIETY+1])
                        #     s['code_title'] = code_title
                        #     aaa = 0

                        # 販売費及び一般管理費の内訳、たな卸資産の内訳を  tabindex=4
                        if toukirieki_flg and husaijunsisan_flg :
                            d['tabindex'] = 4
                            s['revise'] = self.account_db.search_variety_title_syou(s['val'], code=(1, 4))
                            # s['revise'] の候補を順番に試して、初めて正常に取れた code だけ採用する
                            if s.get('revise'):
                                debug_print( 'v2ac 3995 [{}]'.format(s.get('revise')), level=DEBUG_ROWS_INFO)
                                for name in s['revise']:
                                    # 空文字や None はスキップ
                                    if not name:
                                        continue
                                    new_code = self.account_db.search_variety_code(name, code=(1, 4))
                                    debug_print( 'v2ac 4006 [{}@{}]'.format(name,new_code), level=DEBUG_ROWS_INFO)
                                    # 「正常に取れた」かどうかの判定
                                    # ここは search_variety_code の仕様に合わせて調整してください
                                    if new_code:
                                        s['code'] = new_code   # ★ 最初に取れた code だけ反映
                                        debug_print( 'v2ac 4006 [{}@{}]'.format(name,new_code), level=DEBUG_ROWS_INFO)
                                        break                   # それ以降は上書きしない
                            
                            debug_print( 'v2ac 4008 [{}]'.format(d['tabindex']), level=DEBUG_ROWS_INFO)

                        # 販売費及び一般管理費の内訳、たな卸資産の内訳を  order=3
                        # order = 3 if toukirieki_flg and husaijunsisan_flg else s['code'][account_DB.Code.ORDER]
                        # if order == 3:
                        #     aaa = 0

                        if s['code'][account_DB.Code.ORDER] == 1 and s['code'][account_DB.Code.FAMILY] == 13:
                            toukirieki_flg = True
                        if s['code'][account_DB.Code.ORDER] == 2 and s['code'][account_DB.Code.FAMILY] == 120:
                            husaijunsisan_flg = True

                        prev_code = s['code']
                        candidate = {'order': s['code'][account_DB.Code.ORDER], 'family': s['code'][account_DB.Code.FAMILY], 'genus': s['code'][account_DB.Code.GENUS], 'species':s['code'][account_DB.Code.SPECIES], 'variety': s['code'][account_DB.Code.VARIETY], 'property': s['code'][account_DB.Code.PROPERTY], 'variety_name':s['revise'][0]}

                        candidate_code = copy.copy(s['code'])
                        candidate_variety_name = s['revise'][0]
                        # candidate = {'order': s['code'][0], 'family': s['code'][1], 'genus': s['code'][2], 'variety': s['code'][3], 'property': s['code'][4], 'variety_name':s['revise'][0]}

                        if req_code_candidate:
                            # これが次の行(前が無いので次の行のCODEに合わせる)
                            req_code_candidate['order']    = s['code'][account_DB.Code.ORDER] #order
                            req_code_candidate['family']   = s['code'][account_DB.Code.FAMILY]
                            req_code_candidate['genus']    = s['code'][account_DB.Code.GENUS]
                            req_code_candidate['species']  = s['code'][account_DB.Code.SPECIES]
                            req_code_candidate = None

                    else: # 候補が無い
                        candidate = {'order': prev_code[account_DB.Code.ORDER], 'family': prev_code[account_DB.Code.FAMILY], 'genus': prev_code[account_DB.Code.GENUS], 'species':prev_code[account_DB.Code.SPECIES], 'variety': None, 'property': None, 'variety_name':None}

                        candidate_code = copy.copy(prev_code[:account_DB.Code.SPECIES+1]) + (None, None)
                        candidate_variety_name = None
                        # candidate = {'order': prev_code[account_DB.Code.ORDER], 'family': prev_code[account_DB.Code.FAMILY], 'genus': prev_code[account_DB.Code.GENUS], 'variety': 999, 'property': prev_code[account_DB.Code.PROPERTY], 'variety_name':s['revise'][0] if s['revise'] else ''}
                        # candidate = {'order': prev_code[0], 'family': prev_code[1], 'genus': '', 'variety': '', 'property': '', 'variety_name':s['revise'][0] if s['revise'] else ''}
                        if prev_code[account_DB.Code.ORDER] == -1:
                            # 前が無いので次の行のCODEに合わせる
                            req_code_candidate = candidate

                    if 'tabindex' in d:
                        col['tabindex'] = d['tabindex']
                    debug_print( 'v2ac 4026 [{}@{}]'.format(col,s['val']), level=DEBUG_ROWS_INFO)
                    col['candidate'].append(candidate)

                    col['page']     = int(d['page'])
                    col['start_x']  = int(d['bounds'].rect[0])
                    col['start_y']  = int(d['bounds'].rect[1])
                    col['end_x']    = int(d['bounds'].rect[2])
                    col['end_y']    = int(d['bounds'].rect[3])

                    ratio = s['ratio']
                    col['db_exist'] = f'{ratio:.02f}'

                    if s['revise']:
                        # if s['revise'][0] == '株主資本':
                        #     aaa = 0
                        col['val']=s['val']
                        # 候補がある
                        if len(s['revise']) >= 2 and REGEX_REVISE in s['revise'][1]:
                            # 正規表現で強制変換
                            revise = [s['revise'][0]]
                            # 読み取った元の文字列から近いものを探して候補に追加(強制変換したものを第１候補として)
                            close = self.account_db.search_variety_title(s['val'], ratio=0.2, code=search_order)
                            if close:
                                    revise += close
                                    for j in range(len(revise))[:0:-1]:
                                        if revise[j] == s['revise'][0]:
                                            del revise[j] # 強制変換したものと同じなので削除

                            revise = revise[:3]

                        else:
                            revise = s['revise'][1:3]

                        for variety_name in revise:
                            # code = [1,2,3,4,5]
                            code = self.account_db.search_variety_code(variety_name, prev_code[:account_DB.Code.VARIETY])
                            if not code:
                                code = self.account_db.search_variety_code(variety_name, prev_code[:account_DB.Code.SPECIES])
                                if not code:
                                    code = self.account_db.search_variety_code(variety_name, prev_code[:account_DB.Code.GENUS])
                                    if not code:
                                        code = self.account_db.search_variety_code(variety_name, prev_code[:account_DB.Code.FAMILY]) # 必要か？

                            # if not code:
                            #     code = self.account_db.search_variety_code(variety_name)

                            if code:
                                # order = 3 if toukirieki_flg and husaijunsisan_flg else code[account_DB.Code.ORDER]
                                # candidate = {'order': order, 'family': code[account_DB.Code.FAMILY], 'genus': code[account_DB.Code.GENUS], 'species':code[account_DB.Code.SPECIES], 'variety': code[account_DB.Code.VARIETY], 'property': code[account_DB.Code.PROPERTY], 'variety_name':variety_name}
                                candidate = {'order': code[account_DB.Code.ORDER], 'family': code[account_DB.Code.FAMILY], 'genus': code[account_DB.Code.GENUS], 'species':code[account_DB.Code.SPECIES], 'variety': code[account_DB.Code.VARIETY], 'property': code[account_DB.Code.PROPERTY], 'variety_name':variety_name}
                                col['candidate'].append(candidate)

                            aaa = 0

                    aaa= 0

                    for j in range(len(col['candidate']))[:0:-1]:
                        for candidate in col['candidate'][:j]:
                            if col['candidate'][j] == candidate:
                                del col['candidate'][j]
                                break

                elif s['type'] == v2ac.Type.AMOUNT:
                    v = None
                    if len(s['revise']) >= 2:
                        v = s['revise'][1]
                        if s['revise'][0] != COL_ALIGN:
                            on_data = True
                        # elif not v and float(col['db_exist']) >= 0.8:
                        #     v = ''
                        #     # if s['revise'][0] == COL_ALIGN:
                        #     s['revise'][2] = s['revise'][0]
                        #     s['revise'][1] = v
                        #     s['revise'][0] = ''

                        #     on_data = True
                    else:
                        v = s['val'].translate(NORMALIZE_DICTIONARY)

                    if pre_year_col >= 0:
                    # if d['amount_cnt'] == 4 or d['amount_cnt'] == 6 or (self.ratio_column == True and (d['amount_cnt'] == 3 or d['amount_cnt'] == 5)):
                        # CURRENT_PREV_X_X
                        # 4 -> 勘定科目:金額(今期):金額(前期):差額:前年比
                        # PREV_X_CURRENT_X
                        # 4 -> 勘定科目:金額(前期):構成比:金額(今期):構成比

                        # 6 -> 勘定科目:金額(前期):構成比:金額(今期):構成比:金額(増減):増加率
                        if s['amount_no'] == pre_year_col:
                            # 金額(前期)
                            col['amount_pre_year'] = v if v else '0'
                        elif s['amount_no'] == this_year_col:
                            # 金額(今期)
                            col['amount_this_year'] = v if v else '0'
                    else:
                        # 勘定科目:金額:[金額]:[金額]
                        # d['amount_cnt'] == 2 or 3
                        # 一番左の金額を採用
                        try:
                            if not col['amount_this_year'] and v:
                            # if not col['amount_this_year'] and v and int(v) != 0:
                            # if not col['amount_this_year'] and v and int(v) > 0:
                                int(v) # 数字に変換出来なければexcept
                                col['amount_this_year'] = v
                        except:
                            col['amount_this_year'] = ''

                    # if not v:
                    #     v = '0'

            if on_data:
                if not col['amount_this_year']:
                    col['amount_this_year'] = '0'

                # # 勘定科目コードによる処理
                # if len(col['candidate']) >= 1 and col['candidate'][0]['variety'] and col['candidate'][0]['property']:
                #     if col['candidate'][0]['variety'] > 0 and col['candidate'][0]['property'] < 0:
                #         col['amount_this_year'] = col['amount_this_year'].replace('-','')
                #         col['amount_pre_year']  = col['amount_pre_year'].replace('-','')

                data.append(col)
                org_data.append(d)

        # TAB検索
        if len(data) > 0:
            self.tabset(data,org_data)
        #debug_print( 'v2ac 4152 [{}@{}]'.format(data[len(data)-1]['val'],data[len(data)-1]['tabindex']), level=DEBUG_ROWS_INFO)
        # TAB4関連の処理 20240829 尚
        tab4 = False
        for d in data:
            if d.get("page", "NONE") == "NONE" or type(d["page"]) is not int :
                aaa=0
            else :
                width = self.papers[d["page"]]["width"]
                height = self.papers[d["page"]]["height"]
            
                wwww=width*1/3
                bs_l = False
                bs_r = False
                if d["start_x"] < wwww and self.papers[d["page"]]["BS_T_table"] :
                    bs_l = True
                elif d["end_x"] > wwww*2 and self.papers[d["page"]]["BS_T_table"] :
                    bs_r = True
                if bs_l :
                    copydata = []
                    if d["candidate"] != None and len(d["candidate"])>0 :
                        dcl=len(d["candidate"])+0
                        #for j in reversed(range(dcl)) :
                        delflag=False
                        for j in range(dcl) :
                            dc = d["candidate"][j]
                            if dc.get('family', 'NG')== 'NG' or dc["family"] >= 40 :
                                #del d["candidate"][j]
                                delflag=True
                            else :
                                copydata.append(dc)
                    if len(copydata) != 0 and delflag :
                        d["candidate"]=copydata
                        d["tabindex"] = 1
                        #debug_print( 'v2ac 4190 [{}]'.format(dc["family"]), level=DEBUG_ROWS_INFO)
                if bs_r :
                    copydata = []
                    if d["candidate"] != None and len(d["candidate"])>0 :
                        dcl=len(d["candidate"])+0
                        #for j in reversed(range(dcl)) :
                        delflag=False
                        for j in range(dcl) :
                            dc = d["candidate"][j]
                            if dc.get('family', 'NG')== 'NG' or dc["family"] < 40 :
                                #del d["candidate"][j]
                                delflag=True
                            else:
                                copydata.append(dc)
                    if len(copydata) != 0 and delflag :
                        d["candidate"]=copydata
                        d["tabindex"] = 2
                        #debug_print( 'v2ac 4204 [{}]'.format(dc["family"]), level=DEBUG_ROWS_INFO)
                tabindex = d.get("tabindex", "Not found")
                if tabindex != "Not found":
                    if d['tabindex'] == 4:
                        tab4 = True
                        break
        #20240830 尚
        #売上高				
        #売上原価				
        #売上総利益				
        #販売費及び一般管理費（1_4)	1_4系の後には、1_1系、1_2系はこない			
        #営業利益（1_5）	←1_5系が出たかどうかをキー			if 1_5以降1_8
        #営業外収益（1_6系）	雑収入（売上高1_1系）			
        #営業外費用（1_7系）	雑費（販売費及び一般管理費1_4系）			貸倒引当金繰入
        #経常利益（1_8系）	←1_8系が出たかどうかをキー			貸倒引当金戻入
        #特別利益（1_9系）	雑収入（売上高1_1系）			
        #特別損失（1_10系）	雑費（販売費及び一般管理費1_4系）			
        #税引前当期利益（1_11系）				
        #法人税等（1_12系）				
        #税引き後当期利益（1_13系）
        index_1_5to1_8=[]
        index_1_8to1_11=[]
        for i , d in enumerate(data):
            #1_5to1_8
            index_1_5to1_8.append(i)
            #1_8to1_11
            index_1_8to1_11.append(i)


        # 販管費及び一般管理費の内訳（TAB4）が別途ある状態のPL（TAB3）で
        # 販売費及び一般管理費が２回続いた場合、
        # 最初を販売費及び一般管理費1_4_0_0_0
        # 次を販売費及び一般管理費1_4_0_0_1
        aaa = 0
        if tab4:
            try:
                for j, d in enumerate(data[:-1]):
                    if d['tabindex'] == 3 and d['candidate']:
                        c = d['candidate'][0]
                        if c['order'] == 1 and c['family'] == 4 and c['genus'] == 0 and c['species'] == 0 and c['variety'] == 0:
                            c = data[j+1]['candidate'][0]
                            if c['order'] == 1 and c['family'] == 4 and c['genus'] == 0 and c['species'] == 0 and c['variety'] == 0:
                                c['variety'] = 1
                                org_data[j+1]['data'][org_data[j+1]['subject_data']]['code'] = (1,4,0,0,1,-1)

                # TAB4 2列処理除外の為に挿入した行を削除
                for j in range(len(data))[::-1]:
                    add = data[j].pop('add', None) # JSONには不必要なので削除
                    if add and data[j]['tabindex'] == 4:
                        for i, d in enumerate(self.result_data_param):
                            if add is self.result_data_param[i]:
                                del self.result_data_param[i]
                                break
                        del data[j]
            except:
                pass
        else:
            # JSONには不必要なので削除
            for d in data:
                d['add'] = None
        for d in data:
            if len(d["candidate"])>0 and d.get('val', 'NG') != "NG":
                candidate=self.add_candidate_syou(code_o=(1,4),val=d['val'])
                todoflag=True
                for c in d["candidate"]:
                    order=c["order"]
                    family=c["family"]
                    genus=c["genus"]
                    species=c["species"]
                    variety=c["variety"]
                    property=c["property"]
                    if d['tabindex'] == 1 and order==2 and family>=10 and family<=35 :
                        todoflag=False
                    elif d['tabindex'] == 2 and order==2 and family>=40 :
                        todoflag=False
                    elif d['tabindex'] == 3 and order==1 :
                        todoflag=False
                    elif d['tabindex'] == 4 and order==1 and family==4 :
                        todoflag=False
                    elif d['tabindex'] != 1 and d['tabindex'] != 2 and d['tabindex'] != 3 and d['tabindex'] != 4  :
                        todoflag=False
                    break
                if todoflag :
                    cindex=0;
                    for c in d["candidate"]:
                        order=c["order"]
                        family=c["family"]
                        genus=c["genus"]
                        species=c["species"]
                        variety=c["variety"]
                        property=c["property"]
                        if cindex>0 :
                            if d['tabindex'] == 1 and order==2 and family>=10 and family<=35 :
                                d["candidate"].insert(0, c)
                                break
                            elif d['tabindex'] == 2 and order==2 and family>=40 :
                                d["candidate"].insert(0, c)
                                break
                            elif d['tabindex'] == 3 and order==1 :
                                d["candidate"].insert(0, c)
                                break
                            elif d['tabindex'] == 4 and order==1 and family==4 :
                                d["candidate"].insert(0, c)
                                break
                        cindex=cindex+1

        i=-1
        for d in data:
            i=i+1
            if len(d["candidate"])>0 :
                todoflag=True
                j=-1
                for c in d["candidate"]:
                    j=j+1
                    order=c["order"]
                    family=c["family"]
                    genus=c["genus"]
                    species=c["species"]
                    variety=c["variety"]
                    property=c["property"]
                    if species==37 :
                        aaa=0
                    if order==1 and family==4 and j==0:
                            if self.the_1_4_page==d["page"] :
                                data[i]['tabindex'] = 4
                                d['tabindex'] = 4
                    if d['tabindex'] == 1 and order==2 and ((family>=10 and family<=35) or (order==1 and family==4)) :
                        todoflag=False
                    elif d['tabindex'] == 2 and ((order==2 and family>=40) or (order==1 and family==4)) :
                        todoflag=False
                    elif d['tabindex'] == 3 and order==1 :
                        todoflag=False
                    elif d['tabindex'] == 4 :
                        #debug_print( '4070 val : :{}'.format(d['val']), level=DEBUG_ROWS_INFO)
                        if order==1 and family==4 :
                            todoflag=False
                            #debug_print( '4072 val : :{}.{}.{}'.format(d['val'],order,family), level=DEBUG_ROWS_INFO)
                    elif d['tabindex'] != 1 and d['tabindex'] != 2 and d['tabindex'] != 3 and d['tabindex'] != 4  :
                        todoflag=False
                    break
                if todoflag and d.get('val', 'NG') != "NG" :
                    cindex=0
                    if d['tabindex'] == 1 :
                        candidate=self.add_candidate_syou(code_o=(2,10), between_o=(2,35),val=d['val'])
                        if len(candidate)>0 :
                            d["candidate"] = candidate
                    elif d['tabindex'] == 2 :
                        candidate=self.add_candidate_syou(code_o=(2,40), between_o=(2,100),val=d['val'])
                        if len(candidate)>0 :
                            d["candidate"] = candidate
                    elif d['tabindex'] == 3 :
                        candidate=self.add_candidate_syou(code_o=(1,),val=d['val'])
                        if len(candidate)>0 :
                            d["candidate"] = candidate
                    elif d['tabindex'] == 4 :
                        candidate=self.add_candidate_syou(code_o=(1,4),val=d['val'])
                        debug_print( '4095 val : :{}.{}.{}'.format(d['val'],"_",len(candidate)), level=DEBUG_ROWS_INFO)
                        if len(candidate)>0 :
                            d["candidate"] = candidate
                    cindex=cindex+1
        return {'closing_date':closing_date, 'company':company, 'detail':data}
    def add_candidate_syou(self, code_o=(), between_o=() ,val=""):
        title_list=self.account_db.get_variety_title_list(code=code_o, between=between_o)
        title_list_re=[]
        for t in title_list:
            if self.diff_syou_do(t,val) == True :
                title_list_re.append(t)
        if len(title_list_re) ==0 :
            for t in title_list:
                if self.diff_syou_soft_do(t,val) == True :
                    title_list_re.append(t)
        candidate=[]
        for t in title_list_re:
            #code = self.account_db.search_variety_code(t,code=code_o, between=between_o)
            codes = self.account_db.search_variety_codes(t,code=code_o, between=between_o)
            if t == val :
                for code in codes :
                    todoflag=False
                    if len(code_o)>1 and len(between_o)>1 :
                        if code[1]>=code_o[1] and code[1]<=between_o[1] :
                            todoflag=True
                    elif len(code_o)>1 :
                        if code[1]==code_o[1] :
                            todoflag=True
                    if len(candidate)<600 and todoflag==True :
                        candidate.insert(0, {'order': code[0], 'family': code[1], 'genus': code[2], 'species': code[3], 'variety': code[4], 'property': code[5], 'variety_name': t})
            else :
                for code in codes :
                    todoflag=False
                    if len(code_o)>1 and len(between_o)>1 :
                        if code[1]>=code_o[1] and code[1]<=between_o[1] :
                            todoflag=True
                    elif len(code_o)>1 :
                        if code[1]==code_o[1] :
                            todoflag=True
                    if len(candidate)<60 and todoflag==True :
                        candidate.append({'order': code[0], 'family': code[1], 'genus': code[2], 'species': code[3], 'variety': code[4], 'property': code[5], 'variety_name': t})
        return candidate
    def diff_syou_soft_do(self, str, target):
        total_l=len(target)
        if total_l < 3 :
            return self.diff_syou( str,target, 0.4)
        elif total_l == 3 :
            return self.diff_syou( str,target, 0.4)
        else :
            return self.diff_syou( str,target, 0.1)
    def diff_syou(self, str, target,ratio):
        total_l=len(target)
        sum=0
        if total_l==0 :
            return False
        for t in target:
            if t in str :
                sum=sum+1
        if sum/total_l > ratio :
            return True
        else :
            return False
    def diff_syou_do(self, str, target):
        total_l=len(target)
        if total_l < 3 :
            return self.diff_syou( str,target, 0.9)
        elif total_l == 3 :
            return self.diff_syou( str,target, 0.4)
        else :
            return self.diff_syou( str,target, 0.7)

    def tabset(self, _data, _org_data):

    # '読込ループ　U行（キー）

        blank_row = {'candidate':[account_DB.blank_code_dict], 'tabindex':0}

        # 最後にexcelの空白行をエミュレートした行を追加
        # data = copy.copy(_data)  # 追加した行を_data(オリジナル)とは別物とするためにcopy、それ以外は_dataへの参照とするためにdeepcopyは使わない
        data = []
        org_data = []
        for i in range(len(_data)):
            if _data[i]['candidate']:
                data.append(_data[i])
                org_data.append(_org_data[i])

        lastRows = len(data) # 対象となる元データの数

        data += [blank_row for _ in range(5)] # _dataには影響なし

        #欄外処理20231230追記---->　資産の部合計の下に記述されている会計方針などに含まれる勘定科目を拾い出す#11745003
        e=[]
        for j in range(lastRows):
            if not data[j]['candidate'] or not data[j+1]['candidate'] or not data[j+2]['candidate']:
                continue
            hantei1 = data[j]['candidate'][0]
            hantei2 = data[j+1]['candidate'][0]
            hantei3 = data[j+2]['candidate'][0]
            if ((hantei1['order'] == 2 and hantei1['family'] == 35) and (hantei2['order'] == 2 and hantei2['family'] != 40) and (hantei3['order'] == 2  and hantei3['family'] == 40)):
              e.append(j+1)
        print('e::::',e)

        #欄外処理20231230追記<----

        #20231205追加---->
        #各TABに表示される勘定科目コードのfamilyの最大値を初期化
        TAB1_family_max=0 #35
        TAB2_family_max=0 #120
        TAB3_family_max=0 #13
        #各TABに表示される勘定科目コードのfamilyの最大値を確認
        #family<=35 and order==1の最大値をTAB1_family_maxとおく
        for i in range(lastRows):
            hantei = data[i]['candidate'][0]
            if(hantei['order'] == 2 and hantei['family'] <= 35):
                if(TAB1_family_max <  hantei['family']):
                    TAB1_family_max =  hantei['family']
            elif(hantei['order'] == 2 and hantei['family'] >= 40):
                if(TAB2_family_max <  hantei['family']):
                    TAB2_family_max =  hantei['family']
            elif(hantei['order'] == 1 ):
                if(TAB3_family_max <  hantei['family']):
                    TAB3_family_max =  hantei['family']
        #20231205追加<----

        index_origin = -1
        strbs1 = index_origin
        endbs1 = index_origin
        tab1_flg=False
        # '貸借対照表（借方）tab1　開始と終了位置
        for j in range(lastRows):
            if not data[j]['candidate'] or not data[j+1]['candidate'] :#or not data[j+2]['candidate']:
                continue
            hantei1 = data[j]['candidate'][0]
            hantei2 = data[j+1]['candidate'][0]
            #hantei3 = data[j+2]['candidate'][0]
            # If (hantei1 = "2_1" And hantei2 = "2_1" And strbs1 = 0) Or (hantei1 = "2_1" And hantei2 = "2_2" And strbs1 = 0) Or (hantei1 = "2_2" And hantei2 = "2_2" And strbs1 = 0) Then
            if ( (strbs1 == index_origin and hantei1['order'] == 2 and hantei1['family'] == 10 and hantei2['order'] == 2 and hantei2['family'] == 10) or
                 (strbs1 == index_origin and hantei1['order'] == 2 and hantei1['family'] == 35 and hantei2['order'] == 2 and hantei2['family'] == 10) or
                 (strbs1 == index_origin and hantei1['order'] == 2 and hantei1['family'] == 10 and hantei2['order'] == 2 and hantei2['family'] == 20) or
                 (strbs1 == index_origin and hantei1['order'] == 2 and hantei1['family'] == 20 and hantei2['order'] == 2 and hantei2['family'] == 20) ):
                strbs1 = j
                print('strbs1',strbs1)
            # ElseIf hantei1 = "2_-1" And hantei2 = "2_4" And strbs1 > 0 Then
            elif ((strbs1 > index_origin) and (hantei1['order'] == 2 and hantei1['family'] == 35 and hantei2['order'] == 2 and hantei2['family'] >= 40 and endbs1 == index_origin) or
                  (strbs1 > index_origin) and (hantei1['order'] == 2 and hantei1['family'] == 35 and hantei2['order'] == 1 and hantei2['family'] >= 1 and endbs1 == index_origin) or
                  (strbs1 > index_origin) and (hantei1['order'] == 2 and hantei1['family'] == 35 and hantei2['order'] == 1 and hantei2['family'] >= 4 and endbs1 == index_origin) ):
                endbs1 = j
                print('endbs1',endbs1)
            #20231231追記 family=35が出現後か判定
            if((strbs1 > index_origin) and (hantei1['order'] == 2 and hantei1['family'] == 35)):
                tab1_flg=True
            #
            if(tab1_flg==True and endbs1 == index_origin and hantei2['order'] == 2 and hantei2['family'] >= 40) :
                endbs1 = j
                break
            if(endbs1 == index_origin and (hantei1['order'] == 2 and hantei1['family'] == 40) and (hantei2['order'] == 2 and hantei2['family'] == 40)) :
                endbs1 = j-1
                break

        strbs2 = index_origin
        endbs2 = index_origin
        tab1_flg=False
        bs2_flg=False
        Total_debt_equity_at_the_top=False
        # '貸借対照表（貸方）tab2　開始と終了位置
        for j in range(lastRows):
            if not data[j]['candidate'] or not data[j+1]['candidate']:
                continue
            hantei1 = data[j]['candidate'][0]
            hantei2 = data[j+1]['candidate'][0]

            #20231231追記 family=35が出現後か判定
            if((strbs1 > index_origin) and (hantei1['order'] == 2 and hantei1['family'] == 35)):
                tab1_flg=True
            # If hantei1 = "2_-1" And hantei2 = "2_4" And strbs2 = 0 Then
            if ((strbs2 == index_origin) and
                # (hantei1['order'] == 2 and hantei1['family'] == 35 and hantei2['order'] == 2 and hantei2['family'] >= 40)):
                (hantei1['order'] == 2 and hantei1['family'] == TAB1_family_max and hantei2['order'] == 2 and hantei2['family'] >= 40 ) or
                ((strbs2 == index_origin) and (tab1_flg==True) and (hantei2['order'] == 2 and hantei2['family'] >= 40))):
                strbs2 = j + 1
                bs2_flg=True
                print('strbs2:j+1',strbs2)
            # ElseIf hantei1 = "2_12" And strbs1 > 0 Then
            # elif ((strbs1 > index_origin) and (hantei1['order'] == 2 and hantei1['family'] == 120) or
            elif ((strbs2 > index_origin) and (hantei1['order'] == 2 and hantei1['family'] == TAB2_family_max and hantei2['order'] != 2) or
                (strbs2 > index_origin) and (hantei1['order'] == 2 and hantei2['order'] == 1) or
                (strbs2 > index_origin) and (hantei1['order'] == 2 and hantei2['order'] == -1) ):
                endbs2 = j
                print('strbs2:j+1',strbs2)
                print('endbs2:j',endbs2)
                # break
            # 負債・純資産合計が一番上にあるパターンへの対応
            if(bs2_flg and j>57):
                if(j==lastRows-1 or hantei2['order']==1):
                    endbs2 = j
                    print('endbs2',j)


        strflg = index_origin
        endflg = index_origin
        # '販管費の開始と終了位置
        page,tab4_page,cnt_tab4,cnt_other=data[0]['page'],0,0,0
        for j in range(lastRows):
            if not data[j]['candidate'] or not data[j+1]['candidate']:
              if cnt_tab4 > 0 and cnt_other >= 0 :
                if cnt_tab4 / (cnt_tab4+cnt_other) > 0.85:
                    tab4_page = page
              continue
            hantei1 = data[j]['candidate'][0]
            hantei2 = data[j+1]['candidate'][0]

            # If hantei1 = "1_4" And hantei2 = "1_4" And strflg = 0 Then
            if ((strflg == index_origin) and
                ((hantei1['order'] == 1 and hantei1['family'] == 4) and
                 (hantei2['order'] == 1 and hantei2['family'] == 4))):
                strflg = j
            # ElseIf hantei1 = "1_4" And hantei2 <> "1_4" And strflg > 0 Then
            elif ((strflg > index_origin) and
                ((hantei1['order'] == 1 and hantei1['family'] == 4) and
                not (hantei2['order'] == 1 and hantei2['family'] == 4))):
                # (hantei2['order'] != 1 or hantei2['family'] != 4)):
                endflg = j

        # '販管費内訳書の有無判定　tab4の有無 uflg=1
        # '同一ページ内で販管費の比率をチェック

            if page == data[j]['page']:
                if data[j]['candidate'][0]['order'] == 1 and data[j]['candidate'][0]['family'] == 4:
                    cnt_tab4 += 1
                else:
                    cnt_other += 1
            else:
                if cnt_tab4 > 0 and cnt_other >= 0 :
                    if cnt_tab4 / (cnt_tab4+cnt_other) > 0.85:
                        tab4_page = page
                page = data[j]['page']
                cnt_other,cnt_tab4 = 0,0

            if j == lastRows-1:
                if cnt_tab4 > 0 and cnt_other >= 0 :
                    if cnt_tab4 / (cnt_tab4+cnt_other) > 0.85:
                        tab4_page = page


        # '販管費がPLに含まれていいる場合　uflg=0に戻す
        # '１_4開始行の１つ前が1_3または1_4の最後の次の行が１_5
        # If stru > 1 Then
        # if stru > 1:
        #     hantei1 = data[stru - 1]['candidate'][0]
        #     hantei2 = data[endu + 1]['candidate'][0]
        #     # If Cells(stru - 1, 21) = "1_3" And Cells(endu + 1, 21) = "1_5" Then
        #     if ((hantei1['order'] == 1 and hantei1['family'] == 3) and
        #         (hantei2['order'] == 1 and hantei2['family'] == 5)):
        #         uflg = 0

        strpl = index_origin
        endpl = index_origin
        # 'PL　tab3の開始と終了を取得
        for j in range(lastRows):
            if not data[j]['candidate'] or not data[j+1]['candidate']:
                continue
            hantei1 = data[j]['candidate'][0]
            hantei2 = data[j+1]['candidate'][0]

            # If (hantei1 = "1_1" And hantei2 = "1_1" And strpl = 0) Or (hantei1 = "1_1" And hantei2 = "1_2" And strpl = 0) Then
            if ((strpl == index_origin) and
                (hantei1['order'] == 1 and hantei1['family'] == 1)) :
                #((hantei1['order'] == 1 and hantei1['family'] == 1 and hantei2['order'] == 1 and hantei2['family'] == 1) or
                # (hantei1['order'] == 1 and hantei1['family'] == 1 and hantei2['order'] == 1 and hantei2['family'] == 2))):
                strpl = j
            # ElseIf hantei1 = "1_13" And strpl > 0 Then
            # elif ((strpl > index_origin) and
            #       (hantei1['order'] == 1 and hantei1['family'] == 13)):
            # ElseIf hantei1 = "1_13" And strpl > 0  And hantei2 <> "1_13" Then
            elif ((strpl > index_origin) and
                #   (hantei1['order'] == 1 and hantei1['family'] == 13) and
                #   (hantei2['order'] != 1 or  hantei2['family'] != 13)):
                  (hantei1['order'] == 1 and hantei1['family'] == TAB3_family_max) and
                  (hantei2['order'] != 1 or  hantei2['family'] != TAB3_family_max)):
                endpl = j
                break
        print('strpl:',strpl)
        print('endpl:',endpl)

        for i in range(lastRows):
            tabindex = 0

            if(strbs2>-1 and endbs1==-1):
                endbs1=strbs2-1

            # 'tab1判定
            if i >= strbs1 and i <= endbs1 :
                tabindex = 1
                # tb = "tab1"

            # 'tab2判定
            elif i >= strbs2 and i <= endbs2  :
                tabindex = 2
                # tb = "tab2"

            # Cells(i, 22) = tb

            # 'tab3判定
            if strpl <= i and endpl >= i :
                tabindex = 3
                # Cells(i, 22) = "tab3"

            # 'tab4判定
            # debug_print((f'tab4:{tab4_page}'),level=DEBUG_ROWS_INFO)
            # '販管費の科目が1_1_13以降に出現した場合、TAB4とする　20240418修正
            #if tab4_page and tab4_page == data[i]['page'] and data[i]['candidate'][0]['variety'] != None :
            if (tab4_page and tab4_page == data[i]['page'] and data[i]['candidate'][0]['variety'] != None) or (i>endpl and data[i]['candidate'][0]['order'] == 1 and data[i]['candidate'][0]['family'] == 4 ) :
                tabindex = 4

            #20231231---->
            if i in e:
               print('i in e',i)
               tabindex = 0
            #20231231<----

            data[i]['tabindex'] = tabindex
            org_data[i]['tabindex'] = tabindex

            # 挿入したデータ？
            # data[i]['add'] = org_data[i]['add'] if 'add' in org_data[i] else 0
            if 'add' in org_data[i]:
                data[i]['add'] = org_data[i]['add']
            else:
                data[i]['add'] = None

        # # 'tab4判定
        # if uflg == 1:
        #     for i in range(stru, endu+1):
        #     # For i = stru To endu
        #         data[i]['tabindex'] = 4
        #         # Cells(i, 22) = "tab4"
        #         org_data[i]['tabindex'] = 4

    def get_chars_bound(self, chars):

        if not chars:
            return Bound()

        chars_bound = copy.deepcopy(chars[0]['bounds'])
        for i in range(1,len(chars)):
            chars_bound.expand(chars[i]['bounds'])

        return chars_bound

    def get_table_order(self, page):
        # return ()

        table_order = self.papers[page]['table_order']
        if table_order == account_DB.Order.NON:
            table_order = ()
        else:
            table_order = (table_order,)

        return table_order

    #分析の中核 The real boos
    def do_analyze(self, papers):
        #分析始める行をデバッグで表示する
        debug_print('--> start_table_row',level=DEBUG_ROWS_INFO)
        for page, paper in enumerate(papers):
            if paper['table_row_range'][0]:
                debug_print( '{}:{}({}) [{}]'.format(paper['table_row_range'][0]['row']['page'], paper['table_row_range'][0]['row']['row_no'], paper['table_row_range'][0]['row']['block'], paper['table_row_range'][0]['row']['text']),level=DEBUG_ROWS_INFO)
            if paper['table_row_range'][1]:
                debug_print( '  {}({}) [{}]'.format(paper['table_row_range'][1]['row']['row_no'], paper['table_row_range'][1]['row']['block'], paper['table_row_range'][1]['row']['text']),level=DEBUG_ROWS_INFO)
            else:
                debug_print('{}:----'.format(page+1), level=DEBUG_ROWS_INFO)
        debug_print('<-- start_table_row',level=DEBUG_ROWS_INFO)

        print('--> start_table_row')
        for page, paper in enumerate(papers):
            if paper['table_row_range'][0]:
                print( '{}:{}({}) [{}]'.format(paper['table_row_range'][0]['row']['page'], paper['table_row_range'][0]['row']['row_no'], paper['table_row_range'][0]['row']['block'], paper['table_row_range'][0]['row']['text']))
            if paper['table_row_range'][1]:
                print( '  {}({}) [{}]'.format(paper['table_row_range'][1]['row']['row_no'], paper['table_row_range'][1]['row']['block'], paper['table_row_range'][1]['row']['text']))
            else:
                print('{}:----'.format(page+1))
        print('<-- start_table_row')

        no = 0
        data = []
        data_param = []
        for page, paper in enumerate(papers):
            if len(paper["characters"])==0 :
                continue
            # 列タイプカウンター
            # paper['col_type'] = [[0] * 4] * (paper['table_block'][-1]['ed']*2+1)
            paper['col_type'] = []
            for j in range(paper['table_block'][-1]['ed']*2+1):
                paper['col_type'].append([0] * (4+1)) # +1は予測タイプ用

            search_order = self.get_table_order(page)

            # table_row_range = papers[page]['table_row_range']
            # if len(table_row_range) > 1:
            #     table_row_start = table_row_range[0]['row']['row_no']
            # else:
            #     table_row_start = -1

            tb_max = len(paper['table_block'])
            for i in range(tb_max):
                tb = paper['table_block'][i]
                block = tb['row']['row_block']

                blocks_len = len(tb['blocks'])

                # 日付列のセット（縦横共通）
                def set_date_col(found_date, col_param, col_no):
                    if found_date is None:
                        return
                    # col_param = {'page':page, 'block':block, 'no':no, 'row_no':r['row']['row_no'], 'data':[]}

                    l = len(found_date[0][0] + found_date[0][1] + found_date[0][2])
                    txt = r['text'][:l]
                    chars = r['chars'][:l]
                    data.append([page,block, txt])
                    col_param['data'].append({'type':v2ac.Type.UNKNOWN,'val':txt,'revise':[], 'col':col_no, 'chars':chars, 'bounds':self.get_chars_bound(chars)})

                    if len(found_date) >= 2:
                        txt = r['text'][l:]
                        chars = r['chars'][l:]
                        data.append([page,block, txt])
                        col_param['data'].append({'type':v2ac.Type.UNKNOWN,'val':txt,'revise':[], 'col':col_no, 'chars':chars, 'bounds':self.get_chars_bound(chars)})

                    data_param.append(col_param)

                # 縦型or横型
                if tb['ratio'] >= 0.15:
                # if tb['ratio'] >= 0.2:
                    aaa = 0
                    # 縦(ブロック順)
                    for r in paper['rows']:
                        if 'row' not in r:
                            aaa = 0
                            continue

                        # if r['row']['row_no'] < table_row_start:
                        #     aaa = 0

                        if r['row']['block'] != block: # 検索範囲の行ブロック？ (r['block']=本当のブロック番号)
                        # if r['row_block'] != block: # 検索範囲の行ブロック？ (r['block']=本当のブロック番号)
                            continue

                        # data.append([r['text']])
                        if not r['text']:
                            continue

                        if '・' in r['text']:
                            aaa = 0

                        if '※' in r['text']:
                            aaa = 0
                        txt = revise_date_nengo(r['text'])
                        found_date = search_date2(txt)
                        if found_date: # 日付はブロック無視
                            col_param = {'page':page, 'block':block, 'no':no, 'row_no':r['row']['row_no'], 'data':[]}
                            set_date_col(found_date, col_param, r['block'] * 2)
                            # j = r['block'] * 2

                            # l = len(found_date[0][0] + found_date[0][1] + found_date[0][2])
                            # txt = r['text'][:l]
                            # chars = r['chars'][:l]
                            # data.append([page,block, txt])
                            # col_param['data'].append({'type':v2ac.Type.UNKNOWN,'val':txt,'revise':[], 'col':j, 'chars':chars, 'bounds':self.get_chars_bound(chars)})

                            # if len(found_date) >= 2:
                            #     txt = r['text'][l:]
                            #     chars = r['chars'][l:]
                            #     data.append([page,block, txt])
                            #     col_param['data'].append({'type':v2ac.Type.UNKNOWN,'val':txt,'revise':[], 'col':j, 'chars':chars, 'bounds':self.get_chars_bound(chars)})

                            # data_param.append(col_param)
                            aaa = 0
                        else:
                            subject_char = []
                            amount_char  = []
                            # w = self.split_word_by_gap(r)
                            subject, amount = self.split_subject_amount_by_gap(r)
                            # subject, amount = self.split_subject_amount_by_gap(r, check_digit=False) # ※
                            if not subject or not amount:
                                by_gap = False
                                # if '株主' in r['row']['text']:
                                #     aaa = 0
                                # if '雑費' in r['row']['text']:
                                #     aaa = 0


                                f = subject_amount_other_pat.search(r['text'])
                                # f = subject_amount_pat.search(r['text'])
                                if f is not None:
                                    # if f.group(1) and f.group(2):
                                        subject = f.group(1)
                                        amount = f.group(2)
                                        tail_str = f.group(3)
                                        if len(tail_str) > 0 and tail_str[0] == '年': # 1年内を分割しない様にするため
                                            f2 = subject_amount_other_pat.search(tail_str)
                                            if f2 is not None:
                                                subject = subject+amount
                                                subject_char = r['chars'][f.regs[1][0]:f.regs[2][1]]
                                                subject += f2.group(1)
                                                subject_char += r['chars'][f.regs[3][0]+f2.regs[1][0]:f.regs[3][0]+f2.regs[1][1]]

                                                amount = f2.group(2)+f2.group(3)
                                                amount_char = r['chars'][f.regs[3][0]+f2.regs[2][0]:f.regs[3][0]+f.regs[3][1]]
                                                # amount_char  = [] #r['chars'][f.regs[3][1]:f.regs[3][1]]
                                            else:
                                                subject = subject+amount+tail_str
                                                amount = ''
                                                subject_char = r['chars'][f.regs[1][0]:f.regs[3][1]]
                                                amount_char  = [] #r['chars'][f.regs[3][1]:f.regs[3][1]]
                                            # by_gap = True
                                        elif not any(c.isdigit() for c in amount):
                                            subject = subject+amount+tail_str
                                            amount = ''
                                            subject_char = r['chars'][f.regs[1][0]:f.regs[3][1]]
                                            amount_char  = [] #r['chars'][f.regs[3][1]:f.regs[3][1]]

                                        else:
                                            subject_char = r['chars'][f.regs[1][0]:f.regs[1][1]]
                                            amount_char  = r['chars'][f.regs[2][0]:f.regs[2][1]]
                                        subject_bounds = self.get_chars_bound(subject_char)
                                        amount_bounds  = self.get_chars_bound(amount_char)

                                        if subject and amount:
                                            by_gap = True

                            else:
                                by_gap = True

                            if not subject_char and subject:
                                subject_char = r['chars'][:len(subject)]
                            if not amount_char and amount:
                                amount_char = r['chars'][len(subject):]

                            data.append([page,block, subject, amount])

                            j = r['block'] * 2
                            close = self.account_db.search_variety_title(subject, code=search_order)
                            if by_gap:
                            # if close or by_gap:
                                data_param.append({'page':page, 'block':block, 'no':no, 'row_no':r['row']['row_no'], 'data':[{'type':v2ac.Type.SUBJECT,'val':subject,'revise':[], 'col':j, 'chars':subject_char, 'bounds':self.get_chars_bound(subject_char)}, {'type':v2ac.Type.AMOUNT,'val':amount,'revise':[], 'col':j+1, 'chars':amount_char, 'bounds':self.get_chars_bound(amount_char)}]})
                            else:
                                data_param.append({'page':page, 'block':block, 'no':no, 'row_no':r['row']['row_no'], 'data':[{'type':v2ac.Type.UNKNOWN,'val':r['text'],'revise':[], 'col':j, 'chars':r['chars'], 'bounds':r['bounds']}]})
                                # data_param.append({'page':page, 'block':block, 'data':[{'type':v2ac.Type.UNKNOWN,'val':subject,'revise':None}, {'type':v2ac.Type.UNKNOWN,'val':amount,'revise':None}]})
                        no += 1
                        aaa = 0
                    aaa = 0
                else:
                    # 横(行)
                    aaa = 0
                    for r in paper['rows_org']:
                        # if r['row_no'] < table_row_start:
                        #     aaa = 0

                        if r['block'] != block: # 検索範囲の行ブロック？ (v2ac固有)
                            continue

                        cols = [page,block]
                        col_param = {'page':page, 'block':block, 'no':no, 'row_no':r['row_no'], 'data':[]}
                        no += 1

                        if '令和' in r['text']:
                            aaa = 0
                        if '合The' in r['text']:
                            aaa = 0
                        txt = revise_date_nengo(r['text'])
                        found_date = search_date2(txt)
                        if found_date: # 日付ブロック
                            set_date_col(found_date, col_param, tb['st'])
                            # l = len(found_date[0][0] + found_date[0][1] + found_date[0][2])
                            # txt = r['text'][:l]
                            # chars = r['chars'][:l]
                            # cols.append(txt)
                            # col_param['data'].append({'type':v2ac.Type.UNKNOWN,'val':txt, 'revise':[], 'col':tb['st'], 'chars':chars, 'bounds':self.get_chars_bound(chars) })

                        # if found_date: # 日付はブロック無視
                        #     txt = r['text']
                        #     chars = r['chars']
                        #     cols.append(txt)
                        #     col_param['data'].append({'type':v2ac.Type.UNKNOWN,'val':txt, 'revise':[], 'col':tb['st'], 'chars':chars, 'bounds':self.get_chars_bound(chars) })
                        else:
                            for j in range(tb['st'], tb['ed']):
                                txt = ''
                                chars = []
                                for c in r['cols']:
                                    if c['block'] == j:
                                        chars += c['chars']
                                        # cols.append(c['text'])
                                        txt += c['text']

                                found = False
                                f = subject_amount_other_pat.search(txt)
                                if f is not None:
                                    subject = f.group(1)
                                    amount  = f.group(2)
                                    if f.group(3): # 31当金の場合に amount=31になるのを避ける
                                        subject = txt
                                        amount  = ''

                                    if any(c.isdigit() for c in amount): # 数字が含まれている?
                                        close = self.account_db.search_variety_title(subject, code=search_order)

                                        # found = True
                                        # cols.append(subject)
                                        # cols.append(amount)
                                        # col_param['data'].append({'type':v2ac.Type.SUBJECT,'val':subject, 'revise':None })
                                        # col_param['data'].append({'type':v2ac.Type.AMOUNT,'val':amount, 'revise':None })

                                        if close:
                                            found = True
                                            cols.append(subject)
                                            cols.append(amount)
                                            # cols.append(subject if subject is not None else '')
                                            # cols.append(amount if amount is not None else '')

                                            subject_char = chars[f.regs[1][0]:f.regs[1][1]]
                                            amount_char  = chars[f.regs[2][0]:f.regs[2][1]]

                                            col_param['data'].append({'type':v2ac.Type.SUBJECT,'val':subject, 'revise':[], 'col':j, 'chars':subject_char, 'bounds':self.get_chars_bound(subject_char) })
                                            col_param['data'].append({'type':v2ac.Type.AMOUNT,'val':amount, 'revise':[], 'col':j, 'chars':amount_char, 'bounds':self.get_chars_bound(amount_char) })

                                if not found:
                                    cols.append(txt)
                                    col_param['data'].append({'type':v2ac.Type.UNKNOWN,'val':txt, 'revise':[], 'col':j, 'chars':chars, 'bounds':self.get_chars_bound(chars) })

                            if len(cols) > 2 and len(cols[-1]) == 0:
                                del cols[-1]

                                del col_param['data'][-1]

                            data.append(cols)

                            data_param.append(col_param)

                        # if len(cols) > 2 and len(cols[-1]) == 0:
                        #     del cols[-1]

                        #     del col_param['data'][-1]

                        # data.append(cols)

                        # data_param.append(col_param)

                        aaa = 0
                    aaa = 0

        # 収集したデータをまとめる
        page  = -1
        block = -1
        type = [0]
        dmax  = 0

        col_type = []

        for row, d in enumerate(data_param):
            search_order = self.get_table_order(d['page'])

            if row == 187:
                aaa = 0

            if d['page'] == 2 and d['block'] == 1:
                aaa = 0
            if d['page'] != page or d['block'] != block:
                # ブロックの変わり目
                if page != -1:
                    col_type.append({'page':page, 'block':block, 'max':dmax, 'type':type})
                page  = d['page']
                block = d['block']

                type = [0] * (len(d['data']) * 2)
                dmax  = 0

            for col, s in enumerate(d['data']):
                if '**,*' in s['val']:
                    aaa = 0

                # s['type'], s['val']
                def revise_amount(f,s):
                    amount = f.group(2)
                    amount = amount.translate(NORMALIZE_DICTIONARY)
                    if '/' in amount:
                        amount = amount.replace('/',',')
                    if '-' in amount[1:]:
                        amount = amount[0] + amount[1:].replace('-',',') # 先頭が-で2文字以降で-がある場合に対応
                        # if re.match('^[-]',amount) is None:
                            # amount = amount.replace('-',',')
                    st = len(f.group(1))
                    ed = st+len(f.group(2))
                    s['chars'] = s['chars'][st:ed]
                    s['bounds'] = self.get_chars_bound(s['chars'])

                    return [f.group(1),amount,f.group(3)]

                def check_date(s, txt):
                    s0 = None
                    txt = revise_date_nengo(txt)
                    f = search_date(txt)
                    if f is not None:
                        # 日付
                        s['type'] = v2ac.Type.DATE
                        s['revise'] = [f.group(1),f.group(2),f.group(3)]
                        # date_char  = chars[f.regs[2][0]:f.regs[2][1]]
                        f0 = search_date(f.group(1))
                        if f0 is not None:
                            s0 = copy.deepcopy(s)
                            s0['revise'] = [f0.group(1),f0.group(2),f0.group(3)]
                            if '至' in f0.group(3):
                                s['revise'][0] = f0.group(3)
                                s0['revise'][2] = ''

                            s0['val'] = s0['revise'][0]+s0['revise'][1]+s0['revise'][2]
                            s0['chars'] = s0['chars'][:len(s0['val'])]
                            s0['bounds'] = self.get_chars_bound(s0['chars'])

                        s['val'] = s['revise'][0]+s['revise'][1]+s['revise'][2]
                        s['chars'] = s['chars'][-len(s['val']):]
                        s['bounds'] = self.get_chars_bound(s['chars'])

                    return f, s0

                if s['type'] == v2ac.Type.UNKNOWN:
                    # 日付か?
                    # txt = revise_date_nengo(s['val'],99)
                    f, s0 = check_date(s, s['val'])
                    # f = search_date(txt)
                    if f is not None:
                        # 日付
                        if s0:
                            d['data'].insert(col, s0)
                        # s['revise'] = [f.group(1),f.group(2),f.group(3)]
                        # s['type'] = v2ac.Type.DATE
                    else:
                        s['revise'] = self.account_db.search_variety_title(s['val'], code=search_order)
                        if s['revise']:
                            # 勘定科目
                            s['type'] = d['type'] = v2ac.Type.SUBJECT
                        else:
                            f = amount_split_pat.search(s['val'])
                            f2 = num_pat.search(s['val'])
                            if f is not None and f2 is not None:
                                aaa = 0
                                if 'type' not in d:
                                    d['type'] = v2ac.Type.UNKNOWN

                                # if d['type'] != v2ac.Type.SUBJECT:
                                #     for k in range(col-1,-1,-1):
                                #         if d['data'][k]['type'] == v2ac.Type.SUBJECT:
                                #             d['type'] = v2ac.Type.SUBJECT
                                #             break

                                # 行に勘定科目
                                if True: #d['type'] == v2ac.Type.SUBJECT:
                                # if d['type'] == v2ac.Type.SUBJECT:
                                    s['type'] = v2ac.Type.AMOUNT
                                    s['revise'] = revise_amount(f,s)

                                # if d['data'][0]['type'] == v2ac.Type.SUBJECT:
                                #     # 先頭が勘定科目の時のみ
                                #     s['type'] = v2ac.Type.AMOUNT
                                #     s['revise'] = revise_amount(f,s)
                                # elif len(d['data']) >= 2 and d['data'][0]['type'] == v2ac.Type.UNKNOWN and d['data'][1]['type'] == v2ac.Type.SUBJECT:
                                # # elif len(d['data']) >= 2 and not d['data'][0]['val'] and d['data'][1]['type'] == v2ac.Type.SUBJECT:
                                #     s['type'] = v2ac.Type.AMOUNT
                                #     s['revise'] = revise_amount(f,s)
                                else:
                                    s['revise'] = [f.group(1),f.group(2),f.group(3)]

                elif s['type'] == v2ac.Type.SUBJECT:
                    s['revise'] = self.account_db.search_variety_title(s['val'], code=search_order)
                elif s['type'] == v2ac.Type.AMOUNT:
                    f, s0 = check_date(s, s['val'])
                    if f is not None:
                        # 日付
                        if s0:
                            d['data'].insert(col, s0)
                    else:
                        f = amount_split_pat.search(s['val'])
                        if f is not None:
                            s['revise'] = revise_amount(f,s)
                            # s['revise'] = [f.group(1),f.group(2),f.group(3)]
                else:
                    aaa = 0

                if s['type'] == v2ac.Type.SUBJECT:
                    if len(type) > col:
                        type[col] += 1

                    # r = self.account_db.revise_subject(s['val'])
                    # if r is not None and r[1] != s['val']:
                    #     if not s['revise'] or r[1] not in s['revise']:
                    #         if s['val'] not in s['revise']:
                    #             aaa = 0

                elif s['type'] == v2ac.Type.UNKNOWN:
                    # UNKNOWNを勘定科目置き換えリストと照合
                    r = self.account_db.revise_subject(s['val'])
                    if r is not None:
                        # 勘定科目の可能性?
                        s['revise'] = [r[1], f'{REGEX_REVISE}:{r[0]}']
                        s['type'] = d['type'] = v2ac.Type.SUBJECT
                    else:
                        # 67
                        # close = self.account_db.search_variety_title(s['val'], ratio=0.2)
                        # if close:
                        #     aaa = 0
                        if s['chars']:
                        # if s['chars'] is not None and s['chars']:
                            s['revise'] = self.split_word_by_gap(s)
                dmax += 1

        if dmax > 0:
            col_type.append({'page':page, 'block':block, 'max':dmax, 'type':type})

        # 一番左にあるUNKNOWNを前後から種類を推測
        for j, d in enumerate(data_param):
            if len(d['data']) >= 1:
                if d['data'][0]['type'] == v2ac.Type.UNKNOWN:
                    # 勘定科目の可能性?
                    aaa = 0
            # for i, s in enumerate(d['data']):
            #     if i == 0 and s['type'] == v2ac.Type.UNKNOWN:
            #         # 勘定科目の可能性?
            #         aaa = 0

        # すべて列のそれぞれのタイプを数える
        aaa = 0
        for j, d in enumerate(data_param):
            for col, s in enumerate(d['data']):
                type = s['type'] if s['type'] <= v2ac.Type.AMOUNT else v2ac.Type.SUBJECT_AMOUNT

                # if len(papers) <= d['page']:
                #     aaa = 0
                # if len(papers[d['page']]['col_type']) <= s['col']:
                #     aaa = 0
                # if len(papers[d['page']]['col_type'][s['col']]) <= type:
                #     aaa = 0

                papers[d['page']]['col_type'][s['col']][type] += 1

        # 列のタイプを予測
        for page, paper in enumerate(papers):
            if paper.get('col_type')!=None :
                for ct in paper['col_type']:
                    type = v2ac.Type.UNKNOWN
                    max  = -1
                    for j, c in enumerate(ct[:-1]):
                        if max < c:
                            type = j
                            max = c
                    ct[-1] = type

        # 予測した列タイプと違う列タイプを予測したものに合わせる(SUBJECTとAMOUNT)
        aaa = 0
        for row, d in enumerate(data_param):
            if row == 55:
                aaa = 0
            for col, s in enumerate(d['data']):
                predict = papers[d['page']]['col_type'][s['col']][-1]
                if predict == v2ac.Type.UNKNOWN:
                    continue
                if predict != s['type']:
                    if s['type'] == v2ac.Type.AMOUNT and predict == v2ac.Type.SUBJECT:
                        s['type'] = v2ac.Type.SUBJECT
                        close = self.account_db.search_variety_title(s['val'], ratio=0.2)
                        s['revise'] = close
                    elif s['type'] == v2ac.Type.SUBJECT and predict == v2ac.Type.AMOUNT:
                        aaa = 0
                        s['type'] = v2ac.Type.AMOUNT

        NO_CODE = (-1,-1,-1,-1,-1) # code注意
        # NO_CODE = (-1,-1,-1,-1)
        def next_item_code(current, next=1):
            for row, d in enumerate(data_param[current+next:]):
                for col, s in enumerate(d['data']):
                    if s['type'] == v2ac.Type.SUBJECT:
                        if s['revise']:
                        # if 'revise' in s and s['revise']:
                            code = self.account_db.search_variety_code(s['revise'][0])
                            if code:
                                return code
                        else:
                            aaa = 0

            return NO_CODE

        # CODE変更
        def change_variety_code(s, prev_code, ratio=0.2):
            code = NO_CODE
            close = self.account_db.search_close_title(prev_code, s['val'], ratio)
            if close:
                s['revise'] = close
                code = self.account_db.search_variety_code(s['revise'][0], prev_code)
                # if not code:
                #     aaa = 0
                s['code'] = code
                code_title = self.account_db.to_title_text(code)
                s['code_title'] = code_title
            else:
                s['code'] = ()
                s['code_title'] = ''
                aaa = 0

            return code

        # 資本金 or 出資金 判定
        # shihonkin = self.account_db.search_variety_code('資本金')
        # syushikin = self.account_db.search_variety_code('出資金')
        # shisan_gokei = False
        # def repalce_shihonkin_syushikin(s, code, shisan_gokei):
        #     if shisan_gokei:
        #         if code != shihonkin: # 強制変換
        #             s['revise'] = self.account_db.search_variety_title(s['val'], code=shihonkin[:account_DB.Code.FAMILY+1])
        #             if len(s['revise']) == 0:
        #                 s['revise'] = ['資本金']

        #             code = shihonkin
        #     else:
        #         if code != syushikin: # 強制変換
        #             s['revise'] = self.account_db.search_variety_title(s['val'], code=syushikin[:account_DB.Code.FAMILY+1])
        #             if len(s['revise']) == 0:
        #                 s['revise'] = ['出資金']
        #             code = syushikin

        #     return code

        page = -1
        # グループから勘定科目を探して補正する
        prev_code = NO_CODE
        for row, d in enumerate(data_param):
            if page != d['page']:
                search_order = self.get_table_order(d['page'])
                page = d['page']
                # shisan_gokei = False
                table_row_range = papers[page]['table_row_range']

                # 対象テーブル範囲
                if table_row_range[0]:
                    start_table_row_no = table_row_range[0]['row']['row_no']
                else:
                    start_table_row_no = 0

            if row == 55:
                aaa = 0
            if row == 60:
                aaa = 0
            if prev_code[:account_DB.Code.FAMILY+1] == (1,6):
                aaa = 0
            # if row == 91: # debug 031
            #     aaa = 0
            # if row == 126: # debug 031-2
            #     aaa = 0
            # if row == 127: # debug 031-2
            #     aaa = 0
            # elif row == 75:
            #     aaa = 0
            rowindex=0
            for col, s in enumerate(d['data']):
                if s['type'] == v2ac.Type.SUBJECT:
                    if s['revise']:
                        # if s['val'] == '資':
                        #     aaa = 0
                        if prev_code != NO_CODE:
                            code = self.account_db.search_variety_code(s['revise'][0], prev_code[:account_DB.Code.VARIETY])
                            if not code:
                                code = self.account_db.search_variety_code(s['revise'][0], prev_code[:account_DB.Code.SPECIES])
                                if not code:
                                    code = self.account_db.search_variety_code(s['revise'][0], prev_code[:account_DB.Code.GENUS])
                        else:
                            code = None
                        if not code:
                            code = self.account_db.search_variety_code(s['revise'][0], search_order)

                        # sm = SequenceMatcher(None, s['val'], s['revise'][0])
                        # subject_ratio = sm.ratio()
                        # # 資本金 or 出資金 判定
                        # if code == syushikin or code == shihonkin:
                        #     code = repalce_shihonkin_syushikin(s, code, shisan_gokei)

                        s['code'] = code
                        if code:
                            code_title = self.account_db.to_title_text(code)
                            s['code_title'] = code_title

                            if prev_code != NO_CODE:
                                next_code = next_item_code(row)
                                if next_code == NO_CODE:
                                    # 次が無い
                                    next_code = code

                                # # CODE変更
                                # def change_variety_code(s, prev_code):
                                #     close = self.account_db.search_close_title(prev_code, s['val'], 0.2)
                                #     if close:
                                #         s['revise'] = close
                                #         code = self.account_db.search_variety_code(s['revise'][0], prev_code)
                                #         if not code:
                                #             aaa = 0
                                #         s['code'] = code
                                #         code_title = self.account_db.to_title_text(code)
                                #         s['code_title'] = code_title
                                #     else:
                                #         aaa = 0
                                rowindex=rowindex+1
                                if prev_code[account_DB.Code.ORDER] != code[account_DB.Code.ORDER] and rowindex>2:
                                    next_next_code = next_item_code(row,2)
                                    if next_code[account_DB.Code.ORDER] == 3:
                                        aaa = 0
                                    # ORDERが変わった
                                    if code[account_DB.Code.ORDER] != 3:
                                        # 前後のTYPEは同じ?
                                        if next_code[account_DB.Code.ORDER] == prev_code[account_DB.Code.ORDER] or next_next_code[account_DB.Code.ORDER] == prev_code[account_DB.Code.ORDER]:
                                            # 1 -> 2 -> 1 or 1 -> 2 -> 2 -> 1 パターン
                                            # ==> 1 -> 1 -> 1 : 1 -> 1 -> 1 -> 1
                                            _ = change_variety_code(s, prev_code[:account_DB.Code.ORDER+1])
                                            # close = self.account_db.search_close_title(prev_code[:1], s['val'], 0.2)
                                            # if close:
                                            #     s['revise'] = close
                                            #     code = self.account_db.search_variety_code(s['revise'][0], prev_code[:1])
                                            #     if not code:
                                            #         aaa = 0
                                            #     s['code'] = code
                                            # else:
                                            #     aaa = 0
                                    else:
                                        aaa = 0
                                    # title_list = self.account_db.search_close_title(code[:1], s['val'])
                                    # aaa = 0
                                elif prev_code[:account_DB.Code.FAMILY+1] != code[:account_DB.Code.FAMILY+1] and rowindex>2:
                                    # FAMILYが変わった

                                    # # 4 -> 1 ==> 4 -> 4
                                    # if prev_code[1] == 4 and code[1] == 1:
                                    #     change_variety_code(s, prev_code[:2])
                                    #     aaa = 0

                                    # If Cells(i - 1, 2) = Cells(i, 2) And Cells(i - 1, 3) > Cells(i, 3) And Cells(i - 1, 5) > 0 Then

                                    # FAMILYのさかのぼりルール
                                    if prev_code[account_DB.Code.FAMILY] > code[account_DB.Code.FAMILY] and prev_code[account_DB.Code.VARIETY] >= 0:
                                        _ = change_variety_code(s, prev_code[:account_DB.Code.GENUS+1])
                                        aaa = 0
                                    # if prev_code[account_DB.Code.FAMILY] > code[account_DB.Code.FAMILY] and prev_code[account_DB.Code.VARIETY] > 0:
                                        # _ = change_variety_code(s, prev_code[:account_DB.Code.FAMILY+1])

                                    # self.account_db.search_close_title(code[:2], s['val'])
                                    aaa = 0
                                elif prev_code[:account_DB.Code.GENUS+1] != code[:account_DB.Code.GENUS+1] and rowindex>2:
                                    # GENUSが変わった
                                    aaa = 0
                                elif prev_code[:account_DB.Code.SPECIES+1] != code[:account_DB.Code.SPECIES+1] and rowindex>2:
                                    # SPECIESが変わった
                                    aaa = 0
                                else:
                                    # SPECIESまで同じ
                                    # self.account_db.search_close_title(code[:4], s['val'])
                                    aaa = 0

                            prev_code = code
                        else:
                            # 無いのはなぜ? __REGEX_REVISE__
                            aaa = 0
                    else:
                        # SUBJECT列なのに候補がない
                        s['code'] = ()
                        s['code_title'] = ''

                        r = self.account_db.revise_subject(s['val'])
                        if r is not None:
                            # s['revise'] = [r[1], f'{REGEX_REVISE}:{r[0]}']
                            code = self.account_db.search_variety_code(r[1])
                            # if code == syushikin or code == shihonkin:
                            #     code = repalce_shihonkin_syushikin(s, code, shisan_gokei)

                            if len(s['revise']) == 0:
                                s['revise'] = [r[1]]

                            s['revise'] = [s['revise'][0], f'{REGEX_REVISE}:{r[0]}']
                            s['code'] = code
                            if code:
                                code_title = self.account_db.to_title_text(s['code'])
                                s['code_title'] = code_title
                        else:
                            if col > 0:
                                # 前の列もv2ac.Type.SUBJECTで'revise'があればそちらを採用
                                if d['data'][col-1]['type'] == v2ac.Type.SUBJECT and d['data'][col-1]['revise']:
                                    d['data'][col] = d['data'][col-1]
                                    # d['data'][col] = copy.copy(d['data'][col-1])

                elif s['type'] == v2ac.Type.UNKNOWN:
                    # if s['val'] == '資':
                    #     aaa = 0
                    code = self.account_db.search_variety_code(s['val'], search_order)
                    if not code:
                        if prev_code:
                            close = self.account_db.search_variety_title(s['val'], ratio=0.6, code=prev_code[:account_DB.Code.FAMILY+1])
                        else:
                            close = None
                        if not close:
                            close = self.account_db.search_variety_title(s['val'], ratio=0.6, code=search_order)

                        if close:
                            s['revise'] = close
                            code = self.account_db.search_variety_code(close[0], search_order)

                        aaa = 0
                    # if code == syushikin or code == shihonkin:
                    #     code = repalce_shihonkin_syushikin(s, code, shisan_gokei)
                    s['code'] = code
                    if code:
                        code_title = self.account_db.to_title_text(s['code'])
                        s['code_title'] = code_title
                        # codeがあるのでSUBJECTにする
                        s['type'] = v2ac.Type.SUBJECT
                else:
                    code = () #[]
                    s['code'] = code

                # # 資産合計が出たので負債の部
                # if s['code'][:account_DB.Code.FAMILY+1] == (2,35) or s['code'][:account_DB.Code.FAMILY+1] == (2,40):
                #     if start_table_row_no <= d['row_no']:
                #         shisan_gokei = True
                aaa = 0

        HEADER_SCORE_Next       = 0x8000 # 次の行
        HEADER_SCORE_Kamoku     = 0x0800
        HEADER_SCORE_PrevPeriod = 0x0200
        HEADER_SCORE_PrevPeriod_Sub = 0x0040
        HEADER_SCORE_CurrPeriod = 0x0100
        HEADER_SCORE_CurrPeriod_Sub = 0x0080
        HEADER_SCORE_Ratio      = 0x0400

        Header_col = [
                {'regex':re.compile(r'(科目|項目|^科|^項)'), 'score':HEADER_SCORE_Kamoku},
                {'regex':re.compile(r'(増加率)'), 'score':0x20},
                {'regex':re.compile(r'(対売上比)'), 'score':0x10},
                {'regex':re.compile(r'^(前.*[期年].*額?)$'), 'score':HEADER_SCORE_PrevPeriod},
                {'regex':re.compile(r'(前.*[期年].*額?)'), 'score':HEADER_SCORE_PrevPeriod_Sub},
                # {'regex':re.compile(r'^(前.*期.*額?)$'), 'score':HEADER_SCORE_PrevPeriod},
                # {'regex':re.compile(r'(前.*期.*額)'), 'score':HEADER_SCORE_PrevPeriod},
                {'regex':re.compile(r'^((?:[今当].*期|決.*算).*額?)$'), 'score':HEADER_SCORE_CurrPeriod},
                {'regex':re.compile(r'((?:[今当].*期|決.*算).*額?)'), 'score':HEADER_SCORE_CurrPeriod_Sub},
                # {'regex':re.compile(r'((?:今.*期|決.*算).*額)'), 'score':HEADER_SCORE_CurrPeriod},
                # {'regex':re.compile(r'(当.*期)'), 'score':HEADER_SCORE_CurrPeriod},
                {'regex':re.compile(r'(構成比|売上高比率)'), 'score':0x02},
                {'regex':re.compile(r'(金額|額)'), 'score':0x01},
                {'regex':re.compile(r'^(%|対比)$'), 'score':HEADER_SCORE_Ratio},
        ]

        # table_blockで対象行の下から始まる(最下位であれば対象)ブロックの仕切りを使って分ける
        def seperate_col(papers,d):

            cols = None
            tb = None

            if len(d['data']) == 0 or len(d['data'][0]['chars']) == 0:
                return [], []

            # 対象行の元データ
            chars = d['data'][0]['chars'][0]['row']['chars']
            # for s in d['data']:
            for c in chars:
                if tb is None:
                    aaa = 0
                    page = int(c['row']['page'])-1
                    y = c['row']['bounds'].get_top()
                    table_block = self.papers[page]['table_block']
                    tb_no = len(table_block)-1
                    for j in range(len(table_block))[::-1]:
                        if table_block[j]['sy'] <= y <= table_block[j]['ey']:
                            break
                        tb_no = j

                    if tb_no >= 0:
                        tb = table_block[tb_no]['blocks']
                        cols = [{'val':''} for _ in range(len(tb)-1)]
                        aaa = 0
                    aaa = 0

                if tb and cols:
                    for j in range(len(cols)):
                        if tb[j] <= c['bounds'].get_left() <= tb[j+1]:
                            cols[j]['val'] += c['text']

            return cols, tb

        debug_print('--> find_HEADER',level=DEBUG_ROWS_INFO)
        print('--> find_HEADER')
        aaa = 0
        # 見出しを探す
        score = 0
        header_cols = [[] for _ in papers]
        prev_data = None
        for j, d in enumerate(data_param):
            d_data, tb = seperate_col(papers, d)
            aaa = 0
            for d_col, s in enumerate(d_data):
            # for s in d['data']:
                aaa = 0
                for h in Header_col:
                    f = h['regex'].search(s['val'])
                    if f is not None:
                    # if h['regex'].search(s['val']) is not None:
                        score |= h['score']
                        debug_print('{:x}[{}]'.format(h['score'],s['val']),level=DEBUG_ROWS_INFO)
                        print('{:x}[{}]'.format(h['score'],s['val']))
                        header_cols[d['page']].append({'title':s['val'], 'score':h['score'], 'data':d, 'col':d_col, 'col_block':tb[d_col:d_col+2], 'table_block':tb})
                    aaa = 0
            d['score'] = score
            if score > 0:
                debug_print('>> {}:HEADER({:x}) {}'.format(d['page'],score,'--YES--' if score > HEADER_SCORE_Kamoku else 'NO'),level=DEBUG_ROWS_INFO)
                print('>> {}:HEADER({:x}) {}'.format(d['page'],score,'--YES--' if score > HEADER_SCORE_Kamoku else 'NO'))

            if prev_data is not None:
                # 前の行が科目のみ
                if score > HEADER_SCORE_Kamoku:
                    # 科目以外があった
                    prev_data['score'] |= HEADER_SCORE_Next
                    debug_print('^^^ ({:x}) ^^YES^^'.format(prev_data['score']),level=DEBUG_ROWS_INFO)
                    print('^^^ ({:x}) ^^YES^^'.format(prev_data['score']))

                prev_data = None
                score = 0
            else:
                if score == HEADER_SCORE_Kamoku: # 科目のみ見つかった
                    prev_data = d
                else:
                    score = 0

        header = []
        page_header = []
        # ヘッダー行が各ページにあるか？
        for j, d in enumerate(data_param):
            aaa = 0
            if d['score'] > HEADER_SCORE_Kamoku:
                header.append(d)
                page_header.append(d['page'])
            for s in d['data']:
                aaa = 0
        header.sort(key=lambda x:x['no'])
        # header.sort(key=lambda x:(x['page'], x['no']))
        aaa = 0
        # ヘッダー行では無い行をheader_colsから削除
        for hcols in header_cols:
            for j in range(len(hcols))[::-1]:
                d = hcols[j]['data']
                p = d['page']
                no = d['no']

                for h in header:
                    # if p == h['page'] and (no == h['no'] or no == h['no']-1):
                    if p == h['page']:
                        if no == h['no']:
                            break
                        if no == h['no']-1 and (d['score'] & (HEADER_SCORE_PrevPeriod|HEADER_SCORE_CurrPeriod)) == (HEADER_SCORE_PrevPeriod|HEADER_SCORE_CurrPeriod):
                            break
                else:
                    del hcols[j]

        aaa = 0
        # 前期 今期(当期)の並びをみる
        for hcols in header_cols:
            prev_period = -1
            curr_period = -1
            prev_period_sub = -1
            curr_period_sub = -1

            for j, hc in enumerate(hcols):
                if hc['score'] == HEADER_SCORE_PrevPeriod:
                    prev_period = j
                elif hc['score'] == HEADER_SCORE_CurrPeriod:
                    curr_period = j

                if hc['score'] == HEADER_SCORE_PrevPeriod_Sub:
                    prev_period_sub = j
                elif hc['score'] == HEADER_SCORE_CurrPeriod_Sub:
                    curr_period_sub = j

            # 以前のバージョンになるべく影響が出ないようにする為
            if (prev_period < 0 or curr_period < 0) and (prev_period_sub >= 0 and curr_period_sub >= 0):
                prev_period = prev_period_sub
                curr_period = curr_period_sub

            if prev_period >= 0 and curr_period >= 0:
                if prev_period < curr_period:
                    self.period_order = v2ac.PeriodOrder.PREV_X_CURRENT_X  # 前期 X 今期 X
                elif prev_period > curr_period:
                    self.period_order = v2ac.PeriodOrder.CURRENT_PREV_X_X  # 今期 前期 X X

                break
        else:
            self.period_order = v2ac.PeriodOrder.NON # 見つからない

        # 割合の列があるか？推測
        ratio_cnt = 0
        for hcols in header_cols:
            for j, hc in enumerate(hcols):
                if hc['score'] == HEADER_SCORE_Ratio:
                    ratio_cnt += 1

        if ratio_cnt > int(len(header_cols)/2):
        # if ratio_cnt > 0:
            self.ratio_column = True

        print('HEADER:')
        try:
            for h in header:
                for d in h['data']:
                    debug_print('{}:[{}]'.format(h['page'],d['val']),level=DEBUG_ROWS_INFO)
                    print('{}:[{}]'.format(h['page'],d['val']))
                debug_print('-----',level=DEBUG_ROWS_INFO)
                print('-----')
        except:
            debug_print(':----',level=DEBUG_ROWS_INFO)
            print(':----')

        debug_print(f'period_order:{self.period_order}',level=DEBUG_ROWS_INFO)
        print(f'period_order:{self.period_order}')
        debug_print(f'ratio_column:{self.ratio_column}',level=DEBUG_ROWS_INFO)
        print(f'ratio_column:{self.ratio_column}')

        debug_print('<-- find_HEADER',level=DEBUG_ROWS_INFO)
        print('<-- find_HEADER')

        # header = []
        # page_header = []
        # # ヘッダー行が各ページにあるか？
        # for j, d in enumerate(data_param):
        #     aaa = 0
        #     if d['score'] > HEADER_SCORE_Kamoku:
        #         header.append(d)
        #         page_header.append(d['page'])
        #     for s in d['data']:
        #         aaa = 0
        # header.sort(key=lambda x:x['no'])
        # # header.sort(key=lambda x:(x['page'], x['no']))
        aaa = 0

        # 行の属性をセット
        for row, d in enumerate(data_param):
            d['type'] = v2ac.Type.UNKNOWN
            for col, s in enumerate(d['data']):
                d['type'] |= s['type']

        # 情報がある列を数えるために列の最大数のカウンターを用意
        cols_cnt = [0] * len(papers)
        cols_valid_cnt = [0] * len(papers) # 未使用? cols_type_cnt[page][col][4]
        cols_type_cnt = [0] * len(papers) # [0:SUBJECT数,1:AMOUNT数,2:以外,3:有効SUBJECT数,4:推測列タイプ,5:無効列,6:1文字かつ数字以外,7:全数]
        for page, paper in enumerate(papers):
            if len(paper['table_block'])==0 :
                cols_max=0
                cols_cnt[page] = [0] * (cols_max)
                cols_valid_cnt[page] = [0] * (cols_max)
                cols_type_cnt[page] = [[0] * 8 for _ in range(cols_max)]
                continue
            cols_max = paper['table_block'][-1]['ed']*2
            cols_cnt[page] = [0] * (cols_max)
            cols_valid_cnt[page] = [0] * (cols_max)
            cols_type_cnt[page] = [[0] * 8 for _ in range(cols_max)]
            # cols_type_cnt[page] = [[[0] * 3 for _ in range(cols_max)]] * (cols_max)

            # for tc in cols_type_cnt[page]:
            #     tc += [0,0,0]

        subject_cnt = copy.deepcopy(cols_cnt)
        sa_rows = [0] * len(papers)
        s_rows = [0] * len(papers)

        # for j in range(len(cols_cnt)):
        #     cols_cnt[j] = [0] * 10#(cols_cnt[j]+1)

        # 情報がある列を数える
        aaa = 0
        for row, d in enumerate(data_param):

            if (d['type'] & v2ac.Type.SUBJECT_AMOUNT) == v2ac.Type.SUBJECT_AMOUNT:
                sa_rows[d['page']] += 1
                for col, s in enumerate(d['data']):
                    if (s['type'] & v2ac.Type.SUBJECT_AMOUNT):
                        # print('{},{}'.format(d['page'],s['col']))
                        cols_cnt[d['page']][s['col']] += 1

                    if (s['type'] & v2ac.Type.SUBJECT):
                        subject_cnt[d['page']][s['col']] += 1
            if (d['type'] & v2ac.Type.SUBJECT) == v2ac.Type.SUBJECT:
                s_rows[d['page']] += 1

            # 有効?
            for col, s in enumerate(d['data']):
                if s['col'] == 4:
                    aaa = 0
                if (s['type'] == v2ac.Type.SUBJECT):
                    cols_type_cnt[d['page']][s['col']][0] += 1
                    if len(s['revise']) > 0:
                        cols_valid_cnt[d['page']][s['col']] += 1
                        cols_type_cnt[d['page']][s['col']][4] += 1
                elif (s['type'] == v2ac.Type.AMOUNT):
                    cols_type_cnt[d['page']][s['col']][1] += 1
                    cols_valid_cnt[d['page']][s['col']] -= 1
                else:
                    cols_type_cnt[d['page']][s['col']][2] += 1

                # 1文字かつ数字以外
                if s['val'] and len(s['val']) == 1 and (not s['val'][0].isdigit() or s['val'][0] == '1'):
                    cols_type_cnt[d['page']][s['col']][6] += 1

                # 全数
                cols_type_cnt[d['page']][s['col']][7] += 1

        # cols_types = [[]] * len(papers)
        aaa = 0
        for page, paper in enumerate(papers):
            for ct in cols_type_cnt[page]:
                if ct[0] == 0 and ct[1] == 0 and ct[2] == 0:
                    ct[3] = -1
                elif ct[0] > ct[1]:
                    if ct[0] > ct[2]:
                        ct[3] = v2ac.Type.SUBJECT
                    else:
                        ct[3] = v2ac.Type.UNKNOWN
                else:
                    if ct[1] > 0:
                    # if ct[1] > ct[2]:
                        ct[3] = v2ac.Type.AMOUNT
                    else:
                        ct[3] = v2ac.Type.UNKNOWN

        # 列の確認
        debug_print('--> cols_type_cnt',level=DEBUG_ROWS_INFO)
        print('--> cols_type_cnt')
        for page, t in enumerate(cols_type_cnt):

            # 割合列でT表では無いので有効行の最後の行を無効
            if self.ratio_column and not papers[page]['BS_T_table']:
                aaa = 0
                for c in reversed(t):
                # for j in range(len(t)-1,-1,-1):
                    if c[0] != 0 or c[1] != 0 or c[2] != 0:
                        # 有効行の最後の行を無効
                        if c[3] == v2ac.Type.AMOUNT:
                            c[5] = 1
                        break

            # AMOUNT列で全てが一文字で'1'と数字以外しか無い（縦線の残骸と推測）
            for c in reversed(t):
                if c[3] == v2ac.Type.AMOUNT and c[6] == c[7]:
                    c[5] = 1

            invalid_subject_col = -2
            print('<{}>'.format(page))
            for n, c in enumerate(t):
                invalid_col = 0
                if self.ratio_column and papers[page]['BS_T_table']:
                    # 割合列でT表
                    if c[3] == v2ac.Type.SUBJECT:
                        if c[4] == 0:
                            # 有効なSUBJECTが無い
                            c[5] = 1
                            invalid_subject_col = n
                    elif c[3] == v2ac.Type.AMOUNT:
                        if n == invalid_subject_col+1:
                            # 有効なSUBJECTが無い次の列
                            c[5] = 1
                # [0:SUBJECT数,1:AMOUNT数,2:以外,3:有効SUBJECT数,4:推測列タイプ,5:無効列,6:1文字かつ数字以外,7:全数]
                debug_print('{}{}:{}:{} ({},{},{},{})/{}'.format('*' if c[5]==1 else ' ', n, c[3],c[4],c[0],c[1],c[2],c[6],c[7]),level=DEBUG_ROWS_INFO)
                print('{}{}:{}:{} ({},{},{},{})/{}'.format('*' if c[5]==1 else ' ', n, c[3],c[4],c[0],c[1],c[2],c[6],c[7]))

        debug_print('<-- cols_type_cnt',level=DEBUG_ROWS_INFO)
        print('<-- cols_type_cnt')

        # SUBJECT列全体でreviseが無いものを探す(SUBJECT列では無い可能性)
        aaa = 0

            # self.ratio_column
            # table_type = papers[d['page']]['table_type']
            # if table_type == account_DB.Order.NON:

        # 情報が無いと思われる行を除外する
        if False: # 通常処理
        # if self.ratio_column == False: # 通常処理
            for row, d in enumerate(data_param):
                for col, s in enumerate(d['data']):
                    # if d['page'] >= len(cols_cnt) or s['col'] >= len(cols_cnt[d['page']]): # 2023/01/06 --? OK 017
                    #     s['OK'] = ' '
                    # else:
                    s['OK'] = ' ' if s['col'] >= len(cols_cnt[d['page']]) or cols_cnt[d['page']][s['col']] == 0 else '*'
                # if (d['type'] & v2ac.Type.SUBJECT_AMOUNT):
                #     for col, s in enumerate(d['data']):
                #         s['OK'] = ' ' if cols_cnt[d['page']][s['col']] == 0 else '*'
                # else:
                #     for col, s in enumerate(d['data']):
                #         s['OK'] = '-'
        else: # 割合(%)列がある時の処理
            aaa = 0
            for row, d in enumerate(data_param):
                ct = cols_type_cnt[d['page']]
                aaa = 0
                for col, s in enumerate(d['data']):
                    if ct[s['col']][5] != 0:
                        s['OK'] = ' '
                    else:
                        s['OK'] = ' ' if s['col'] >= len(cols_cnt[d['page']]) or cols_cnt[d['page']][s['col']] == 0 else '*'


        # 日付情報
        closing_dates = []
        date_ok = False
        for row, d in enumerate(data_param):
            for col, s in enumerate(d['data']):
                if s['type'] == v2ac.Type.DATE:
                    if '現在' in s['revise'][2] or 'から' in s['revise'][2]:
                        # 決算日ではない
                        continue
                    if '前期' in s['revise'][0]:
                        # 前期の日付は対象では無い
                        break

                    ad = revise_date_to_AD(s['revise'][1])
                    if ad:
                        dt = datetime.datetime.strptime(ad, '%Y/%m/%d')
                        cd = {'dt':dt, 'page':d['page'], 'bounds':s['bounds']}
                        closing_dates.append(cd)
                        if '至' in s['revise'][0] or 'まで' in s['revise'][2]:
                            # 決算日確定
                            date_ok = True
                            closing_dates = [cd]
                            break
            if date_ok:
                break

        if closing_dates:
            max_papers = len(papers)
            closing_dates.sort(key=lambda x: (x['dt'],max_papers-x['page']))
            # 一番最後
            closing_date = {'date':closing_dates[-1]['dt'].strftime('%Y/%m/%d'), 'page':closing_dates[-1]['page'], 'bounds':closing_dates[-1]['bounds']}
        else:
            closing_date = {'date':'', 'page':-1, 'bounds':Bound()}

        aaa = 0

        # 勘定科目の行の始まりを探してその行以降とデータのある列を抽出
        data_page = -1
        data_on = False
        excluded_title = False
        data_param_max = len(data_param)
        data_param_AC = [] # 勘定項目のみのリスト
        for row, d in enumerate(data_param):
            #data_list = d.get('data') if isinstance(d, dict) else None
            #if isinstance(data_list, list) and data_list and isinstance(data_list[0], dict) and 'val' in data_list[0]:
            #    debug_print('v2ac 5832:{}'.format(data_list[0]['val']), level=DEBUG_ROWS_INFO)
            # if row == 66:
            #     aaa = 0
            if data_page != d['page']:
                search_order = self.get_table_order(d['page'])
                data_page = d['page']
                data_on = False
                excluded_title = False

                table_row_range = papers[data_page]['table_row_range']

                # 対象テーブル範囲
                if table_row_range[0]:
                    start_table_row_no = table_row_range[0]['row']['row_no']
                    # start_table_row_no = table_row_range[0]['no']
                else:
                    start_table_row_no = 0
                if table_row_range[1]:
                    end_table_row_no   = table_row_range[1]['row']['row_no']
                    # end_table_row_no   = table_row_range[1]['no']
                else:
                    end_table_row_no = 9999

                # 対象外テーブルタイトル行
                if table_row_range[2]:
                    except_table_row_no   = table_row_range[2]['row']['row_no']
                    # except_table_row_no   = table_row_range[2]['no']
                else:
                    except_table_row_no = 9999

            if except_table_row_no <= d['row_no']:
                # 対象外テーブルのタイトル以降
                continue
            #if isinstance(data_list, list) and data_list and isinstance(data_list[0], dict) and 'val' in data_list[0]:
            #    debug_print('v2ac 5867:{}'.format(data_list[0]['val']), level=DEBUG_ROWS_INFO)
            # 対象テーブル範囲外?
            # if not (start_table_row_no <= d['row_no'] <= end_table_row_no):
            #     continue

            # # 対象外のテーブルタイトルがあるか確認
            # for ts in account_DB.except_table_subject:
            #     if subject in ts:

            # タイトル行を探す
            for col, s in enumerate(d['data']):
                if True: #s['type'] == v2ac.Type.SUBJECT:
                    if 'ex' in s and s["ex"]=="exs1" :
                      s['code']=(1,1,0,0,0,1)
                      s['code_title'] = "1[損益計算書]:1[売上高]:0[純売上高]:0[売上高]:0[売上高]"
                      s['OK'] = "+"
                      data_on = True
                    elif 'ex' in s and s["ex"]=="exa1" :
                      s['OK'] = "+"
                      data_on = True
                    elif len(s['chars']) >= 1:
                        if 'row' not in s['chars'][0]['row']:
                            break
                        txt = s['chars'][0]['row']['row']['text']
                        f = subject_amount_pat.search(txt)
                        if f is not None:
                            subject = f.group(1)
                            amount = f.group(2)
                            close = self.account_db.search_variety_title(subject, ratio=0.5, code=search_order)
                            if not close:
                                if s['revise']:
                                    close = self.account_db.search_variety_title(s['revise'][0], ratio=0.5, code=search_order)

                            if close:
                                code = self.account_db.search_variety_code(close[0],(3,)) # タイトル行=3
                                if code and code[account_DB.Code.PROPERTY] == 0:
                                    excluded_title = True # 以降の行を除外
                                    d['title_code'] = code

                        break

            if data_on == False:
                if (d['type'] & v2ac.Type.SUBJECT_AMOUNT) == v2ac.Type.SUBJECT_AMOUNT or d['type'] == v2ac.Type.UNKNOWN :
            #        if start_table_row_no <= d['row_no']:
                        data_on = True

            # if excluded_title == True:
            #     continue
            #debug_print('v2ac 5919 data_on:{} excluded_title:{} start_table_row_no:{}'.format(data_on,excluded_title,start_table_row_no), level=DEBUG_ROWS_INFO)
            if data_on == False or excluded_title == True:
                continue
            #if isinstance(data_list, list) and data_list and isinstance(data_list[0], dict) and 'val' in data_list[0]:
            #    debug_print('v2ac 5925:{}'.format(data_list[0]['val']), level=DEBUG_ROWS_INFO)
            dd = copy.copy(d)

            dd['data'] = []
            #if isinstance(data_list, list) and data_list and isinstance(data_list[0], dict) and 'val' in data_list[0]:
            #    debug_print('v2ac 5933:{}'.format(data_list[0]['val']), level=DEBUG_ROWS_INFO)
            for col, s in enumerate(d['data']):
                if s['OK'] != ' ':
                    dd['data'].append(copy.copy(s))

            if len(dd['data']) > 0:
                data_param_AC.append(dd)

        aaa = 0

        # SUBJECTの列を探す
        subject_cols = [[] for _ in papers]
        amount_cols = [[] for _ in papers]
        aaa = 0
        for j, d in enumerate(data_param_AC):
            data_list = d.get('data') if isinstance(d, dict) else None
            if (isinstance(data_list, list) and len(data_list) > 0 and isinstance(data_list[0], dict) and 'val' in data_list[0]):
                val = data_list[0]['val']
                debug_print(f'v2ac 5939 [{val}]', level=DEBUG_ROWS_INFO)
        for row, d in enumerate(data_param_AC):
            for col, s in enumerate(d['data']):
                if s['type'] == v2ac.Type.SUBJECT:
                    # SUBJECTが有った
                    if s['col'] not in subject_cols[d['page']]:
                            subject_cols[d['page']].append(s['col'])
                elif s['type'] == v2ac.Type.AMOUNT:
                    # AMOUNTが有った
                    if s['col'] not in amount_cols[d['page']]:
                            amount_cols[d['page']].append(s['col'])


        # SUBJECTを探す
        row_max = len(data_param_AC)
        for row, d in enumerate(data_param_AC):
            subject_on = False
            data_on = False

            # if d['type'] < v2ac.Type.SUBJECT_AMOUNT:
            #     d['type'] |= v2ac.Type.REMOVE
            #     continue

            col_max = len(d['data'])
            for col in range(col_max)[::-1]:
                if d['data'][col]['type'] != v2ac.Type.UNKNOWN:
                    data_on = True

                if subject_on:
                    # SUBJECTより前にある列を削除
                    del d['data'][col]
                else:
                    if d['data'][col]['type'] == v2ac.Type.SUBJECT:
                        # SUBJECTが有った
                        subject_on = True

            if not data_on:
                # データが無い?
                # d['type'] |= v2ac.Type.REMOVE
                aaa = 0

            if not subject_on:
                col = -1
                if d['type'] <= v2ac.Type.SUBJECT_AMOUNT:
                    for sc in subject_cols[d['page']]: # 左優先
                        for c, s in enumerate(d['data']):
                            if s['col'] == sc:
                                col = c
                                break
                        if col != -1:
                            break

                col2 = col

                # SUBJECTが無いのでSUBJECT候補となる列を探す
                def next_subject_col(r,n):

                    for s in data_param_AC[r+n]['data']:
                        if s['type'] == v2ac.Type.SUBJECT:
                            col = s['col']
                            for j, ss in enumerate(data_param_AC[r]['data']):
                                if ss['col'] == s['col']:
                                    return j
                    return -1

                col = -1
                if row > 0: # 最前行？
                    # 前の行をみる
                    col = next_subject_col(row,-1)

                if col == -1:
                    if row+1 < row_max:
                        # 後の行をみる
                        col = next_subject_col(row,1)

                if col2 != col:
                    aaa = 0

                if col != -1:
                    # SUBJECT候補列
                    s = d['data'][col]
                    if s['type'] < v2ac.Type.SUBJECT_AMOUNT:
                        s['type'] = v2ac.Type.SUBJECT
                        d['type'] |= s['type']
                        for c in range(col)[::-1]:
                            d['data'][c]['OK'] = '-'
                            # del d['data'][c]

                    if len(s['val']) == 0:
                        # 空白なので除外
                        d['type'] |= v2ac.Type.REMOVE
                    aaa = 0
        aaa = 0

        # 除外行の削除
        # for row in range(len(data_param_AC))[::-1]:
        #     if data_param_AC[row]['type'] == v2ac.Type.REMOVE:
        #         del data_param_AC[row]

        # 未登録のSUBJECTを前の行のSUBJECTのコードから予測する
        prev_code = NO_CODE
        for row, d in enumerate(data_param_AC):
            # if row == 50:
            #     aaa = 0

            # if d['type'] < v2ac.Type.SUBJECT_AMOUNT:
            #     # SUBJECT + AMOUNT の両方が揃っていない
            #     aaa = 0

            if not (d['type'] & v2ac.Type.REMOVE):
            # if d['type'] != v2ac.Type.REMOVE:
                for col, s in enumerate(d['data']):
                    if s['type'] == v2ac.Type.SUBJECT:
                        if not s['code']:
                            code = NO_CODE
                            if (d['type'] & v2ac.Type.AMOUNT):
                                # AMOUNTもある
                                code = change_variety_code(s, prev_code[:account_DB.Code.FAMILY+1],ratio=0.2)
                                if code == NO_CODE:
                                    code = change_variety_code(s, prev_code[:account_DB.Code.ORDER+1],ratio=0.2)

                            if not s['val']:
                            # if code == NO_CODE:
                                d['type'] |= v2ac.Type.REMOVE

                        else:
                            prev_code = s['code']

        aaa = 0
        for j, d in enumerate(data_param_AC):
            data_list = d.get('data') if isinstance(d, dict) else None
            if (isinstance(data_list, list) and len(data_list) > 0 and isinstance(data_list[0], dict) and 'val' in data_list[0]):
                val = data_list[0]['val']
                debug_print(f'v2ac 6072 [{val}]', level=DEBUG_ROWS_INFO)
        # SUBJECT列とAMOUNT列のパターンを見つける
        subject_amount_cols = [[] for _ in papers]
        aaa = 0
        for row, d in enumerate(data_param_AC):
            d['subject_col'] = -1
            d['subject_data']  = -1
            sa_cols = []
            sau_cols = []
            subject_on = False
            for col, s in enumerate(d['data']):
                if s['type'] == v2ac.Type.SUBJECT:
                    # SUBJECTが有った
                    d['subject_col'] = s['col']
                    d['subject_data']  = col
                    subject_on = True
                    sa_cols = [s['col']]
                    sau_cols = [s['col']]
                elif s['type'] == v2ac.Type.AMOUNT:
                    # AMOUNTが有った
                    sa_cols.append(s['col'])
                    sau_cols.append(s['col'])

                elif s['type'] == v2ac.Type.UNKNOWN:
                    if subject_on:
                        # sa_cols.append(s['col'])
                        sau_cols.append(s['col'])

            d['cols'] = sa_cols
            if sau_cols:
                for j, sa in enumerate(subject_amount_cols[d['page']]):
                    if sa[0] == sau_cols[0]: # SUBJECT列が同じ
                        if sa != sau_cols:
                            subject_col = sau_cols[0]
                            sau_cols = sau_cols[1:]
                            sau_cols.extend(sa[1:])
                            sau_cols = [subject_col] + list(set(sau_cols))

                            sau_cols.sort(key=lambda x: x)
                            subject_amount_cols[d['page']][j] = sau_cols
                            # if len(sa) < len(sau_cols):
                            #     subject_amount_cols[d['page']][j] = sau_cols
                        break
                else:
                    subject_amount_cols[d['page']].append(sau_cols)

            aaa = 0

        aaa = 0
        # AMOUNT列を揃える
        for row, d in enumerate(data_param_AC):
            if not (d['type'] & v2ac.Type.REMOVE):
                for sau_cols in subject_amount_cols[d['page']]:
                    if d['subject_col'] == sau_cols[0]:
                        break
                else:
                    continue

                if sau_cols == d['cols']:
                    continue

                aaa = 0

                for sa in sau_cols[1:]:
                    for col, s in enumerate(d['data']):
                        if s['type'] == v2ac.Type.SUBJECT:
                            continue
                        if sa == s['col']:
                            if s['type'] == v2ac.Type.UNKNOWN:
                                if d['subject_data'] >= 0 and d['data'][d['subject_data']]['code']:
                                    s['type'] = v2ac.Type.AMOUNT
                                    if len(s['revise']) == 1:
                                        s['revise'] += ['','']
                                    d['type'] |= s['type']
                            break
                    else:
                        aaa = 0
                        new_col = {'type':v2ac.Type.AMOUNT, 'val':'', 'revise':[COL_ALIGN,'',''], 'col':sa, 'char':[], 'bounds':Bound(), 'code':(), 'OK':'#'}
                        for col in range(len(d['data']))[::-1]:
                            if (col > 0 and d['data'][col-1]['type'] == v2ac.Type.SUBJECT):
                                d['data'].insert(col,new_col)
                                break
                            if d['data'][col]['col'] <= sa+1:
                                d['data'].insert(col,new_col)
                                break

        aaa = 0

        for row, d in enumerate(data_param_AC):
            if not (d['type'] & v2ac.Type.REMOVE):
                aaa = 0
                d['data'].sort(key=lambda x: (x['col'],x['type']))
                aaa = 0
                for col, s in enumerate(d['data']):
                    if s['type'] == v2ac.Type.AMOUNT:
                        # print(f'{row}:{col}')
                        if 'revise' not in s:
                            aaa = 0
                        if len(s['revise']) >= 2:
                            aaa = 0
                        else:
                            s['OK'] = '+'

        aaa = 0

        # 収集された１行分の領域を算出
        for j, d in enumerate(data_param_AC):
            aaa = 0
            d['bounds'] = None
            for s in d['data']:
                if 'bounds' in s and s['bounds'] and not s['bounds'].is_empty():
                    if d['bounds']:
                        d['bounds'].expand(s['bounds'])
                    else:
                       d['bounds'] = copy.deepcopy(s['bounds'])

            if not d['bounds']:
                d['bounds'] = Bound()

        aaa = 0

        # 重なっている行の統合(find_rowsの重なり判定と同様の処理)
        rows_scale = [0.25,0.30]
        for j, d1 in enumerate(data_param_AC[:-1]):
            aaa = 0
            for d2 in data_param_AC[j+1:]:
                if d1['page'] == d2['page'] and d1['subject_col'] == d2['subject_col']:
                    if not d1['bounds'].is_empty() and not d2['bounds'].is_empty():
                    # if not d1['bounds'].is_empty() and not d2['bounds'].is_empty() and max(d1['bounds'].rect[0],d2['bounds'].rect[0]) <= min(d1['bounds'].rect[2],d2['bounds'].rect[2]):

                        y12 = int((d1['bounds'].rect[3]-d1['bounds'].rect[1]) * rows_scale[0] + 0.5)
                        y1 = d1['bounds'].rect[1] + y12
                        y2 = d1['bounds'].rect[3] - y12

                        y12d = int((d2['bounds'].rect[3]-d2['bounds'].rect[1]) * rows_scale[1] + 0.5)
                        y1d = d2['bounds'].rect[1] + y12d
                        y2d = d2['bounds'].rect[3] - y12d

                        if (y1d <= y1 <= y2d) or (y1 <= y1d <= y2):
                            if (d1['type'] & v2ac.Type.REMOVE):
                                d = d2
                                dd = d1
                            else:
                                d = d1
                                dd = d2

                            aaa = 0
                            for k, s in enumerate(d['data']):
                                if s['type'] == v2ac.Type.AMOUNT:
                                    if not s['val']:
                                        for ss in dd['data']:
                                            if ss['type'] == v2ac.Type.AMOUNT and s['col'] == ss['col']:
                                                d['data'][k] = copy.deepcopy(ss)
                                                ss['val'] = ''
                                                # d['type'] |= v2ac.Type.AMOUNT
                                                break
        aaa = 0

        paper_info = [[] for _ in papers]
        # paper_ratio        = [0.0] * len(papers)
        paper_subject_info = [{'ratio':0, 'cnt':0} for _ in range(len(papers))]
        # paper_subject_info = [{'perfect':0, 'cnt':0}] * len(papers)

        # データの調整と構成チェック
        for j, d in enumerate(data_param_AC):
            data_list = d.get('data') if isinstance(d, dict) else None
            if (isinstance(data_list, list) and len(data_list) > 0 and isinstance(data_list[0], dict) and 'val' in data_list[0]):
                val = data_list[0]['val']
                debug_print(f'v2ac 6240 [{val}]', level=DEBUG_ROWS_INFO)
        # for j, d in enumerate(data_param):
            code = []

            amount_no = 0
            amount_repeat = 0
            subject_ratio = 0.0

            prev_val_col = -1
            for k, s in enumerate(d['data']):
                if s['OK'] != '-':
                    if s['type'] == v2ac.Type.SUBJECT:
                        if 'code' in s and s['code']:
                            code = s['code']
                            sm = SequenceMatcher(None, remove_brackets.sub(r'\1',s['val']), s['revise'][0])
                            subject_ratio = sm.ratio()
                        else:
                            subject_ratio = 0.0

                        s['ratio'] = subject_ratio

                        # paper_ratio[d['page']] += subject_ratio

                        paper_subject_info[d['page']]['ratio'] += subject_ratio
                        paper_subject_info[d['page']]['cnt'] += 1

                    elif s['type'] == v2ac.Type.AMOUNT:
                        s['amount_no'] = amount_no
                        amount_no += 1

                        if 'revise' in s and s['revise'] and len(s['revise']) > 1:
                        # if 'revise' in s and s['revise']:
                        #     if len(s['revise']) <= 1:
                        #         aaa = 0
                            # マイナス値
                            ret = triangle_minus_sign.search(s['revise'][1])
                            if ret:
                                s['revise'][1] = triangle_minus_sign.sub('-', s['revise'][1])
                            #     s['revise'][1] = triangle_minus_sign.sub('-' if len(code) >= 5 and code[4] == 0 else '', s['revise'][1])
                            else:
                                # 金額の前の(s['revise'][0])最後をチェック
                                ret = error_head_minus_sign.search(s['revise'][0])
                                if ret:
                                    s['revise'][0] = s['revise'][0][:-1]
                                    s['revise'][1] = '-'+s['revise'][1]
                                elif prev_val_col >= 0:
                                    # 前の項目の(正規化前の文字列の)最後をチェック
                                    ret = error_head_minus_sign.search(d['data'][prev_val_col]['val'])
                                    if ret:
                                        s['val'] = d['data'][prev_val_col]['val'][-1] + s['val']
                                        d['data'][prev_val_col]['val'] = d['data'][prev_val_col]['val'][:-1]
                                        s['revise'][1] = '-'+s['revise'][1]

                            # AMOUNTの,.を取り除く
                            s['revise'][1] = re.sub(r'[,.、]', '', s['revise'][1])
                            # 。-> 0
                            s['revise'][1] = s['revise'][1].replace('。','0')

                            # -の前に文字がある場合に取り除く
                            if '-' in s['revise'][1]:
                                ret = triangle_minus_sign.search(s['revise'][1])
                                if ret.start(0) > 0:
                                    s['revise'][1] = s['revise'][1][ret.start(0):]


                            if subject_ratio > 0.0 and s['revise'][1]:
                                amount_repeat += 1
                                # if amount_repeat > 1:
                                #     aaa = 0
                        else:
                            aaa = 0

                if len(s['val']) > 0:
                    prev_val_col = k

            d['amount_cnt'] = amount_no
            d['amount_repeat'] = amount_repeat
            for c in paper_info[d['page']]:
                if c['counts'] == amount_no:
                    c['cnt'] += 1
                    if amount_repeat > 1:
                        c['repeat'] += 1
                    break
            else:
                paper_info[d['page']].append({'counts':amount_no, 'cnt':1, 'repeat':1 if amount_repeat > 1 else 0})

        for c in paper_info:
            c.sort(key=lambda x: (x['cnt']),reverse=True)

        aaa = 0
        for p in paper_subject_info:
        #    debug_print( 'v2ac 6393 [{}@{}]'.format(p['ratio'],p['cnt']), level=DEBUG_ROWS_INFO)
            p['del'] = True if p['cnt'] == 0 or (p['ratio']/p['cnt']) < 0.4 else False

        # 勘定科目と思われる行が極端に少ないページを除外
        for i in range(len(data_param_AC))[::-1]:
            if paper_subject_info[data_param_AC[i]['page']]['del']:
                del data_param_AC[i]
        # for i in range(len(data_param_AC))[::-1]:
        #     if paper_ratio[data_param_AC[i]['page']] < 2.0:
        #         del data_param_AC[i]
        for j, d in enumerate(data_param_AC):
            data_list = d.get('data') if isinstance(d, dict) else None
            if (isinstance(data_list, list) and len(data_list) > 0 and isinstance(data_list[0], dict) and 'val' in data_list[0]):
                val = data_list[0]['val']
                debug_print(f'v2ac 6345 [{val}]', level=DEBUG_ROWS_INFO)
        # variety_code を SUBJECT行に設定
        def set_variety_code(s, variety_code, insert_revise=False):
            s['code'] = variety_code # (0,0,0,0,0)
            s['code'] +=(self.account_db.code_to_variety_property(s['code']),)
            code = self.account_db.code_to_title(s['code'], self.account_db.variety)
            if insert_revise == False:
                s['revise'] = [code]
            else:
                s['revise'].insert(0,code)
                if len(s['revise']) > 3: # 3個以上は３個にする
                    s['revise'] = s['revise'][:3]

            code_title = self.account_db.to_title_text(s['code'])
            s['code_title'] = code_title

        if self.period_order == v2ac.PeriodOrder.NON: # 前期、今期が見出しにある場合はルールを適用しない
            # 2,3列ルール
            # FAMILY->3ケタ
            # 横並び処理
            # flags = 1:勘定科目が存在しない場合は挿入
            # TAB4は除外
            SbySs = [ # CODE注意
                {'code':(1, 1),   'dest':(1, 1, 0, 0,-1),   'flags':0x11},
                # {'code':(1, 1, 0),   'dest':(1, 1, 0, 0,-1),   'flags':0x01},
                {'code':(1, 2, 2),   'dest':(1, 2, 2, 0,-1),   'flags':0x01},
                {'code':(1, 2, 3),   'dest':(1, 2, 0, 0,-1),   'flags':0x01},
                # {'code':(1, 2, 0),   'dest':(1, 2, 0, 0,-1),   'flags':0x01},
                # {'code':(1, 3, 0),   'dest':(1, 3, 0, 0, 0),   'flags':0x01},
                {'code':(1, 4),      'dest':(1, 4, 0, 0,-1),   'flags':0x01},
                {'code':(1, 6, 0),   'dest':(1, 6, 0, 0,-1),   'flags':0x01},
                {'code':(1, 7, 0),   'dest':(1, 7, 0, 0,-1),   'flags':0x01},
                {'code':(1, 9, 0),   'dest':(1, 9, 0, 0,-1),   'flags':0x01},
                {'code':(1,10, 0),   'dest':(1,10, 0, 0,-1),   'flags':0x01},
            ]

            insert_data = False
            for j, d in enumerate(data_param_AC):
                if insert_data:
                    insert_data = False
                    continue

                counts = paper_info[d['page']][0]['counts']

                # 表と行の値の数が揃っていない
                if d['amount_cnt'] != counts:
                    if d['type'] & v2ac.Type.SUBJECT == d['type'] & v2ac.Type.SUBJECT:
                        d['type'] |= v2ac.Type.REMOVE
                        aaa = 0

                if (self.ratio_column == True and counts == 2) or (self.ratio_column == False and (counts == 2 or counts == 3)): # 横並びが2,3 (ページ毎) 比率％テーブルは除く
                # if self.ratio_column == False and (counts == 2 or counts == 3): # 横並びが2,3 (ページ毎) 比率％テーブルは除く
                    find_SbySs = False
                    if d['amount_repeat'] > 1:
                        # (2列目の金額>0)
                        find_SbySs = True
                        if counts == 3:
                            aaa = 0
                            for s in d['data']:
                                if s['type'] == v2ac.Type.AMOUNT and s['amount_no'] == 2:
                                    # 金額の3列目
                                    if len(s['revise']) == 3 and s['revise'][1]:
                                        break
                            else:
                                find_SbySs = False

                    if find_SbySs:
                        code = d['data'][d['subject_data']]['code']
                        for ss in SbySs:
                            comp_len = len(ss['code'])
                            if ss['code'][:comp_len] != code[:comp_len]:
                            # if ss['code'][:account_DB.Code.GENUS+1] != code[:account_DB.Code.GENUS+1]:
                                continue

                            # 右側の値が0 もしくは無効な値
                            # invalid_amount = False
                            # amount_no = counts-1 # 最後の列(counts=2:3番目 counts=3:3番目)
                            # try:
                            #     for s in d['data']:
                            #         if s['type'] == v2ac.Type.AMOUNT and s['amount_no'] == amount_no:
                            #             if len(s['revise']) >= 2 and int(s['revise'][1]) == 0:
                            #                 # 有効な値では無い
                            #                 invalid_amount = True
                            #                 break
                            # except:
                            #     invalid_amount = True

                            # if invalid_amount:
                            #     continue

                            aaa = 0

                            # if ss['code'][2] == None or ss['code'][2] == code[2]:
                            #     if ss['code'][3] == None or ss['code'][3] <= code[3]:
                            #         aaa = 0
                            #         for k, dd in enumerate(data_param_AC):
                            #             if d == dd:
                            #                 continue
                            #             cc = dd['data'][d['subject_data']]['code']
                            #             if ss['res'][:3] == cc[:3]:
                            #                 if ss['res'][3] != None:
                            #                     if ss['res'][3] <= 0:
                            #                         if ss['res'][3] == cc[3]:
                            #                             aaa = 0
                            #                             break
                            #                     elif ss['res'][3] <= cc[3]:
                            #                         aaa = 0
                            #                         break
                            #         else:
                            #             dd = None

                            # on = True
                            # if ss['flags'] & 0x02: # variety≦0が存在せず?
                            #     aaa= 0
                            #     for k, dd in enumerate(data_param_AC):
                            #         cc = dd['data'][d['subject_data']]['code']
                            #         # if ss['code'][:3] == cc[:3]:
                            #         #     if cc[3] <= 0:
                            #         #         break
                            #         if ss['code'][:3] == cc[:3] and cc[3] <= 0:
                            #             on = False  # 存在した
                            #             break

                            # if not on:
                            #     continue

                            # 発生条件は一致した

                            # 代入（なければ挿入)する勘定科目の行を探す
                            row_no = -1
                            for k, dd in enumerate(data_param_AC):
                                if d['page'] != dd['page']:
                                    continue
                                cc = dd['data'][d['subject_data']]['code']
                                if ss['dest'][:account_DB.Code.VARIETY+1] == cc[:account_DB.Code.VARIETY+1]: # CODE注意
                                # if ss['dest'][:4] == cc[:4]:
                                    row_no = k
                                    break

                            if row_no == -1:
                                # 行は存在しない
                                if (ss['flags'] & 0x01) != 0x01:
                                    continue # 見つからず、挿入もしないので何もしない

                                # 元データをコピーして挿入する勘定科目に書き換える
                                ddd = copy.deepcopy(d)
                                s = ddd['data'][d['subject_data']]
                                s['code'] = ss['dest']+(self.account_db.code_to_variety_property(ss['dest']),)
                                s['revise'] = [self.account_db.code_to_title(s['code'][:account_DB.Code.VARIETY+1], self.account_db.variety)]
                                code_title = self.account_db.to_title_text(s['code'][:account_DB.Code.VARIETY+1])
                                s['code_title'] = code_title

                                # if (ss['flags'] & 0x10) == 0x10:
                                #     # 前にある売上高1_1_0_0_0>=を変更1_1_0_0_1
                                #     if j > 0:
                                #         for jj in range(j-1,-1,-1):
                                #             d2 = data_param_AC[jj]
                                #             s2 = d2['data'][d2['subject_data']]
                                #             code = s2['code']
                                #             if code[:account_DB.Code.SPECIES+1] == (1,1,0,0) and code[account_DB.Code.VARIETY] <= 0:
                                #                 set_variety_code(s2, (1,1,0,0,1))
                                #                 # s2['code'] = (1,1,0,0,1)
                                #                 # s2['code'] +=(self.account_db.code_to_variety_property(s2['code']),)
                                #                 # s2['revise'] = [self.account_db.code_to_title(s2['code'][:account_DB.Code.VARIETY+1], self.account_db.variety)]
                                #                 # code_title = self.account_db.to_title_text(s2['code'][:account_DB.Code.VARIETY+1])
                                #                 # s2['code_title'] = code_title
                                #                 break

                                # 金額を一旦削除
                                for s in ddd['data']:
                                    if s['type'] == v2ac.Type.AMOUNT:
                                        s['val'] = ''
                                        s['revise'] = []

                                # 該当行の下に挿入
                                row_no = j+1
                                data_param_AC.insert(row_no, ddd)
                                insert_data = True

                                # 挿入したデータ(TAB4の処理でto_jsonで使用)
                                ddd['add'] = ddd

                            else:
                                ddd = d

                            # 元データの最後の列
                            amount_no = counts-1 # 最後の列(counts=2:3番目 counts=3:3番目)
                            src = None
                            for s in d['data']:
                                if s['type'] == v2ac.Type.AMOUNT and s['amount_no'] == amount_no:
                                    src = copy.deepcopy(s)
                                    # s['revise'] = []
                                    break

                            # 行を書き換える
                            ddd = data_param_AC[row_no]

                            if src:
                                aaa = 0
                                # 先データの２番目
                                for k, s in enumerate(ddd['data']):
                                    if s['type'] == v2ac.Type.AMOUNT and s['amount_no'] == amount_no:
                                        # src['amount_no'] = 0
                                        ddd['data'][k] = src
                                        # s['revise'] = []
                                        break
                                else:
                                    src = None

                            if src:
                                break

                            aaa = 0

                            #         if dd:
                            #             # 代入すべき科目があった
                            #             aaa = 0
                            #         else:
                            #             # 代入すべき科目がないので追加
                            #             aaa = 0

                            #         break
                        else:
                            # 対象となる発生場所条件が無いので一番左にある金額を採用
                            ss = None

        # prev_code = (-1,-1,-1,-1,-1,-1) # CODE注意
        # for i, d in enumerate(data_param_AC):
        #     if d['type'] & v2ac.Type.REMOVE:
        #         continue
        #     for s in d['data']:
        #         if s['OK'] == '-':
        #             continue

        #         if s['type'] == v2ac.Type.SUBJECT:
        #             if 'code' in s and s['code']:
        #                 code2 = self.account_db.search_variety_code(s['revise'][0], prev_code[:account_DB.Code.VARIETY])
        #                 if not code2:
        #                     code2 = self.account_db.search_variety_code(s['revise'][0], prev_code[:account_DB.Code.SPECIES])
        #                     if not code2:
        #                         code2 = self.account_db.search_variety_code(s['revise'][0], prev_code[:account_DB.Code.GENUS])

        #                 if code2 and s['code'] != code2:
        #                     s['code'] = code2
        #                     code_title = self.account_db.to_title_text(s['code'][:account_DB.Code.VARIETY+1])
        #                     s['code_title'] = code_title
        #                     aaa = 0

        #             prev_code = s['code']

        #KOKO
        # if ratio_cnt > 0:
        # self.ratio_column = False
        self.ratio_pt_col = [False] * 8
        self.ratio_col_max = [0] * 8
        self.ratio_col_cnt = [0] * 8
        self.ratio_pt_cnt = [0] * 8 # '.'がある
        if self.period_order == v2ac.PeriodOrder.NON:
            self.ratio_col_max = [0] * 8
            self.ratio_col_cnt = [0] * 8
            self.ratio_pt_cnt = [0] * 8 # '.'がある
            # タイトルが読めていない（網掛け）の場合に比率と思われる列を推測する
            for j, d in enumerate(data_param_AC):
                for ss in d['data']:
                    if ss['type'] == v2ac.Type.AMOUNT and ss.get('amount_no')!=None and ss.get('val')!=None:
                        n = ss['amount_no']
                        val = ss['val']
                        if len(val) > 0:
                            self.ratio_col_max[n] += 1

                        if val != '0' and len(val) <= 5:
                            self.ratio_col_cnt[n] += 1
                        if '.' in val:
                            self.ratio_pt_cnt[n] += 1
        for j in range(len(self.ratio_pt_col)):
            if self.ratio_col_max[j] > 0 and (self.ratio_pt_cnt[j] / self.ratio_col_max[j]) / 0.5:
                self.ratio_pt_col[j] = True


        aaa = 0
        # 売上高合計1_1_0_0_-1がある場合
        # 前にある売上高1_1_0_0_0>=を変更1_1_0_0_1
        for j, d in enumerate(data_param_AC):
        #    if d['data'][0]['val']=='退職金掛け金' :
        #        debug_print( 'v2ac 6682 [{}]'.format(d['data'][0]['val']), level=DEBUG_ROWS_INFO)
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,-1):    # 売上高合計
                if j > 0:
                    for jj in range(j-1,-1,-1):
                        d2 = data_param_AC[jj]
                        s2 = d2['data'][d2['subject_data']]
                        code = s2['code']
                        if code[:account_DB.Code.SPECIES+1] == (1,1,0,0) and code[account_DB.Code.VARIETY] <= 0:
                            set_variety_code(s2, (1,1,0,0,1))
                            break

        # 売上高（合計）1_1_0_0_0 が２回続いた場合
        # 売上高 ∑1_1_0-∑(1_1_1)を計算した結果と違う金額の行を1_1_0_0_1とする
        ac_count,uriage_sum=0,0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,0):
                ac_count+=1
                if ac_count>1:
                    break

        def get_year_amount(d, year_col):
            amount = 0
            for ss in d['data']:
                if ss['type'] == v2ac.Type.AMOUNT and ss['amount_no'] == year_col:
                    #20240419　ss['revise'][1]が''で落ちるのを回避するために追記
                    if len(ss['revise']) >= 2 and ss['revise'][1]:
                        amount = int(ss['revise'][1])
                    break

            return amount
        for j, d in enumerate(data_param_AC):
            data_list = d.get('data') if isinstance(d, dict) else None
            if (isinstance(data_list, list) and len(data_list) > 0 and isinstance(data_list[0], dict) and 'val' in data_list[0]):
                val = data_list[0]['val']
                debug_print(f'v2ac 6658 [{val}]', level=DEBUG_ROWS_INFO)
        if ac_count > 1:
            for j, d in enumerate(data_param_AC):
                _, this_year_col = self.get_period_col(d)
                d['amount_this_year'] = get_year_amount(d, this_year_col)

                s = d['data'][d['subject_data']]
                if s['code'][:account_DB.Code.FAMILY+1] == (1,1,):
                    if s['code'][account_DB.Code.GENUS] == 0:
                        uriage_sum+= d['amount_this_year']
                    elif s['code'][account_DB.Code.GENUS] == 1:
                        uriage_sum-= abs(d['amount_this_year'])
                if s['code'][:account_DB.Code.FAMILY+1] == (1,2,):
                    break
            for j, d in enumerate(data_param_AC):
                s = d['data'][d['subject_data']]

                if s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,0) and uriage_sum!= d['amount_this_year']:
                    set_variety_code(s, (1,1,0,0,1))

        # 売上高1_1_0_0_1 が２回続いた場合、上の行を1_1_0_0_0とする
        ac_count,uriage_sum=0,0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,1):
                ac_count+=1
                if ac_count>1:
                    break
        if ac_count > 1:
            for j, d in enumerate(data_param_AC):
                s = d['data'][d['subject_data']]
                if s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,1):
                    set_variety_code(s, (1,1,0,0,0))
                    break


        # 損益計算書の売上原価に棚卸と仕入がある場合の合計
        oroshi = -1
        shiire = -1
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.FAMILY+1] == (1,2):    # 売上原価
                if s['code'][account_DB.Code.GENUS] == 1:    # 期首棚卸
                    oroshi = j
                    aaa = 0
                elif s['code'][account_DB.Code.GENUS] == 2:  # 当期仕入
                    shiire = j

                    if (oroshi > 0) and (j+1 < len(data_param_AC)):
                        next = data_param_AC[j+1]['data'][d['subject_data']]
                        # if next['code'] and next['code'][account_DB.Code.VARIETY] <= 0: # 合計
                        if next['code'] and next['code'][account_DB.Code.VARIETY] < 0: # 合計
                            if next['code'][:account_DB.Code.VARIETY] != (1,2,2,0):
                                code = self.account_db.search_variety_code(next['val'], s['code'][:account_DB.Code.SPECIES]+(0,))
                                if code:
                                    close = self.account_db.search_close_title(code[:account_DB.Code.SPECIES]+(0,), next['val'], 0.2)

                                if not code or not close or code[:account_DB.Code.VARIETY] != (1,2,2,0):
                                    code = (1,2,2,0,-1,-1) # 見つからないので強制的に"合計"
                                    close = [self.account_db.code_to_title(code[:account_DB.Code.VARIETY+1], self.account_db.variety)]
                                    # close = ['合計']

                                code_title = self.account_db.to_title_text(code)
                                next['code_title'] = code_title
                                next['code'] = code
                                next['revise'] = close
                                # close = [self.account_db.code_to_title(code[:account_DB.Code.VARIETY+1], self.account_db.variety)]

                            # oroshi = -1

                elif False and s['code'][account_DB.Code.GENUS] == 3:  # 期末棚卸
                    aaa = 0
                    if shiire > 0 and j+1 < len(data_param_AC):
                        next = data_param_AC[j+1]['data'][d['subject_data']]
                        # if next['code'] and next['code'][account_DB.Code.VARIETY] <= 0: # 合計
                        if next['code'] and next['code'][account_DB.Code.VARIETY] < 0: # 合計
                            if next['code'][:account_DB.Code.VARIETY] != (1,2,3,0):
                                code = self.account_db.search_variety_code(next['val'], s['code'][:account_DB.Code.SPECIES]+(0,))
                                if code:
                                    close = self.account_db.search_close_title(code[:account_DB.Code.SPECIES]+(0,), next['val'], 0.2)

                                if not code or not close or code[:account_DB.Code.VARIETY] != (1,2,3,0):
                                    code = (1,2,3,0,-1,-1) # 見つからないので強制的に"合計"
                                    close = [self.account_db.code_to_title(code[:account_DB.Code.VARIETY+1], self.account_db.variety)]
                                    # close = ['合計']

                                code_title = self.account_db.to_title_text(code)
                                next['code_title'] = code_title
                                next['code'] = code
                                next['revise'] = close
                                # close = [self.account_db.code_to_title(code[:account_DB.Code.VARIETY+1], self.account_db.variety)]

                            # shiire = -1
        for j, d in enumerate(data_param_AC):
            data_list = d.get('data') if isinstance(d, dict) else None
            if (isinstance(data_list, list) and len(data_list) > 0 and isinstance(data_list[0], dict) and 'val' in data_list[0]):
                val = data_list[0]['val']
                debug_print(f'v2ac 6752 [{val}]', level=DEBUG_ROWS_INFO)
        # Sub Macro3()
        Flg = 0
        lastRow = len(data_param_AC)-1

        # ルール２ 前後(ORDER + FAMILY)
        # s = data_param_AC[0]['data'][data_param_AC[0]['subject_data']]
        # beforeKey = s['code'][:account_DB.Code.FAMILY+1]
        # order = s['code'][account_DB.Code.ORDER]
        beforeKey = None
        order = None

        prev_page = -1
        for i in range(0,lastRow):
        # for i in range(1,lastRow):
            if beforeKey == None or order == None:
                s = data_param_AC[i]['data'][data_param_AC[i]['subject_data']]
                if len(s['code']) >= account_DB.Code.FAMILY+1:
                    beforeKey = s['code'][:account_DB.Code.FAMILY+1]
                if len(s['code']) >= 1:
                    order = s['code'][account_DB.Code.ORDER]
                continue

            d = data_param_AC[i]
            cur_line = d['data'][d['subject_data']]
            if len(cur_line['code']) <= account_DB.Code.FAMILY:
                continue

            thisKey = cur_line['code'][:account_DB.Code.FAMILY+1]
            if thisKey != beforeKey:
                if Flg == 0:
                    d = data_param_AC[i+1]
                    next_line = d['data'][d['subject_data']]
                    if len(next_line['code']) <= account_DB.Code.FAMILY:
                        beforeKey = thisKey
                        continue

                    startRow = i

                    if cur_line['code'][account_DB.Code.FAMILY] == next_line['code'][account_DB.Code.FAMILY]:
                        Flg = 1
                elif Flg == 1:
                    d = data_param_AC[i-1]
                    prev_line = d['data'][d['subject_data']]
                    if len(prev_line['code']) <= account_DB.Code.FAMILY:
                        continue

                    endRow = i - 1
                    Flg = 0

                    if prev_line['code'][account_DB.Code.FAMILY] > cur_line['code'][account_DB.Code.FAMILY]:
                        # 黄色

                        # 対象の１つ前
                        start_row = startRow
                        if start_row > 0:
                            start_row -= 1
                        d = data_param_AC[start_row]
                        start_line = d['data'][d['subject_data']]

                        # 対象の１つ後
                        end_row = endRow
                        if end_row < (lastRow-1):
                            end_row += 1
                        d = data_param_AC[end_row]
                        end_line = d['data'][d['subject_data']]

                        if len(start_line['code']) > account_DB.Code.FAMILY and len(end_line['code']) > account_DB.Code.FAMILY:
                            start_code = start_line['code'][:account_DB.Code.FAMILY+1]
                            end_code = end_line['code'][:account_DB.Code.FAMILY+1]

                            for j in range(startRow, endRow+1):
                                d = data_param_AC[j]
                                cur_line = d['data'][d['subject_data']]

                                close = self.account_db.search_variety_title(cur_line['val'], ratio=0.2, code=start_code, between=end_code)
                                if close:
                                    code = self.account_db.search_variety_code(close[0], code=start_code[:account_DB.Code.VARIETY], between=end_code[:account_DB.Code.VARIETY])
                                    if not code:
                                        code = self.account_db.search_variety_code(close[0], code=start_code[:account_DB.Code.SPECIES], between=end_code[:account_DB.Code.SPECIES])
                                        if not code:
                                            code = self.account_db.search_variety_code(close[0], code=start_code[:account_DB.Code.GENUS], between=end_code[:account_DB.Code.GENUS])
                                            if not code:
                                                code = self.account_db.search_variety_code(close[0], code=start_code[:account_DB.Code.FAMILY], between=end_code[:account_DB.Code.FAMILY])


                                    cur_line['revise'] = close
                                    cur_line['code'] = code
                                    code_title = self.account_db.to_title_text(code)
                                    cur_line['code_title'] = code_title

                                aaa = 0

            beforeKey = thisKey
            # beforeKey = cur_line['code'][:account_DB.Code.FAMILY+1]

            if prev_page < 0:
                prev_page = d['page']

            if cur_line['code'] and order != cur_line['code'][account_DB.Code.ORDER]:
                Flg = 0
                startRow = i

        # 負債の部の合計の金額＞０（負債の部計2_60_0_0_-3などvariety<=0）
        # 負債の部（負債の部2_60_0_0_-4）に金額がない、又は==0
        # 行ごと削除
        variety_4 = -1
        variety_0 = -1
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.SPECIES+1] == (2,60,0,0):
                if s['code'][account_DB.Code.VARIETY] == -4:
                    v = 0
                    for ss in d['data']:
                        if ss['type'] == v2ac.Type.AMOUNT:
                            try:
                                v = int(ss['revise'][1])
                                if v > 0:
                                    break
                            except:
                                pass
                    else:
                        variety_4 = j

                    if v > 0:
                        break

                elif s['code'][account_DB.Code.VARIETY] <= 0:
                    variety_0 = j

                if variety_0 >= 0 and variety_4 >= 0:
                    del data_param_AC[variety_4]
                    break

        # 2_30　→　2_40　最後の2_30　を2_35_0_0_0
        # 2_30が無い場合、
        # 2_20　→　2_40　最後の2_20　を2_35_0_0_0
        #2024-08-09 尚　沖田案件のためキャンセルする
        #prev_data = None
        #for j, d in enumerate(data_param_AC):
        #    s = d['data'][d['subject_data']]
        #    if s['code'][:account_DB.Code.FAMILY+1] == (2,40,):
        #        if prev_data:
        #            if prev_data['code'][:account_DB.Code.FAMILY+1] == (2,20,) or prev_data['code'][:account_DB.Code.FAMILY+1] == (2,30,):
        #                set_variety_code(s, (2,35,0,0,0))
                        # code = (2,35,0,0,0,1,)
                        # s['revise'] = [self.account_db.code_to_title(code, self.account_db.variety)]
                        # s['code'] = code
                        # code_title = self.account_db.to_title_text(code)
                        # s['code_title'] = code_title

        #        break
        #    prev_data = s
        a=9999
        # 長期借入金（流動負債）(2_40_2_0_29）→長期借入金（固定負債）(2_50_0_5_1）
        for j, d in enumerate(data_param_AC):
            if s['code'][:account_DB.Code.VARIETY+1] == (2,40,2,0,29):
                set_variety_code(s, (2,50,0,5,1))

        for j, d in enumerate(data_param_AC):
            data_list = d.get('data') if isinstance(d, dict) else None
            if (isinstance(data_list, list) and len(data_list) > 0 and isinstance(data_list[0], dict) and 'val' in data_list[0]):
                val = data_list[0]['val']
                debug_print(f'v2ac 6918 [{val}]', level=DEBUG_ROWS_INFO)
        # 営業利益（1_5）が出て来たら、雑収入（1_1_0_0_64）と収入（1_1_0_0_-9、1_1_0_0_22）は営業外収益の雑収入（1_6_0_9_1）とする
        # 経常利益（1_8）が出て来たら、雑収入（1_1_0_0_64、1_6_0_9_1）と収入（1_1_0_0_-9、1_1_0_0_22）は特別利益の雑収入（1_9_0_7_2）とする
        ac_flg=0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.FAMILY+1] == (1,5,):
                ac_flg = 1
            if ac_flg ==1:
                if s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,64) or s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,-9)  or s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,22) :
                    set_variety_code(s, (1,6,0,9,1))
            if s['code'][:account_DB.Code.FAMILY+1] == (1,8,):
                ac_flg = 2
            if ac_flg ==2:
                if s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,64) or s['code'][:account_DB.Code.VARIETY+1] == (1,6,0,9,1) or s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,-9)  or s['code'][:account_DB.Code.VARIETY+1] == (1,1,0,0,22) :
                    set_variety_code(s, (1,9,0,7,2))

        # 雑収入（1_9_0_7_2）の次に（1_6）が出て来た場合、（1_6_0_9_1）とする
        ac_flg,num_j=0,0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.VARIETY+1] == (1,9,0,7,2):
                num_j=j
            if j==num_j+1:
                if s['code'][:account_DB.Code.FAMILY+1] == (1,6,):
                    ac_flg =1
                    break
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if j==num_j and ac_flg==1:
                set_variety_code(s, (1,6,0,9,1))
                
        # 期首棚卸高が期末棚卸高になっている修正
        ac_flg=0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.GENUS+1] == (1,2,1):
                ac_flg = 1
            if  ac_flg ==0 and s['code'][:account_DB.Code.GENUS+1] == (1,2,3):
                set_variety_code(s, (1,2,1,0,5))

        # 無形固定資産2_20_2_0_0が２つある場合、最初を有形固定資産2_20_1_0_0に置き換える
        ac_count,get_j=0,0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.VARIETY+1] == (2,20,2,0,0):
                ac_count += 1
                if ac_count==1:
                    get_j=j
            if ac_count>1:
                break
        if ac_count==2:
            print('data_param_AC[get_j]1',data_param_AC[get_j])
            d=data_param_AC[get_j]
            s = d['data'][d['subject_data']]
            set_variety_code(s, (2,20,1,0,0))
            # print('data_param_AC[get_j]2',data_param_AC[get_j])
        #たな卸資産関係の勘定科目が１回のみ出現場合、合計科目⇒普通科目2_10_3_1_2
        ac_count,get_j=0,0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.SPECIES+1] == (2,10,3,1):
                ac_count += 1
                if ac_count==1:
                    get_j=j
            if ac_count>1:
                break
        if ac_count==1:
            d=data_param_AC[get_j]
            s = d['data'][d['subject_data']]
            if s['code'][account_DB.Code.VARIETY] <=0 :
                set_variety_code(s, (2,10,3,1,2))
        #預り金#######################
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.VARIETY+1] == (2,40,3,20,0):
                set_variety_code(s, (2,40,3,20,1))
                break
        #繰延資産2_20_3_0_45⇒2_30_0_0_0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.VARIETY+1] == (2,20,3,0,45):
                set_variety_code(s, (2,30,0,0,0))
        #繰延資産　2_20_1_1_4が固定資産合計2_20_0_0_-1の後に出て来た場合、繰延資産　2_30_0_0_27に
        ac_count=0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.SPECIES+1] == (2,20,0,0) and s['code'][account_DB.Code.VARIETY] <=0 and ac_count==0:
                ac_count=1
            if ac_count==1 and s['code'][:account_DB.Code.VARIETY+1] == (2,20,1,1,4):
                set_variety_code(s, (2,30,0,0,27))
                break
        #繰延資産2_30_0_0_0の後に長期前払費用2_20_3_5_1、2_20_2_0_4が出て来た場合2_30_0_0_11に、賃借権2_20_2_0_12が出て来た場合2_30_0_0_24
        ac_count=0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.FAMILY+1] == (2,30,) and ac_count==0:
                ac_count=1
            if (ac_count==1 and s['code'][:account_DB.Code.VARIETY+1] == (2,20,3,5,1)) or (ac_count==1 and s['code'][:account_DB.Code.VARIETY+1] == (2,20,2,0,4)) :
                set_variety_code(s, (2,30,0,0,11))
            if (ac_count==1 and s['code'][:account_DB.Code.VARIETY+1] == (2,20,2,0,12)) :
                set_variety_code(s, (2,30,0,0,24)) 
        # 出資金（無形固定資産）2_20_2_9_19　⇒（投資その他）2_20_3_2_1        
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if (s['code'][:account_DB.Code.VARIETY+1] == (2,20,2,9,19)) :
                set_variety_code(s, (2,20,3,2,1))      
                break
        # 保険積立金（無形固定資産）2_20_2_9_20⇒保険積立金（投資その他）2_20_3_3_3
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if (s['code'][:account_DB.Code.VARIETY+1] == (2,20,2,9,20)) :
                set_variety_code(s, (2,20,3,3,3))      
                break

        #計（流動負債）2_40_0_0_-3の後に短期借入金2_40_2_0_1、長期借入金2_40_2_0_29、役員借入金2_40_2_0_5があった場合
        ac_count=0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.SPECIES+1] == (2,40,0,0) and s['code'][account_DB.Code.VARIETY] <=0 and ac_count==0:
                ac_count=1
            if ac_count==1 and s['code'][:account_DB.Code.VARIETY+1] == (2,40,2,0,1):
                set_variety_code(s, (2,50,0,5,29))
            if ac_count==1 and s['code'][:account_DB.Code.VARIETY+1] == (2,40,2,0,29):
                set_variety_code(s, (2,50,0,5,1))
            if ac_count==1 and s['code'][:account_DB.Code.VARIETY+1] == (2,40,2,0,5):
                set_variety_code(s, (2,50,0,9,2))

        ## 短期借入金2_50_0_5_29が固定負債より前の場合、短期借入金2_40_2_0_1に修正
        ac_count=0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.SPECIES+1] == (2,50,0,0)  and ac_count==0:
                ac_count=1
            if ac_count==0 and s['code'][:account_DB.Code.VARIETY+1] == (2,50,0,5,29):
                set_variety_code(s, (2,40,2,0,1))
        # 固定負債が出てこない場合、短期借入金2_40_2_0_1に修正　20240801
        ac_count=0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.SPECIES+1] == (2,50,0,0) :
                ac_count = 1
                break
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]    
            if ac_count==0 and s['code'][:account_DB.Code.VARIETY+1] == (2,50,0,5,29):
                set_variety_code(s, (2,40,2,0,1))

        # #
        # #長期借入金　2_40_2_0_29が流動負債合計　2_40_0_0_-1の後に出てきたら、長期借入金　2_50_0_5_1に
        # ac_count=0
        # for j, d in enumerate(data_param_AC):
        #     s = d['data'][d['subject_data']]
        #     if s['code'][:account_DB.Code.SPECIES+1] == (2,40,0,0) and s['code'][account_DB.Code.VARIETY] <=0 and ac_count==0:
        #         ac_count=1
        #     if ac_count==1 and s['code'][:account_DB.Code.VARIETY+1] == (2,40,2,0,29):
        #         set_variety_code(s, (2,50,0,5,1))
        #         break

        #車両運搬具####################
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.VARIETY+1] == (2,20,1,9,0):
                set_variety_code(s, (2,20,1,9,6))
                break
        #外注費####################
        gaityu_index=-1
        kanjo123_index=0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if len(s['code'])>5 and s['code'][0] == 2 and s['code'][1] == 20 and s['code'][2] == 1 and  s['code'][3] == 9 and  s['code'][4] == 0:
                s['code']=(2,20,1,9,6,1)
            if len(s['code'])>5 and s['code'][0] == 2 and s['code'][1] == 40 and s['code'][2] == 3 and  s['code'][3] == 20 and  s['code'][4] == 0:
                s['code']=(2,40,3,20,1,1)
            if len(s['code'])>5 and s['code'][0] == 1 and s['code'][1] == 2 and s['code'][2] == 2 and  s['code'][3] == 1 and  s['code'][4] == 1:
                if gaityu_index==-1 :
                    gaityu_index=j
            if len(s['code'])>5 and s['code'][0] == 1 and s['code'][1] == 2 and s['code'][2] == 3 :
                if kanjo123_index==0 :
                    kanjo123_index=j
        if gaityu_index != -1:
            for j, d in enumerate(data_param_AC):
                s = d['data'][d['subject_data']]
                if gaityu_index == j:
                    s['code']=(1,2,2,0,253,1)
                    s['code_title']="1[損益計算書]:2[売上原価]:2[当期仕入高]:0[当期商品仕入高]:253[外注費]"
        # 利益準備金 2_70_2_1_4⇒2_70_3_1_1
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.VARIETY+1] == (2,70,3,1,1):
                set_variety_code(s, (2,70,2,1,4))
                break
        #利益剰余金（中分類）2_70_3に所属する（小分類）が複数ある場合の利益剰余金は合計科目の利益剰余金を選択する
        # 資本金が２つ並ぶ時に、２つとも資本金（合計）2_70_1_0_0_合計が選ばれないように
        ac_count,shihon_count=0,0
        riekijouyo_futu,shihon=-1,-1
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.GENUS+1] == (2,70,3):
                ac_count += 1
            if s['code'][:account_DB.Code.VARIETY+1] == (2,70,3,2,13):
                riekijouyo_futu=j
            # if s['code'][:account_DB.Code.VARIETY+1] == (2,70,1,0,0):
            #     shihon_count+=1
            #     if shihon_count==2:
            #         shihon=j

        if ac_count>1 and riekijouyo_futu>0:
            d=data_param_AC[riekijouyo_futu]
            s = d['data'][d['subject_data']]
            set_variety_code(s, (2,70,3,0,0))

        # 負債の部合計2_60_0_0_0を資産の部合計2_35に誤読#########
        ac_count=0
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.FAMILY+1] == (2,70,):
                ac_count=j-1
                break
        ## 直前の行に'code'があるか判定
        for j,d in enumerate(data_param_AC):
            if j==ac_count:
                s = d['data'][d['subject_data']]
                if (s['code']):
                    if "合計" in s['val']:
                        set_variety_code(s, (2,60,0,0,0))
                        break
                else:
                    ac_count-=1
                    break
        ### 直前の行に'code'がない場合、もう1行遡って判定
        for j,d in enumerate(data_param_AC):
            if j==ac_count:
                s = d['data'][d['subject_data']]
                if (s['code']):
                    if "合計" in s['val']:
                        set_variety_code(s, (2,60,0,0,0))
                        break

                # if s['code'] !=():
                #     print s['code']
                # else:
                #     print("empty!!!")

        # 純資産の部の誤読
        # 新株予約権(2,90)または非支配株主持ち分(2,100)がある場合その次の行をj_strとする
        # j_str以降で最終行またはorderが変わる直前をj_endとする。
        # j_end - j_str ==2の時で、j_str!=(2,110)の場合、 (2,110,0,0,0)をセット
        # j_end!=(2,120)の場合、 (2,120,0,0,0)をセット
        ac_acount,page_no,chk_flg,j_str,j_end=0,0,0,0,0
        for j,d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if s['code'][:account_DB.Code.FAMILY+1] >= (2,90,) and s['code'][:account_DB.Code.FAMILY+1] <= (2,100,):
                j_str=j
                chk_flg=1
            if (chk_flg ==1 and s['code'][:account_DB.Code.ORDER+1]== (1,)):
                j_end=j-1
                break
            elif chk_flg == 1 and j == len(data_param_AC) - 1:
                j_end = j
        if j_end-j_str==2:
            s=data_param_AC[j_end-1]['data'][d['subject_data']]
            if s['code'][:account_DB.Code.FAMILY+1] != (2,110,):
                set_variety_code(s, (2,110,0,0,0))
            s=data_param_AC[j_end]['data'][d['subject_data']]
            if s['code'][:account_DB.Code.FAMILY+1] != (2,120,):
                set_variety_code(s, (2,120,0,0,0))

        for j, d in enumerate(data_param_AC):
            data_list = d.get('data') if isinstance(d, dict) else None
            if (isinstance(data_list, list) and len(data_list) > 0 and isinstance(data_list[0], dict) and 'val' in data_list[0]):
                val = data_list[0]['val']
                debug_print(f'v2ac 7190 [{val}]', level=DEBUG_ROWS_INFO)
        # 雑費が複数ある時の処理
        zappi = []
        for j, d in enumerate(data_param_AC):
            s = d['data'][d['subject_data']]
            if len(s['revise']) > 0:
                if s['revise'][0] == '雑費':
                    zappi.append({'row':d, 'ratio':s['ratio']})
                    aaa = 0

        if len(zappi) >= 2:
            zappi[-1]['ratio'] += 0.5 # 一番下を優先
            zappi_sorted = sorted(zappi, key=lambda x:x['ratio'], reverse=True)
            for i in range(1,len(zappi_sorted)):
                z = zappi_sorted[i]['row']
                s = z['data'][z['subject_data']]
                swapped = False
                for j in range(1, len(s['revise'])):
                    for k in range(i):
                        zz = zappi_sorted[k]['row']
                        ss = zz['data'][zz['subject_data']]
                        if ss['revise'][0] != s['revise'][j]:
                            s['revise'][0], s['revise'][j] = s['revise'][j], s['revise'][0]
                            swapped = True
                            break
                    else:
                        aaa = 0
                    if swapped:
                        break
            for i in range(1,len(zappi_sorted)):
                z = zappi_sorted[i]['row']
                s = z['data'][z['subject_data']]
                code = self.account_db.search_variety_code(s['revise'][0])
                s['code'] = code
                if code:
                    code_title = self.account_db.to_title_text(s['code'])
                    s['code_title'] = code_title

                # if len(s['revise']) >= 2:
                #     s['revise'][0], s['revise'][1] = s['revise'][1], s['revise'][0]
                #     code = self.account_db.search_variety_code(s['revise'][0])
                #     s['code'] = code
                #     if code:
                #         code_title = self.account_db.to_title_text(s['code'])
                #         s['code_title'] = code_title

                aaa = 0

            # zappi_sorted = sorted(zappi, key=lambda x:x['ratio'], reverse=True)
            # for j in range(1,len(zappi_sorted)):
            #     z = zappi_sorted[j]['row']
            #     s = z['data'][z['subject_data']]
            #     if len(s['revise']) >= 2:
            #         s['revise'][0], s['revise'][1] = s['revise'][1], s['revise'][0]
            #         code = self.account_db.search_variety_code(s['revise'][0])
            #         s['code'] = code
            #         if code:
            #             code_title = self.account_db.to_title_text(s['code'])
            #             s['code_title'] = code_title

            #     aaa = 0

        # 置き換えルール col_no列表記 the_code の時に rep_code
        def replace_code_plural_col(data, col_no, the_code, rep_code):
            code_len = len(the_code)
            for j, d in enumerate(data):
                s = d['data'][d['subject_data']]
                if s['code'] and s['code'][:code_len] == the_code:
                    set_variety_code(s, rep_code, insert_revise=True)

        # replace_code_plural_col(data_param_AC, 2, (1,1,0,0,0), (1,1,0,0,1))


        # 置き換えルール revise[0]がrevise の時に to_revise_codeを採用して候補にadd_revise
        def replace_code_candidate(data, revise, to_revise_code, add_revise):
            aaa = 0
            for j, d in enumerate(data):
                s = d['data'][d['subject_data']]
                if s['revise'] and s['revise'][0] == revise:
                    set_variety_code(s, to_revise_code)
                    s['revise'] += add_revise # revise + add_revise で['revise']は２つ以上になり候補がto_revise_codeでは無いものになる
                    break

        replace_code_candidate(data_param_AC, '当期商品仕入高', (1,2,2,0,1), ['当期商品仕入高'])

        # 置き換えルール 読み込んだ値がval で　次の行が next であれば to
        def replace_code_next_code(data, val, code):
            for j, d in enumerate(data[:-1]):
                s = d['data'][d['subject_data']]
                n = data[j+1]['data'][data[j+1]['subject_data']]
                if s['val'] == val:
                    aaa = 0
                    for c in code:
                        if n['code'][:len(c['next'])] == c['next']:
                            set_variety_code(s, c['to'])
                            break

                break # 先頭行のみ

        # 置き換えルール 先頭で読み込んだ値がval で　次の行が next であれば to
        replace_code_next_code(data_param_AC, '動', [{'next':(2,10), 'to':(2,10,0,0,0)},{'next':(2,40), 'to':(2,40,0,0,0)},{'next':(1,1), 'to':(1,1,0,0,43)}])

        # 置き換えルール 直前before_codeと直後after_codeの間にthe_codeがあればrep_codeに置き換え
        def replace_code_just_between_code(data, the_code, rep_code, before_code, after_code):
            before_code_len = len(before_code)
            after_code_len = len(after_code)

            _after_code  = after_code + ((0,) * (account_DB.Code.VARIETY+1-after_code_len))
            after_code_val   = int(account_DB.COMBINE_CODE.format(  _after_code[account_DB.Code.ORDER],  _after_code[account_DB.Code.FAMILY],  _after_code[account_DB.Code.GENUS],  _after_code[account_DB.Code.SPECIES]))

            for j, d in enumerate(data[1:-1]):
                s = d['data'][d['subject_data']]

                if s['code'][:account_DB.Code.VARIETY+1] == the_code:
                    if data[j-1]['data'][data[j-1]['subject_data']]['code'][:before_code_len] == before_code:
                        next_code   = data[j+1]['data'][data[j+1]['subject_data']]['code']
                        next_code_val   = int(account_DB.COMBINE_CODE.format( next_code[account_DB.Code.ORDER],  next_code[account_DB.Code.FAMILY],  next_code[account_DB.Code.GENUS],  next_code[account_DB.Code.SPECIES]))

                        if after_code_val <= next_code_val:
                            set_variety_code(s, rep_code)

        # 前が2_35 かつ 次が 2_40以上
        # 流動資産2_10_0_0_0 -> 2_40_0_0_0
        replace_code_just_between_code(data_param_AC, (2,10,0,0,0), (2,40,0,0,0), (2,35), (2,40))

        # 置き換えルール before_codeとafter_codeの間にthe_codeがあればrep_codeに置き換え
        def replace_code_between_code(data, the_code, rep_code, before_code, after_code):
            before_code_len = len(before_code)
            after_code_len = len(after_code)

            _before_code  = before_code + ((0,) * (account_DB.Code.VARIETY+1-before_code_len))
            before_code_val   = int(account_DB.COMBINE_CODE.format(  _before_code[account_DB.Code.ORDER],  _before_code[account_DB.Code.FAMILY],  _before_code[account_DB.Code.GENUS],  _before_code[account_DB.Code.SPECIES]))
            _after_code  = after_code + ((0,) * (account_DB.Code.VARIETY+1-after_code_len))
            after_code_val   = int(account_DB.COMBINE_CODE.format(  _after_code[account_DB.Code.ORDER],  _after_code[account_DB.Code.FAMILY],  _after_code[account_DB.Code.GENUS],  _after_code[account_DB.Code.SPECIES]))

            on = False
            for j, d in enumerate(data):
                s = d['data'][d['subject_data']]
                data_code   = s['code']
                # data_code   = data[j]['data'][data[j]['subject_data']]['code']
                data_code_val   = int(account_DB.COMBINE_CODE.format( data_code[account_DB.Code.ORDER],  data_code[account_DB.Code.FAMILY],  data_code[account_DB.Code.GENUS],  data_code[account_DB.Code.SPECIES]))
                if on == False:
                    if data_code_val >= before_code:
                        on = True
                else:
                    if data_code_val >= after_code:
                        break
                    if s['code'][:account_DB.Code.VARIETY+1] == the_code:
                        set_variety_code(s, rep_code)

        # 置き換えルール reference_code(after_flag True:以降 or False:以前)にthe_codeがあればrep_codeに置き換え
        def replace_code_reference_code(data, the_code, rep_code, after_flag, reference_code, reference_code2=None):
            reference_code_len = len(reference_code)
            on = False
            for j, d in enumerate(data):
                s = d['data'][d['subject_data']]
                if on == False:
                    if s['code'][:reference_code_len] == reference_code:
                        on = True
                    elif reference_code2 != None and s['code'][:reference_code_len] == reference_code2:
                        on = True

                if after_flag == True and on == False:
                    continue
                if after_flag == False and on == True:
                    break

                if s['code'][:account_DB.Code.VARIETY+1] == the_code:
                    set_variety_code(s, rep_code)

        # def replace_code_reference_code(data, the_code, rep_code, after_flag, reference_code, reference_code2=None):
        #     reference_code_len = len(reference_code)
        #     on = False
        #     for j, d in enumerate(data):
        #         s = d['data'][d['subject_data']]
        #         if on == False:
        #             if s['code'][:reference_code_len] == reference_code:
        #                 on = True
        #             elif reference_code2 != None and s['code'][:reference_code_len] == reference_code2:
        #                 on = True
        #             continue

        #         if s['code'][:account_DB.Code.VARIETY+1] == the_code:
        #             set_variety_code(s, rep_code)

        # 2_35以降
        # 流動資産2_10_0_0_0 -> 2_40_0_0_0
        # replace_code_reference_code(data_param_AC, (2,10,0,0,0), (2,40,0,0,0), True, (2,35), (2,40))

        # 置き換えルール
        # 2_35, 2_40以降
        # 預金 2_10_1_1_8 -> 預り金2_40_0_20_0
        replace_code_reference_code(data_param_AC, (2,10,1,1,8), (2,40,0,20,1), True, (2,35), (2,40))
        # 1_2_2以降
        # 期首棚卸高1_2_1_0_5 -> 期末棚卸高1_2_3_0_5
        #replace_code_reference_code(data_param_AC, (1,2,1,0,5), (1,2,3,0,5), True, (1,2,2))

        # # 2_35, 2_40以降
        # # 出資金 2_20_3_2_1 -> 資本金2_70_1_0_0
        # replace_code_reference_code(data_param_AC, (2,20,3,2,1), (2,70,1,0,0), True, (2,35), (2,40))

        # # 2_35, 2_40以前
        # # 資本金2_70_1_0_0 -> 出資金 2_20_3_2_1
        # replace_code_reference_code(data_param_AC, (2,70,1,0,0), (2,20,3,2,1), False, (2,35), (2,40))

        # on = False
        # for j, d in enumerate(data_param_AC):
        #     s = d['data'][d['subject_data']]
        #     if s['code'][:account_DB.Code.GENUS+1] == (1,2,2):
        #         on = True
        #         continue

        #     if on == False:
        #         continue

        #     if s['code'][:account_DB.Code.VARIETY+1] == (1,2,1,0,5):
        #         set_variety_code(s, (1,2,3,0,5))

        debug_print( 'subject_cols -->',level=DEBUG_ROWS_INFO)
        for page, c in enumerate(subject_cols):
            debug_print( '{}:{}'.format(page,c), level=DEBUG_ROWS_INFO)
        debug_print( 'subject_cols <--',level=DEBUG_ROWS_INFO)
        debug_print( 'amount_cols -->',level=DEBUG_ROWS_INFO)
        for page, c in enumerate(amount_cols):
            debug_print( '{}:{}'.format(page,c), level=DEBUG_ROWS_INFO)
        debug_print( 'amount_cols <--',level=DEBUG_ROWS_INFO)
        debug_print( 'subject_amount_cols -->',level=DEBUG_ROWS_INFO)
        for page, c in enumerate(subject_amount_cols):
            debug_print( '{}:{}'.format(page,c), level=DEBUG_ROWS_INFO)
        debug_print( 'subject_amount_cols <--',level=DEBUG_ROWS_INFO)

        debug_print( 'cols_cnt -->',level=DEBUG_ROWS_INFO)
        for page, c in enumerate(cols_cnt):
            debug_print( '{}:{}'.format(page,c), level=DEBUG_ROWS_INFO)
        debug_print( 'cols_cnt <--',level=DEBUG_ROWS_INFO)

        debug_print( 'col_type -->',level=DEBUG_ROWS_INFO)
        for c in col_type:
            debug_print( '{}'.format(c), level=DEBUG_ROWS_INFO)
        debug_print( 'col_type <--',level=DEBUG_ROWS_INFO)

        # debug_print( 'result_data_param -->',level=DEBUG_ROWS_INFO)
        # for d in data_param:
        #     debug_print( '{}, {}, {}:{}{}'.format(d['page'],d['block'],d['score'], 'HEADER-->' if d['score']>0x00 else '', 'OK' if d['score']>HEADER_SCORE_Kamoku else 'NO'), level=DEBUG_ROWS_INFO)
        #     for s in d['data']:
        #         if s['type'] == v2ac.Type.SUBJECT:
        #             debug_print( '>>> {}'.format(s['code_title'] if 'code_title' in s else '-1[未登録]'), level=DEBUG_ROWS_INFO)

        #         debug_print( '{} {}: {}'.format(s['OK'],s['col'],[s['type'], s['val'],'' if 'revise' not in s else s['revise']]), level=DEBUG_ROWS_INFO)
        #         # debug_print( ' {}: chars{}'.format([s['type'],s['val'],'' if 'revise' not in s else s['revise']], [] if 'chars' not in s else [c['text'] for c in s['chars']]), level=DEBUG_ROWS_INFO)
        # debug_print( 'result_data_param <--',level=DEBUG_ROWS_INFO)

        debug_print( 'paper_info -->',level=DEBUG_ROWS_INFO)
        for page, c in enumerate(paper_info):
            debug_print( '{}:{}'.format(page,c), level=DEBUG_ROWS_INFO)
        debug_print( 'paper_info <--',level=DEBUG_ROWS_INFO)

        debug_print( 'result_data_param_AC -->',level=DEBUG_ROWS_INFO)
        for d in data_param_AC:
            debug_print( '<{}> {}, {}, {}, {}:{}{} {} amount_cnt:{}'.format('x' if d['type'] & v2ac.Type.REMOVE else ' ', d['page'],d['block'],d['score'], d['type'], 'HEADER-->' if d['score']>0x00 else '', 'OK' if d['score']>HEADER_SCORE_Kamoku else 'NO', d['title_code'] if 'title_code' in d else '', d['amount_cnt']), level=DEBUG_ROWS_INFO)
            for s in d['data']:
                if s['type'] == v2ac.Type.SUBJECT:
                    debug_print( '>>> {}'.format(s['code_title'] if 'code_title' in s else '-1[未登録]'), level=DEBUG_ROWS_INFO)

                debug_print( '{}({}):<{}> {}: {}'.format(d['page'],s['amount_no'] if 'amount_no' in s else '-',s['OK'],s['col'],[s['type'], s['val'],'' if 'revise' not in s else s['revise']]), level=DEBUG_ROWS_INFO)
                # debug_print( ' {}: chars{}'.format([s['type'],s['val'],'' if 'revise' not in s else s['revise']], [] if 'chars' not in s else [c['text'] for c in s['chars']]), level=DEBUG_ROWS_INFO)
        debug_print( 'result_data_param <--',level=DEBUG_ROWS_INFO)

        debug_print( 'closing_date:{}'.format(closing_date), level=DEBUG_ROWS_INFO)

        debug_print( 'do_analyze -->',level=DEBUG_ROWS_INFO)
        for d in data:
            msg = '{}, {}'.format(d[0],d[1])
            for s in d[2:]:
                msg += r', "{}"'.format(s)

            debug_print( msg, level=DEBUG_ROWS_INFO)
            # debug_print( d, level=DEBUG_ROWS_INFO)
        debug_print( 'do_analyze <--',level=DEBUG_ROWS_INFO)

        self.result_data = data
        self.result_data_param = data_param_AC #data_param

        self.paper_info = paper_info
        self.closing_date = closing_date

        return

    def get_period_col(self, d):
        this_year_col = 0
        pre_year_col  = -1

        if d['amount_cnt'] == 2:
            if self.period_order == v2ac.PeriodOrder.CURRENT_PREV:
                    # 勘定科目:金額(今期):金額(前期)
                    pre_year_col  = 1
                    this_year_col = 0
            elif self.period_order == v2ac.PeriodOrder.PREV_CURRENT:
                    # 勘定科目:金額(前期):金額(今期)
                    pre_year_col  = 0
                    this_year_col = 1
        elif d['amount_cnt'] == 3:
            if self.period_order == v2ac.PeriodOrder.CURRENT_PREV_X_X:
                if self.ratio_column == True:
                    # 勘定科目:金額(今期):金額(前期):金額(差額)
                    pre_year_col  = 1
                    this_year_col = 0
            else:
                if self.ratio_column == True:
                    # 勘定科目:金額(前期):金額(今期):金額(差額)
                    pre_year_col  = 0
                    this_year_col = 1

        elif d['amount_cnt'] == 4:
            if self.period_order == v2ac.PeriodOrder.CURRENT_PREV_X_X:
                if self.ratio_column == True:
                    # 勘定科目:金額(今期):構成比:金額(前期):構成比 [:金額(差額):前年比]
                    pre_year_col  = 2
                    this_year_col = 0
                else:
                    # 勘定科目:金額(今期):金額(前期):金額(差額):前年比
                    pre_year_col  = 1
                    this_year_col = 0
            else:
                if not self.ratio_pt_col[0] and not self.ratio_pt_col[1] and not self.ratio_pt_col[2] and self.ratio_pt_col[3]:
                    # 見出し行が読めていない可能性から推測
                    # 勘定科目:金額(今期):金額(前期):金額(差額):前年比
                    pre_year_col  = 1
                    this_year_col = 0
                else:
                    # 4 -> 勘定科目:金額(前期):構成比:金額(今期):構成比
                    pre_year_col  = 0
                    this_year_col = 2

        elif d['amount_cnt'] == 5:
            if self.period_order == v2ac.PeriodOrder.CURRENT_PREV_X_X:
                if self.ratio_column == True:
                    # 勘定科目:金額(今期):構成比:金額(前期):構成比 :金額(差額)[:前年比]
                    pre_year_col  = 2
                    this_year_col = 0
                else:
                    # 勘定科目:金額(前期):構成比:金額(今期):構成比 :金額(差額)[:前年比]
                    pre_year_col  = 0
                    this_year_col = 2
            else:
                # 勘定科目:金額(前期):構成比:金額(今期):構成比 :金額(差額)[:前年比]
                pre_year_col  = 0
                this_year_col = 2

        elif d['amount_cnt'] == 6:
            if self.period_order == v2ac.PeriodOrder.CURRENT_PREV_X_X:
                pre_year_col  = 2
                this_year_col = 0
            else:
                # 6 -> 勘定科目:金額(前期):構成比:金額(今期):構成比:金額(増減):増加率
                pre_year_col  = 0
                this_year_col = 2

        return pre_year_col, this_year_col

    # 派生クラス固有ID
    def special_id_find(self, texts, papers, conditions_id, N, page, search, search_part_flag, keyword_list, key_grp_bounds, keyword_opt):
        if conditions_id == 100:

            self.do_analyze(papers)

            # CSV
            # self.to_csv()

            # デバッグ用CSV
            # self.to_param_csv()
            # self.to_cd_csv()

            # self.to_result_csv()

            # JSON(データの書き換えを行う事がある)
            block_result = self.to_json()

            # デバッグ用CSV
            self.to_result_csv()

            return None, None, None, None, block_result
        return None

    # def special_id_found_inbounds(self, texts, papers, conditions_id, N, page, search, search_part_flag, keyword_list, key_grp_bounds, keyword_opt, row, bound, text_page_no):
    #     # found_text, keyword_text, text_bounds, keyword_bounds
    #     return None

    # 以下は処理しない
    def find_table(self, rows, file_name, img, no): # ?
        return
    def find_nearest_column(self, texts, row, regex_ret, type, keyword_opt, image):
        return None, None, None, None
    # def find_vertical_line(self, file_name, img_org, bounds, img_width=True):
    #     return []
    def collect_article_title(self, words, article_no):
        return [], 0
    def decision_article(self):
        return

    # def _split_words(self, words, no, loop):

    #     if loop == 0:
    #         extacted_words = []

    #         page = '0'
    #         page_no = 0
    #         i = 0
    #         clear_img = None
    #         debug_print( 'VLINE -->',level=DEBUG_ROWS_INFO)
    #         for w in words:
    #             if page != w['page']:
    #                 page = w['page']
    #                 page_no = int(page)-1

    #                 # self.clear_char_area(self.papers[page_no]['texts'],self.papers[page_no]['image'],self.papers[page_no]['path'])
    #                 clear_img = self.clear_char_area(self.papers[page_no]['characters'],self.papers[page_no]['image'],self.papers[page_no]['path'])
    #                 if clear_img is None:
    #                     clear_img = self.papers[page_no]['image']

    #                 i = 0
    #             else:
    #                 i += 1
    #             # 縦線を探す
    #             b = copy.deepcopy(w['bounds'])
    #             b.expand_wh(0,int(b.get_height()*0.2))
    #             # b.expand_wh(0,b.get_height())
    #             vline = self.find_vertical_line('{}_{:02}.jpg'.format(self.papers[page_no]['path'],i), clear_img, b, img_width=True)
    #             # vline = self.find_vertical_line('{}_{:02}.jpg'.format(self.papers[page_no]['path'],i), self.papers[page_no]['image'], b, img_width=True)

    #             debug_print( '\n<{}> {}'.format(w['bounds'].to_string(),w['text']),level=DEBUG_ROWS_INFO)
    #             debug_print( vline,level=DEBUG_ROWS_INFO)

    #             if vline:
    #                 left = 0
    #                 keyword_col = -1
    #                 vcnt = []
    #                 for col, right in enumerate(vline):
    #                     text, chars, bounds = self.get_chars_between_LR_text(w['chars'], left, right)
    #                     if text:
    #                         # extacted_words.append({'col':col, 'text':{'text':text, 'chars':chars, 'bounds':bounds, 'page':w['page']}})
    #                         ew = {'done':w['done'], 'page':w['page'], 'article_no':w['article_no'], 'article_row':w['article_row'], 'serial_row':chars[0]['row']['serial_row'], 'row_no':w['row_no'], 'block':w['block'], 'type':WORD_SPLIT_OPT_NON, 'text':text, 'bounds':bounds, 'chars':chars}
    #                         extacted_words.append(ew)
    #                         aaa = 0
    #                     vcnt.append(len(text))

    #                     left = right

    #                 vcnt2 = []
    #                 z = True
    #                 for v in vcnt:
    #                     if z == True:
    #                         if v != 0:
    #                             z = False
    #                             vcnt2.append(v)
    #                     else:
    #                         vcnt2.append(v)

    #                 debug_print( '{} -> {}'.format(vcnt,vcnt2),level=DEBUG_ROWS_INFO)

    #             else:
    #                 extacted_words.append(w)

    #             words = extacted_words

    #         debug_print( 'VLINE <--',level=DEBUG_ROWS_INFO)

    #     return super().split_words(words, no, loop)

'''
excelでcsv : SJISで保存 -> utf-8 に変換

sqlite3 v2ac.db
CREATE TABLE type(id INTEGER, item TEXT);
CREATE TABLE family (type_id INTEGER, id INTEGER, item TEXT);
CREATE TABLE genus  (type_id INTEGER, family_id INTEGER, id INTEGER, item TEXT);
CREATE TABLE variety(type_id INTEGER, family_id INTEGER, genus_id INTEGER, id INTEGER, property INTEGER, item TEXT);
#CREATE TABLE species(type_id INTEGER, family_id INTEGER, genus_id INTEGER, id INTEGER, item TEXT);
#CREATE TABLE variety(type_id INTEGER, family_id INTEGER, genus_id INTEGER, species_id INTEGER, id INTEGER, item TEXT);
delete from variety;

.tables
.schema type
.separator ,
.import variety.csv variety

.import type.csv type
.import family.csv family
.import genus.csv genus
.import species.csv species
select * from type;
select * from family;
select * from genus;
select * from species;
select * from variety;
.q
'''

'''
        # 縦線が無い帳票で左右に分れている項目
        # 現金  123,456  買掛金  654,321 -> 現金  123,456 | 買掛金  654,321

        if len(col_list) <= 2:
            table_on = False
            for r in vrows:
                found = list(subject_amount_pat.finditer(r['row']['text']))
                if len(found) >= 2:
                    close = []
                    for g in found:
                        c = self.account_db.search_variety_title(g.group(1))
                        if c:
                            close.append({'ret':g, 'close':c} )

                    if len(close) >= 2:
                        # 同じ行に2個以上の勘定科目
                        ret = [close[0]['ret'], close[1]['ret']]
                        amount  = [ret[0].group(2), ret[1].group(2)]
                        if amount[0] and amount[1]:

                            st_amount = ret[0].start(2)
                            ed = ret[0].end(2)-1
                            st = ret[1].start(1)
                            if ed != st:

                                # 勘定科目の前の数字が金額か?
                                # 現金  123,456  (1) 買掛金  654,321
                                x = r['row']['chars'][st]['bounds'].get_left()  # 勘定科目の前
                                for i in reversed(range(st_amount, st)):
                                    h = r['row']['chars'][i]['bounds'].get_height()
                                    c = r['row']['chars'][i]['text']
                                    diff = x - r['row']['chars'][i]['bounds'].get_right() # 金額の後
                                    d = c.isdigit()
                                    if c.isdigit() and diff >= h: # 幅であるが高さを閾に使う
                                        if i != ed:
                                            aaa = 0
                                        ed = i
                                        break
                                    x = r['row']['chars'][i]['bounds'].get_left()  # 勘定科目の前

                                x1 = r['row']['chars'][ed]['bounds'].get_right() # 金額の後
                                x2 = r['row']['chars'][st]['bounds'].get_left()  # 勘定科目の前
                                cx = int((x1+x2)/2)

                                # 縦線を探す
                                for col in col_list:
                                    if (col['x']-xw) <= cx <= (col['x']+xw):
                                    # if x1 < col['x'] < x2:
                                        # あった
                                        col['cnt'] += 1
                                        if col['min'] > x1:
                                            col['min'] = x1
                                        if col['max'] < x2:
                                            col['max'] = x2
                                        break
                                else:
                                    # 無いのでcol情報に追加
                                    aaa = 0
                                    if not table_on:
                                        # とりあえず先頭に挿入
                                        col_list.insert(0, {'x':cx, 'max':cx, 'min':cx, 'cnt':1, 'flags':1})
                                        table_on = True

                if table_on:
                    aaa = 0
                    for j in range(2):
                        if not r['vline'][j]:
                            r['vline'][j] = [0,width]

                        r['vline'][j].append(cx)
                        r['vline'][j].sort(key=lambda x: x)

                    aaa = 0

                aaa = 0
'''
# python /var/www/html/pys/iTaskScanPapers.py --json /home/ec2-user/data/json/v2ac.json  --pdf /home/ec2-user/data/ --dpi 400