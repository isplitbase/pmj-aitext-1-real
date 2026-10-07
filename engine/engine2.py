

# import enum
# import sys
import os
import time# import datetime
# import calendar
import gc


import re

import subprocess
import copy
import cv2
import numpy as np
from PIL import Image, ImageEnhance
# from numpy.core import numeric
# from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

# import traceback
# import math
import json
import pickle
# from collections import OrderedDict

# Imports the Google Cloud client library
from google.cloud import vision
from google.cloud.vision import types
#from google.cloud import vision_v1
#from google.cloud.vision_v1 import types
#from google.cloud.vision_v1 import AnnotateImageResponse

import util.defines
from util.defines import *
from util.utility import *
from util.coordinate import Point, Bound
import engine.pre_process_image as pre_process_image
import engine.pre_process_imag_area as pre_process_imag_area
import socket
from inspect import CO_NEWLOCALS
from PIL import Image, ImageDraw, ImageFont, ImageOps

#os.environ['http_proxy'] = 'http://ty-nlbproxy.iflex.jp.panasonic.com:8080'
#os.environ['https_proxy'] = 'http://ty-nlbproxy.iflex.jp.panasonic.com:8080'

# if AI_KERAS_PROCESS:
#     from PIL import Image
#     from PIL import ImageFile
#     import keras
#     from keras.models import load_model
#     keras_param = os.path.join(os.path.dirname(__file__),'cnn.h5')
#     keras_model = load_model(keras_param)

# # import pkg_resources, imp
# # imp.reload(pkg_resources)

# if AI_GINZA_PROCESS:
#     from engine.getContractName import getContractName, setContractNameNLP
#     # from getContractName import setContractNameNLP

# # if AI_GINZA_PROCESS:
#     import spacy
#     import ginza
#     import pkg_resources
#     packages = pkg_resources.working_set.by_key.keys()
#     nlp = spacy.load('ja_ginza_electra')
#     setContractNameNLP(nlp)

# AI関連の初期化
# プログラム起動時に一律初期化を行っていたが、メモリの消費量が大きので使う場合のみ行う
from PIL import Image
#from PIL import ImageFile
# 初期化は一度だけ
INIT_AI_KERAS = False
INIT_AI_GINZA = False
keras_model = None
nlp = None



# --- injected safety helper ---
def _code_len_ok(code, n):
    return isinstance(code, (list, tuple)) and len(code) >= n
# --- end helper ---

ENGINE_VERSION = '015-v2.base'

def init_AI_process(ai_keras_process, ai_ginza_process):
    global INIT_AI_KERAS, INIT_AI_GINZA

    if ai_keras_process and INIT_AI_KERAS == False:
        # predict_type_of_paper (図面予測)
        INIT_AI_KERAS = True # 初期化は一度だけ
        # if AI_KERAS_PROCESS:

        # from PIL import Image
        # from PIL import ImageFile
        import keras
        from keras.models import load_model
        keras_param = os.path.join(os.path.dirname(__file__),'cnn.h5')

        global keras_model
        keras_model = load_model(keras_param)

    if ai_ginza_process and INIT_AI_GINZA == False:
        #find_contract_word (形態素解析)

        INIT_AI_GINZA = True # 初期化は一度だけ
        # if AI_GINZA_PROCESS:

        from engine.getContractName import getContractName, setContractNameNLP
        # from getContractName import setContractNameNLP

        import spacy
        import ginza
        import pkg_resources
        packages = pkg_resources.working_set.by_key.keys()

        global nlp
        nlp = spacy.load('ja_ginza_electra')
        setContractNameNLP(nlp)


# 漢字　正規表現
reg_kanji = re.compile('[\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002EBEF]')
# 々, 〆, 〇（\u3005-\u3007）# 含めない？
from .engine import engine
class engine2(engine):
# class engine2(object):
    #self.inData       = {}
    #self.outData      = {}

    #self.root_str    = ''
    #self.number_of_images = 0
    #self.extension   = ''

    #self.analyze     = 'non'  # 1

    #self.format_cols = []

    #self.papers      = []

    #self.id          = 'non'
    #self.result      = -1

    #self.uri         = ''

    title       = 0
    dateofissue = '9999/99/99'
    payment     = '9999/99/99'
    desc        = ['','']
    total       = -1
    tax         = -1

    transfer    = {}
#    transfer    = ['bank':'non','branch':'non','account':'non','type':'non','name':'non']

    def init_AI(self):
        init_AI_process(self.ai_keras_process, self.ai_ginza_process)

    def __init__(self, inData, start_date, main_version='', version=ENGINE_VERSION, id='non', debug_suffix=''):
        super().__init__(start_date, main_version, version, id, debug_suffix)
        # self.start_date = start_date
        # self.main_version = main_version
        # self.version = version
        # self.id     = id
        self.ai_ginza_process = AI_GINZA_PROCESS # 形態素解析
        self.ai_keras_process = AI_KERAS_PROCESS # 図面の予測

        self.find_rows_scale = [DEFAULT_FIND_ROWS_SCALE,DEFAULT_FIND_ROWS_SCALE]
        self.save_image = True  # 読み込んだ イメージを処理が終わるまで保存

        # print( '-> engine({})'.format(self.version))
        # debug_print('-> engine({})'.format(self.version),level=DEBUG_ROWS_INFO)

        #self.inData       = {}
        self.outData      = {}

        #self.root_str    = ''
        #self.number_of_images = 0
        #self.extension   = ''

        #self.analyze     = 'non'  # 1

        #self.format_cols = []

        self.papers      = []

        self.result      = -1

        self.combine_rows = []
        self.article_rows = []

        self.inData  = inData
        # self.id     = id
        # self.uri    = inData['root_str']

        try:
            self.root_str           = inData['root_str']
        except:
            self.root_str           = ''

        try:
            self.number_of_images   = int(inData['number_of_images'])
        except:
            self.number_of_images   = 0

        # 0.9.025 : OCR をかけるページを指定
        try:
            self.open_page_list = inData['open_page_list']
        except:
            # 指定がない場合はすべて
            self.open_page_list = [str(i+1) for i in range(self.number_of_images)]

        try:
            self.extension          = inData['extension']
        except:
            self.extension = ''
        self.kojin_tri = {}
        self.in_calibration     = []

        self.in_calibration_template = False
        self.in_calibration_offset = False
        self.in_calibration_scale  = False
        self.in_calibration_non  = False

        calib_option = 'NON'

        ## 契約書 V2 バージョンはキャリブレーション処理はしないようにする
        try:
            calib_option = inData['calibration']['option']
        except:
            calib_option = ''

        if calib_option == '' or 'NON' in calib_option.upper():
            self.in_calibration_non  = True
            calib_option = 'NON'
        elif 'TEMPLATE' in calib_option.upper():
            self.in_calibration_template = True
        else:
            if 'OFFSET' in calib_option.upper():
                self.in_calibration_offset = True
            if 'SCALE' in calib_option.upper():
                self.in_calibration_scale  = True

        try:
            calib = inData['calibration']['parameter']
        except:
            calib = []

        for c in calib:
            bound = Bound(left=int(c['template'][0]),top=int(c['template'][1]),right=int(c['template'][2]),bottom=int(c['template'][3]))
            self.in_calibration.append({'file':int(c['file']), 'template':bound})


        #ll1 = [d.get('bound') for d in self.in_calibration if d.get('file') == no]
        #if len(ll1) > 0:
        #    bb1 = ll1[0]

        #offset = True if self.in_calibration_offset == True and (offset_x != 0 or offset_y != 0) else False
        #scale  = True if self.in_calibration_scale == True and (scale_x != '1.0' or scale_y != '1.0') else False

        self.out_calibration    = {}
        self.out_calibration['option'] = calib_option
        self.out_calibration['parameter'] = []

        self.calibration = []
        try:
            self.document_judgment_flag        = inData['document_judgment_flag']
        except:
            self.document_judgment_flag        = "NONE"
        try:
            self.del_line_str_right        = inData['del_line_str_right']
        except:
            self.del_line_str_right        = "NONE"
        try:
            self.special_handling        = inData['special_handling']
        except:
            self.special_handling        = "NONE"
        try:
            self.pageNumber        = inData['pageNumber']
        except:
            self.pageNumber        = "NONE"
        try:
            self.format_cols        = inData['format_info']['cols']
        except:
            self.format_cols        = []

        try:
            self.analyze    = inData['analyze']
            #if inData['analyze'] == 'get_all_text':
            #    self.analyze    = 0
            #elif inData['analyze'] == ANALYZE_analysis_by_format:
            #    self.analyze    = 1
            #else:
            #    self.analyze    = 2
        except:
            self.analyze     = ANALYZE_analysis_by_format
            #self.analyze        = 1

        try:
            character_position = inData['character_position']
        except:
            character_position = ''

        if character_position == '':
            if self.analyze == ANALYZE_get_all_character: # defalt ->
                character_position = 'BOUND,CENTER'
            else:
                character_position = 'NON'

        if 'BOUND' in character_position.upper():
            self.character_bound = True
        else:
            self.character_bound = False

        if 'CENTER' in character_position.upper():
            self.character_center = True
        else:
            self.character_center = False

        try:
            self.height_adjust  = float(inData['height_adjust'])
        except:
            self.height_adjust  = 1.0

        try:
            self.width_adjust  = float(inData['width_adjust'])
        except:
            self.width_adjust  = 1.0

        try:
            self.separators        = inData['separators']
        except:
            self.separators        = []

        self.separators_regex     = []
        for s in self.separators:
            try:
                find_option        = s['option']
            except:
                find_option        = ''

            if find_option == '':
                find_option        = 'NON'

            if 'REGEX' in find_option.upper():
            #if find_option.upper() == 'REGEX':
                keyword = s['keyword']
            else:
                keyword = regex_space(s['keyword'])

            if 'REMOVE' in find_option.upper():
                remove = True
            else:
                remove = False

            self.separators_regex.append({'keyword':keyword,'remove':remove})

        # 項目分割を無条件で行うようする
        self.separators_regex.append({'keyword':REGEX_SEARCH_DATE,'remove':False})   # 日付検索
        self.separators_regex.append({'keyword':REGEX_SEARCH_AMOUNT,'remove':False}) # 合計検索

        # itask_col_conditions_parameterの文字列オプションの前処理
        #for col in inData['format_info']['cols']:
        #    for cond in col['col_conditions']:
        #        for conds_param in cond['itask_col_conditions_parameter']:
        #            # 検索タイプオプション
        #            try:
        #                opt = conds_param['search_opt']
        #            except:
        #                opt = 'WHOLE'

        #            if 'PART' in opt.upper():
        #                search_part = True
        #            else:
        #                search_part = False

        #            conds_param['search_part'] = search_part

        # n#の処理 (グループ検索の準備)
        # keyword = 'xxx#keyword'の処理
        self.keyword_param()

        # 第ｎ条
        self.article_no = 0

        # KEYWORDの読み込み　（仮）
        self.keyword = []
        self.setup_keyword()

        #明細領域
        self.load_box_heading(inData)

    def keyword_param(self):
        self.keyword_group = []
        for col_no, col in enumerate(self.format_cols[:]):
            for cond in col['col_conditions']:
                for conds_param in cond['itask_col_conditions_parameter']:
                    try:
                        keyword  = conds_param['keyword']
                        key_grp = ''
                        conds_param['keyword_list'] = []

                        # n# conditions_id=n に強制的に書き換える #デバッグのため
                        if '#' in keyword:
                            s = keyword.split('#')
                            cond['conditions_id'] = s[0]
                            keyword = s[1]

                        # オプションの指定
                        if cond['conditions_id'].lower() == 'option':
                            # ai_ginza_process
                            m = re.search('GINZA\((.*)\)', keyword, flags=re.IGNORECASE)
                            if m is not None:
                                self.ai_ginza_process = True if m.group(1).lower() == 'on' else False

                            # ai_keras_process
                            m = re.search('KERAS\((.*)\)', keyword, flags=re.IGNORECASE)
                            if m is not None:
                                self.ai_keras_process = True if m.group(1).lower() == 'on' else False

                            # 必要ないので削除
                            del self.format_cols[col_no]
                            continue

                        if cond['conditions_id'] == '100':
                            m = re.search('frs\( *(\d+.\d+) *, *(\d+.\d+) *\)', keyword, flags=re.IGNORECASE)
                            if m is not None:
                                self.find_rows_scale[0] = float(m.group(1))*-1.0
                                self.find_rows_scale[1] = float(m.group(2))*-1.0

                        # ~オプションの保存
                        conds_param['keyword_opt']  = {'flags':'', 'text_list':['']}
                        if KEYWORD_OPT_PRIOR in keyword: # 優先単位指定
                            s = keyword.split(KEYWORD_OPT_PRIOR)
                            # conds_param['keyword_opt']['text'] = s[0]
                            conds_param['keyword_opt']['flags'] = KEYWORD_OPT_PRIOR
                            conds_param['keyword_opt']['text_list'] = s[0].split(',')
                            keyword = s[1]
                        elif KEYWORD_OPT_SPECIFIC in keyword: # 特定単位指定
                            s = keyword.split(KEYWORD_OPT_SPECIFIC)
                            # conds_param['keyword_opt']['text'] = s[0]
                            conds_param['keyword_opt']['flags'] = KEYWORD_OPT_SPECIFIC
                            conds_param['keyword_opt']['text_list'] = s[0].split(',')
                            keyword = s[1]

                        conds_param['key_grp_bounds'] = Bound()
                        # @グループ #デバッグのため
                        if '@' in keyword:
                            s = keyword.split('@')
                            keyword = s[0]
                            key_grp = s[1]
                            conds_param['key_grp'] = key_grp
                            for cat in self.keyword_group:
                                if cat['keyword'] == key_grp:
                                    break
                            else:
                                self.keyword_group.append({'keyword':key_grp, 'page':'', 'bounds':Bound(), 'conds_param':conds_param})
                        else:
                            conds_param['key_grp'] = ''

                        keyword_list = keyword.split(',')
                        if cond['conditions_id'] == '32' or cond['conditions_id'] == '33':
                            # NOTE: 32,33 甲乙丙パターンの場合に正規表現は使わない(変更する場合は注意)
                            conds_param['keyword_list'] = keyword_list
                            # for keyword in keyword_list:
                            #     conds_param['keyword_list'].append(keyword)
                        else:
                            for keyword in keyword_list:
                                conds_param['keyword_list'].append(regex_space(keyword))

                    except:
                        None

    def load_keyword(self):
        keyword = {
            'keyword': [
                { 'title': '@', 'option': 'address' },
                { 'title': '@', 'option': 'date' },
                { 'title': '@', 'option': 'yen'},
                { 'title': '@', 'option': 'area'},
                { 'title': '@', 'option': 'term_year_month'},
                { 'title': '@', 'option': 'term_month'},
                { 'title': '@', 'option': 'term_prior'},
                { 'title': '@', 'option': 'unit_unit'},
                { 'title': '@', 'option': 'unit_building'},
                { 'title': '@', 'option': 'amount' },
                { 'title': '決算報告書' },
                { 'title': '貸借対照表' },
                { 'title': '(単位:千円)' },
                { 'title': '単位:千円' },
                { 'title': '(単位:百万円)' },
                { 'title': '単位:百万円' },
                { 'title': '科目' },
                { 'title': '金額' },
                { 'title': 'その他' },
                { 'title': '投資その他の資産' },
                { 'title': '(純資産の部)' },
                { 'title': '純資産の部' },
                { 'title': '(資産の部)' },
                { 'title': '資産の部' },
                { 'title': '【流動資産】' },
                { 'title': '現金及び預金' },
                { 'title': '仮払消費税等' },
                { 'title': '未成工事支出金' },
                { 'title': '未収消費税' },
                { 'title': '流動資産合計' },
                { 'title': '資産の部合計' },
                { 'title': '(負債の部)' },
                { 'title': '負債の部' },
                { 'title': '【流動負債】' },
                { 'title': '短期借入金' },
                { 'title': '短期借り入金' },
                { 'title': '預り金' },
                { 'title': '仮受消費税等' },
                { 'title': '流動負債合計' },
                { 'title': '負債の部合計' },
                { 'title': '固定負債' },
                { 'title': '負債合計' },
                { 'title': '【株主資本】' },
                { 'title': '株主資本' },
                { 'title': '資本金' },
                { 'title': '利益剰余金' },
                { 'title': '自己株式' },
                { 'title': 'その他利益剰余金' },
                { 'title': '繰越利益剰余金' },
                { 'title': 'その他利益剰余金合計' },
                { 'title': '利益剰余金合計' },
                { 'title': '株主資本合計' },
                { 'title': '資産合計' },
                { 'title': '純資産合計' },
                { 'title': '純資産の部合計' },
                { 'title': '負債及び純資産合計' },
                { 'title': '負債・純資産合計' },
                { 'title': '【売上高】' },
                { 'title': '売上高' },
                { 'title': '売上高合計' },
                { 'title': '売上原価' },
                { 'title': '合計' },
                { 'title': '商品売上原価' },
                { 'title': '売上原価' },
                { 'title': '売上総利益金額' },
                { 'title': '販売費及び一般管理費' },
                { 'title': '販売費及び一般管理費合計' },
                { 'title': '営業損失金額' },
                { 'title': '受取利息' },
                { 'title': '雑収入' },
                { 'title': '営業外収益合計' },
                { 'title': '雑損失' },
                { 'title': '営業外費用合計' },
                { 'title': '経常損失金額' },
                { 'title': '税引前当期純損失金額' },
                { 'title': '当期純損失金額' },
                { 'title': '流動負債' }
            ]
        }

        return keyword

    def setup_keyword(self):
        # self.keyword = []

        try:
#            keyword = {'keyword':[]}
            keyword = self.load_keyword()

            #file_path = os.path.join(os.path.dirname(__file__),'keyword.json')

            #with open(file_path, mode='r') as f:
            #    keyword = json.load(f,encoding=PDF_ENCODING)

            self.keyword_title = []
            #Titleが無い場合は @ を入れておく（特に意味はないが文字数でのソートがあるので１文字)
            for k in keyword['keyword']:
                try:
                    k['title']
                except:
                    k['title'] = '@'

            ## title文字数が多い順にソート
            #keyword['keyword'].sort(key=lambda x: len(x['title']),reverse=True)

            for k in keyword['keyword']:

                try:
                    find_option = k['option']
                except:
                    find_option = ''

                if find_option == '':
                    find_option = 'NON'

                k['option'] = find_option

                k['remove'] = True if 'REMOVE' in find_option.upper() else False

                if 'REGEX' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_REGEX
                    regx_title = k['title']
                elif 'YEN' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_YEN
                    regx_title = '.'
                elif 'AMOUNT' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_AMOUNT
                    regx_title = '.'
                elif 'TEL' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_TEL
                    regx_title = '.'
                elif 'ZIP' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_ZIP
                    regx_title = '.'
                elif 'NUMBER' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_NUMBER
                    regx_title = '.'
                elif 'DATE' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_DATE
                    regx_title = '.'
                elif 'ADDR' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_ADDR
                    regx_title = '.'
                elif 'AREA' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_AREA
                    regx_title = '.'
                elif 'TERM_YEAR_MONTH' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_TERM_YEAR_MONTH
                    regx_title = '.'
                elif 'TERM_MONTH' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_TERM_MONTH
                    regx_title = '.'
                elif 'TERM_PRIOR' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_TERM_PRIOR
                    regx_title = '.'
                elif 'UNIT_UNIT' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_UNIT
                    regx_title = '.'
                elif 'UNIT_BUILDING' in find_option.upper():
                    k['option'] = WORD_SPLIT_OPT_UNIT_BUILDING
                    regx_title = '.'

                else:
                    k['option'] = WORD_SPLIT_OPT_NON
                    regx_title = regex_space2(k['title'])

                    self.keyword_title.append(k['title'])

                #regx_title = ''
                #for c in k['title']:
                #    if len(regx_title) > 0:
                #        regx_title += '[\s　]*'  #文字間のスペースを容認
                #    regx_title += c

                k['regx'] = re.compile('(.*)(' + regx_title + ')(.*)')
                #k['regx'] = re.compile(k['title'])


            # title文字数が多い順にソート
            keyword['keyword'].sort(key=lambda x:(len(x['title']), -x['option']),reverse=True)
            # keyword['keyword'].sort(key=lambda x: len(x['title']) and -x['option'],reverse=True)

            self.keyword = keyword['keyword']
            #for k in keyword['keyword']:
            #    self.keyword.append(k)

        except Exception as e:
            #print(e)
        #####except:
            None

        if DEBUG_ROWS_INFO >= DEBUG_PRINT_LEVEL:
            debug_print( 'KEYWORD -->',level=DEBUG_ROWS_INFO)
            for k in self.keyword:
                debug_print( '{} : {}'.format(k['title'],k['option']),level=DEBUG_ROWS_INFO)
            debug_print( 'KEYWORD <--',level=DEBUG_ROWS_INFO)

#        rrr = re.compile(r'([^\\￥\$＄\-―△▲\d\(]*)([\\￥\$＄\-―△▲]?[0-9０-９,，.．\-\(\)]+円?)(\D*)')
##        rrr = re.compile(r'([^\d\(\)]*)(\d{7}|(?:0\d{1,4}-|\(0\d{1,4}\) ?)?\d{1,4}-\d{4})(\D*)')
##        rrr = re.compile(r'(\D*)((?:\d{7})|(?:\d{3}-\d{4}))(\D*)')
##        rrr = re.compile(r'([^\\￥\$＄\-―△▲\d]*)([\\￥\$＄\-―△▲]?(?:(?:(?:[1-9]\d*)(?:[,\.]\d{3})*)|0)(?:\.\d+)?円?)(\D*)')
#        ret = rrr.search(r'1,234(あい)')
#        ggg = ret.groups()
#        ret = rrr.search(r'270-007|')
#        ret = rrr.search(r'27-0072|')
#        ret = rrr.search(r'2700072|')
#        ret = rrr.search(r'02700072|')
#        ret = rrr.search(r'|(12,700,072)|')
#        ret = rrr.search(r'(03)3597-1681')
#        ret = rrr.search(r'|(03)3597-1681|')
#        ret = rrr.search(r'|090-3597-1681|')
#        ret = rrr.search(r'|03(3597)1681|')
#        ret = rrr.search(r'1234567|')
#        ret = rrr.search(r'|▲1,234,567|')
#        ret = rrr.search(r'|-1.0|')
#        ret = rrr.search(r'|\123円|')
#        ret = rrr.search(r'|$1,234|')
#        ret = rrr.search(r'|12,345円|')
#        ret = rrr.search(r'|￥123,456|')

#        a= 0

    #明細領域
    def load_box_heading(self, inData):
        #明細領域
        self.table = {}
        # 明細行の列見出し
        try:
            self.table['heading']   = inData['box_heading']
        except:
            self.table['heading']   = [{'title':'商品名', 'alias':'商品名,商品,内容,内訳,品名,規格', 'type':'STR'},
                                       {'title':'数量',   'alias':'数量,数',                         'type':'QUANTITY'},
                                       {'title':'金額',   'alias':'金額,税抜金額,金額(税抜き)',      'type':'AMOUNT'},
                                    ]
        debug_print( 'HEADING -->',level=DEBUG_ROWS_INFO)
        for t in self.table['heading']:
            debug_print( '{} [{}] {}'.format(t['title'],t['alias'],t['type']),level=DEBUG_ROWS_INFO)
        debug_print( 'HEADING <--',level=DEBUG_ROWS_INFO)

        # 内部形式に変換
        for h in self.table['heading']:
            try:
                type = h['type'].upper()
                if type == 'STR':
                    h['type_id'] = BOX_HEADING_TYPE_STR
                elif type == 'QUANTITY':
                    h['type_id'] = BOX_HEADING_TYPE_QUANTITY
                elif type == 'AMOUNT':
                    h['type_id'] = BOX_HEADING_TYPE_AMOUNT
                else:
                    h['type_id'] = BOX_HEADING_TYPE_NON
            except:
                h['type_id'] = BOX_HEADING_TYPE_NON

            try:
                h['alias_list'] = h['alias'].split(',')
            except:
                h['alias_list'] = []

            # 文字数が多い順にソート
            h['alias_list'].sort(key=lambda x: len(x),reverse=True)

            h['regex'] = [] # aliasの正規表現
            alias_char = '' # 文字の誤認識の時にaliasに含まれる文字で正規表現
            for a in h['alias_list']:
                h['regex'].append(re.compile(regex_space2(a)))
                for c in a:
                    ret = reg_kanji.search(c) # 対象は漢字だけ
                    if ret is not None:
                        if c not in alias_char:
                            alias_char += c
            h['alias_char_regex'] = re.compile('['+alias_char+']')

    def get_line_text(self, texts, height_average):
        # KEYWORDをまとめる
        row_text = ''
        row_info = []
        text_info = []
        cnt = 0
        for i, r in enumerate(texts):
            txt = r['text']
            #txt = r['text'].replace(' ','').replace('　','')
            if len(text_info) == 0:
                row_text = txt
                #row_info = [i] * len(txt)
                row_info = [cnt] * len(txt)
                cnt = 1
                text_info.append(r)
                continue

            if text_info[0]['bounds'].is_same_line(r['bounds'],height_average):#average_size):
                row_text += txt
                #row_info.extend([i] * len(txt))
                row_info.extend([cnt] * len(txt))
                cnt += 1
                text_info.append(r)

            else:
                yield row_text, text_info, row_info

                row_text = txt
                cnt = 0
                #row_info = [i] * len(txt)
                row_info = [cnt] * len(txt)
                cnt += 1
                text_info.clear()
                text_info.append(r)

        yield row_text, text_info, row_info

    def find_keyword(self, texts, height_average):

        extacted_texts = []
        #extacted_texts = texts[:]

        # 同一行にまとめてKEYWORD探す
        for row_text, text_info, row_info in self.get_line_text(texts, height_average):
            cnt = len(text_info)

            # KEYWORDが含まれるか？
            for k in self.keyword:
                ret = k['regx'].search(row_text)
                if ret:
                    #if cnt >= 2:    # データが2つ以上にまたがる
                    #    None

                    added = -1
                    # 前
                    for i in range(ret.regs[1][0],ret.regs[1][1]):
                        if row_info[i] != added:
                            added = row_info[i]
                            extacted_texts.append(text_info[added])

                    # 検索文字列
                    r = None #text_info[ret.regs[2][0]]
                    #r['text'] = row_text
                    #added = row_info[ret.regs[2][0]]
                    for i in range(ret.regs[2][0],ret.regs[2][1]):
                        if row_info[i] != added:
                            added = row_info[i]
                            if r == None:
                                r = text_info[added] #text_info[i]
                            else:
                                r['bounds'].expand(text_info[added]['bounds'])
                                for col in text_info[added]['cols']['text']: #text_info[i]['cols']['text']:
                                    r['text'] += col['text']
                                    r['cols']['text'].append(col)

                    if r != None:
                        extacted_texts.append(r)

                    # 後
                    for i in range(ret.regs[3][0],ret.regs[3][1]):
                        if row_info[i] != added:
                            added = row_info[i]
                            extacted_texts.append(text_info[added])

                    #t1 = row_text[ret.regs[1][0]:ret.regs[1][1]]
                    #t2 = row_text[ret.regs[2][0]:ret.regs[2][1]]
                    #t3 = row_text[ret.regs[3][0]:ret.regs[3][1]]

                    #g = ret.group()
                    #gs = ret.groups()
#title   : '仮払消費税等'
#row_text: '仮払 消費 税 等470,957'
#row_info: [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1]
#ret.regs: ((0, 16), (0, 0), (0, 9), (9, 16))
#gs      : ('', '仮払 消費 税 等', '470,957')
                    break
            else:
                for i in range(cnt):
                    extacted_texts.append(text_info[i])

        return extacted_texts

    def find_blocks(self, chars, no, paper):

        paper_w = paper['width']
        paper_h = paper['height']

        blocks = []

        if len(chars) == 0:
            return [{'row':0, 'sy':0, 'ey':paper_h, 'blocks':[0,paper_w]}]
            # return [0,paper_w]

        # 一番左にある文字のXを求める
        left_char = paper_w
        for c in chars:
            if c['bounds'].rect[0] < left_char:
                left_char = c['bounds'].rect[0]

        # 初めの１０文字中の最大幅で空白を探すため
        max = 10
        char_width = 0
        if len(chars) < max:
            max = len(chars)
        for i in range(0,max):
            if chars[i]['bounds'].get_width() > char_width:
                char_width = chars[i]['bounds'].get_width()
        char_width *= 2     # 2文字分


        blocks.append(paper_w)
        prev_x = paper_w
        right_char = int((paper_w-left_char) / char_width + 0) * char_width + left_char

        prev_space = True
        for x in range(right_char,left_char,-char_width):
            a = 0
            for c in chars:
                if (x <= c['bounds'].rect[0] <= prev_x) or (x <= c['bounds'].rect[2] <= prev_x):
                    prev_space = False
                    break
            else:
                if prev_space == False:
                    blocks.append(x)
                prev_space = True

            prev_x = x

        blocks.append(0)
        blocks = sorted(blocks)

        debug_print( 'find_blocks({}) --> {}'.format(no,blocks),level=DEBUG_ROWS_INFO)
        #debug_print( blocks,level=DEBUG_ROWS_INFO)
        #debug_print( 'find_blocks({}) <--'.format(no),level=DEBUG_ROWS_INFO)

        return [{'row':0, 'sy':0, 'ey':paper_h, 'blocks':blocks}]
        # return blocks

    def find_rows(self, chars, no, blocks, paper):

        # rows_scale = self.find_rows_scale
        blocks_info = []
        max = 0
        for b in blocks:
            for i in range(len(b['blocks'])-1):
                max += 1
                blocks_info.append({'sx':b['blocks'][i], 'sy':b['sy'], 'ex':b['blocks'][i+1], 'ey':b['ey']})
        rows = [None] * (max)
        for b in range(0,max):
            rows[b] = []
        # rows = [None] * (max-1)
        # for b in range(0,max-1):
        #     rows[b] = []
        # a = 0
        # 行を検出して分ける
        for c in chars:
            for b in range(0,max):
            # for b in range(0,max-1):
                # if blocks[b] <= c['bounds'].center[0] < blocks[b+1]:
                if blocks_info[b]['sx'] <= c['bounds'].rect[0] < blocks_info[b]['ex']:
                # if blocks[b] <= c['bounds'].rect[0] < blocks[b+1]:
                    if blocks_info[b]['sy'] <= c['bounds'].rect[1] < blocks_info[b]['ey']:
                        break
            else:
                continue

            row = None
            for r in rows[b]:
                y1 = r['bounds'].get_top()
                y2 = r['bounds'].get_bottom()

                y1d = c['bounds'].get_top()
                y2d = c['bounds'].get_bottom()

                # if c['text'] == '.':
                #     rows_scale_r = 0.35
                #     rows_scale_c = 1.0
                # else:
                #     rows_scale_r = 0.35    # 縦の縮小
                #     rows_scale_c = 0.35    # 縦の縮小

                rows_scale = self.find_rows_scale

                # rows_scale = 0.35    # 縦の縮小

                y12 = int((y2-y1) * rows_scale[0] + 0.5)
                y1 = y1 + y12
                y2 = y2 - y12

                y12d = int((y2d-y1d) * rows_scale[1] + 0.5)
                y1d = y1d + y12d
                y2d = y2d - y12d

#                debug_print( '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(y1,y2,y1d,y2d,type(y1),type(y2),type(y1d),type(y2d)),level=DEBUG_ROWS_INFO)

                if (y1d <= y1 <= y2d) or (y1 <= y1d <= y2):
                    # if '2' == c['text'] and c['bounds'].rect[0] == 3150 and c['bounds'].rect[1] == 346:
                    # # if '投資その他の資産' in r['text']:
                    #     aaa = 0
                    remove_char = False
                    # 「誤認識対策」同一文字で領域が重なっている
                    if c['text'].isnumeric(): # 数字
                        c_width = c['bounds'].get_width() # 対象文字の幅
                        # overlap_threshold = (c_width*0.3)
                        overlap_max = 0
                        for t in r['chars']:
                            if t['text'] == c['text']:
                                t_width = t['bounds'].get_width() # 保存済み文字の幅
                                left  = c['bounds'].get_left()  if c['bounds'].get_left()  < t['bounds'].get_left()  else t['bounds'].get_left()
                                right = c['bounds'].get_right() if c['bounds'].get_right() > t['bounds'].get_right() else t['bounds'].get_right()

                                w = (right - left)

                                # overlap = (c_width + t_width) - w
                                # 幅が狭い方を使う
                                if c_width <= t_width:
                                    n_width = c_width
                                else:
                                    n_width = t_width
                                overlap = (n_width + n_width) - w

                                if overlap > 0:
                                    aaa = 0

                                overlap_threshold = (n_width*0.33)
                                if overlap >= overlap_threshold:
                                    remove_char = True
                                    break
                    else:
                        for t in r['chars']:
                            if t['text'] == c['text']:
                                if t['bounds'].is_included(c['bounds'], True):
                                    remove_char = True
                                    break

                    # for t in r['chars']:
                    #     if not t['text'].isnumeric():
                    #         if t['text'] == c['text']:
                    #             if t['bounds'].is_included(c['bounds'], True):
                    #                 remove_char = True
                    #                 break

                    if remove_char == False:
                        r['text'] += c['text']
                        #r['chars'].insert(0,c)
                        r['chars'].append(c)
                        r['bounds'].expand(c['bounds'])
                        row = r
                    break

                    #r['text'] += c['text']
                    ##r['chars'].insert(0,c)
                    #r['chars'].append(c)
                    #r['bounds'].expand(c['bounds'])
                    #break

                # a += 1
            else:
                # if '2' == c['text'] and c['bounds'].rect[0] == 3150 and c['bounds'].rect[1] == 346:
                #     aaa = 0
                row = {'row_no':0, 'serial_row':0, 'block':b, 'type':WORD_SPLIT_OPT_NON, 'text':c['text'], 'bounds':copy.deepcopy(c['bounds']), 'chars':[c]}
#                row = {'row_no':0, 'text':copy.copy(c['text']), 'bounds':copy.deepcopy(c['bounds']), 'chars':[c]}

                rows[b].append(row)
                #rows.insert(0,row)

                # a = 0

            #if row:
            #    max = len(blocks)
            #    for i in range(0,max-1):
            #        if blocks[i] <= row['bounds'].rect[0] <= blocks[i+1]:
            #            row['block'] = i
            #            break

        extacted_rows = []
        # 行が上から下になる様にソート
        for b in range(0,max):
        # for b in range(0,max-1):
            rows[b] = sorted(rows[b], key=lambda x:x['bounds'].rect[1])

            # 行ごとに左から右になる様にソート
            for row_no, r in enumerate(rows[b]):
                r['chars'] = sorted(r['chars'], key=lambda x:x['bounds'].rect[0])

                row = None
                for c in r['chars']:
                    if c['text'] in ["(",")","（","）","I","."] :
                        a=999
                    elif row == None:
                        row = {'page':str(no+1), 'row_no':row_no, 'serial_row':0, 'block':b, 'type':WORD_SPLIT_OPT_NON, 'text':c['text'], 'bounds':copy.deepcopy(c['bounds']), 'chars':[c]}
                    #if row == None:
                    #    row = {'page':str(no+1), 'row_no':row_no, 'serial_row':0, 'block':b, 'type':WORD_SPLIT_OPT_NON, 'text':c['text'], 'bounds':copy.deepcopy(c['bounds']), 'chars':[c]}
                    else:
                        row['text'] += c['text']
                        row['chars'].append(c)
                        row['bounds'].expand(c['bounds'])

                if row:
                    extacted_rows.append(row)

            #text = ''
            #for c in r['chars']:
            #    text += c['text']

            #r['row_no']   = row_no
            #r['text'] = text

            #debug_print( '{}\t{}\t{}\t{}\t{}\t{}'.format(r['text'],r['bounds'].get_left(),r['bounds'].get_top(),r['bounds'].get_right(),r['bounds'].get_bottom(),r['row_no']),level=DEBUG_STR_INFO)

            # c = 0

        debug_print( 'find_rows({}) -->[{},{}]'.format(no,self.find_rows_scale[0],self.find_rows_scale[1]),level=DEBUG_ROWS_INFO)
        extacted_rows = sorted(extacted_rows, key=lambda x:(x['block'],x['row_no']))
        if DEBUG_STR_INFO >= DEBUG_PRINT_LEVEL:
            for row in extacted_rows:
                char_x = '['
                for c, char in enumerate(row['chars']):
                    if c != 0:
                        char_x += ','
                    char_x += '{}'.format(char['bounds'].rect[0])
                char_x += ']'
                debug_print( '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(row['text'],row['bounds'].get_left(),row['bounds'].get_top(),row['bounds'].get_right(),row['bounds'].get_bottom(),row['row_no'], row['block'], char_x),level=DEBUG_STR_INFO)

        debug_print( 'find_rows({}) <--'.format(no),level=DEBUG_ROWS_INFO)

        a = 0

        return extacted_rows
        #return rows

    # 表の縦線を探す
    def find_vertical_line2(self, file_name, img_org, bounds, img_width=True):

        x_spike = []

        if img_width:
            left = 0
            right = img_org.shape[1]
        else:
            left = bounds.get_left()
            right = bounds.get_right()

        img = img_org[bounds.get_top() : bounds.get_bottom() , left : right]

        # BGR -> グレースケール
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if file_name is not None:
            cv2.imwrite(file_name+'.head.th.jpg', img_gray)
            os.chmod(file_name+'.head.th.jpg', FILE_PARMITION)

        # 画像の大きさを取得
        height, width, channels = img.shape[:3]

        x1,y1,x2,y2 = 0, 0, width, height
        y3=y2-y1
        x3=0

        #縦線検出
        for x in range(x1,x2):
            sum = 0
            for y in range(y1,y2):
                if img_gray[y,x] > 125:
                    sum = sum + 255
            sum=sum/y3
            if sum < 10 and x-x3>5:
                print(sum,x)
                x3=x
                img = cv2.line(img,(x,y1),(x,y2),(0,255,0),2)

                x_spike.append(x+left)

        # debug用
        line_color = (0, 0, 255) # red
        for x in x_spike:
            cv2.line(img, (x, 0), (x, img.shape[0]), line_color, thickness=2)

        if file_name is not None:
            cv2.imwrite(file_name+'.head.jpg', img)
            os.chmod(file_name+'.head.jpg', FILE_PARMITION)

        return x_spike



    # 表の縦線を探す
    def find_vertical_line(self, file_name, img_org, bounds, img_width=True):
    # def find_vertical_line(self, file_name, img_org, bounds, no):
        #img_path = "content0_line.jpg"
        #img_org = cv2.imread(img_path)
        #img = img_org.copy()

        if img_org is None:
            return []

        if img_width:
            left = 0
            right = img_org.shape[1]
        else:
            left = bounds.get_left()
            right = bounds.get_right()

        img = img_org[bounds.get_top() : bounds.get_bottom() , left : right]
        #img = img_org[bounds.get_top() : bounds.get_bottom() , bounds.get_left() : bounds.get_right()]

        _, img_th = cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_OTSU)

        # reverse white and black for dilate and erode
        img_th = 255 - img_th

        # if file_name is not None:
        #     cv2.imwrite(file_name+'.head.th.jpg', img_th)
        #     os.chmod(file_name+'.head.th.jpg', FILE_PARMITION)
        # vertical kernel to connect dot line to solid line
        #kernel = np.zeros((5,5), np.uint8)
        #kernel[:, 2] = 1

        #img_th = cv2.dilate(img_th, kernel, iterations=8)
        #cv2.imwrite("dilate.jpg",img_th)
        #img_th = cv2.erode(img_th, kernel, iterations=2)
        #cv2.imwrite("erode.jpg",img_th)

        vp = np.sum((img_th != 0).astype(np.uint8), axis=0)

        thresh_spike = int(bounds.get_height()*0.9)
        # thresh_spike = bounds.get_height()-5 #48
        # thresh_spike = nmax = np.max(vp)-5
        loc_x_spike = np.where(vp > thresh_spike)


        x_spike = []
        prev_x = -1
        for x in loc_x_spike[0]:
            if prev_x < x: # 連続したもの(2ドット以内)
                x_spike.append(left+x)
            prev_x = x+2

        # 最後にイメージの幅を追加
        if len(x_spike) > 0 and img_width:
            if x_spike[-1]+2 < img_org.shape[1]:
                x_spike.append(img_org.shape[1])

        if file_name is not None:
            # draw vertical lines
            line_color = (0, 0, 255) # red
            for x in x_spike:
                cv2.line(img, (x, 0), (x, img.shape[0]), line_color, thickness=2)

        #_, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4)
            cv2.imwrite(file_name+'.head.jpg', img)
            os.chmod(file_name+'.head.jpg', FILE_PARMITION)

        #ax1.imshow(img_org)
        #ax2.scatter(range(len(vp)), vp)
        #ax3.imshow(img_th)
        #ax4.imshow(img)
        #plt.show()

        return x_spike

    # rows['chars'][start-end]['bounds'] を返す
    def get_chars_bounds(self, chars, start, end):
        text = ''
        bounds = None
        for i in range(start,end):
            if bounds == None:
                bounds = copy.deepcopy(chars[i]['bounds'])
                text = chars[i]['text']
            else:
                bounds.expand(chars[i]['bounds'])
                text += chars[i]['text']
        return bounds, text

    def get_chars_between_LR_text(self, chars, left, right):
        bounds = None
        text = ''
        _chars = []
        for c in chars:
            if left <= c['bounds'].get_left() < right:
                _chars.append(c)
                text += c['text']
                if bounds is None:
                    bounds = copy.deepcopy(c['bounds'])
                else:
                    bounds.expand(c['bounds'])

        return text, _chars, bounds

    # 列の縦線を探す
    # def find_col_vline(self, rows, file_name, img):

    #     for r in rows:
    #         vline1 = self.find_vertical_line(file_name, img, r['bounds'], img_width=False)
    #         vline = self.find_vertical_line2(file_name, img, r['bounds'], img_width=False)

    #         vlines = []
    #         for v in vline:
    #             for c in r['chars']:
    #                 if c['bounds'].get_left() <= v <= c['bounds'].get_right():
    #                     break
    #             else:
    #                 vlines.append(v)

    #         a = 0

    #     a = 1

    # 表（明細行）を探す
    def find_table(self, rows, file_name, img, no):
        if img is None:
            return
    # def find_table(self, rows, file_name, img, boxes, no):

        gokei_regex = re.compile('合[\s　]*計')

        debug_print( 'find_table({}) -->'.format(no),level=DEBUG_ROWS_INFO)
        #found = []
#        for r in rows:
#            col = []
#            for h in self.table['heading']:
#                #found = False
#                for regex in h['regex']:
#                    ret = regex.search(r['text'])
#                    if ret:
#                        # 文字列の領域を保存
#                        bounds = None
#                        for i in range(ret.start(),ret.end()):
##                        for i in range(ret.regs[0][0],ret.regs[0][1]):
#                            if bounds == None:
#                                bounds = copy.deepcopy(r['chars'][i]['bounds'])
#                            else:
#                                bounds.expand(r['chars'][i]['bounds'])

#                        col.append({'heading':h, 'text':ret.group(), 'bounds':bounds})
#                        break # 一致したので次の列
#                else:
#                    break # 一致しないので次の行へ

#            else: # すべての列が一致したので見出し行の候補
#                # 縦線を探す
#                vline = self.find_vertical_line(file_name, img, r['bounds'], no)
#                found.append({'row':r, 'col':col, 'vline':vline})

        # 見出し行の候補となる行を探す
        debug_print( 'pass(1) -->',level=DEBUG_STR_INFO)

        heading_num = len(self.table['heading'])
        perfect_score = heading_num * 10
        passing_score = perfect_score/2 # 候補になる点数
        # passing_score = (heading_num-1) * 10 # 候補になる点数
        found = []
        for r in rows:
            col = []
            found_score = 0
            for h in self.table['heading']:
                #found = False
                for regex in h['regex']:
                    ret = regex.search(r['text'])
                    if ret:
                        # 文字列の領域を保存
                        bounds, _ = self.get_chars_bounds(r['chars'], ret.start(),ret.end())
#                        bounds = None
#                        for i in range(ret.start(),ret.end()):
##                        for i in range(ret.regs[0][0],ret.regs[0][1]):
#                            if bounds == None:
#                                bounds = copy.deepcopy(r['chars'][i]['bounds'])
#                            else:
#                                bounds.expand(r['chars'][i]['bounds'])

                        score = 10
                        found_score += score
                        col.append({'heading':h, 'text':ret.group(), 'bounds':bounds, 'score':score, 'linked':False})
                        break
                else:
                    ret = h['alias_char_regex'].search(r['text'])
                    if ret:
                        score = 5
                        found_score += score

                        text = ret.group()
                        bounds, _ = self.get_chars_bounds(r['chars'], ret.start(),ret.end())
                    else:
                        score = 0
                        text = ''
                        bounds = Bound()

                    col.append({'heading':h, 'text':text, 'bounds':bounds, 'score':score})
                    aaa = 0
                    #pass

            if found_score >= passing_score: # 見出し文字列が一致したので候補にする
            #if found_num >= heading_num-1: # 見出し文字列が一致したので候補にする
                # 縦線を探す
                vline = self.find_vertical_line(file_name, img, r['bounds'], img_width=True)
                # vline = self.find_vertical_line(file_name, img, r['bounds'], no)
                found.append({'row':r, 'col':col, 'vline':vline, 'score':found_score})

        found = sorted(found, key=lambda x:(int(x['row']['page']),x['row']['block'],x['row']['row_no']))
        for i, f in enumerate(found):
            debug_print( '[{}]\t{}/{}({})\t{}\t{}\t{}\t{}\t{}\t{}'.format(i,f['score'],perfect_score,passing_score,f['row']['row_no'], f['row']['text'],f['row']['bounds'].get_left(),f['row']['bounds'].get_top(),f['row']['bounds'].get_right(),f['row']['bounds'].get_bottom()),level=DEBUG_STR_INFO)

            for c in f['col']:
                debug_print( '   {}\t{}\t{}\t{}\t{}\t{}\t{}\t[{}]\t{}'.format(c['score'],c['text'],c['bounds'].get_left(),c['bounds'].get_top(),c['bounds'].get_right(),c['bounds'].get_bottom(),c['heading']['title'], c['heading']['alias'],c['heading']['type']),level=DEBUG_STR_INFO)

        # 区切り(vline)で見出し行を分けてみる
        debug_print( 'pass(2) -->',level=DEBUG_STR_INFO)
        # テーブルのY(上限、下限)を決める ：実際は後続の処理で"合計"の上までを対象とする
        img_height = img.shape[0]
        max = len(found)-1
        for i, f in enumerate(found):
            f['top'] = f['row']['bounds'].get_top()
            if i < max and f['row']['page'] == found[i+1]['row']['page'] and f['row']['block'] == found[i+1]['row']['block']:
                # 後ろに続く同一ページ、ブロックの見出し行があるので直前まで
                bottom = found[i+1]['row']['bounds'].get_top()-1
            else:
                # 後ろに続く同一ページ、ブロックはない
                bottom = img_height
                # 要検討
            f['bottom'] = bottom

            debug_print( '[{}] top:{} bottom:{} vline{}'.format(i, f['top'], f['bottom'], f['vline']),level=DEBUG_STR_INFO)
            left = 0
            data = []
            for j, right in enumerate(f['vline']):
                text, _, bounds = self.get_chars_between_LR_text(f['row']['chars'], left, right)
                # bounds = None
                # text = ''
                # for c in f['row']['chars']:
                #     if left <= c['bounds'].get_left() < right:
                #         text += c['text']
                #         if bounds is None:
                #             bounds = copy.deepcopy(c['bounds'])
                #         else:
                #             bounds.expand(c['bounds'])

                debug_print( ' [{}]\t{}\t{}\t{}'.format(j, text, left,right),level=DEBUG_STR_INFO)

                data.append({'left':left, 'right':right, 'text':text, 'bounds':bounds, 'col':None, 'cell':[], 'score':0})
                left = right

            f['data'] = data

        debug_print( 'pass(2) <--',level=DEBUG_STR_INFO)

        # 分けた見出しを結びつける
        debug_print( 'pass(3) -->',level=DEBUG_STR_INFO)
        for i, f in enumerate(found):
            found_score = 0
            for c in f['col']:

                linked = False
                # 見出しaliasに完全一致するものを探す
                for a in c['heading']['alias_list']:
                    for d in f['data']:
                        if d['col'] is None and d['text'] != '':
                            if a == d['text']:
                                c['linked'] = linked = True # 結びついた
                                d['col'] = c
                                score = 10
                                d['score'] = score
                                found_score += score
                                break
                    if linked:
                        break
                else:
                    # 完全一致するものが無いので一文字だけで探してみる
                    for d in f['data']:
                        if d['col'] is None and d['text'] != '':
                            ret = c['heading']['alias_char_regex'].search(d['text'])
                            if ret:
                                c['linked'] = linked = True # 結びついた
                                d['col'] = c
                                score = 5
                                d['score'] = score
                                found_score += score
                                break

            f['data_score'] = found_score
            debug_print( '[{}]\t{}/{}({})'.format(i,found_score,perfect_score,passing_score),level=DEBUG_STR_INFO)
            for d in f['data']:
                debug_print( '   {}\t{}\t{}\t{}'.format(d['score'], d['text'],d['left'],d['right']),level=DEBUG_STR_INFO)


        debug_print( 'pass(3) <--',level=DEBUG_STR_INFO)

        # 明細行の読み取り
        for i, f in enumerate(found):
            cell_data = []
            data_rows = 0
            f['reason_exit'] = 'end loop'
            for r in rows:
                # 同一ページ、同一ブロックで見出し行よりも下にあるもの
                if f['row']['page'] != r['page'] or f['row']['block'] != r['block'] or f['row']['row_no'] > r['row_no']:
                    continue
                # 「合計」が現れたら終了
                if gokei_regex.search(r['text']) is not None:
                    f['reason_exit'] = 'total:{}'.format(r['text'])
                    break
                # 表の下限を超えたので終了
                if r['bounds'].get_bottom() > f['bottom']:
                    f['reason_exit'] = 'bottom:{}>{}'.format(r['bounds'].get_bottom(),f['bottom'])
                    break

                row_data = []
                # データの収集

                for j, d in enumerate(f['data']):
                    text, _, bounds = self.get_chars_between_LR_text(r['chars'], d['left'], d['right'])

                    row_data.append({'text':text, 'bounds':bounds if bounds is not None else Bound()})

                cell_data.append(row_data)
            f['cell'] = cell_data

        # CELLデータ抽出
        debug_print( 'pass(4) -->',level=DEBUG_STR_INFO)
        debug_print( '[{}]{}'.format(file_name, '>>CELLs' if len(found) > 0 else ''),level=DEBUG_STR_INFO)
        for i, f in enumerate(found):
            debug_print( '[{}]---------->'.format(i),level=DEBUG_STR_INFO)
            txt = '    '
            for d in f['data']:
                if d['col'] is not None:
                    txt += '{}[{}],'.format(d['col']['heading']['title'],d['col']['heading']['type'])
                else:
                    txt += ','

            debug_print( '{}'.format(txt.replace('"','""')),level=DEBUG_STR_INFO)

            for r in f['cell']:
                txt = '    '
                for c in r:
                    txt += '{},'.format(c['text'])
                debug_print( '{}'.format(txt.replace('"','""')),level=DEBUG_STR_INFO)
            debug_print( '[{}]<----- {}'.format(i, f['reason_exit']),level=DEBUG_STR_INFO)

        # debug_print( 'pass(4) <--',level=DEBUG_STR_INFO)

        # 列データの型を調べる

        debug_print( 'pass(5) -->',level=DEBUG_STR_INFO)
        col_type_amount     = re.compile('^[0-9０-９,，.．]+(?:円|YEN)?$')
        col_type_mix   = re.compile('^[^0-9０-９,，.．]*[0-9０-９,，.．]+[^0-9０-９,，.．]?$')
        for i, f in enumerate(found):
            cells = f['cell']
            rows = len(cells)
            type_cnt = []
            for col, d in enumerate(f['data']):
                cnt = {'target':d['text'] if d['col'] is None else d['text']+'(*'+d['col']['heading']['title']+')', 'mix':0, 'amount':0, 'str':0, 'non':0}
                for row in range(1,rows):
                    text = cells[row][col]['text']
                    if len(text) == 0:
                        cnt['non'] += 1
                    else:
                        ret = col_type_amount.search(text)
                        if ret is not None:
                            cnt['amount'] += 1
                        else:
                            ret = col_type_mix.search(text)
                            if ret is not None:
                                cnt['mix'] += 1
                            else:
                                cnt['str'] += 1
                type_cnt.append(cnt)
            f['type_cnt'] = type_cnt

            txt = ''
            # txt = '{},'.format(i)
            for cnt in type_cnt:
                txt += '{}[{}:{}:{}:{}],'.format(cnt['target'], cnt['str'], cnt['mix'],cnt['amount'],cnt['non'])
            debug_print( '{}'.format(txt),level=DEBUG_STR_INFO)

        debug_print( '--------------------------',level=DEBUG_STR_INFO)

        # 結果を保存
        self.table['found'] = found

        # debug_print( '--------------------------',level=DEBUG_ROWS_INFO)
        # for i, f in enumerate(self.table['found']):
        #     #vline = self.find_vertical_line(file_name, img, f['row']['bounds'], no)
        #     #f['vline'] = vline
        #     debug_print( '{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(i,f['row']['row_no'], f['row']['text'],f['row']['bounds'].get_left(),f['row']['bounds'].get_top(),f['row']['bounds'].get_right(),f['row']['bounds'].get_bottom()),level=DEBUG_STR_INFO)
        #     for c in f['col']:
        #         debug_print( '   {}\t{}\t{}\t{}\t{}\t{}\t[{}]\t{}'.format(c['text'],c['bounds'].get_left(),c['bounds'].get_top(),c['bounds'].get_right(),c['bounds'].get_bottom(),c['heading']['title'], c['heading']['alias'],c['heading']['type']),level=DEBUG_STR_INFO)

        # debug_print( 'find_table({}) <--'.format(no),level=DEBUG_ROWS_INFO)

    # テーブルの列（縦線）で文字列を分ける
    # def split_table_col_words(self, words):

    #     extacted_words = []

    #     for w in words:
    #         extacted_words.append(w)

    #     return extacted_words

    # 文字列の属性を調べる
    def check_word_type(self, option, text, chars):

        ret = None

        if option == WORD_SPLIT_OPT_YEN: # 金額(円）
        ##elif k['title'] == REGEX_SEARCH_AMOUNT:# 合計
            ret = search_cmm_yen(text)
        elif option == WORD_SPLIT_OPT_AMOUNT: # 金額
            ret = search_cmm_mount(text)
        elif option == WORD_SPLIT_OPT_NUMBER: # 数字
        #elif k['title'] == REGEX_SEARCH_NUMBER:# 数字
            ret = search_number(text)
        elif option == WORD_SPLIT_OPT_DATE: # 日付
        #if k['title'] == REGEX_SEARCH_DATE:
            ret = search_date(text)
        elif option == WORD_SPLIT_OPT_ADDR: # 住所
            #ret = search_address(text)

            ret = search_address(text, chars)

            #if w['done'] & WORD_SPLIT_DONE_ADDRESS == WORD_SPLIT_DONE_NON:
            #    ret = search_address(text, w['chars'])
            #    if ret == None:
            #        w['done'] = w['done'] | WORD_SPLIT_DONE_ADDRESS
            #else:
            #    ret = None

        elif option == WORD_SPLIT_OPT_AREA: # 面積
            #text = '床面積1階184.73㎡'
            ret = search_unit_area(text)
        elif option == WORD_SPLIT_OPT_TERM_YEAR_MONTH: # 期間(年月)
            ret = search_unit_term_year_month(text)
        elif option == WORD_SPLIT_OPT_TERM_MONTH: # 期間(月)
            ret = search_unit_term_month(text)
        elif option == WORD_SPLIT_OPT_TERM_PRIOR: # 期間(前)
            ret = search_unit_term_prior(text)
        elif option == WORD_SPLIT_OPT_UNIT: # 単位
            ret = search_unit(text)
            # if ret:
            #     unit = 0
        elif option == WORD_SPLIT_OPT_UNIT_BUILDING: # 単位
            ret = search_unit_building(text)

        return ret


    # 文字列をタイプで分ける
    def split_words(self, words, no, loop):

        split_cnt = 0

        extacted_words = []

        for w in words:
            if w['done'] & WORD_SPLIT_DONE_ALL:
                extacted_words.append(w)
                continue

            ret = None
            # KEYWORDが含まれるか？
            for k in self.keyword:
                if k['option'] != WORD_SPLIT_OPT_NON:
                    ret = self.check_word_type(k['option'], w['text'], w['chars'])
                # if k['option'] == WORD_SPLIT_OPT_YEN: # 金額(円）
                # ##elif k['title'] == REGEX_SEARCH_AMOUNT:# 合計
                #     ret = search_cmm_yen(w['text'])
                # elif k['option'] == WORD_SPLIT_OPT_AMOUNT: # 金額
                #     ret = search_cmm_mount(w['text'])
                # elif k['option'] == WORD_SPLIT_OPT_NUMBER: # 数字
                # #elif k['title'] == REGEX_SEARCH_NUMBER:# 数字
                #     ret = search_number(w['text'])
                # elif k['option'] == WORD_SPLIT_OPT_DATE: # 日付
                # #if k['title'] == REGEX_SEARCH_DATE:
                #     ret = search_date(w['text'])
                # elif k['option'] == WORD_SPLIT_OPT_ADDR: # 住所
                #     #ret = search_address(w['text'])

                #     ret = search_address(w['text'], w['chars'])

                #     #if w['done'] & WORD_SPLIT_DONE_ADDRESS == WORD_SPLIT_DONE_NON:
                #     #    ret = search_address(w['text'], w['chars'])
                #     #    if ret == None:
                #     #        w['done'] = w['done'] | WORD_SPLIT_DONE_ADDRESS
                #     #else:
                #     #    ret = None

                # elif k['option'] == WORD_SPLIT_OPT_AREA: # 面積
                #     #w['text'] = '床面積1階184.73㎡'
                #     ret = search_unit_area(w['text'])
                # elif k['option'] == WORD_SPLIT_OPT_TERM_YEAR_MONTH: # 期間(年月)
                #     ret = search_unit_term_year_month(w['text'])
                # elif k['option'] == WORD_SPLIT_OPT_TERM_MONTH: # 期間(月)
                #     ret = search_unit_term_month(w['text'])
                # elif k['option'] == WORD_SPLIT_OPT_TERM_PRIOR: # 期間(前)
                #     ret = search_unit_term_prior(w['text'])
                # elif k['option'] == WORD_SPLIT_OPT_UNIT: # 単位
                #     ret = search_unit(w['text'])
                #     # if ret:
                #     #     unit = 0

                else:                               # 正規表現
                    ret = k['regx'].search(w['text'])
                if ret:
                    # 対象文字列はKEYWORDのみなのでこれ以上処理をしない
                    if ret.regs[1][0] == ret.regs[1][1] and ret.regs[3][0] == ret.regs[3][1]:
                        ret = None

                        w['done'] = w['done'] | WORD_SPLIT_DONE_ALL#True
                        w['type'] = k['option']
                        #if not 'serial_row_list' in w:
                        #    w['serial_row_list'] = [w['serial_row']]
                        #if #keyword
                        extacted_words.append(w)

                        break

                    split_cnt += 1

                    #if len(w['chars']) > ret.regs[3][1]:
                    #    regs = ret.regs[0:3] + ((ret.regs[3][0],len(w['chars'])),)
                    #    #ret.regs[3][1] = len(w['chars'])
                    #else:
                    #    regs = ret.regs
                    regs = ret.regs

                    for j in range(1,4):
                        s = None

                        if j == 1:
                            st = 0
                        else:
                            st = regs[j][0]

                        ed = regs[j][1]
                        for i in range(st, ed):
                            if s == None:
                                s = {'done':w['done'], 'page':w['page'], 'article_no':w['article_no'], 'article_row':w['article_row'], 'serial_row':w['chars'][i]['row']['serial_row'], 'row_no':w['row_no'], 'block':w['block'], 'type':WORD_SPLIT_OPT_NON, 'text':w['chars'][i]['text'], 'bounds':copy.deepcopy(w['chars'][i]['bounds']), 'chars':[w['chars'][i]]}
                                #s = {'done':WORD_SPLIT_DONE_NON, 'page':w['page'], 'article_no':w['article_no'], 'serial_row':w['chars'][i]['row']['serial_row'], 'row_no':w['row_no'], 'block':w['block'], 'type':WORD_SPLIT_OPT_NON, 'text':w['chars'][i]['text'], 'bounds':copy.deepcopy(w['chars'][i]['bounds']), 'chars':[w['chars'][i]]}
                                #s = {'page':w['page'], 'article_no':w['article_no'], 'serial_row':w['serial_row'], 'row_no':w['row_no'], 'block':w['block'], 'type':WORD_SPLIT_OPT_NON, 'text':w['chars'][i]['text'], 'bounds':copy.deepcopy(w['chars'][i]['bounds']), 'chars':[w['chars'][i]]}
                                #s = {'serial_row':w['serial_row'], 'serial_row_list':[w['serial_row']], 'row_no':w['row_no'], 'block':w['block'], 'type':WORD_SPLIT_OPT_NON, 'text':w['chars'][i]['text'], 'bounds':copy.deepcopy(w['chars'][i]['bounds']), 'chars':[w['chars'][i]]}
                            else:
                                s['text'] += w['chars'][i]['text']
                                s['bounds'].expand(w['chars'][i]['bounds'])
                                s['chars'].append(w['chars'][i])
                                #if not w['chars'][i]['row']['serial_row'] in s['serial_row_list']:
                                #    s['serial_row_list'].append(w['chars'][i]['row']['serial_row'])

                        if s:
                            #if j == 1: #keywordの前
                            #if j == 2: #keyword
                            #if j == 3: #keywordの後

                            if j == 2:
                                s['done'] = w['done'] | WORD_SPLIT_DONE_ALL
                                s['type'] = k['option']

                            extacted_words.append(s)
                    break
            else:
                w['done'] = w['done'] | WORD_SPLIT_DONE_ALL
                #if not 'serial_row_list' in w:
                #    w['serial_row_list'] = [w['serial_row']]
                extacted_words.append(w)
                a = 0

        if split_cnt == 0:
            if DEBUG_STR_INFO >= DEBUG_PRINT_LEVEL:
                debug_print( 'split_words({}) -->'.format(loop),level=DEBUG_ROWS_INFO)
                for r in extacted_words:
                    debug_print( '{}:{}({},{},{},{})\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(r['page'], r['article_no'], r['serial_row'], r['row_no'], r['block'], r['type'], r['text'],r['bounds'].get_left(),r['bounds'].get_top(),r['bounds'].get_right(),r['bounds'].get_bottom(), r['row_no'], r['block']),level=DEBUG_STR_INFO)
                    #debug_print( '({}{},{},{},{})\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(r['serial_row'], r['serial_row_list'], r['row_no'], r['block'], r['type'], r['text'],r['bounds'].get_left(),r['bounds'].get_top(),r['bounds'].get_right(),r['bounds'].get_bottom(), r['row_no'], r['block']),level=DEBUG_STR_INFO)

                debug_print( 'split_words({}) <--'.format(loop),level=DEBUG_ROWS_INFO)

        return split_cnt, extacted_words


    article_regex = re.compile(r'(.*?)(第)([0-9０-９]+?)(条)(.*)')

    #article_regex = re.compile(r'(.*?)(第[0-9０-９]条)(.*)')
#    article_regex = re.compile(r'(.*[^第])(第?[0-9０-９]条)(.*)')
    def collect_article_title(self, words, article_no):

        article = []

        for w in words:
            txt = w['text']
            #txt = 'この第１条は第２条の'
            top = 0
            while True:
                ret = self.article_regex.search(txt)
                if ret:
                    grp = ret.groups()

                    start = ret.regs[2][0] + top
                    stop  = ret.regs[4][1] + top

                    for i in range(start,stop):
                        if i == start:
                            a = {'score':0, 'flags':0, 'col':0, 'article_no':int(grp[2]), 'row_no':w['row_no'], 'block':w['block'], 'text':w['chars'][i]['text'], 'bounds':copy.deepcopy(w['chars'][i]['bounds']), 'border':Bound(), 'start_pos':start, 'stop_pos':stop, 'len':len(txt), 'row':w}
                        else:
                            a['text'] += w['chars'][i]['text']
                            a['bounds'].expand(w['chars'][i]['bounds'])

                    article.append(a)

                    txt = grp[4]
                    top += ret.regs[5][0]
                    i = 0
                else:
                    break

        i = 0


        # 列を探す
        col   = 0
        block = 0
        max = len(article)
        if max > 0:
            # Xでソート
            article = sorted(article, key=lambda x:x['bounds'].rect[0])
            base = None
            # 列を探す
            for a in article:

                # 同一列判定
                if base == None or (a['bounds'].rect[0] > (base.rect[0] + int(float(base.get_width()) * (2.0 / 3.0)))): # lx + w*(2/3)
                #if base == None or (a['bounds'].rect[0] > base.rect[2]):
                    base = copy.deepcopy(a['bounds'])
                    if a['block'] != block:
                        col = 0
                    col = col + 1
                    block = a['block']
                else:
                    base.rect[2] = a['bounds'].rect[2]

                a['col'] = col


            #while True:
            #    base = None
            #    # 処理をしていない物のうち一番左端の第ｎ条を探す
            #    for a in article:
            #        if a['col'] > 0:
            #            continue
            #        if base == None:
            #            base = a
            #        else:
            #            if base['bounds'].rect[0] > a['bounds'].rect[0]:
            #                base = a

            #    if base == None:
            #        break

            #    base_bounds = copy.deepcopy(base['bounds'])

            #    for a in article:
            #        tl = 0
            #        br = 0+2

            #        # 同一列判定
            #        if base_bounds.rect[tl] <= a['bounds'].rect[tl] <= base_bounds.rect[br]:
            #            include = True
            #        elif a['bounds'].rect[tl] <= base_bounds.rect[tl] <= a['bounds'].rect[br]:
            #            include = True
            #        else:
            #            include = False

            #        if include:
            #            if a['bounds'].rect[tl] < base_bounds.rect[tl]:
            #                base_bounds.rect[tl] = a['bounds'].rect[tl]
            #            if base_bounds.rect[br] < a['bounds'].rect[br]:
            #                base_bounds.rect[br] = a['bounds'].rect[br]

            #            a['col'] = col

            #    col = col + 1

        # 条文の終端　"以上" , "通を作成し"
        for w in words:
            if search_article_terminate(w['text']):
                a = {'score':999, 'flags':1, 'col':1, 'article_no':-1, 'row_no':w['row_no'], 'block':w['block'], 'text':w['chars'][i]['text'], 'bounds':copy.deepcopy(w['chars'][i]['bounds']), 'border':Bound(), 'start_pos':-1, 'stop_pos':-1, 'len':0}
                article.append(a)

        # col(no)順でソート
        article = sorted(article, key=lambda x:(x['block'], x['col'], x['row_no']))


        # a['score']==1:同列 ==2:順番通り ==3:決定

        # 一番左の列にある第n条を基準にする
        no  = article_no
        l_no = -1
        col = 1
        prev_a = None
        for a in article:
            if l_no == -1:
                l_no  = a['article_no']
                # 新たに第１条
                if a['article_no'] == 1:
                    a['score'] |= 1
                    no = 0

            #    col = a['col']

            # 同じ列？
            if col == a['col']:
                a['score'] |= 2
                prev_a = None
            else:
                col = a['col']
                prev_a = a

            if (l_no) == a['article_no']: # ページ内は順番どおり
                a['score'] |= 8
                l_no += 1

            if a['col'] == 1: # col 1 優先
                a['score'] |= 16

            if a['start_pos'] == 0: # 行の最初
                a['score'] |= 32
            if a['start_pos'] == a['len']: # 第n条のみ
                a['score'] |= 64


            if (no+1) == a['article_no']: # 全体は順番どおり
                a['score'] |= 4
                no += 1

                # 直前が列代わりの時に同一列としてマーク
                if prev_a:
                    if prev_a['col'] == a['col']:
                        prev_a['score'] |= 2
                        prev_a = None



        return article, no

    def decision_article(self):

        # 最後のn条の　nを求める
        max_article = 0
        for paper in self.papers:
            for a in paper['article']:
                if max_article < a['article_no']:
                    max_article = a['article_no']

        for i in range(1,max_article+1):
            article = None
            score = 0
            for paper in self.papers:
                for a in paper['article']:
                    if i == a['article_no']:
                        if score < a['score']:
                            score = a['score']
                            article = a
            if article:
                start_pos = article['start_pos']
                if start_pos == 0:
                    article['score'] += 32
                else:
                    txt = article['row']['text'][:start_pos]
                    if '(' in txt and ')' in txt:
                        article['score'] += 32
                    elif start_pos < 5:
                        article['score'] += 16
                # article['score'] += 32

        # blockを確定して領域を(border)を求める
        for paper in self.papers:

            block = -1
            prev_a = None

            for a in paper['article']:
                if a['score'] >= 32:
                # if a['score'] >= 30:
                    a['flags'] = 1

                    hh = int(a['bounds'].get_height()/2)
                    a['border'] = Bound(left=paper['blocks'][0]['blocks'][a['block']],top=a['bounds'].get_top()-hh,right=paper['blocks'][0]['blocks'][a['block']+1]-1,bottom=a['bounds'].get_bottom())
                    # a['border'] = Bound(left=paper['blocks']['blocks'][0][a['block']],top=a['bounds'].get_top()-hh,right=paper['blocks']['blocks'][0][a['block']+1]-1,bottom=a['bounds'].get_bottom())
                    # a['border'] = Bound(left=paper['blocks'][a['block']],top=a['bounds'].get_top()-hh,right=paper['blocks'][a['block']+1]-1,bottom=a['bounds'].get_bottom())
                    if prev_a:
                        if block == a['block']:
                            prev_a['border'].rect[3] = a['border'].rect[1]-1
#                           prev_a['border'].rect[3] = a['border'].rect[1]-(a['border'].get_height()/2)
                           #prev_a['border'].rect[3] = a['border'].rect[1]-1
                        else:
                           prev_a['border'].rect[3] = paper['height']

                    block = a['block']
                    prev_a = a

            if prev_a:
                prev_a['border'].rect[3] = paper['height']

            # 採用した物を抽出
            # paper['extacted_article'] = []
            for a in paper['article']:
                if a['flags'] == 1:
                    paper['extacted_article'].append(a)

        a = 0
        #debug
        if DEBUG_STR_INFO >= DEBUG_PRINT_LEVEL:
            debug_print( 'article() -->',level=DEBUG_ROWS_INFO)
            for no, paper in enumerate(self.papers):
                debug_print( '<{}>'.format(no),level=DEBUG_ROWS_INFO)
                debug_print( 'blocks {}'.format(paper['blocks'][0]['blocks']),level=DEBUG_ROWS_INFO)
                for a in paper['article']:
                    debug_print( '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t({}\t{}\t{}\t{})'.format(a['col'],a['score'],a['flags'],a['article_no'],a['text'],a['bounds'].get_left(),a['bounds'].get_top(),a['bounds'].get_right(),a['bounds'].get_bottom(), a['row_no'], a['block'],a['border'].get_left(),a['border'].get_top(),a['border'].get_right(),a['border'].get_bottom()),level=DEBUG_STR_INFO)

            debug_print( 'article() <--',level=DEBUG_ROWS_INFO)

    #def find_article(self):

    #    article_no = 1

    #    for page, paper in enumerate(self.papers):
    #        article = paper['article']
    #        if article == None:
    #            continue

    #        for a in article:
    #            i = 0

    article_note_pat = re.compile(r'^[(（].+[)）]$')
    # 第n条のブロック毎に行をまとめる
    def find_article_rows(self):

        rows = []
        prev_row = None
        article_no = -1

        serial = 0
        for no, paper in enumerate(self.papers):
            extacted_article = paper['extacted_article']
            article_max = len(extacted_article)
            article = 0
            found = False

            for row in paper['rows']:
                # 通しの行番号をつける
                row['serial_row'] = serial
                serial += 1

                if article < article_max: # 条文
                    if extacted_article[article]['border'].is_topleft_included(row['chars'][0]['bounds']):
                    #if extacted_article[article]['border'].is_topleft_included(row['bounds']):
                    #if extacted_article[article]['border'].is_included(row['bounds'],True):
                        article_no = extacted_article[article]['article_no']
                        flags = 1#extacted_article[article]['article_no']
                        found = True
                    else:
                        if found:
                            article += 1
                            if article < article_max and extacted_article[article]['border'].is_included(row['bounds'],True):
                                article_no = extacted_article[article]['article_no']
                                flags = 2#extacted_article[article]['article_no']
                                found = True
                            else:
                                found = False
                                flags = -2
                        else:
                            flags = -3

                else:
                    if found:
                        flags = 0#found
                    else:
                        flags = -1

                r = {'article_no':article_no, 'article':article, 'flags':flags, 'text':row['text'], 'row':row}
                rows.append(r)

                # 第n条の前の行が(*)の場合に条文のブロックに含める
                if prev_row:
                    if prev_row['article_no'] != r['article_no']:
                        if self.article_note_pat.search(prev_row['text']):
                            prev_row['article_no'] = r['article_no']

                prev_row = r

            paper['texts'] = paper['rows']


        # 元データにここで求めた新しい情報をセット
        #for r in rows:
        #    row = r['row']
        #    row['article_no'] = r['article_no']
        #    for c in row['chars']:
        #        c['row'] = row

        #    bbb = 0

        # 検索用データリストを作成
        combine_rows = []
        row = None
        for r in rows:
            # 元データにここで求めた新しい情報をセット
            nr = r['row']
            nr['article_no'] = r['article_no']
            for c in nr['chars']:
                c['row'] = nr

            # 新しい情報リストにセット
            if r['article_no'] == -1 or row == None or r['article_no'] != row['article_no']:
                row = copy.copy(r['row'])
                row['bounds'] = copy.deepcopy(row['bounds']) # 元データを保持

                row['done'] = WORD_SPLIT_DONE_NON
                combine_rows.append(row)

            else:
                row['text'] += r['text']
                row['bounds'].expand(r['row']['bounds'])
                row['chars'] += r['row']['chars']

                bbb = 0

        if DEBUG_ROWS_INFO >= DEBUG_PRINT_LEVEL:
            debug_print( 'article_rows[rows] -->',level=DEBUG_ROWS_INFO)
            for t in rows:
                debug_print( '{} : {} : {} : {}'.format(t['article'], t['flags'], t['article_no'], t['text']),level=DEBUG_ROWS_INFO)
            debug_print( 'article_rows <--',level=DEBUG_ROWS_INFO)

            debug_print( 'article_rows[combine_rows] -->',level=DEBUG_ROWS_INFO)
            for t in combine_rows:
                debug_print( '{} : {} : {}:{} : {} : {}'.format(t['serial_row'], t['row_no'], t['page'], t['block'], t['article_no'], t['text']),level=DEBUG_ROWS_INFO)
            debug_print( 'article_rows <--',level=DEBUG_ROWS_INFO)

        return combine_rows

    #def block_rows(self):

    #    extacted_texts = []
    #    prev_text = None

    #    serial = 0
    #    for no, paper in enumerate(self.papers):
    #        for row in paper['rows']:
    #            # 通しの行番号をつける
    #            row['serial_row'] = serial
    #            serial += 1

    #            for a in paper['extacted_article']:
    #                b = 0
    #                if a['border'].is_included(row['bounds'],True):
    #                    if prev_text and prev_text['article_no'] == a['article_no']:
    #                        prev_text['text'] += row['text']
    #                    else:
    #                        for t in extacted_texts:
    #                            if t['article_no'] == a['article_no']:
    #                                t['text'] += row['text']
    #                                prev_text = t
    #                                break
    #                        else:
    #                            t = {'article_no':a['article_no'], 'text':row['text']}
    #                            extacted_texts.append(t)
    #                            prev_text = t
    #                    break
    #            else:
    #                # ブロック外
    #                extacted_texts.append({'article_no':-1, 'text':row['text']})

    #        paper['texts'] = paper['rows']

    #    paper['extacted_texts'] = extacted_texts

    #    debug_print( 'block_rows -->',level=DEBUG_ROWS_INFO)
    #    for t in extacted_texts:
    #        debug_print( '{} : {}'.format(t['article_no'], t['text']),level=DEBUG_ROWS_INFO)
    #    debug_print( 'block_rows <--',level=DEBUG_ROWS_INFO)

    #    a = 1

    def revise_tilt_old(self, img, filename=None):
        #gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        #edges = cv2.Canny(gray,600,600,apertureSize = 3)
        #lines = cv2.HoughLines(edges,1,np.pi/180,400)

        ##minLineLength = 400
        ##maxLineGap = 100
        ##linesP = cv2.HoughLinesP(edges,1,np.pi/180,100,minLineLength,maxLineGap)
        ##img2 = img.copy()
        ##for line in linesP:
        ##    for x1,y1,x2,y2 in line:
        ##        cv2.line(img2,(x1,y1),(x2,y2),(0,255,0),2)


        #img2 = img.copy()
        #angle = 0
        #a = 0
        #for line in lines:
        #    for rho,theta in line:
        #        a = np.cos(theta)
        #        b = np.sin(theta)
        #        x0 = a*rho
        #        y0 = b*rho
        #        x1 = int(x0 + 1000*(-b))
        #        y1 = int(y0 + 1000*(a))
        #        x2 = int(x0 - 1000*(-b))
        #        y2 = int(y0 - 1000*(a))

        #        if theta > 3 or (0 < theta < 0.1): #縦線の場合
        #            angle =180/np.pi * theta - 180
        #        elif theta > 1.5 and theta < 1.65: #横線の場合
        #            angle =180/np.pi * theta - 90

        #        cv2.line(img2,(x1,y1),(x2,y2),(0,255,0),2)
        #        #if abs(a) < abs(angle):
        #        #    a = angle
        #angle = a

        #cv2.imwrite(filename+'.edges.jpg', img2)

        #angle = 0
        #for rho,theta in lines[0]:
        #  if theta > 3 or (0 < theta < 0.1): #縦線の場合
        #    angle =180/np.pi * theta - 180
        #  elif theta > 1.5 and theta < 1.65: #横線の場合
        #    angle =180/np.pi * theta - 90

        angle = self.get_degree(img)

#        print(theta)
        if angle == 0:
            if filename:
                cv2.imwrite(filename, img)
                os.chmod(filename, FILE_PARMITION)
            return img

        #画像の中心を指定
        height = img.shape[0]
        #幅を定義
        width = img.shape[1]
        #回転の中心を指定
        center = (int(width/2), int(height/2))
        #回転角を指定(ラジアンではなく角度)
        #angle = angle
        #スケールを指定
        scale = 1.0
        #getRotationMatrix2D関数を使用
        trans = cv2.getRotationMatrix2D(center, angle , scale)
        #アフィン変換
        image2 = cv2.warpAffine(img, trans, (width,height),borderValue=(255, 255, 255))
        #画像の保存
        if filename:
            cv2.imwrite(filename, image2)
            os.chmod(filename, FILE_PARMITION)

        return image2

    # 表が含まれている領域を探す
    def find_table_area(self, img_org):
        img = img_org.copy()

        # BGR -> グレースケール
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.blur(gray,(5,5))
        # エッジ抽出 (Canny)
        edges1 = cv2.Canny(gray, 100, 500, apertureSize=3) # 膨張処理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges1 = cv2.dilate(edges1, kernel)

        left, top = img.shape[0], img.shape[1]
        right = bottom = 0

        contours,hierarchy = cv2.findContours(edges1,cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        # 面積でフィルタリング

        for cnt, hrchy in zip(contours, hierarchy[0]):
            if cv2.contourArea(cnt) < 3000:
                continue # 面積が小さいものは除く
            if hrchy[3] == -1:
                continue  # ルートノードは除く

            x, y, w, h = cv2.boundingRect(cnt)
            if left > x:
                left = x
            if top > y:
                top = y
            if right < (x+w):
                right = (x+w)
            if bottom < (y+h):
                bottom = (y+h)
            a = 0

        return Bound(left=left,top=top,right=right,bottom=bottom)


    # 輪郭抽出
    def rinkaku(self, fname, img, filename=None):
        blank = np.zeros((img.shape[0], img.shape[1], 3))

        contours,hierarchy = cv2.findContours(fname,cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        # 面積でフィルタリング
        rects = []
        for cnt, hrchy in zip(contours, hierarchy[0]):
            if cv2.contourArea(cnt) < 3000:
                continue # 面積が小さいものは除く
            if hrchy[3] == -1:
                continue  # ルートノードは除く
            # 輪郭を囲む長方形を計算する。
            rect = cv2.minAreaRect(cnt)
            rect_points = cv2.boxPoints(rect).astype(int)
            rects.append(rect_points)

        # x-y 順でソート
        rects = sorted(rects, key=lambda x: (x[0][1], x[0][0]))  # 描画する。
        for i, rect in enumerate(rects):
            color = np.random.randint(10, 255, 3).tolist()
            cv2.drawContours(img, rects, i, color, 2)
            cv2.putText(img, str(i), tuple(rect[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 3)
            cv2.drawContours(blank, rects, i, color, 2)
            cv2.putText(blank, str(i), tuple(rect[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 3)

        if filename:
            cv2.imwrite(filename, img)
            os.chmod(filename, FILE_PARMITION)
            cv2.imwrite(filename+'.bl.jpg', blank)
            os.chmod(filename+'.bl.jpg', FILE_PARMITION)

        return rects

    def find_box(self, filename, img_org, no):
        img = img_org.copy()
        #img = cv2.imread(filename)

        #img = self.revise_tilt(img,filename+'.tilt.jpg')

        # BGR -> グレースケール
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.blur(gray,(5,5))
        # エッジ抽出 (Canny)
        edges1 = cv2.Canny(gray, 100, 500, apertureSize=3) # 膨張処理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges1 = cv2.dilate(edges1, kernel)
        fname=''

        rects = self.rinkaku(edges1, img, filename+'.box.jpg')
        self.table['rects'] = rects
        boxes = []

        debug_print( 'find_box({},{}) -->'.format(no,filename),level=DEBUG_STR_INFO)
        for i, r in enumerate(self.table['rects']):
            b = Bound(np_array=r)
            boxes.append(b)

            #for h in self.table['heading']:
            #    a = 0
            debug_print( '{}:{}\t{}\t{}\t{}'.format(i, b.get_left(),b.get_top(),b.get_right(),b.get_bottom()),level=DEBUG_STR_INFO)
            a = 1

        debug_print( 'find_box({},{}) <--'.format(no,filename),level=DEBUG_STR_INFO)

        self.table['boxes'] = boxes

        return boxes

    def predict_type_of_paper(self, path):
        imsize = (32, 32)

        def load_image(path):
            img = Image.open(path)
            img = img.convert('RGB')
            # 学習時に、(128, 128, 3)で学習したので、画像の縦・横は今回 変数imsizeの(128, 128)にリサイズします。
            img = img.resize(imsize)
            # 画像データをnumpy配列の形式に変更
            img = np.asarray(img)
            img = img / 255.0


            return img


        global keras_model

        # keras_model = load_model(keras_param)
        img = load_image(path)
        prd = keras_model.predict(np.array([img]))
        [[a,b,c,d]] = keras_model.predict(np.array([img]))
        debug_print(str(int(a*1000)/10)+"% "+str(int(b*1000)/10)+"% "+str(int(c*1000)/10)+"% "+str(int(d*1000)/10)+"% ",level=DEBUG_STR_INFO) # 精度の表示
        # debug_print(str(int(a*1000)/10)+"% "+str(int(b*1000)/10)+"% ",str(int(c*1000)/10)+"% ",str(int(d*1000)/10)+"% ",level=DEBUG_STR_INFO) # 精度の表示
        #   print(prd) # 精度の表示
        prelabel = np.argmax(prd, axis=1)
        if prelabel == 0:
            debug_print(">>> 捺印",level=DEBUG_STR_INFO)
        elif prelabel == 1:
            debug_print(">>> 条文",level=DEBUG_STR_INFO)
        elif prelabel == 2:
            debug_print(">>> 表",level=DEBUG_STR_INFO)
        elif prelabel == 3:
            debug_print(">>> 図画",level=DEBUG_STR_INFO)

        return prelabel

    def OCR_cache(self, READ):
        ret = False
        vsn_file = self.root_str + CACHE_FILE_EXT
        if READ: # 読み込み
            try:
                if os.path.exists(vsn_file):
                    with open(vsn_file, mode='rb') as f:
                        cache = pickle.load(f)

                        self.article_no = cache.article_no
                        self.calibration = copy.deepcopy(cache.calibration)
                        self.combine_rows = copy.deepcopy(cache.combine_rows)
                        self.out_calibration = copy.deepcopy(cache.out_calibration)
                        self.papers = copy.deepcopy(cache.papers)


                        ret = True
                    # os.chmod(vsn_file, FILE_PARMITION)
            except Exception as e:
                print(str(e))
        else: # 書き込み
            try:
                with open(vsn_file, mode='wb') as f:
                    cache = pickle.dump(self, f)
                    ret = True

            except Exception as e:
                print(str(e))
            finally:
                os.chmod(vsn_file, FILE_PARMITION)

        return ret
    
    def OCR(self):

        # キャッシュの読み込み
        #if self.OCR_cache(True) == True:
        #    return

        if self.extension.upper() == PDF_FILE_EXT:
            # for PDF file
            jar_file = os.path.join(os.path.dirname(__file__),'readpdftext-jar-with-dependencies.jar')

            # PDFは1ファイル(self.number_of_images==1)のみとする
            file_name = self.root_str + str(0) + self.extension
            if str(1) in self.open_page_list:

                response = subprocess.check_output(['java', '-Xms1m', '-Xmx1024m', '-jar', jar_file, file_name, '2>', 'nul'])
                ###with io.open(file_name+'.txt', 'wb') as pdf_txt_file:
                ###    pdf_txt_file.write(response)

                pdf_str = response.decode(util.defines.PDF_ENCODING)

                #################
                #pdf_str = pdf_str.replace(r'"\"', r'"\\"')

                pdf_json = json.loads(pdf_str,encoding=util.defines.PDF_ENCODING)

                #################

                image_h, image_w = pdf_json['height'], pdf_json['width']

                image_max_no = len(pdf_json['xy'])

        else:
            # for JPG file
    #        client = vision.ImageAnnotatorClient()
            #GOOGLE_APPLICATION_CREDENTIALS=C:\Users\aloha\source\repos\iTaskScanPapers\service-account-file.json
            account_file = os.path.join(os.path.dirname(__file__),'service-account-file.json')
            # [pmj-aitext-1] Cloud Run では鍵ファイルを置かず、サービスアカウントの権限(ADC)で呼ぶ
            if os.path.exists(account_file):
                client = vision.ImageAnnotatorClient.from_service_account_json(account_file)
            else:
                client = vision.ImageAnnotatorClient()
            #client = vision_v1.ImageAnnotatorClient.from_service_account_json(account_file)

            image_max_no = self.number_of_images

        total = 0
        self.xyl={}
        self.xym={}
        self.xyr={}
        self.xybs={}
        taisyakuTaisyouPage=9999
        for no in range(0, image_max_no):
            open_page = str(no+1) in self.open_page_list
            if self.extension.upper() != PDF_FILE_EXT:
                file_name = self.root_str + str(no) + self.extension
                #file_name = os.path.join(os.path.dirname(__file__),str(no) + self.extension)

            start = time.time()

            print('OCR<{}>:{}...'.format(open_page,file_name))
            debug_print('OCR<{}>:{}...'.format(open_page,file_name),level=DEBUG_STR_INFO)
            extacted_texts = []
            #first_text = 1
            #no = 0

            height_average  = 10
            width_average   = 10

            ave_h = 0
            ave_w = 0
            cnt_w = 0

            texts = []

            source_texts = []

            source_characters = []

            image_h, image_w = 0, 0
            response = None

            img = None
            contours = None
            angle = 0

            if open_page:
                if self.extension.upper() == PDF_FILE_EXT:
                    #pdf_file = True
                    #first_text = 0
                    #pdf_file = 'c:\\temp\\test07.pdf'
                    #pdf_file = os.path.join(os.path.dirname(__file__),'noread_01.pdf')

                    for item in pdf_json['xy'][no]:
                        text = {}
                        text['text'] = item['text']

                        sx = item['SX']
                        sy = item['SY']
                        ex = item['EX']
                        ey = item['EY']

                        text['bounds'] = Bound(left=int(sx),top=int(sy),right=int(ex),bottom=int(ey))

                        source_texts.append(text)

                    if self.character_bound or self.character_center:
                        source_characters = source_texts[:]

                else:
                    if self.ai_keras_process:
                    # if AI_KERAS_PROCESS and self.ai_keras_process:
                        predict = self.predict_type_of_paper(file_name)
                    else:
                        predict = 0
                    if predict != 3: # 3:図面は対象外とする
                        #pdf_file = False
                        #first_text = 1

                        # image size
                        org_img = cv2.imread(file_name)

                        # 前処理
                        img = self.preprocess_loaded_image(org_img)

                        img, contours, angle, table_bound = self.revise_tilt(img,file_name+TILT_FILE) # デバッグ用にfile_name+'.tilt.jpg'を渡す
                        image_h, image_w = img.shape[0], img.shape[1]

    ###                    # Loads the image into memory
    ###                    with io.open(file_name+'.tilt.jpg', 'rb') as image_file:
    ####                    with io.open(file_name, 'rb') as image_file:
    ###                        content = image_file.read()

    ###                    #image = vision.Image(content=content)
    ###                    image = types.Image(content=content)

                        # vsn_file = os.path.splitext(file_name)[0] + CACHE_FILE_EXT
                        # response = None
                        # try:
                        #     if os.path.exists(vsn_file):
                        #         with open(vsn_file, mode='rb') as f:
                        #             #vsn_response = f.read()
                        #             #response = AnnotateImageResponse.deserialize(vsn_response)
                        #             response = pickle.load(f)
                        #         # os.chmod(vsn_file, FILE_PARMITION)
                        # except Exception as e:
                        #     print(str(e))

                        # tilt_img = self.rotate_image(org_img,angle,None)
                        #「株主資本等変動計算書」　等キーワードが一番上になるので、画像上部を消す前に、テキストを取り出し、判断する
                        source_texts, source_characters, response, cache_data, img_t, _ = super().get_text_detection(no, img, file_name, client, def_cache_data={'rotate':None})
                        haveExceptionFlag=False
                        #if self.document_judgment_flag == "kojin" or 'konjin' in self.document_judgment_flag :
                        #    print("2525 is kojin!");
                        #else :
                        #    source_texts,source_characters,haveExceptionFlag=page_jyogai(source_texts,source_characters,"株主資本等変動計算書",7)
                        #if haveExceptionFlag==False :
                        #    source_texts,source_characters,haveExceptionFlag=page_jyogai(source_texts,source_characters,"製造原価報告書",6)


                        #エリア読み取り
                        if self.document_judgment_flag == "lines" :
                            #img, img_bk = pre_process_imag_area.preprocess_image_v2ac(img)

                            filename2 = file_name+'.real.jpg'
                            cv2.imwrite(filename2, img)
                            os.chmod(filename2, FILE_PARMITION)
                            debug_print( '##############################engine2>OCR 2558#'+str(no)+'#',level=DEBUG_ROWS_INFO)
                            del_line_str_right_flag=False
                            if self.del_line_str_right != "NONE" :
                                
                                oklist=self.del_line_str_right.split(',')
                                if str(no) in oklist :
                                    debug_print( '##############################engine2>OCR 2563#'+str(no)+'#',level=DEBUG_ROWS_INFO)
                                    del_line_str_right_flag=True
                                    dlsr_ok_flag=True
                                    try:
                                        newimg,img_disp,rs2_ascend,rs3_ascend,_=pre_process_imag_area.del_line_str_right(img,img)
                                    except Exception as err:
                                        import traceback
                                        error_message = traceback.format_exc()
                                        print(f"Unexpected {error_message=}, {type(error_message)=}")
                                        debug_print( '#####################################################################################',level=DEBUG_ROWS_INFO)
                                        debug_print( '#####################################################################################',level=DEBUG_ROWS_INFO)
                                        debug_print( '##############################engine2>OCR 2570 error:#'+str(error_message)+'#',level=DEBUG_ROWS_INFO)
                                        debug_print( '#####################################################################################',level=DEBUG_ROWS_INFO)
                                        debug_print( '#####################################################################################',level=DEBUG_ROWS_INFO)
                                        dlsr_ok_flag=False
                                    
                                   

                                    if dlsr_ok_flag :
                                        #移動後文字列
                                        plot_labeling_box(newimg, rs3_ascend)
                                        filename2 = file_name+'.rs3_ascend.jpg'
                                        cv2.imwrite(filename2, newimg)
                                        os.chmod(filename2, FILE_PARMITION)

                                        #移動前文字列
                                        plot_labeling_box(img, rs2_ascend)
                                        filename2 = file_name+'.rs2_ascend.jpg'
                                        cv2.imwrite(filename2, img)
                                        os.chmod(filename2, FILE_PARMITION)
                                        source_texts, source_characters, response, cache_data, img_t, _ = super().get_text_detection(no, newimg, file_name, client, def_cache_data={'rotate':None})
                                        self.restore_position_detection_text(source_characters,rs2_ascend,rs3_ascend)
                            if del_line_str_right_flag==False :
                                debug_print( '##############################engine2>OCR 2582#'+self.del_line_str_right+'#',level=DEBUG_ROWS_INFO)
                                source_texts, source_characters, response, cache_data, img_t, _ = super().get_text_detection(no, img, file_name, client, def_cache_data={'rotate':None})
                            paper = {}
                            image_h, image_w = img.shape[0], img.shape[1]
                            paper['width']  = image_w
                            paper['height'] = image_h
                            paper['image'] = img
                            paper['contours'] = contours
                            paper['angle']    = angle
                            paper['rotate']   = None
                            paper['table_block'] = []
                            paper['table_row_range'] = [False,False]
                            paper['characters'] = source_characters
                            paper['source_texts'] = source_texts
                            self.papers.append(paper)
                            if no == image_max_no-1 :
                                return
                            continue

                        # キャッシュ(vsn)か(キャッシュがなければ)VisionAPIから内部データへ(派生の場合にimgが変更される時もある)

                        tmpimg=cv2pil(img)
                        img=enhanced(tmpimg)
                        # 黄色除去(del_yellow)と回転（r_flags）と傾き補正（angle）はしたいが、その他の画像処理（*tilt.jpgは文字が濃くなっていたりノイズ除去等）
                        #黄色除去(del_yellow)

                        img_t=pre_process_image.del_yellow(img)
                        if img_t is not None :
                            img2 = img_t.copy()
                            imgkatamuki = img_t.copy()
                        else :
                            img2 = img.copy()
                            imgkatamuki = img.copy()
                        if 'img_t' in locals() : del img_t
                        if image_w > image_h :
                            cv2.rectangle(imgkatamuki, (0, 0), (image_w, round(image_h*0.03)), (255, 255,255), cv2.FILLED)
                        filename2 = file_name+'.katamuki.jpg'
                        cv2.imwrite(filename2, imgkatamuki)
                        # 黄色除去画像で回転角取得
                        _, contours, angle, table_bound = super().revise_tilt(imgkatamuki)

                        # 元画像を回転
                        imgtit = self.rotate_image(img,angle,None,False)
                        #img_t = self.rotate_image(img2,angle,None,False)
                        #imgtit = self.rotate_image(imgkatamuki,angle,None,False)
                        img_t = self.rotate_image(imgkatamuki,angle,None,False)
                        filename2 = file_name+'.katamuki1.jpg'
                        #cv2.imwrite(filename2, imgtit)
                        if imgtit is None :
                            imgtit = img.copy()
                        if img_t is not None :
                            img2 = img_t.copy()
                        if 'img_t' in locals() : del img_t
                        #回転（r_flags）
                        #     文字を取る
                        if haveExceptionFlag==False :
                            source_texts, source_characters, response, cache_data, img_t, _ = super().get_text_detection(no, img2, file_name, client, def_cache_data={'rotate':None})
                        if img_t is not None :
                            img2 = img_t.copy()
                        if 'img_t' in locals() : del img_t
                        #回転の判定＆実施
                        p = re.compile('[\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002EBEF]+')
                        cnt = 0
                        #20220923 mizuno------>
                        flg = 0
                        checkwords=["貸借","損益","販売","収支","負債","株式","売上","利益","資産","合計","支払","営業","収入","車輛","車両","商品","棚卸","期末","給料","現金","科目","所在地","その他","経費","給与"]
                        if self.document_judgment_flag != "kojin" and 'konjin' not in self.document_judgment_flag :
                            checkwords=["貸借","損益","販売","青色","収支","負債","株式","期首","期末","費用","損益","棚卸","利益","株主","会社","資産","令和","合計","支払","営業","収入","株式","会社","株式会社","棚卸","期末"]
                        r_flags=None
                        for t in source_texts:
                          l = len(t['text'])
                          if l == 2 and p.fullmatch(t['text']) and flg ==0:
                            for w in checkwords:
                              if t['text']==w:
                                flg = 1
                                b1 = source_characters[cnt]['bounds'].rect
                                b2 = source_characters[cnt+1]['bounds'].rect
                                break
                          cnt += l
                        #checkwordsに当てはまらなかった場合の処理
                        cnt = 0
                        if flg ==0:
                          for t in source_texts:
                              l = len(t['text'])
                              if l == 2 and p.fullmatch(t['text']):
                                b1 = source_characters[cnt]['bounds'].rect
                                b2 = source_characters[cnt+1]['bounds'].rect
                                break
                              cnt += l
                          else:
                              b1 = b2 = None
                        #<--------------20220923 mizuno

                        if b1 and b2:
                            x1 ,y1, x2, y2 = int(b1[0]),int(b1[1]),int(b2[0]),int(b2[1])
                            a, b = abs(x2-x1), abs(y2-y1)

                            if a > b and x2-x1 > 0:
                                r_flags = -1 # None
                            elif a < b and y2-y1 > 0:
                                r_flags = cv2.ROTATE_90_COUNTERCLOCKWISE
                            elif a > b and x2-x1 < 0:
                                r_flags = cv2.ROTATE_180
                            elif a < b and y2-y1 < 0:
                                r_flags = cv2.ROTATE_90_CLOCKWISE
                            else:
                                r_flags = None

                            if r_flags is not None:
                                if r_flags != -1:
                                    img_t = cv2.rotate(img2, r_flags)
                                    if img_t is not None :
                                        img2 = img_t.copy()
                                    if 'img_t' in locals() : del img_t
                                else:
                                    vsn_file = self.get_cache_file_name(file_name)
                                    self.cache_write(vsn_file, response, {'rotate':r_flags})
                        filename2 = file_name+'.katamuki2.jpg'
                        cv2.imwrite(filename2, img2)
                        # 黄色除去画像で回転角取得
                        _, contours, angle, table_bound = super().revise_tilt(img2)


                        # 色を濃くする
                        #_, bw_image_cv2_225 = cv2.threshold(img2, 225, 255, cv2.THRESH_BINARY)
                        #img2 = cv2.cvtColor(bw_image_cv2_225, cv2.COLOR_BGR2RGB)


                        # 元画像を傾き補正

                        imgtit = self.rotate_image(img2,angle,None,False)
                        img_t = self.rotate_image(img2,angle,None,False)
                        if imgtit is None :
                            imgtit = img.copy()
                        r_flags=None
                        if self.special_handling=="geminihoujin" :
                            geminihoujin=999
                        if self.special_handling=="special_handling0" :
                            #個人特別書式####################
                            special_handling0_r,special_handling0_c,special_handling0_stats_v,special_handling0_boxes,img_sh=kojin_special_handling0(img_t)
                            filename2 = file_name+'.special_handling.jpg'
                            cv2.imwrite(filename2, img_sh)
                            self.special_handling0_boxes=special_handling0_boxes
                            source_texts, source_characters, response, cache_data, img_t, rotate  = self.get_text_detection_kojin(no, img_t, file_name, client)
                            img,kojin_tri=pre_process_image.replace_triangle_k(img_t)
                            
                            paper = {}
                            image_h, image_w = img_t.shape[0], img_t.shape[1]
                            paper['width']  = image_w
                            paper['height'] = image_h
                            paper['image'] = img_t
                            paper['contours'] = contours
                            paper['angle']    = angle
                            paper['rotate']   = rotate
                            paper['characters'] = source_characters
                            paper['boxes']=special_handling0_boxes;
                            self.papers.append(paper)
                            self.kojin_tri[no]=kojin_tri
                            return
                        if self.special_handling=="special_handling1" :
                            #個人特別書式前期あり####################
                            special_handling0_r,special_handling0_c,special_handling0_stats_v,special_handling0_boxes,img_sh=kojin_special_handling1(img_t)
                            filename2 = file_name+'.special_handling.jpg'
                            cv2.imwrite(filename2, img_sh)
                            self.special_handling0_boxes=special_handling0_boxes
                            source_texts, source_characters, response, cache_data, img_t, rotate  = self.get_text_detection_kojin(no, img_t, file_name, client)
                            img,kojin_tri=pre_process_image.replace_triangle_k(img_t)
                            
                            paper = {}
                            image_h, image_w = img_t.shape[0], img_t.shape[1]
                            paper['width']  = image_w
                            paper['height'] = image_h
                            paper['image'] = img_t
                            paper['contours'] = contours
                            paper['angle']    = angle
                            paper['rotate']   = rotate
                            paper['characters'] = source_characters
                            paper['boxes']=special_handling0_boxes;
                            self.papers.append(paper)
                            self.kojin_tri[no]=kojin_tri
                            return
                        if (self.document_judgment_flag == "kojin" or 'konjin' in self.document_judgment_flag) and self.special_handling!="special_handling0" and self.special_handling!="special_handling1" :
                            img,kojin_tri=pre_process_image.replace_triangle_k(img_t)

                            if img is not None :
                                filename2 = file_name+'.S_R.jpg'
                                cv2.imwrite(filename2, img)
                                img2 = img.copy()
                            self.kojin_tri[no]=kojin_tri
                            if img2 is not None :
                                filename2 = file_name+'.befor_del_line.jpg'
                                cv2.imwrite(filename2, img2)
                            if 'img_t' in locals() : del img_t
                            #noicelockを実行するかどうかを判断するため、まず、青色申告書ですかを判断する　
                            isAoiroShikokuKesansyo=False
                            isTaisyakuTaisyou=False
                            isZatusyunyu=False
                            minx=1000000
                            maxx=0
                            for c in source_characters:
                                if c['bounds'].rect[0]<minx :
                                    minx = c['bounds'].rect[0]
                                if c['bounds'].rect[2]>maxx :
                                    maxx = c['bounds'].rect[2]
                            text,x1,y1,x2,y2,c_h=get_right_characters(source_characters,"損益計算書",0.8)
                            havesonekikeisansyo=False
                            if x1 is not None and x1<minx+(maxx-minx)/2 :
                                havesonekikeisansyo=True
                            
                            if (hikaku_characters(source_characters,"分所得税青色申告決算書",0.8) or havesonekikeisansyo) and hikaku_characters_shikokub(source_characters) == False:
                                #文字で青色申告決算書の判定をする
                                isAoiroShikokuKesansyo=True
                            elif (hikaku_characters(source_characters,"資産",0.8) or havesonekikeisansyo) and (taisyakuTaisyouPage >100 or no>2) and hikaku_characters_shikokub(source_characters) == False :
                                #文字で貸借対照表の判定をする
                                isTaisyakuTaisyou=True
                                taisyakuTaisyouPage=no
                            elif (hikaku_characters(source_characters,"負債",0.8) or havesonekikeisansyo) and (taisyakuTaisyouPage >100 or no>2) and hikaku_characters_shikokub(source_characters) == False :
                                #文字で貸借対照表の判定をする
                                isTaisyakuTaisyou=True
                                taisyakuTaisyouPage=no
                            elif (hikaku_characters(source_characters,"資本",0.8) or havesonekikeisansyo) and (taisyakuTaisyouPage >100 or no>2) and hikaku_characters_shikokub(source_characters) == False :
                                #文字で貸借対照表の判定をする
                                isTaisyakuTaisyou=True
                                taisyakuTaisyouPage=no
                            elif hikaku_characters(source_characters,"貸借対照表",0.7) and (taisyakuTaisyouPage >100 or no>2) and hikaku_characters_shikokub(source_characters) == False :
                                #文字で貸借対照表の判定をする
                                isTaisyakuTaisyou=True
                                taisyakuTaisyouPage=no
                            elif hikaku_characters(source_characters,"資産負債調",0.7) and (taisyakuTaisyouPage >100 or no>2) and hikaku_characters_shikokub(source_characters) == False:
                                #文字で貸借対照表の判定をする
                                isTaisyakuTaisyou=True
                            elif hikaku_characters(source_characters,"資產負債調",0.7) and (taisyakuTaisyouPage >100 or no>2) and hikaku_characters_shikokub(source_characters) == False:
                                #文字で貸借対照表の判定をする
                                isTaisyakuTaisyou=True
                            elif hikaku_characters(source_characters,"給料賃金の内訳",0.8):
                                #文字で貸借対照表の判定をする
                                isZatusyunyu=True
                            elif hikaku_characters(source_characters,"専従者給与の内訳",0.8):
                                #文字で貸借対照表の判定をする
                                isZatusyunyu=True
                            elif hikaku_characters(source_characters,"雑収入",0.9):
                                #文字で貸借対照表の判定をする
                                isZatusyunyu=True
                            elif no==0 and hikaku_characters_shikokub(source_characters) == False:
                                #文字で青色申告決算書の判定をする
                                isAoiroShikokuKesansyo=True
                            elif no==1 and taisyakuTaisyouPage>99 and image_max_no==2 and hikaku_characters(source_characters,"所得から差し引かれる",0.8) == False :
                                isTaisyakuTaisyou=True
                                taisyakuTaisyouPage=no
                            elif no==1 and image_max_no==3:
                                isZatusyunyu=True
                            elif no==2 and hikaku_characters_shikokub(source_characters) == False:
                                #文字で青色申告決算書の判定をする
                                isTaisyakuTaisyou=True
                                taisyakuTaisyouPage=no
                            if isAoiroShikokuKesansyo :
                                try:
                                    img2,xyl,xym,xyr,white_image=noicelock(img2)

                                    filename2 = file_name+'.white_image.jpg'
                                    cv2.imwrite(filename2, white_image)
                                    source_texts_white, source_characters_white, response_white, cache_data_white, img2_white, white_ = super().get_text_detection(no, white_image, filename2, client, def_cache_data={'rotate':None})
                                    v=0
                                    for c in source_characters_white:
                                        if c['text']=="C":
                                            source_characters_white[v]['text']="0"
                                        if c['text']=="D":
                                            source_characters_white[v]['text']="0"
                                        if c['text'].isdecimal()==False:
                                            del source_characters_white[v]
                                        v=v+1
                                        
                                    self.xyl[no]=xyl
                                    self.xym[no]=xym
                                    self.xyr[no]=xyr
                                    self.xyl[1000]=source_characters_white
                                    debug_print( '2868 page_no {} : 青色申告決算書'.format(no),level=DEBUG_ROWS_INFO)
                                except:
                                    import traceback
                                    traceback.print_exc()
                                    print("######xxxxxxxxxxxxxxxxxxxxxxxxXXXXXXX########")
                                    print("######page noicelock is failed########")
                                    print("######xxxxxxxxxxxxxxxxxxxxxxxxXXXXXXX########")
                            elif isTaisyakuTaisyou :
                                try:
                                    debug_print( '2879 page_no {} : 貸借対照表'.format(no),level=DEBUG_ROWS_INFO)
                                    #filename2 = file_name+'.2878.jpg'
                                    #cv2.imwrite(filename2, img2)
                                    img2,xybs=noicelock_bs(img2)
                                    debug_print(f"xybs len={len(xybs)}", level=DEBUG_ROWS_INFO)
                                    for i, v in enumerate(xybs):
                                        debug_print(f"xybs[{i}]={v}", level=DEBUG_ROWS_INFO)
                                    self.xybs[no]=xybs
                                except:
                                    import traceback
                                    traceback.print_exc()
                                    print("######xxxxxxxxxxxxxxxxxxxxxxxxXXXXXXX########")
                                    print("######page noicelock is failed########")
                                    print("######xxxxxxxxxxxxxxxxxxxxxxxxXXXXXXX########")
                                    taisyakuTaisyouPage=9999
                            if img2 is not None :
                                filename2 = file_name+'.S_R.jpg'
                                cv2.imwrite(filename2, img2)
                            source_texts, source_characters, response, cache_data, img_t, rotate  = self.get_text_detection_kojin(no, img2, file_name, client)
                            filename2 = file_name+'.tilt.jpg'
                            cv2.imwrite(filename2, imgtit)
                        elif self.special_handling!="special_handling0" and self.special_handling!="special_handling1" :

                            if img_t is not None :
                                filename2 = file_name+'.S_R.jpg'
                                cv2.imwrite(filename2, img)
                                img = img_t.copy()
                            if img is not None :
                                filename2 = file_name+'.S_R.jpg'
                                cv2.imwrite(filename2, img)
                                img2 = img.copy()
                            if imgtit is not None :
                                filename2 = file_name+'.tilt.jpg'
                                cv2.imwrite(filename2, imgtit)
                            try:
                                source_texts, source_characters, response, cache_data, img_t, rotate = self.get_text_detection(no, img2, file_name, client)
                                #株主資本等変動計算書
                                if haveExceptionFlag==False :
                                    source_texts1,source_characters1,haveflag=page_jyogai(source_texts,source_characters,"株主資本等変動計算書",8)
                                    if haveflag==False :
                                        source_texts1,source_characters1,haveflag=page_jyogai(source_texts,source_characters,"製造原価報告書",6)
                                    if haveflag==False :
                                        source_texts1,source_characters1,haveflag=page_jyogai2(source_texts,source_characters,"当期(首|末)残高",3)
                                if haveflag==True :
                                    source_texts=source_texts1
                                    source_characters=source_characters1
                            except:
                                paper = {}
                                image_h, image_w = img.shape[0], img.shape[1]
                                paper['path']       = file_name
                                paper['response']   = []
                                paper['width']  = image_w
                                paper['height'] = image_h
                                paper['image'] = img

                                paper['contours'] = []
                                paper['angle']    = angle
                                paper['rotate']   = r_flags
                                paper['extacted_article'] = []
                                paper['article']    = []
                                paper['blocks']     = []
                                paper['rows']       = []
                                paper['texts']      = []
                                paper['characters'] = []
                                paper['col_type'] = []
                                paper['table_block'] = []
                                paper['table_row_range'] = [False,False]
                                self.papers.append(paper)
                                continue

                        rotate=r_flags
                        
                        if img_t is not None :
                            img2 = img_t.copy()
                        if 'img_t' in locals() : del img_t
                        if img2 is not None:
                            # imgが変更された
                            img = img2
                            image_h, image_w = img.shape[0], img.shape[1]

                        # _ = self.rotate_image(org_img,angle,rotate,file_name+TILT_FILE)

                        # ガベージ対象
                        del org_img
                        org_img = None

            # else:
            #     response = None
            #     image_h, image_w = 0, 0

            ocr_time = time.time()

            debug_print('Texts:')

            paper = {}
            paper['path']       = file_name

            paper['response']   = response
            #paper['characters'] = source_characters

            #if pdf_file == False:   # jpg
            #    # image size
            #    img = cv2.imread(file_name)

            #    image_h, image_w = img.shape[0], img.shape[1]

            paper['width']  = image_w
            paper['height'] = image_h

            # 縦線検出のために保存 (メモリ圧迫の場合には再考の必要)
            if self.save_image == False:
                del img
                img = None

            paper['image'] = img

            paper['contours'] = contours
            paper['angle']    = angle
            paper['rotate']   = rotate

            paper['extacted_article'] = []

            #min_x, min_y, max_x, max_y = image_w, image_h, 0, 0
            calib = Bound(left=image_w, top=image_h, right=0, bottom=0)
            calib2 = Bound(left=image_w, top=image_h, right=0, bottom=0)

            for character in source_characters:
                calib2.minmax(character['bounds'])

            calib2.revise()


            if self.analyze != ANALYZE_get_all_character:
                cnt = 0

                # text_annotation --> full_text_annotation
                for cnt, text in enumerate(source_characters):
                #for cnt, text in enumerate(source_texts):

                    texts.append(text)

                    if True:#pdf_file or cnt > 0:
                        bound = text['bounds'] #Bound(text.bounding_poly.vertices)
                        ave_h += bound.get_height()
                        ave_w += bound.get_width()
                        cnt_w += len(text['text']) #text.description)

                        # キャリブレーションの為に最大値最小値を保存
                        calib.minmax(bound)


                # 読み込み文書のキャリブレーション
                calib.revise()
                self.calibration.append({'file':no, 'bound':calib})

                if self.document_judgment_flag == "kojin" :
                    self.document_judgment_flag = 'konjinaoiro'
                
                if cnt == 0:
                    cnt = 1
                if cnt_w == 0:
                    cnt_w = 1

                ave = ave_h
                print('cnt={}(cnt_w={}) ==> ave_w={}(ave_w/cnt_w={}): ave_h={}(ave_h/cnt={})'.format(cnt,cnt_w,ave_w,ave_w/cnt_w,ave_h,ave_h/cnt))
                average_size = ave/cnt/2
    #            height_average  = ave/cnt/2*1.5*self.height_adjust #ave/cnt/2
                height_average  = ave/cnt*self.height_adjust #ave/cnt/2
    #            width_average   = ave/cnt*self.width_adjust
                width_average   = ave_w/cnt_w*self.width_adjust

                print('    adjust={}:size={},height={},width={}'.format(self.height_adjust,average_size,height_average,width_average))
#ここから
                #BOX を探す
                # boxes = self.find_box(file_name,img, no)
                if self.document_judgment_flag != "kojin" and 'konjin' not in self.document_judgment_flag :
                    # 列ブロックを探す
                    blocks = self.find_blocks(source_characters,no,paper)
                    # 行を探す
                    extacted_rows = self.find_rows(source_characters,no,blocks,paper)

                    # 列の縦線を探す
                    # self.find_col_vline(extacted_rows, file_name, img)

                    # 表（明細）を探す
                    self.find_table(extacted_rows, file_name, img, no)
                    # self.find_table(extacted_rows, file_name, img, boxes, no)

                    article, self.article_no = self.collect_article_title(extacted_rows, self.article_no)
                    
                    templ = [d.get('template') for d in self.in_calibration if d.get('file') == int(no)]

                    if self.in_calibration_template:
                        self.out_calibration['parameter'].append({'file':str(no),'template':calib.get_json_rect()})
                    elif self.in_calibration_non:
                        self.out_calibration['parameter'].append({'file':str(no),'bound':calib.get_json_rect()})
                    else:
                        templ_bound = templ[0] if len(templ) > 0 else Bound()
                        self.out_calibration['parameter'].append({'file':str(no),'template':templ_bound.get_json_rect(),'bound':calib.get_json_rect()})

                    paper['article']    = article
                    paper['blocks']     = blocks
                    paper['rows']       = extacted_rows
                paper['texts']      = [] # extacted_temp #extacted_texts

            paper['characters'] = source_characters
            try:
                if get_1_4_flag(source_characters) :
                    self.the_1_4_page=no
                elif self.get('the_1_4_page')==None :
                    self.the_1_4_page=None
            except:
                self.the_1_4_page=None

            debug_print( '##############################document_judgment_flag is '+self.document_judgment_flag+'#############################',level=DEBUG_ROWS_INFO)


            self.papers.append(paper)
            end = time.time()

            t = end-start
            print('>>>>>>>>>>>> OK!\n>{}S : {}S'.format(ocr_time-start,t))

            total += (t)

            # ファイル毎 (処理が重い場合は検討)
            gc.collect()
        
        print('TOTAL===>{}S'.format(total))
        if self.document_judgment_flag != "kojin" and 'konjin' not in self.document_judgment_flag :        
            # すべてのページから第n条のブロックを決める
            self.decision_article()

            # 第n条のブロック毎に行をまとめる
            self.article_rows = self.find_article_rows()
            self.combine_rows = []
            for a in self.article_rows:
                c = copy.deepcopy(a)
                a['article_row'] = c
                self.combine_rows.append(a)

        # self.combine_rows = self.article_rows()

        #####aa = time.time()
        ###### ワード単位に分割
        #####for loop in range(100):
        #####    split_cnt, combine_rows = self.split_words(combine_rows,0,loop)
        #####    if split_cnt == 0:
        #####        break
        #####else:
        #####    b = 0
        #####bb = time.time()

        #####self.combine_rows = combine_rows

        #for no, paper in enumerate(self.papers):
        #    # ワード単位に分割
        #    for loop in range(20):
        #        split_cnt, paper['texts'] = self.split_words(paper['texts'],no,loop)
        #        if split_cnt == 0:
        #            break
        #    else:
        #        b = 0

        # キャッシュの書き込み
#        self.OCR_cache(False)


## 住所検索
#    def find_address(self, txt_src_org):

#        found = False
#        ret_address = None

#        txt_src = txt_src_org.replace(' ','').replace('　','')
#        a1 = ''
#        a2 = ''
#        a3 = ''
#        a4 = ''

#        if city_regex.search(txt_src): # 全てを検索すると重くなるので"市区町村"が含まれているのものだけ
#            for i, city in enumerate(city_list):
#                addr = city[2]
#                ret = addr.search(txt_src)
#                if ret:
#                    a1 = ret.group(0) # 全体
#                    a2 = ret.group(1) # 前（都道府県とは限らない）
#                    a3 = ret.group(2) # 市区町村
#                    a4 = ret.group(3) # 後ろ

#                    if a2:
#                        if pref_list[city[0]-1][1] in a2:
#                            # 都道府県名が含まれていれば、それ以外のものを取り除く
#                            a2 = pref_list[city[0]-1][1]
#                        #含まれていなければそのまま

#                    else:
#                        a2 = ''

#                    ret_address = a2 + a3 + a4
#                    ret_address = ret_address.replace(' ','').replace('　','')

#                    found = True

#        debug_print(txt_src_org,level=DEBUG_BOUND_INFO)
#        if ret_address:
#            debug_print('{}\n{},{},{}\n\n{}'.format(a1,a2,a3,a4,ret_address),level=DEBUG_BOUND_INFO)
#        debug_print('--------------------\n',level=DEBUG_BOUND_INFO)

#        return ret_address if found == True else None

    # 文字が含まれる領域をリストにする
    def bounds_list(self, text, start=0, end=-1):

        bounds_list = []
        char_bounds = None

        if end == -1:
            end = len(text['chars'])

        for i in range(start,end):
            c = text['chars'][i]
            if char_bounds == None or char_bounds['page'] != c['row']['page'] or char_bounds['serial_row'] != c['row']['serial_row']:
                char_bounds = {'page':c['row']['page'], 'serial_row':c['row']['serial_row'], 'bounds':copy.deepcopy(c['bounds'])}
                bounds_list.append(char_bounds)
            else:
                char_bounds['bounds'].expand(c['bounds'])

        result_pos = []
        for bounds in bounds_list:
            pos = {'page':bounds['page']}
            pos.update(**bounds['bounds'].get_bound())
            result_pos.append(pos)

        return result_pos #bounds_list

    # 位置関係　距離による判定
    def find_nearest_word(self, texts, row, regex_ret, type, keyword_opt):
        keyword = row['text']
        found_list = []

        if regex_ret:
            # keywordの先頭文字がある正確な通し行番号
            st = regex_ret.span(0)[0]
            keyword_serial_row = keyword['chars'][st]['row']['serial_row']
            start = st
            end   = regex_ret.span(0)[1]
        else:
            keyword_serial_row = keyword['serial_row']
            st = 0
            end = -1

        keyword_bounds = self.bounds_list(keyword, st, end)

        upper = keyword_serial_row - 3   # 上限
        lower = keyword_serial_row + 3   # 下限

        for text in texts:
            if upper <= text['text']['serial_row'] <= lower:
                if keyword['article_no'] == text['text']['article_no']:
                    if text['text']['type'] == type:
                        d = text['text']['serial_row'] - keyword_serial_row
                        ad = abs(d)
                        if ad == 0:
                            f = 0
                        else:
                            f = -(d / ad + 1) / 2
                        dist = 2 * ad + f

                        #if dist == 0: # 即採用 (戻りjsonの為に整える)
                        #    return text

                        found_list.append({'dist':dist, 'd':d, 'f':f, 'text':text})

        if len(found_list) == 0:
            return None, None, None

        # 距離順(同一行の場合は左→右)にソート
        found_list = sorted(found_list, key=lambda x: (x['dist'], x['text']['index']))

        # ソートしたので先頭が候補から一番近い
        found = found_list[0]

        # KEYWORD に　~オプションがある場合は後ろに該当ワードがあるか確認
        if len(keyword_opt['text_list'][0]) > 0:
            # 次だけの場合
            # if len(found_list) >= 2:
            #     if keyword_opt in found_list[1]['text']['text']['text']:
            #         found = found_list[1]

            # すべて探す場合
            for i in range(0,len(found_list)):
                if any(x for x in keyword_opt['text_list'] if x in found_list[i]['text']['text']['text']):
                # if keyword_opt['text'] in found_list[i]['text']['text']['text']:
                    found = found_list[i]
                    break

        if keyword_opt['flags'] == KEYWORD_OPT_SPECIFIC: # 特定単位指定
            if any(x for x in keyword_opt['text_list'] if x in found['text']['text']['text']) == False:
            # if keyword_opt['text'] not in found['text']['text']['text']:
                # 指定された単位でなければ対象外とする
                return None, None, None

        # 0.9.065.v2 までの処理
        # for f in found_list:
        #     if found == None:
        #         found = f
        #     else:
        #         if f['dist'] < found['dist']:
        #             found = f

        # if found == None:
        #     return None, None, None
        # ここまで

        # 戻りjsonの為に整える
        text_bounds = self.bounds_list(found['text']['text'])
        #text_bounds = self.bounds_list(found['text']['text'], 0, len(found['text']['text']['chars']))

        return found['text'], text_bounds, keyword_bounds

    # 列の縦線で文字列を分けて探す
    def find_nearest_column(self, texts, row, regex_ret, type, keyword_opt, image):
        if image is None:
            return None, None, None, None

        text_bounds = None
        keyword_bounds = None
        found = None
        found_keyword = None
        _keyword_bounds, keyword = self.get_chars_bounds(row['text']['chars'], regex_ret.start(),regex_ret.end())

        row_text = row['text']
        row_no = row_text['row_no']

        page = int(row_text['page'])-1
        rows = self.papers[page]['rows']
        # 次の行を見つける
        next = None
        for r in rows:
            if r['page'] == row_text['page'] and r['row_no'] == row_no+1:
                next = r
                break
        else:
            # 見つからない
            return None, None, None, None

        vline = self.find_vertical_line(None, image, row_text['bounds'], img_width=True)
    #    vline = self.find_vertical_line('/home/shoji/src/iTask/v2/data/test1', image, row_text['bounds'], img_width=True)
        # vline = self.find_vertical_line2('/home/shoji/src/iTask/v2/data/test2', image, row_text['bounds'], img_width=True)

        if len(vline) < 3:
            # 表ではない可能性
            return None, None, None, None

        current_col = []
        next_col    = []

        left = 0
        # col = 0
        keyword_col = -1
        for col, right in enumerate(vline):
            text, chars, bounds = self.get_chars_between_LR_text(row_text['chars'], left, right)
            current_col.append({'col':col, 'text':{'text':text, 'chars':chars, 'bounds':bounds, 'page':row_text['page']}})
            if keyword == text:
                keyword_col = col

            text, chars, bounds = self.get_chars_between_LR_text(next['chars'], left, right)
            next_col.append({'col':col, 'text':{'text':text, 'chars':chars, 'bounds':bounds, 'page':row_text['page']}})

            left = right
            # col += 1

        if keyword_col < 0:
            # キーワードが見つからない
            return None, None, None, None

        # 右
        right_col = current_col[keyword_col+1] if keyword_col+1 < len(current_col) else None
        # 下
        below_col = next_col[keyword_col] if keyword_col < len(next_col) else None

        # デフォルトは下優先
        order = [below_col, right_col]
        if keyword_opt['flags'] == KEYWORD_OPT_PRIOR: # 優先
        # if keyword_opt['text'] == '右' and keyword_opt['flags'] == KEYWORD_OPT_PRIOR:
            if any(x for x in keyword_opt['text_list'] if x == '右'):
                # 右優先
                order = [right_col, below_col]
        elif keyword_opt['flags'] == KEYWORD_OPT_SPECIFIC: # 特定
            if any(x for x in keyword_opt['text_list'] if x == '右'):
                # 右特定
                order = [right_col]
            elif any(x for x in keyword_opt['text_list'] if x == '下'):
                # 下特定
                order = [below_col]

        ret = None
        for w in order:
            # 優先順で検索
            if w is not None:
                ret = self.check_word_type(type, w['text']['text'], w['text']['chars'])
                if ret is not None:
                    break
        else:
            # 値(属性)が見つからない
            return None, None, None, None

        # 見つかったので値をセットする
        if regex_ret:
            st  = regex_ret.start()
            end = regex_ret.end()
        else:
            st = 0
            end = -1
        keyword_bounds = self.bounds_list(row_text, st, end)

        found_keyword = current_col[keyword_col]

        found = w
        pos = {'page':found['text']['page']}
        pos.update(**found['text']['bounds'].get_bound())
        text_bounds = [pos]

        return found, found_keyword, text_bounds, keyword_bounds

    def propn(self, _str):
        global nlp

        #doc = nlp('第32条本契約締結の日以降,甲及び乙の丙に対する本契約上の権利義務は全て株式会社トータルオフィスパートナー(所在地東京都港区芝浦一丁目2番3号,代表取締役社長西田昌史)が代理して行うことができるものとし、甲及び乙並びに丙はこれを承認する。')
        doc =  nlp(_str)
        # print(ginza.bunsetu_spans(doc))
        str = ""
        str2= ""
        PROPN_FLG =0

        found_list = []
        first_idx = 0
        for sent in doc.sents:
            for token in sent:
                info = [
                    token.i,         # トークン番号
                    token.text,     # テキスト
                    token.lemma_,    # 基本形
                    token.pos_,      # 品詞
                    #token.tag_,      # 品詞詳細
                    token.idx,
                ]
                print(info)
                if(token.pos_ == 'NOUN' or token.pos_ == 'NUM' or token.pos_ == 'SYM' or token.pos_ == 'PROPN'): # or token.pos_ == 'PUNCT'):
                    if(token.text != '商号' and token.text != '代理人' and token.text != '氏名'):
                    # if(token.text != '商号'):# or token.text != '代理人' or token.text != '氏名'):
                        if len(str) == 0:
                            first_idx = token.idx
                        str += token.text

                    # if(token.pos_ == 'PROPN' or token.text == '株式会社'):
                    if token.pos_ == 'PROPN':
                        # if PROPN_FLG == 0:
                        #     first_idx = token.idx
                        PROPN_FLG |= 1
                    elif '会社' in token.text or '法人' in token.text:
                        # if PROPN_FLG == 0:
                        #     first_idx = token.idx
                        PROPN_FLG |= 2
                        # PROPN_FLG += 1
                    elif token.pos_ == 'SYM':
                        if(PROPN_FLG == 0):
                            str = ""
                            # first_idx = token.idx

                elif(PROPN_FLG == 0):
                    str = ""
                    # first_idx = token.idx
                elif(PROPN_FLG > 0 or token.pos_ == 'ADP'):
                    found_list.append({'index':first_idx, 'flag':PROPN_FLG, 'text':str})
                    PROPN_FLG =0
                    str = ""
                    # first_idx = token.idx
                    # break

        if len(str) > 0:
            found_list.append({'index':first_idx, 'flag':PROPN_FLG, 'text':str})

        print(_str)
        print('------>')
# PROPN_COMPANY = 1 # 会社
# PROPN_ADDR    = 2 # 住所
# PROPN_NAME    = 3 # 名前
# PROPN_OTHER = 4 # 上記以外

        for inf in found_list:
            if inf['flag'] & 2:
                inf['type'] = PROPN_COMPANY # 会社
            else:
                addr = search_address(inf['text'])
                if addr is not None:
                    inf['index'] += addr.regs[2][0]
                    inf['text'] = addr.group(2)
                    inf['type'] = PROPN_ADDR # 住所
                else:
                    date_text = search_date(inf['text'])
                    if date_text is not None:
                        inf['index'] += date_text.regs[2][0]
                        inf['text'] = date_text.group(2)
                        inf['type'] = PROPN_DATE # 日付
                    elif inf['flag'] & 1:
                        inf['type'] = PROPN_NAME # 名前
                    else:
                        inf['type'] = PROPN_OTHER # その他

            print(inf)
        print('<------')

        return found_list

    def find_propn_list(self, texts, upper, lower, keyword, keyword_serial_row, keyword_text=''):

        found_list = []

        for text in texts:
            if upper <= text['serial_row'] <= lower and keyword['article_no'] == text['article_no']:
                ret = self.propn(text['text'])
                if ret is None:
                    continue

                for index, p in enumerate(ret):
                    if True: #type == 0 or type == r['type']: # typeの指定が無い、またはtypeが一致
                        d = text['serial_row'] - keyword_serial_row
                        ad = abs(d)
                        if ad == 0:
                            f = 0
                        else:
                            f = -(d / ad + 1) / 2
                        dist = 2 * ad + f

                        #if dist == 0: # 即採用 (戻りjsonの為に整える)
                        #    return text

                        found_list.append({'dist':dist, 'd':d, 'f':f, 'a':p['text'], 'text':text, 'index':index, 'propn':p})

        debug_print( 'find_contract_word [{}]{} {}-->'.format(keyword_text, upper, lower),level=DEBUG_ROWS_INFO)
        for f in found_list:
            debug_print( '[{}] {} {} {} {}'.format(f['d'], f['propn']['type'], f['index'], f['dist'], f['propn']['text']),level=DEBUG_ROWS_INFO)
        debug_print( 'find_contract_word <--',level=DEBUG_ROWS_INFO)

        return found_list

    # 契約情報　会社、名前、住所
    def find_contract_word(self, _texts, row, regex_ret, type, keyword_opt):
        if self.ai_ginza_process == False:
        # if AI_GINZA_PROCESS == False or self.ai_ginza_process == False:
            return None, None, None

        found_text = None

        keyword = row['text']
        article = keyword['article_row']
        found_list = []

        keyword_text = ''

        # keywordの先頭文字がある正確な通し行番号
        st = regex_ret.span(0)[0]
        keyword_serial_row = keyword['chars'][st]['row']['serial_row']
        # start = st
        end   = regex_ret.span(0)[1]

        keyword_bounds = self.bounds_list(keyword, st, end)
        keyword_text = keyword['text'][st:end]

        found = None

        # 条文内、条文外、押印欄のいずれでも
        # キーワードと同一行に指定タイプのワードがあれば最短距離で採用

        # 対象文字列内でのkeywordの位置
        k_bounds = keyword['chars'][st]['bounds']
        for i, c in enumerate(article['chars']):
            c_bounds = c['bounds']
            if k_bounds.is_equal(c_bounds):
                st = i
                end = st+len(keyword_text)
                break
        else:
            end = end - st
            st = 0

        ret = self.propn(article['text'])

        if ret is not None:
            distance = 0
            for r in ret:
                if type == 0 or type == r['type']: # typeの指定が無い、またはtypeが一致
                    if st >= r['index']: # ketwordより前
                        d = abs(st - (r['index']+len(r['text'])))
                    else: # 後
                        d = abs(r['index'] - end)
                    if found is None or distance > d:
                        distance = d
                        found = r

            if found is not None:
                st = found['index']
                end = st+len(found['text'])

                found_text = {'text':{'text':found['text'], 'bounds':article['chars'][st]['row']['bounds'], 'page':article['page']}}
                text_bounds = self.bounds_list(article, st, end)

        if found is None and article['article_no'] < 0: # 同一行内に無く条文以外である
            # 対象は条文外

            # 初めに対象行の前後の住所の行を探す
            upper = keyword_serial_row - 2   # 上限
            lower = keyword_serial_row + 2   # 下限

            found_list = self.find_propn_list(self.article_rows, upper, lower, keyword, keyword_serial_row, keyword_text)

            if len(found_list) == 0:
                return None, None, None

            # 距離順(同一行の場合は左→右)にソート
            # found_list = sorted(found_list, key=lambda x: (x['dist'], x['index']))

            # 甲乙丙パターン
            # 住所
            # 組織名
            # 氏名
            # の並びに限定するか？

            adr = None
            no  = None
            # 住所の行を探す
            for n, f in enumerate(found_list):
                if f['propn']['type'] == PROPN_ADDR:
                    adr = f
                    no = n
                    break

            if adr is not None:
                # 住所が見つかった場合はその行から下
                base_serial_row = found_list[no]['text']['serial_row']
            else:
                # 住所が見つからない場合は対象外
                return None, None, None
                # # 住所が見つからない場合はKEYWORDから下
                # base_serial_row = keyword_serial_row

            # 基準(住所)の行から下を抽出 (６行分)
            upper = base_serial_row   # 上限
            lower = base_serial_row + 6   # 下限

            found_list = self.find_propn_list(self.article_rows, upper, lower, keyword, keyword_serial_row, keyword_text)

            # 指定タイプの行を探す
            for n, f in enumerate(found_list):
                if f['propn']['type'] == type:
                    found = f
                    # no = n
                    break
            else:
                return None, None, None

            # NOTE: 他の２パターンとは違いKEYWORD行(条文内)とは"別の行"を返すので注意
            st = found['propn']['index']
            end = st+len(found['propn']['text'])

            # found_text = found
            found_text = {'text':{'text':found['text']['text'][st:end], 'bounds':found['text']['chars'][st]['row']['bounds'], 'page':found['text']['page']}}
            text_bounds = self.bounds_list(found['text'], st, end)

            # # KEYWORD に　~オプションがある場合は後ろに該当ワードがあるか確認
            # if len(keyword_opt['text_list'][0]) > 0:
            #     # 次だけの場合
            #     # if len(found_list) >= 2:
            #     #     if keyword_opt in found_list[1]['text']['text']['text']:
            #     #         found = found_list[1]

            #     # すべて探す場合
            #     for i in range(0,len(found_list)):
            #         if any(x for x in keyword_opt['text_list'] if x in found_list[i]['text']['text']):
            #         # if keyword_opt['text'] in found_list[i]['text']['text']['text']:
            #             found = found_list[i]
            #             break

            # if keyword_opt['flags'] == KEYWORD_OPT_SPECIFIC: # 特定単位指定
            #     if any(x for x in keyword_opt['text_list'] if x in found['text']['text']) == False:
            #     # if keyword_opt['text'] not in found['text']['text']['text']:
            #         # 指定された単位でなければ対象外とする
            #         return None, None, None

            # 0.9.065.v2 までの処理
            # for f in found_list:
            #     if found == None:
            #         found = f
            #     else:
            #         if f['dist'] < found['dist']:
            #             found = f

            # if found == None:
            #     return None, None, None
            # ここまで

            # 戻りjsonの為に整える
            # text_bounds = self.bounds_list(found['text'])

            #text_bounds = self.bounds_list(found['text']['text'], 0, len(found['text']['text']['chars']))

        if found_text is None:
            return None, None, None

        return found_text, text_bounds, keyword_bounds

    def get_article_info(self, article):
        # ['text']['bounds'] は最初の行のみをセット
        info = {'text':{'text':article['text'], 'bounds':article['chars'][0]['row']['bounds'], 'page':article['page']}}

        bounds = []
        row_no = -1
        for c in article['chars']:
            if c['row']['row_no'] != row_no:
                row_no = c['row']['row_no']
                bounds.append(c['row']['bounds'])

        return info, bounds

    # 派生クラス固有ID
    def special_id_find(self, texts, papers, conditions_id, N, page, search, search_part_flag, keyword_list, key_grp_bounds, keyword_opt):
        # 無条件検索
        # found_text, text_bounds, keyword_bounds
        return None

    def special_id_found_inbounds(self, texts, papers, conditions_id, N, page, search, search_part_flag, keyword_list, key_grp_bounds, keyword_opt, row, bound, text_page_no):
        # 領域内にオブジェクトが存在
        # found_text, text_bounds, keyword_bounds
        return None


    # キャリブレーションでbound調整
    def caribration_adjust(self, bound, page):
        if self.in_calibration_template == False and self.in_calibration_non == False:
            # ページのキャリブレーションデータを検索
            templ = [d.get('template') for d in self.in_calibration if d.get('file') == page]
            try:
                pre_offset_x, pre_offset_y = 0, 0
                after_offset_x, after_offset_y = 0, 0
                scale_x, scale_y = '1.0', '1.0'

                loaded_image = [d.get('bound') for d in self.calibration if d.get('file') == page]
                if len(loaded_image) > 0:

                    pre_offset_x = templ[0].get_left()
                    pre_offset_y = templ[0].get_top()

                    if self.in_calibration_scale:
                        loaded_image_w, loaded_image_h = loaded_image[0].get_width(), loaded_image[0].get_height()
                        templ_w, templ_h = templ[0].get_width(), templ[0].get_height()
                        if loaded_image_w != templ_w:
                            scale_x = str(float(loaded_image_w) / float(templ_w))
                        if loaded_image_h != templ_h:
                            scale_y = str(float(loaded_image_h) / float(templ_h))

                    # オフセット処理ONの場合は対象文書の左上、OFFの場合はテンプレートの左上（）
                    if self.in_calibration_offset:
                        after_offset_x = loaded_image[0].get_left()
                        after_offset_y = loaded_image[0].get_top()
                    else:
                        after_offset_x = pre_offset_x
                        after_offset_y = pre_offset_y

            except:
                None

            # searchを　一旦　(0,0)基点にする
            bound.offset(-pre_offset_x, -pre_offset_y)
            if scale_x != '1.0' or scale_y != '1.0':
                bound.scale(scale_x, scale_y)

            bound.offset(after_offset_x, after_offset_y)

# conditions_id:
# 0	# keyword検索 一部一致 該当【key】の後ろの【n】番目の項目を取り出す
# 1	# keyword検索 一部一致 該当【key】の前の【n】番目の項目を取り出す
# 2	# 日付検索
# 3 # keyword　【key】そのままを返す
# 4	# keyword検索 完全一致 該当【key】の後ろの【n】番目の項目を取り出す
# 5	# keyword検索 完全一致 該当【key】の前の【n】番目の項目を取り出す
# 6	# 範囲検索
# 7	# 住所検索

# 8	# keyword検索 一部一致 数字検索 該当【key】の後ろの【n】番目の項目を取り出す
# 9	# keyword検索 一部一致 数字検索 該当【key】の前の【n】番目の項目を取り出す

# 同一行内
    def FindItem(self, texts, papers, conditions_id, N, page, search, search_part_flag, keyword_list, key_grp_bounds, keyword_opt):
    #def FindItem(self, texts, papers, conditions_id, N, page, search, search_part_flag, regex):
    #def FindItem(self, texts, papers, conditions_id, N, page, search, search_part_flag, keyword, regex):

        #debug
        #if conditions_id == 4:
        #    conditions_id = 8
        #elif conditions_id == 5:
        #    conditions_id = 9

        # texts[279]['text']['text'] = '第10条'
        # texts[279]['text']['type'] = 35
        # texts[280]['text']['text'] = '(敷金)'
        # texts[280]['text']['type'] = 0

        # found_text = None
        # found_text_list = []
        # found = False

        # prev_page_no = -1
        # pre_offset_x, pre_offset_y = 0, 0
        # after_offset_x, after_offset_y = 0, 0
        # scale_x, scale_y = '1.0', '1.0'

        # 甲乙丙（名前パターン）
        if conditions_id == 32 or conditions_id == 33:
            found = False

            if self.ai_ginza_process == False:
            # if AI_GINZA_PROCESS == False:
                return None   # return None, None, None, None

            for paper in self.papers:
                # ai_ginza_process==Trueの時にimportされる
                from engine.getContractName import getContractName
                found_data, st, wrd, kw_st, kwrd  = getContractName(paper['characters'], paper['rows'], keyword_list)
                if found_data is not None:
                    break
            else:
                return None   # return None, None, None, None

            end = st + len(wrd)
            kw_end = kw_st + len(kwrd)

            found_text = {'text':{'text':wrd, 'bounds':found_data['chars'][st]['row']['bounds'], 'page':found_data['chars'][st]['row']['page']}}
            text_bounds = self.bounds_list(found_data, st, end)

            found_keyword = {'text':kwrd, 'bounds':found_data['chars'][kw_st]['row']['bounds'], 'page':found_data['chars'][kw_st]['row']['page']}
            keyword_bounds = self.bounds_list(found_data, kw_st, kw_end)
            return found_text, found_keyword, text_bounds, keyword_bounds
            # return None, None, None, None
        else:
            # 派生クラス固有ID
            ret = self.special_id_find(texts, papers, conditions_id, N, page, search, search_part_flag, keyword_list, key_grp_bounds, keyword_opt)
            if ret is not None and [True for x in ret if x is not None]:  # ret:tuple None以外がある
            # if (not None) in ret:
                return ret
            # found_text, text_bounds, keyword_bounds = self.special_id_find(texts, papers, conditions_id, N, page, search, search_part_flag, keyword_list, key_grp_bounds, keyword_opt)
            # if found_text is not None:
            #     return found_text, None, text_bounds, keyword_bounds


        # for index, row in enumerate(texts):
        for index2, regex in enumerate(keyword_list):
            found_text = None
            found_text_list = []
            found = False

            prev_page_no = -1
            pre_offset_x, pre_offset_y = 0, 0
            after_offset_x, after_offset_y = 0, 0
            scale_x, scale_y = '1.0', '1.0'

            # for index2, regex in enumerate(keyword_list):
            for index, row in enumerate(texts):
                #if index2 == 0 and index == 462:
                #    test = 0
                #print('{}:{}:{}\n'.format(regex,index2,index))
                # page の bound内に入っているか？
                text_page_no = int(row['text']['page'])
                if (page == '' or page == row['text']['page']):
                    # text_page_no = int(row['text']['page'])

                    # ページ変わった時に処理をする
                    if text_page_no != prev_page_no:
                        bound = copy.deepcopy(search)

                    if bound.is_empty() and conditions_id != 6:
                        try:
                            page_size = papers[text_page_no-1]
                            bound  = Bound(right=page_size['width'],bottom=page_size['height'])
                            #page_size = ll1 = [d.get('bound') for d in papers if d.get('file') == no]
                        except:
                            None

                    # パラメータに応じてスケールとオフセット処理
                    if text_page_no != prev_page_no: # ページが変わった
                        self.caribration_adjust(bound, text_page_no-1)
                    # if self.in_calibration_template == False and self.in_calibration_non == False:
                    #     if text_page_no != prev_page_no:
                    #         # ページのキャリブレーションデータを検索
                    #         templ = [d.get('template') for d in self.in_calibration if d.get('file') == text_page_no-1]
                    #         try:
                    #             pre_offset_x, pre_offset_y = 0, 0
                    #             after_offset_x, after_offset_y = 0, 0
                    #             scale_x, scale_y = '1.0', '1.0'

                    #             loaded_image = [d.get('bound') for d in self.calibration if d.get('file') == text_page_no-1]
                    #             if len(loaded_image) > 0:

                    #                 pre_offset_x = templ[0].get_left()
                    #                 pre_offset_y = templ[0].get_top()

                    #                 if self.in_calibration_scale:
                    #                     loaded_image_w, loaded_image_h = loaded_image[0].get_width(), loaded_image[0].get_height()
                    #                     templ_w, templ_h = templ[0].get_width(), templ[0].get_height()
                    #                     if loaded_image_w != templ_w:
                    #                         scale_x = str(float(loaded_image_w) / float(templ_w))
                    #                     if loaded_image_h != templ_h:
                    #                         scale_y = str(float(loaded_image_h) / float(templ_h))

                    #                 # オフセット処理ONの場合は対象文書の左上、OFFの場合はテンプレートの左上（）
                    #                 if self.in_calibration_offset:
                    #                     after_offset_x = loaded_image[0].get_left()
                    #                     after_offset_y = loaded_image[0].get_top()
                    #                 else:
                    #                     after_offset_x = pre_offset_x
                    #                     after_offset_y = pre_offset_y

                    #         except:
                    #             None

                    #         # searchを　一旦　(0,0)基点にする
                    #         bound.offset(-pre_offset_x, -pre_offset_y)
                    #         if scale_x != '1.0' or scale_y != '1.0':
                    #             bound.scale(scale_x, scale_y)

                    #         bound.offset(after_offset_x, after_offset_y)

                    prev_page_no = text_page_no

                    if row['text']['bounds'].is_included(bound, search_part_flag) == True:
    #            if (page == '' or page == row['text']['page']) and row['text']['bounds'].is_included(bound, search_part_flag) == True:
                        if conditions_id == 0 or conditions_id == 1 or conditions_id == 4 or conditions_id == 5 or (conditions_id in CONDITION_FIND_TYPE_AFTER or conditions_id in CONDITION_FIND_TYPE_BEFORE): #  keyword検索
                        #if conditions_id == 0 or conditions_id == 1 or conditions_id == 4 or conditions_id == 5 or (conditions_id >= 8 and conditions_id <= 15): #  keyword検索
    #                    if conditions_id == 0 or conditions_id == 1 or conditions_id == 4 or conditions_id == 5: #  keyword検索

                            found = False
                            #for regex in keyword_list:
                            #if regex:

                            if regex == REGEX_SEARCH_NON: # キーワード指定無し
                                k_found = None
                                found = True
                            else:
                                k_found = re.search(regex, row['text']['text'])
                                if k_found:
                                    if conditions_id == 28 or conditions_id == 29:
                                        found = False
                                        # 条文の先頭のみを対象とする
                                        # (対象文字列が
                                        #  条文の先頭行で次の行が第n条、もしくは
                                        #  第n条が先頭で次の行の先頭が対象文字列 (等を考慮して2文字目までを許容

                                        if texts[index]['text']['article_no'] > 0:
                                            article_no = texts[index]['text']['article_no']
                                            if index >= 1:
                                                prev_article_no = texts[index-1]['text']['article_no']
                                                if prev_article_no != article_no:
                                                    # 対象文字列が条文の先頭行
                                                    if index+1 < len(texts) and texts[index+1]['text']['type'] == WORD_SPLIT_OPT_UNIT:
                                                        if search_unit_article_no(texts[index+1]['text']['text']) is not None:
                                                            # 次の行が第n条
                                                            found = True # 対象文字列が条文の先頭行で次の行が第n条

                                                elif index >= 2: # 前の行は同じ n条
                                                    if k_found.start() <= 1:
                                                        # 対象文字列が先頭（2文字目までを許容）
                                                        if article_no != texts[index-2]['text']['article_no']:
                                                            # 前の前の行が違うので前の行が先頭
                                                            if texts[index-1]['text']['type'] == WORD_SPLIT_OPT_UNIT:
                                                                # 属性は一致
                                                                if search_unit_article_no(texts[index-1]['text']['text']) is not None:
                                                                    # 前の行は第n条
                                                                        found = True # 第n条が先頭で次の行の先頭が対象文字列
                                            if found:
                                                # 条文を抜き出す
                                                article = texts[index]['text']['article_row']
                                                found_text = {'text':{'text':article['text'], 'bounds':article['chars'][0]['row']['bounds'], 'page':article['page']}}
                                                # found_text = texts[index]['text']['article_row']['text']
                                                # found_text, text_bounds = self.get_article_info(texts[index]['text']['article_row'])
                                                text_bounds     = self.bounds_list(article)
                                                keyword_bounds  = self.bounds_list(row['text'])
                                                return found_text, row['text'], text_bounds, keyword_bounds
                                    elif conditions_id == 30 or conditions_id == 31:
                                        # 契約情報（甲乙丙）
                                        found = False
                                        # article = texts[index]['text']['article_row']
                                        found_text, text_bounds, keyword_bounds = self.find_contract_word(texts, row, k_found, N, keyword_opt)
                                        if found_text:
                                            return found_text, row['text'], text_bounds, keyword_bounds

                                    elif conditions_id <= 1 or conditions_id >= 8:  # 0 or 1 or 8 ～ 15 一部一致
        #                                if conditions_id <= 1:  # 0 or 1 一部一致
                                        found = True
                                        #break # keyword_list
                                    else:                   # 4 or 5 完全一致
                                        kkk = k_found.group()
                                        if k_found.group() == row['text']['text']:
                                            found = True
                                            #break # keyword_list

                            #if conditions_id <= 1:  # 0 or 1 一部一致
                            #    if keyword and keyword in row['text']['text']:
                            #        found = True
                            #else:                   # 4 or 5 完全一致
                            #    if keyword and keyword == row['text']['text']:
                            #        found = True

                            # グループ検索
                            #if found == True and key_grp_bounds.is_empty() == False:
                            if found == True:
                                if key_grp_bounds.is_empty() == False:
                                    if key_grp_bounds.is_included(row['text']['bounds'],True) == False:
                                        found = False

                            if found == True:
                                end = len(texts)

                                if conditions_id == 0 or conditions_id == 4: # 該当【key】の後ろの【n】番目の項目を取り出す
                                    cnt = 0
                                    for i in range(index,end): # (index,end) v0.9.017 # range(index,end+1)v0.9.046??
                                        if texts[i]['text']['bounds'].is_included(bound,search_part_flag) == True:
                                            if cnt == N:
                                                text_bounds     = self.bounds_list(texts[i]['text'])
                                                keyword_bounds  = self.bounds_list(row['text'])

                                                return texts[i], row['text'], text_bounds, keyword_bounds

                                                #result_pos = {'page':texts[i]['text']['page']}
                                                #result_pos.update(**texts[i]['text']['bounds'].get_bound())
                                                #result_pos = [result_pos]
                                                #keyword_pos = {'page':row['text']['page']}
                                                #keyword_pos.update(**row['text']['bounds'].get_bound())
                                                #keyword_pos = [keyword_pos]
                                                #return texts[i], row['text'], result_pos, keyword_pos

                                                #return texts[i], row['text'], None, None

                                            cnt += 1
                                    found = False
                                    #return None, None

                                elif conditions_id in CONDITION_FIND_TYPE_AFTER: # タイプ検索 該当【key】の後ろの【n】番目の項目を取り出す
                                #elif conditions_id == 8 or conditions_id == 10 or conditions_id == 12 or conditions_id == 14: # タイプ検索 該当【key】の後ろの【n】番目の項目を取り出す
                                    found = False
                                    WORD_OPT = CONDITION_TO_WORD_OPT[int(conditions_id/2)]
                                    if N == 0:
                                        # 最初にテーブルのパターンで検索
                                        found_text, found_keyword, text_bounds, keyword_bounds = self.find_nearest_column(texts, row, k_found, WORD_OPT, keyword_opt, papers[text_page_no-1]['image'])
                                        if found_text:
                                            return found_text, found_keyword['text'], text_bounds, keyword_bounds
                                        # 次一番近い値を検索
                                        found_text, text_bounds, keyword_bounds = self.find_nearest_word(texts, row, k_found, WORD_OPT, keyword_opt)
                                        if found_text:
                                            return found_text, row['text'], text_bounds, keyword_bounds
                                    else:
                                        cnt = 1
                                        for i in range(index,end): # (index,end) v0.9.017 # range(index,end+1)v0.9.046??
                                            if texts[i]['text']['type'] == WORD_OPT and texts[i]['text']['bounds'].is_included(bound,search_part_flag) == True:
                                                if cnt >= N:
                                                    keyword_opt_found = any(x for x in keyword_opt['text_list'] if x in texts[i]['text']['text'])
                                                    # keyword_opt_found = keyword_opt['text'] in texts[i]['text']['text']
                                                    if keyword_opt_found == False and keyword_opt['flags'] == KEYWORD_OPT_SPECIFIC:
                                                        pass
                                                    else:
                                                        if found == False or keyword_opt_found:
                                                            text_bounds     = self.bounds_list(texts[i]['text'])
                                                            keyword_bounds  = self.bounds_list(row['text'])
                                                            found_text = texts[i]
                                                            found = True
                                                            if keyword_opt_found:
                                                                break
                                                        else:
                                                            break # 見つかった次がkeyword_optに該当しなければ終了
                                                cnt += 1
                                        if found == True:
                                            return found_text, row['text'], text_bounds, keyword_bounds

                                    # found = False
                                    #return None, None

                                elif conditions_id in CONDITION_FIND_TYPE_BEFORE: # タイプ検索 該当【key】の前の【n】番目の項目を取り出す
                                #elif conditions_id == 9 or conditions_id == 11 or conditions_id == 13 or conditions_id == 15: # タイプ検索 該当【key】の前の【n】番目の項目を取り出す
                                    found = False
                                    WORD_OPT = CONDITION_TO_WORD_OPT[int(conditions_id/2)]
                                    if N == 0:
                                        # 最初にテーブルのパターンで検索
                                        found_text, found_keyword, text_bounds, keyword_bounds = self.find_nearest_column(texts, row, k_found, WORD_OPT, keyword_opt, papers[text_page_no-1]['image'])
                                        if found_text:
                                            return found_text, found_keyword['text'], text_bounds, keyword_bounds
                                        # 次一番近い値を検索
                                        found_text, text_bounds, keyword_bounds = self.find_nearest_word(texts, row, k_found, WORD_OPT, keyword_opt)
                                        if found_text:
                                            return found_text, row['text'], text_bounds, keyword_bounds
                                    else:
                                        cnt = 1
                                        for i in range(index,-1,-1): # (index,0,-1) v0.9.017 #(index,-1,-1) v0.9.046??
                                            if texts[i]['text']['type'] == WORD_OPT and texts[i]['text']['bounds'].is_included(bound,search_part_flag) == True:
                                                if cnt >= N:
                                                    keyword_opt_found = any(x for x in keyword_opt['text_list'] if x in texts[i]['text']['text'])
                                                    # keyword_opt_found = keyword_opt['text'] in texts[i]['text']['text']
                                                    if keyword_opt_found == False and keyword_opt['flags'] == KEYWORD_OPT_SPECIFIC:
                                                        pass
                                                    else:
                                                        if found == False or keyword_opt_found:
                                                        # if found == False or keyword_opt in texts[i]['text']['text']:
                                                            text_bounds     = self.bounds_list(texts[i]['text'])
                                                            keyword_bounds  = self.bounds_list(row['text'])
                                                            found_text = texts[i]
                                                            found = True
                                                            if keyword_opt_found:
                                                            # if keyword_opt in texts[i]['text']['text']:
                                                                break
                                                        else:
                                                            break # 見つかった次がkeyword_optに該当しなければ終了
                                                cnt += 1
                                        if found == True:
                                            return found_text, row['text'], text_bounds, keyword_bounds
                                    # found = False
                                    #return None, None

                                else: # conditions_id == 1 or conditions_id == 5 # 該当【key】の前の【n】番目の項目を取り出す
                                    cnt = 0
                                    for i in range(index,-1,-1): # (index,0,-1) v0.9.017
                                        if texts[i]['text']['bounds'].is_included(bound,search_part_flag) == True:
                                            if cnt == N:
                                                text_bounds     = self.bounds_list(texts[i]['text'])
                                                keyword_bounds  = self.bounds_list(row['text'])

                                                return texts[i], row['text'], text_bounds, keyword_bounds

                                                #result_pos = {'page':texts[i]['text']['page']}
                                                #result_pos.update(**texts[i]['text']['bounds'].get_bound())
                                                #result_pos = [result_pos]
                                                #keyword_pos = {'page':row['text']['page']}
                                                #keyword_pos.update(**row['text']['bounds'].get_bound())
                                                #keyword_pos = [keyword_pos]
                                                #return texts[i], row['text'], result_pos, keyword_pos

                                                #return texts[i], row['text'], None, None

                                            cnt += 1
                                    found = False
                                    #return None, None

                        #elif conditions_id == 2: # 日付検索
                        #    date_text = search_date(row['text']['text'])
                        #    if date_text:
                        #    #if len(date_text) > 0:
                        #        return row
                        elif conditions_id == 2 : # 2.日付検索
                            found = True

                            # 検索条件は座標のみ
                            if found_text == None:
                                found_text = copy.deepcopy(row)  #元のデータは変更しない様にする
                            else:
                                # 範囲内に複数ある場合は追加する
                                found_text['text']['text'] += row['text']['text']
                                found_text['text']['bounds'].expand(row['text']['bounds'])
                                found_text['index'] *= -1 # 変更したのでindexは無効(未使用)

                        elif conditions_id == 6: # 6.範囲検索
                            found = True

                            # 検索条件は座標のみ
                            found_text_list.append(copy.deepcopy(row))  #元のデータは変更しない様にする

                        elif conditions_id == 7 : # 7.住所検索
                            #found = True

                            #if found_text == None:
                            #    found_text = copy.deepcopy(row)  #元のデータは変更しない様にする
                            #else:
                            #    # 範囲内に複数ある場合は追加する
                            #    found_text['text']['text'] += row['text']['text']
                            #    found_text['text']['bounds'].expand(row['text']['bounds'])
                            #    found_text['index'] *= -1 # 変更したのでindexは無効(未使用)

                            addr_str = find_address(row['text']['text'])
                            #addr_str = self.find_address(row['text']['text'])
                            if addr_str:
                                found_text = copy.deepcopy(row)
                                if addr_str != found_text['text']['text']:
                                    found_text['text']['text'] = addr_str
                                #    found_text['text']['bounds'].expand(row['text']['bounds'])
                                    found_text['index'] *= -1 # 変更したのでindexは無効(未使用)

                                return found_text, None, None, None
                        else:
                            # 派生エンジン固有ID
                            ret = self.special_id_found_inbounds(texts, papers, conditions_id, N, page, search, search_part_flag, keyword_list, key_grp_bounds, keyword_opt, row, bound, text_page_no)
                            if ret is not None and [True for x in ret if x is not None]:  # ret:tuple None以外がある
                            # if (not None) in ret:
                                return ret
                            # found_text, text_bounds, keyword_bounds = self.special_id_found_inbounds(texts, papers, conditions_id, N, page, search, search_part_flag, keyword_list, key_grp_bounds, keyword_opt, row, bound, text_page_no)
                            # if found_text is not None:
                            #     return found_text, text_bounds, keyword_bounds

            # ループ変更
            if found == True:
                break

        if found == False:
            return None   # return None, None, None, None

        if conditions_id == 2: # 日付検索
            found_text['text']['text'] = revise_date_nengo(found_text['text']['text'])
            found_text['text']['text'] = revise_date(found_text['text']['text'])
            date_text = search_date(found_text['text']['text'])
            if date_text: # 日付に合致
                found_text['text']['text'] = date_text.group(2)
            else:
                found_text = None

        elif conditions_id == 6: # 6.範囲検索
            char_max = len(found_text_list)

            ### Vision API の順番で結合 (0.9.027)

            #### 範囲内の文字の高さ平均を求める
            ###ave_h = 0
            ###for list in found_text_list:
            ###    ave_h += list['text']['bounds'].get_height()

            ###    print('t={},r={} w={},h={}'.format(list['text']['text'], list['text']['bounds'].get_rect(),list['text']['bounds'].get_width(),list['text']['bounds'].get_height()))

            ###height_average = ave_h / char_max
            ###print('height_average={}'.format(height_average))

            #### XY座標で並び替え
            ###for i in range(0,char_max):
            ###    for j in range(i+1,char_max):
            ###        b1 = found_text_list[i]['text']['bounds']
            ###        b2 = found_text_list[j]['text']['bounds']

            ###        if b1.is_same_line(b2,height_average):#average_size):
            ###            if b1.is_left(b2) == False:
            ###                found_text_list[i], found_text_list[j] = found_text_list[j], found_text_list[i]
            ###        else:
            ###            if b1.is_above(b2) == False:
            ###                found_text_list[i], found_text_list[j] = found_text_list[j], found_text_list[i]

            # 文字の結合
            found_text = found_text_list[0]
            for i in range(1,char_max):
                found_text['text']['text'] += found_text_list[i]['text']['text']
                found_text['text']['bounds'].expand(found_text_list[i]['text']['bounds'])

        return found_text, None, None, None

    def Analyze(self):

        ### すべてのページから第n条のブロックを決める
        ##self.decision_article()

        ### 第n条のブロック毎に行をまとめる
        ##combine_rows = self.article_rows()

        combine_rows = self.combine_rows

        aa = time.time()

        # テーブルの列（縦線）で文字列を分ける
        # self.split_table_col_words(combine_rows)

        # ワード単位に分割
        for loop in range(100):
            split_cnt, combine_rows = self.split_words(combine_rows,0,loop)
            if split_cnt == 0:
                break
        else:
            b = 0
        bb = time.time()

        self.combine_rows = combine_rows

        #self.find_article()

        #　すべてのページのテキストをまとめる
        all_texts = self.combine_rows #[]
        all_characters = []
        #ページ番号をセット
        #すべての文字を追加する
        for page, paper in enumerate(self.papers):
            page_str = str(page+1)
            #for text in paper['texts']:
            #    text['page'] = page_str
            #    all_texts.append(text)

            for character in paper['characters']:
                character['page'] = page_str
                all_characters.append(character)

        max_page = len(self.papers)   # max_page = page+1
        if max_page == 0:
            max_page = 1

        keyword_group = [[]] * (max_page)
        #廃棄した
        if len(self.keyword_group) > 0:
            #グループ検索

            for grp in self.keyword_group:
                for text in all_texts:
                    if text['text'] == grp['keyword']:
                        grp['page'] = text['page']
                        grp['bounds'] = copy.deepcopy(text['bounds'])

                        grp['conds_param']['key_grp_bounds'] = grp['bounds']
                        keyword_group[int(grp['page'])-1].append(grp)

                        #page_size = self.papers[int(text['page'])-1]
                        #grp['bounds'].rect[2] = page_size['width']
                        #grp['bounds'].rect[3] = page_size['height']

            # ページごとに処理
            for group_no, grp in enumerate(keyword_group):
                # group_no = page
                page_size = self.papers[group_no]

                ## グループの領域を検出
                ## グループ文字の左上にズレがあるのでXYともに揃える
                #grp_max = len(grp)
                #for i in range(0,grp_max):
                #    for j in range(i+1,grp_max):
                #        grp_a = grp[i]
                #        grp_b = grp[j]
                #        if grp_a['page'] != grp_b['page']: # ページが違う場合は対象外
                #            continue

                #        # k=0:X座標  k=1:Y座標
                #        for k in range(0,2):
                #            tl = k
                #            br = k+2

                #            if grp_a['bounds'].rect[tl] < grp_b['bounds'].rect[tl] < grp_a['bounds'].rect[br]:
                #                grp_b['bounds'].rect[tl] = grp_a['bounds'].rect[tl]
                #            elif grp_b['bounds'].rect[tl] < grp_a['bounds'].rect[tl] < grp_b['bounds'].rect[br]:
                #                grp_a['bounds'].rect[tl] = grp_b['bounds'].rect[tl]

                a = 0
                col_no = -1
                col_bounds = []
                # 隣接した領域との境界を調整
                base = Bound()

                sorted_grp = sorted(grp, key=lambda x:x['bounds'].rect[0])          # X方向
                grp_max = len(sorted_grp)
                for s_grp in sorted_grp:
                    grp_bounds = s_grp['bounds']
                #for i in range(0,grp_max):
                    #grp_bounds = sorted_grp[i]['bounds']

                    tl = 0
                    br = 0+2

                    # 同一行判定
                    if base.rect[tl] <= grp_bounds.rect[tl] <= base.rect[br]:
                        include = True
                    elif grp_bounds.rect[tl] <= base.rect[tl] <= grp_bounds.rect[br]:
                        include = True
                    else:
                        include = False

                    if include:
                        s_grp['col_no'] = col_no

                        if grp_bounds.rect[tl] < base.rect[tl]:
                            base.rect[tl] = grp_bounds.rect[tl]
                        if base.rect[br] < grp_bounds.rect[br]:
                            base.rect[br] = grp_bounds.rect[br]

                    else:
                        col_no = col_no + 1
                        s_grp['col_no'] = col_no

                        base = copy.deepcopy(grp_bounds)
                        col_bounds.append(base)

                col_max = len(col_bounds)
                # X方向　左右に拡張
                # row == 0  左端
                col_bounds[0].rect[0] = 0
                for i in range(0,col_max-1):
                    col_bounds[i].rect[2] = col_bounds[i+1].rect[0]-1
                # col_no    右端
                col_bounds[col_no].rect[2] = page_size['width']

                for s_grp in sorted_grp:
                    col_no = s_grp['col_no']
                    s_grp['bounds'].rect[0] = col_bounds[col_no].rect[0]
                    s_grp['bounds'].rect[2] = col_bounds[col_no].rect[2]

                #sorted_grp = sorted(sorted_grp, key=lambda x:x['bounds'].rect[1])   # Y方向
                #for i in range(0,2):
                #    prev_grp = None
                #    tl = 1 - i
                #    bl = i + 2
                #    for s_grp in sorted_grp:
                #        if prev_grp:
                #            if s_grp['bounds'].rect[tl] == prev_grp['bounds'].rect[tl]:
                #                prev_grp['bounds'].rect[bl] = s_grp['bounds'].rect[i]-1

                #        page_size = self.papers[int(s_grp['page'])-1]
                #        s_grp['bounds'].rect[bl] = page_size['width'] if i == 0 else page_size['height']
                #        prev_grp = s_grp

                # DEBUG: sorted_grp = sorted(sorted_grp, key=lambda x:x['bounds'].rect[1],reverse=True)   # Y方向

                # X方向　左右に拡張
                # row == 0  左端
                # col_no    右端

                # Y方向　上下に拡張
                # 同一 col_no 内の最初
                # 同一 col_no 内の最後
                sorted_grp = sorted(sorted_grp, key=lambda x:(x['col_no'], x['bounds'].rect[1]))   # Y方向

                prev_grp = None
                for s_grp in sorted_grp:
                    if prev_grp:
                        if s_grp['col_no'] == prev_grp['col_no']:
                            prev_grp['bounds'].rect[3] = s_grp['bounds'].rect[1] - 1
                        else:
                            prev_grp['bounds'].rect[3] = page_size['height']
                            s_grp['bounds'].rect[1] = 0
                    else:
                        s_grp['bounds'].rect[1] = 0

                    prev_grp = s_grp

                # 最後
                sorted_grp[-1]['bounds'].rect[3] = page_size['height']

                for s_grp in sorted_grp:
                    s_grp['bounds'].recalc()

                keyword_group[group_no] = sorted_grp

        self.keyword_group = keyword_group
        a = 0

        #paper_width     = paper['width']
        #paper_height    = paper['height']

        # 元データをコピー
        accorded_texts = []
        for cnt, text in enumerate(all_texts):
            accorded_texts.append({'index':cnt,'text':text})

            #accorded_texts = all_texts[:]

        accorded_characters = []
        for cnt, character in enumerate(all_characters):
            accorded_characters.append({'index':cnt,'text':character})

        # 抽出項目をcol_idでソート
        #cols = sorted(self.format_cols, key=lambda x:x['col_id'],reverse=True)
        cols = sorted(self.format_cols, key=lambda x:x['col_id'])

        id      = ''
        name    = ''
        ii = 0

        ret_cols = []   #　空の抽出項目リスト

        # 抽出項目ごとの処理
        for col in cols:
            r = {}
            r['col_id']         = col['col_id']
            r['col_name']       = col['col_name']
            r['itask_form_id']  = col['itask_form_id']

            #　抽出条件のソート
            col_conds = sorted(col['col_conditions'], key=lambda x:x['conditions_sort_number'])
            #col_conds = sorted(col['col_conditions'], key=lambda x:x['conditions_sort_number'],reverse=True)

            # 条件
            OK  = False
            N   = 0
            keyword = ''

            next_search  = Bound()

            found_text = {}

            result_text = ''
            result_text_bounds = None
            result_page = ''

            result_keyword = ''
            result_keyword_bounds = None
            result_keyword_page     = ''

            result_text_bounds_list = None
            result_keyword_bounds_list = None

            block_result = None

            #　抽出条件ごとの処理 (複数条件で一項目*******************)
            for cond in col_conds:
                cid = int(cond['conditions_id'])


                # get_flag:OK まで絞り込みを繰り返し
                for conds_param in cond['itask_col_conditions_parameter']:

                    try:
                        format_page = conds_param['i_task_format_page']
                    except:
                        format_page = '' #'1'

                    try:
                        N = int(conds_param['n'])
                    except:
                        N = 0 # None

                    if next_search.is_empty() == True:
                        try:
                            search  = Bound(vertices=None,left=int(conds_param['search_start_x']), top=int(conds_param['search_start_y']), right=int(conds_param['search_end_x']), bottom=int(conds_param['search_end_y']))
                        except:
                            search  = Bound()

                        search_flag = True
                        #if search.is_empty() == True:
                        #    search  = Bound(right=paper_width,bottom=paper_height)
                        #else:
                        #    # パラメータに応じてスケールとオフセット処理
                        #    if self.in_calibration_template == False and self.in_calibration_non == False:
                        #        # ページのキャリブレーションデータを検索
                        #        templ = [d.get('template') for d in self.in_calibration if d.get('file') == int(format_page)-1]
                        #        try:
                        #            offset_x, offset_y = 0, 0
                        #            scale_x, scale_y = '1.0', '1.0'

                        #            loaded_image = [d.get('bound') for d in self.calibration if d.get('file') == int(format_page)-1]
                        #            if len(loaded_image) > 0:

                        #                offset_x = templ[0].get_left()
                        #                offset_y = templ[0].get_top()
                        #                # searchを　一旦　(0,0)基点にする
                        #                search.offset(-offset_x, -offset_y)

                        #                if self.in_calibration_scale:
                        #                    loaded_image_w, loaded_image_h = loaded_image[0].get_width(), loaded_image[0].get_height()
                        #                    templ_w, templ_h = templ[0].get_width(), templ[0].get_height()
                        #                    if loaded_image_w != templ_w:
                        #                        scale_x = str(float(loaded_image_w) / float(templ_w))
                        #                    if loaded_image_h != templ_h:
                        #                        scale_y = str(float(loaded_image_h) / float(templ_h))

                        #                    if scale_x != '1.0' or scale_y != '1.0':
                        #                        search.scale(scale_x, scale_y)

                        #                # オフセット処理ONの場合は対象文書の左上、OFFの場合はテンプレートの左上（）
                        #                if self.in_calibration_offset:
                        #                    offset_x = loaded_image[0].get_left()
                        #                    offset_y = loaded_image[0].get_top()

                        #                search.offset(offset_x, offset_y)

                        #                #scale  = True if self.in_calibration_scale == True and (scale_x != '1.0' or scale_y != '1.0') else False


                        #        except:
                        #            None

                    else:
                        search = next_search
                        search_flag = False

                    try:
                        area    = Bound(vertices=None,left=int(conds_param['area_start_x']), top=int(conds_param['area_start_y']), right=int(conds_param['area_end_x']), bottom=int(conds_param['area_end_y']))
                    except:
                        area    = Bound()

                    try:
                        keyword = conds_param['keyword']
                        regex = regex_space(keyword)
                        keyword_list = conds_param['keyword_list']
                        key_grp_bounds = conds_param['key_grp_bounds']
                        key_grp = conds_param['key_grp']
                        keyword_opt = conds_param['keyword_opt']
                    except:
                        keyword = ''
                        regex   = ''
                        keyword_list = [REGEX_SEARCH_NON]
                        key_grp_bounds = Bound()
                        key_grp = ''
                        keyword_opt = {'flags':'', 'text_list':['']}

                    try:
                        search_opt = conds_param['search_opt']
                    except:
                        search_opt = 'WHOLE'

                    if 'PART' in search_opt.upper():
                        search_part = True
                    else:
                        search_part = False

                    if cid == 3: # keyword
                        result_text = keyword
                        OK = True
                    else:
                        if search.is_empty() == False or search_flag == True:
                            if cid == 16:
                                aaaaaaa = 0
                            # search指定があるので範囲で検索
                            #大事
                            ret = self.FindItem(accorded_texts if cid != 6 else accorded_characters,self.papers,cid,N,format_page,search,search_part,keyword_list,key_grp_bounds,keyword_opt)
                            # found_text, found_keyword, text_bounds_list, keyword_bounds_list = self.FindItem(accorded_texts if cid != 6 else accorded_characters,self.papers,cid,N,format_page,search,search_part,keyword_list,key_grp_bounds,keyword_opt)
                            #found_text = self.FindItem(accorded_texts if cid != 6 else accorded_characters,self.papers,cid,N,format_page,search,search_part,regex,keyword_list)
                            #found_text = self.FindItem(accorded_texts if cid != 6 else accorded_characters,self.papers,cid,N,format_page,search,search_part,keyword,regex)
#                            found_text = self.FindItem(accorded_texts,cid,N,format_page,search,search_part,keyword,regex)

                            if ret is None:
                            # if ret is None or not [True for x in ret if x is not None]:  # ret:tuple 全てNone
                            # if (not None) not in ret:
                            # if found_text == None:
                                # 見つからないので継続不可
                                result_text         = ''
                                result_text_bounds  = None
                                result_page         = ''
                                result_keyword          = ''
                                result_keyword_bounds   = None
                                result_keyword_page     = ''
                                result_key_grp          = ''

                                result_text_bounds_list = None
                                result_keyword_bounds_list = None

                                block_result        = None

                                OK = True
                            elif area.is_empty() == True:
                                if len(ret) >= 5:
                                    block_result        = ret[4]
                                else: #if len(ret) >= 4:
                                    block_result = None

                                    found_text          = ret[0]
                                    found_keyword       = ret[1]
                                    text_bounds_list    = ret[2]
                                    keyword_bounds_list = ret[3]

                                    # 後続項目なし　なので項目確定
                                    result_text             = found_text['text']['text']
                                    result_text_bounds      = found_text['text']['bounds']
                                    result_page             = found_text['text']['page']
                                    result_key_grp          = key_grp
                                    if found_keyword:
                                        result_keyword          = found_keyword['text']
                                        result_keyword_bounds   = found_keyword['bounds']
                                        result_keyword_page     = found_keyword['page']
                                    else:
                                        result_keyword          = ''
                                        result_keyword_bounds   = None
                                        result_keyword_page     = ''

                                    result_text_bounds_list = text_bounds_list
                                    result_keyword_bounds_list = keyword_bounds_list

                                OK = True
                            else:
                                # 後続項目あり
                                area.offset(found_text['text']['bounds'].get_left(), found_text['text']['bounds'].get_top())
                                next_search = area

                    break #itask_col_conditions_parameterは当面1個

                if OK == True:
                    break

            # 項目の種別による処理
            if block_result is not None:
                # block_result
                r['block_result'] = block_result
            else:
                r['col_result']         = result_text
                if result_text_bounds:
                    r.update(**result_text_bounds.get_bound())

                r['col_result_group']   = key_grp

                r['col_result_page']    = result_page

                r['col_keyword'] = result_keyword
                if result_keyword_bounds:
                    r.update(**result_keyword_bounds.get_bound(prefix="keyword_"))
                r['col_keyword_page'] = result_keyword_page

                if result_text_bounds_list:
                    r['result_pos'] = result_text_bounds_list
                if result_keyword_bounds_list:
                    r['keyword_pos'] = result_keyword_bounds_list


            #if col['itask_form_id'] == '0': #　文字列　後
            #    r['col_result'] = col['col_comment']#'ABCDE'
            #elif col['itask_form_id'] == '1': #　文字列　前
            #    r['col_result'] = '1,234,567'
            #elif col['itask_form_id'] == '2': #　日付
            #    r['col_result'] = '2019年8月1日'
            #elif col['itask_form_id'] == '3': #　キー
            #    r['col_result'] = keyword
            #elif col['itask_form_id'] == '4': #　一部一致
            #    r['col_result'] = col['itask_form_id'] + '(Not implement)'
            #else:
            #    r['col_result'] = col['itask_form_id'] + '(Not implement)'

            #　結果の保存
            ret_cols.append(r)


        self.outData['root_str']                    = self.root_str
        self.outData['number_of_images']            = self.number_of_images
        self.outData['open_page_list']              = self.open_page_list
        self.outData['analyze']                     = self.analyze
        self.outData['calibration']                 = self.out_calibration
        self.outData['format_info']                 = {}
        self.outData['format_info']['format_id']    = self.inData['format_info']['format_id']
        self.outData['format_info']['cols']         = ret_cols


        #client = vision.ImageAnnotatorClient()

        #debug_print( "OpenPapers : {} : {}".format(self.id, self.uri) )
        #with open(self.uri, 'rb') as f:
        #    debug_print('END  #####################\n')



        #client = vision.ImageAnnotatorClient()
        ## The name of the image file to annotate
        #file_name = os.path.join(os.path.dirname(__file__),'content_0.jpg')
        ## Loads the image into memory
        #with io.open(file_name, 'rb') as image_file:
        #    content = image_file.read()

        #image = types.Image(content=content)

        #response = client.text_detection(image=image)

        #texts = response.text_annotations
        #print('Texts:')

        #for text in texts:
        #    print('\n"{}"'.format(text.description), end=', ')
        #    #print('\n"{}"'.format(text.description))

        #    vertices = (['({},{})'.format(vertex.x, vertex.y)
        #                for vertex in text.bounding_poly.vertices])

        #    print('{}'.format(','.join(vertices)))
        #    #print('bounds: {}'.format(','.join(vertices)))
        #    ii = 0
    #手動分析の分析処理
    def Analyze_lines(self):
        combine_rows = self.combine_rows
        recode = {}
        page_codes = []
        for page, paper in enumerate(self.papers):
            page_str = str(page+1)
            codes=[]
            ylist=[]
            for c in paper['characters']:
                addylistflag=True
                newy=0
                debug_print( '##############################engine2>Analyze_lines 4675#'+c['text']+'#',level=DEBUG_ROWS_INFO)
                for y in ylist:
                    if y+50>c['bounds'].rect[1] and y-50<c['bounds'].rect[1] :
                        newy = y
                        addylistflag=False
                if addylistflag :
                    newy = c['bounds'].rect[1]
                    ylist.append(c['bounds'].rect[1])
                codes.append([c['text'],c['bounds'].rect[0],c['bounds'].rect[1],c['bounds'].rect[2],c['bounds'].rect[3],newy])
            codes = sorted(codes,key=lambda x:(x[5],x[1]))
            page_codes.append(codes)
        recode["page_codes"] = page_codes
        return recode
    #個人申告計算書の分析処理
    def Analyze_kojin(self):

        combine_rows = self.combine_rows

        aa = time.time()

        # ワード単位に分割
        for loop in range(100):
            split_cnt, combine_rows = self.split_words(combine_rows,0,loop)
            if split_cnt == 0:
                break
        else:
            b = 0
        bb = time.time()

        self.combine_rows = combine_rows
        #ワード単位に分けた行

        #　すべてのページのテキストをまとめる
        all_texts = self.combine_rows #[]
        all_characters = []

        print(">>>>>>>>>>>>>>>>>>>>>4516>>>>>>>>>>>>>>")
        #青色申告決算書ページ
        aoiroShikokuKesansyoPage=9999
        #貸借対照表ページ
        taisyakuTaisyouPage=9999
        #雑収入
        zatusyunyuPage=9999
        t3=[]
        t1=[]
        m1=[]
        t2_0=[]
        t2_1=[]
        m2=[]
        t2_1_old=[]
        m2_old=[]
        for page, paper in enumerate(self.papers):
            page_str = str(page+1)
            #for text in paper['texts']:
            #    text['page'] = page_str
            #    all_texts.append(text)
            isAoiroShikokuKesansyo=False
            isTaisyakuTaisyou=False
            isZatusyunyu=False
            minx=1000000
            maxx=0
            for c in paper['characters']:
                if c['bounds'].rect[0]<minx :
                    minx = c['bounds'].rect[0]
                if c['bounds'].rect[2]>maxx :
                    maxx = c['bounds'].rect[2]
            
            if self.special_handling=="special_handling0" or  self.special_handling=="special_handling1" :
                #個人特別書式####################
                if paper.get("boxes") is not None and len(paper["boxes"])>1 and  paper.get("characters") is not None and len(paper["characters"])>1 and len(paper["boxes"])>=44:
                    xys=paper["boxes"]
                    
                    if len(xys)>=16 :
                        i=0
                        for c in xys:
                            if i>=16 :
                                i=i+1
                                continue
                            y=(c[3]+c[1])/2
                            c_h=c[3]-c[1]
                            an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper["characters"],0,y,c[0],c[2],0-(c[3]-c[1])/2-20,c_h*2,False,True,False,self.kojin_tri[page])
                            if an is None :
                                t1.append([None,c[0],c[1],c[2],c[3],page])
                            else :
                                t1.append([an,c[0],c[1],c[2],c[3],page])
                            i=i+1
                    if len(xys)>=32 :
                        h_sample_m=[None,None,None,None,None,None,None,None,2097,2196,2290,2379,2478,2577,None,None,None]
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"消耗品費",0.8)
                        if m_text is None :
                            m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"減価償却費",0.8)
                        if m_text is None :
                            m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"福利厚生費",0.8)
                        if m_text is None :
                            m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"給料賃金",0.8)
                        if m_text is None :
                            m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"外注工賃",0.8)
                        if m_text is None :
                            m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"利子割引料",0.8)
                        if m_text is None :
                            m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"地代家賃",0.8)
                        addx1x2=True
                        i=0
                        for c in xys:
                            if i<=15 or i>=33 :
                                i=i+1
                                continue
                            y=(c[3]+c[1])/2
                            c_h=c[3]-c[1]
                            an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper["characters"],0,y,c[0],c[2],0-(c[3]-c[1])/2-20,c_h*2,False,True,False,self.kojin_tri[page])
                            if an is None :
                                t1.append([None,c[0],c[1],c[2],c[3],page])
                            else :
                                t1.append([an,c[0],c[1],c[2],c[3],page])
                            if m_x1 is None :
                                m_x2=c[0]-(2214-2100)
                                m_x1=c[0]-(2214-1450)
                                if self.special_handling=="special_handling1" :
                                    m_x2=c[0]-(2309-2228)
                                    m_x1=c[0]-(2309-1854)
                                addx1x2=False
                            elif addx1x2 :
                                m_x1=m_x1-35
                                m_x2=m_x2+40
                                addx1x2=False
                            if h_sample_m[i-16] is not None and m_x1 is not None and m_x2 is not None :
                                an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],m_x1,y,0,m_x2,(c[1]-c[3])/2)
                                m1.append([an,first_x1,first_y1,last_x2,last_y2])
                            else :
                                m1.append([None,None,None,None,None])
                            i=i+1
                    if len(xys)>=44 :
                        h_sample_m =[None,1434,1524,None,None,None,1901,2000,None,None,None,None]
                        h_sample_mr=[None,1434,1524,None,None,None,1901,2000,None,None,None,None]
                        r_text,r_x1,r_y1,r_x2,r_y2,r_c_h=get_right_characters(paper['characters'],"貸倒引当金",0.8)
                        if r_text is None :
                            r_text,r_x1,r_y1,r_x2,r_y2,r_c_h=get_right_characters(paper['characters'],"専従者給与",0.8)
                        addx1x2=True
                        i=0
                        for c in xys:
                            if i<=32 or i>=45 :
                                i=i+1
                                continue
                            y=(c[3]+c[1])/2
                            c_h=c[3]-c[1]
                            an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper['characters'],0,y,c[0],c[2],0-(c[3]-c[1])/2,c_h*2,False,True,False,self.kojin_tri[page])
                            if an is None :
                                t1.append([None,c[0],c[1],c[2],c[3],page])
                            else :
                                t1.append([an,c[0],c[1],c[2],c[3],page])

                            if r_x1 is None :
                                r_x2=c[0]-(2214-2100)
                                r_x1=c[0]-(2214-1450)
                                if self.special_handling=="special_handling1" :
                                    m_x2=c[0]-(3432-3340)
                                    m_x1=c[0]-(3432-3018)
                                addx1x2=False
                            elif addx1x2 :
                                r_x1=r_x1-35
                                r_x2=r_x2+200
                                addx1x2=False
                            if h_sample_mr[i-33] is not None and r_x1 is not None and r_x2 is not None :
                                an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],r_x1,y,0,r_x2,(c[1]-c[3])/2-3)
                                m1.append([an,first_x1,first_y1,last_x2,last_y2])
                            else :
                                m1.append([None,None,None,None,None])
                            i=i+1
                    ##########################################################################################
                    #結果オブジェクトを生成する###############################################################
                    ##########################################################################################
                    ret_cols = []   #　空の抽出項目リスト
                    i=0
                    cl1=[]
                    cl1.append(["売上（収入）金額",1,1,0,0,0,1])
                    cl1.append(["期首棚卸高",1,2,1,0,4,-1])
                    cl1.append(["仕入金額",1,2,2,0,0,-1])
                    cl1.append(["小計",1,2,0,0,-3,1])
                    cl1.append(["期末棚卸高",1,2,3,0,6,1])
                    cl1.append(["差引原価",1,2,0,0,-9,1])
                    cl1.append(["差引金額",1,3,0,0,-4,1])
                    cl1.append(["租税公課",1,4,2,2,1,-1])
                    cl1.append(["荷造運賃",1,4,2,13,4,-1])
                    cl1.append(["水道光熱費",1,4,2,3,1,-1])
                    cl1.append(["旅費交通費",1,4,2,4,3,-1])
                    cl1.append(["通信費",1,4,2,5,1,-1])
                    cl1.append(["広告宣伝費",1,4,2,15,1,-1])
                    cl1.append(["接待交際費",1,4,2,6,1,-1])
                    cl1.append(["損害保険料",1,4,2,7,3,-1])
                    cl1.append(["修繕費",1,4,2,8,1,-1])
                    cl1.append(["消耗品費",1,4,2,9,1,-1])
                    cl1.append(["減価償却費",1,4,2,1,1,-1])
                    cl1.append(["福利厚生費",1,4,1,8,1,-1])
                    cl1.append(["給料賃金",1,4,1,0,1,-1])
                    cl1.append(["外注工賃",1,4,2,14,3,-1])
                    cl1.append(["利子割引料",1,7,0,2,9,-1])
                    cl1.append(["地代家賃",1,4,2,11,1,-1])
                    cl1.append(["貸倒金",1,4,2,38,2,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["雑費",1,4,2,45,1,-1])
                    cl1.append(["経費の計",1,20,0,0,1,-1])
                    cl1.append(["経費の差引金額",1,5,0,0,-6,-1])
                    cl1.append(["貸倒引当金戻入",1,6,0,3,1,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["計",1,6,0,0,-4,-1])
                    cl1.append(["専従者給与",1,4,1,0,2,-1])
                    cl1.append(["貸倒引当金繰入",1,4,2,36,1,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["",2,999,0,0,0,-1])
                    cl1.append(["計",1,7,0,0,-4,-1])
                    cl1.append(["青色申告特別控除前の所得金額",1,11,0,0,1,-1])
                    cl1.append(["青色申告特別控除額",1,20,0,0,2,-1])
                    cl1.append(["所得金額",1,11,0,0,-7,-1])
                    if t1 is None or len(t1)==0 :
                        t1=[]
                        m1=[]
                        for num in range(len(cl1)): 
                            t1.append([None,None,None,None,None,0])
                            m1.append([None,None,None,None,None,0])
                    for cl1_s in cl1 :
                        if i<len(t1) :
                            ts1=t1[i]
                        else :
                            ts1=[None,None,None,None,None]
                        r = {}
                        r['col_id']         = "n"+str(i)
                        r['col_name']       = "n"+str(i)
                        r['itask_form_id']  = 99999
                        candidate=[]
                        if (i<16 or m1[i-16][0] is None) :
                            if cl1[i] is not None :
                                candidate_sub={}
                                candidate_sub["order"]=cl1[i][1]
                                candidate_sub["family"]=cl1[i][2]
                                candidate_sub["genus"]=cl1[i][3]
                                candidate_sub["species"]=cl1[i][4]
                                candidate_sub["variety"]=cl1[i][5]
                                candidate_sub["property"]=cl1[i][6]
                                candidate_sub["variety_name"]=cl1[i][0]
                                candidate.append(candidate_sub)
                                if cl1[i][2]==999 :
                                    r["kotei"]="m1_"+str(i)
                                else :
                                    r["kotei"]="kotei_1_"+str(i)
                            else :
                                candidate_sub={}
                                candidate_sub["order"]=1
                                candidate_sub["family"]=9
                                candidate_sub["genus"]=9
                                candidate_sub["species"]=9
                                candidate_sub["variety"]=999
                                candidate_sub["property"]=-1
                                candidate_sub["variety_name"]="予期せぬ項目"
                                candidate.append(candidate_sub)
                                r["kotei"]="m1_"+str(i)
                        elif i>=16 and m1[i-16][0] is not None:
                            close=self.account_db.search_variety_title_syou(m1[i-16][0])
                            for xi, xc in enumerate(close):
                                if "車両費"==xc or "車輛費"==xc or "車輌費"==xc :
                                    close[0], close[xi] = close[xi], close[0]
                            r["kotei"]="m1_"+str(i)
                            candidate=[]
                            for c in close :
                                code = self.account_db.search_variety_code(c,code=(1,4),between=(1,35))
                                candidate_sub={}
                                if code is not None and len(code)>0 and code[0] is not None :
                                    if code[0]==2 and code[1]==40 and code[2]==2 and code[3]==0 and code[4]==29 :
                                        candidate_sub["order"]=2
                                        candidate_sub["family"]=50
                                        candidate_sub["genus"]=0
                                        candidate_sub["species"]=5
                                        candidate_sub["variety"]=1
                                        candidate_sub["property"]=1
                                        candidate_sub["variety_name"]="長期借入金"
                                    else :
                                        # safety: ensure code has >=6 elements before unpacking
                                        if not _code_len_ok(code, 6):
                                            continue
                                        candidate_sub["order"]=code[0]
                                        candidate_sub["family"]=code[1]
                                        candidate_sub["genus"]=code[2]
                                        candidate_sub["species"]=code[3]
                                        candidate_sub["variety"]=code[4]
                                        candidate_sub["property"]=code[5]
                                        candidate_sub["variety_name"]=c
                                if i>16 and i<33 :
                                    if _code_len_ok(code, 2) and code[0] == 1 and (code[1] in (2, 4, 7, 10)) :
                                        debug_print( '##############################4932 c is '+c+'#############################',level=DEBUG_ROWS_INFO)
                                        if c=="支払手数料" :
                                            candidate_sub["order"]=1
                                            candidate_sub["family"]=4
                                            candidate_sub["genus"]=2
                                            candidate_sub["species"]=18
                                            candidate_sub["variety"]=1
                                            candidate_sub["property"]=-1
                                            candidate_sub["variety_name"]=c
                                            candidate.append(candidate_sub)
                                        elif _code_len_ok(code, 2) and code[1] == 4:
                                            candidate.append(candidate_sub)
                                elif i>33 and i<48 :
                                    if _code_len_ok(code, 2) and code[0] == 1 and (code[1]==4 or code[1]==7 or code[1]==10) :
                                        candidate.append(candidate_sub)
                            if len(candidate)==0 :
                                if len(cl1)>i and cl1[i] is not None :
                                    candidate=[]
                                    candidate_sub={}
                                    candidate_sub["order"]=cl1[i][1]
                                    candidate_sub["family"]=cl1[i][2]
                                    candidate_sub["genus"]=cl1[i][3]
                                    candidate_sub["species"]=cl1[i][4]
                                    candidate_sub["variety"]=cl1[i][5]
                                    candidate_sub["property"]=cl1[i][6]
                                    candidate_sub["variety_name"]=cl1[i][0]
                                    candidate.append(candidate_sub)
                                    if cl1[i][2]==999 :
                                        r["kotei"]="m1_"+str(i)
                                    else :
                                        r["kotei"]="kotei_1_"+str(i)
                                else :
                                    candidate_sub={}
                                    candidate_sub["order"]=1
                                    candidate_sub["family"]=9
                                    candidate_sub["genus"]=9
                                    candidate_sub["species"]=9
                                    candidate_sub["variety"]=999
                                    candidate_sub["property"]=-1
                                    candidate_sub["variety_name"]="予期せぬ項目"
                                    candidate.append(candidate_sub)
                        r["candidate"]=candidate
                        r["amount_pre_year"]=""
                        if ts1[0] is None :
                            r["amount_this_year"]=""
                        else :
                            r["amount_this_year"]=ts1[0]
                        r["db_exist"]="1.00"
                        r["start_x"]=ts1[1]
                        r["start_y"]=ts1[2]
                        r["end_x"]=ts1[3]
                        r["end_y"]=ts1[4]
                        r["tabindex"]=2
                        r["page"]=int(self.pageNumber)
                        if ts1[1] is None :
                            r["start_x"]=0
                        if ts1[2] is None :
                            r["start_y"]=0
                        if ts1[3] is None :
                            r["end_x"]=0
                        if ts1[4] is None :
                            r["end_y"]=0
                        r["start_x"]=int(r["start_x"])
                        r["start_y"]=int(r["start_y"])
                        r["end_x"]=int(r["end_x"])
                        r["end_y"]=int(r["end_y"])
                        ret_cols.append(r)
                        i+=1
                    block_result={}
                    closing_date={}
                    closing_date["date"]=""
                    closing_date["page"]=1
                    closing_date["start_x"]=0
                    closing_date["start_y"]=0
                    closing_date["end_x"]=0
                    closing_date["end_y"]=0
                    block_result["closing_date"]=closing_date

                    company={}
                    company["candidate"]=[]
                    company["page"]=1
                    company["start_x"]=0
                    company["start_y"]=0
                    company["end_x"]=0
                    company["end_y"]=0
                    block_result["company"]=company

                    block_result["detail"]=ret_cols
                    cols=[]
                    cols_sub={}
                    cols_sub["col_id"]=""
                    cols_sub["col_name"]=""
                    cols_sub["itask_form_id"]=""
                    cols_sub["block_result"]=block_result
                    cols.append(cols_sub)
                    self.outData['root_str']                    = self.root_str
                    self.outData['number_of_images']            = self.number_of_images
                    self.outData['open_page_list']              = self.open_page_list
                    self.outData['analyze']                     = self.analyze
                    self.outData['calibration']                 = self.out_calibration
                    self.outData['format_info']                 = {}
                    self.outData['format_info']['format_id']    = self.inData['format_info']['format_id']
                    self.outData['format_info']['cols']         = cols
                    self.outData['document_judgment_flag']      = self.document_judgment_flag

                return



            text,x1,y1,x2,y2,c_h=get_right_characters(paper['characters'],"損益計算書",0.8)
            havesonekikeisansyo=False
            if x1 is not None and x1<minx+(maxx-minx)/2 :
                havesonekikeisansyo=True
            
            if (hikaku_characters(paper['characters'],"分所得税青色申告決算書",0.8) or havesonekikeisansyo) and hikaku_characters_shikokub(paper['characters']) == False :
                #文字で青色申告決算書の判定をする
                aoiroShikokuKesansyoPage=page
                isAoiroShikokuKesansyo=True
            elif (hikaku_characters(paper['characters'],"資産",0.8) or havesonekikeisansyo) and hikaku_characters_shikokub(paper['characters']) == False :
                #文字で青色申告決算書の判定をする
                taisyakuTaisyouPage=page
                isTaisyakuTaisyou=True
            elif (hikaku_characters(paper['characters'],"負債",0.8) or havesonekikeisansyo) and hikaku_characters_shikokub(paper['characters']) == False :
                #文字で青色申告決算書の判定をする
                taisyakuTaisyouPage=page
                isTaisyakuTaisyou=True
            elif (hikaku_characters(paper['characters'],"資本",0.8) or havesonekikeisansyo) and hikaku_characters_shikokub(paper['characters']) == False :
                #文字で青色申告決算書の判定をする
                taisyakuTaisyouPage=page
                isTaisyakuTaisyou=True
            elif hikaku_characters(paper['characters'],"貸借対照表",0.7) and (taisyakuTaisyouPage >100 or page>2) and hikaku_characters_shikokub(paper['characters']) == False :
                #文字で貸借対照表の判定をする
                taisyakuTaisyouPage=page
                isTaisyakuTaisyou=True
            elif hikaku_characters(paper['characters'],"資産負債調",0.7) and (taisyakuTaisyouPage >100 or page>2) and hikaku_characters_shikokub(paper['characters']) == False :
                #文字で貸借対照表の判定をする
                taisyakuTaisyouPage=page
                isTaisyakuTaisyou=True
            elif hikaku_characters(paper['characters'],"資產負債調",0.7) and (taisyakuTaisyouPage >100 or page>2) and hikaku_characters_shikokub(paper['characters']) == False :
                #文字で貸借対照表の判定をする
                taisyakuTaisyouPage=page
                isTaisyakuTaisyou=True
            elif hikaku_characters(paper['characters'],"給料賃金の内訳",0.8) and zatusyunyuPage >100 :
                #文字で貸借対照表の判定をする
                isZatusyunyu=True
            elif hikaku_characters(paper['characters'],"専従者給与の内訳",0.8) and zatusyunyuPage >100 :
                #文字で貸借対照表の判定をする
                isZatusyunyu=True
            elif hikaku_characters(paper['characters'],"雑収入",0.9) and zatusyunyuPage >100 :
                #文字で貸借対照表の判定をする
                zatusyunyuPage=page
                isZatusyunyu=True
            elif page==0 and hikaku_characters_shikokub(paper['characters']) == False:
                #文字で青色申告決算書の判定をする
                aoiroShikokuKesansyoPage=page
                isAoiroShikokuKesansyo=True
            elif page==1 and taisyakuTaisyouPage>99 and len(self.papers)==2 and hikaku_characters(paper['characters'],"所得から差し引かれる",0.8) == False :
                isTaisyakuTaisyou=True
                taisyakuTaisyouPage=page
            elif page==1 and len(self.papers)==3:
                isZatusyunyu=True
            elif page==2 and taisyakuTaisyouPage>99 and hikaku_characters_shikokub(paper['characters']) == False :
                #文字で青色申告決算書の判定をする
                isTaisyakuTaisyou=True
                taisyakuTaisyouPage=page

            for c in paper['characters']:
                c['page'] = page_str
                all_characters.append(c)
            print("###############"+str(page)+"の処理##################")

            #文字で青色申告決算書の場合
            if isAoiroShikokuKesansyo and len(t1)<5 :
              t1=[]
              m1=[]
              print("###############"+page_str+"は青色申告決算書##################")
              #青色申告書の中身

              answer,first_x1,first_y1,last_x2,last_y2,line=None,None,None,None,None,None
              #「雑収入を含む」に関する情報を集計
              text,x1,y1,x2,y2,c_h=get_right_characters(paper['characters'],"雑収入を含む",0.8)
              otext,ox1,oy1,ox2,oy2,oc_h=get_right_characters(paper['characters'],"消耗品費",0.6) 
              if otext is None :
                otext,ox1,oy1,ox2,oy2,oc_h=get_right_characters(paper['characters'],"福利厚生費",0.7) 
              if otext is None :
                otext,ox1,oy1,ox2,oy2,oc_h=get_right_characters(paper['characters'],"利子割引料",0.7) 
              A0text,A0x1,A0y1,A0x2,A0y2,A0c_h=get_right_characters(paper['characters'],"修繕費",0.8) 
              A1text,A1x1,A1y1,A1x2,A1y2,A1c_h=get_right_characters(paper['characters'],"損害保険料",0.7) 
              A2text,A2x1,A2y1,A2x2,A2y2,A2c_h=get_right_characters(paper['characters'],"水道光熱費",0.7) 
              if c_h is not None :
                textmaxx=c_h*2
              if oc_h is not None :
                textmaxx=oc_h*2
              h_sample_o=[1383,1524,1622,1718,1809,1910,2054,2199,2290,2387,2481,2574,2673,2766,2865,2958]
              h_sample=[1383,1524,1622,1718,1809,1910,2054,2199,2290,2387,2481,2574,2673,2766,2865,2958]
              if self.xyl.get(page) is not None and len(self.xyl[page])>1 :
                xys=self.xyl[page]
                for c in xys:
                    y=(c[3]+c[1])/2
                    c_h=c[3]-c[1]
                    an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(self.xyl[1000],0,y,c[0],c[2],0-(c[3]-c[1])/2-20,c_h*2,False,True,False,self.kojin_tri[page])
                    if an is None :
                        t1.append([None,c[0],c[1],c[2],c[3],page])
                    else :
                        t1.append([an,c[0],c[1],c[2],c[3],page])
              else :
                if x1 is not None and ox1 is not None :
                  #雑収入の数字を検索するｙ座標
                  y2=y2-c_h-round(c_h/3)
                  #数値を検索する距離
                  line=round(c_h*3.5)
                  answer,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper['characters'],x2,y2,line,ox1,round(c_h*2/2),textmaxx,False,False,True,self.kojin_tri[page])
                  line=line+x2
                  t1.append([answer,first_x1,first_y1,last_x2,last_y2,page])
                elif ox1 is not None :
                  #「雑収入を含む」を見つからない場合「売上収入金額」に関する情報を集計
                  text,x1,y1,x2,y2,c_h=get_right_characters(paper['characters'],"売上収入金額",0.8) 
                  if x1 is not None :
                      #雑収入の数字を検索するｙ座標
                      y2=y2+round(c_h/3)
                      #数値を検索する距離
                      line=round(c_h*3.5)
                      print("ch:::::"+str(ox1))
                      print("ch:::::"+str(oc_h))
                      answer,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper['characters'],x2,y2,line,ox1,round(c_h*2/2),textmaxx,False,False,True,self.kojin_tri[page])
                      line=line+x2
                      t1.append([answer,first_x1,first_y1,last_x2,last_y2,page])
              if len(t1)>0 :
                  nh=None
                  oh=None
                  #修繕費がある場合
                  if A0x1 is not None and y2 is not None :
                    #現在比較項目のY座標
                    ny=A0y2-round(A0c_h/2)
                    #原始表の長さ
                    oh=h_sample_o[15]-h_sample_o[0]
                    #現在表の長さ
                    nh=ny-y2
                    print("4432::::::::"+str(ny)+"_"+str(oh)+"_"+str(nh))
                  #損害保険料がある場合
                  elif A1x1 is not None and y2 is not None :
                    #現在比較項目のY座標
                    ny=A1y2-round(A1c_h/2)
                    #原始表の長さ
                    oh=h_sample_o[14]-h_sample_o[0]
                    #現在表の長さ
                    nh=ny-y2
                  #水道光熱費がある場合
                  elif A2x1 is not None and y2 is not None :
                    #現在比較項目のY座標
                    ny=A2y2-round(A2c_h/2)
                    #原始表の長さ
                    oh=h_sample_o[9]-h_sample_o[0]
                    #現在表の長さ
                    nh=ny-y2
                  if len(t1)==1 :
                    #比率
                    hiritu=1
                    if nh is not None :
                        hiritu=nh/oh

                    i=0
                    for c in h_sample_o:
                        if i==0 :
                            h_sample[i]=y2
                        else :
                            print("4453::::::::"+str(y2)+"_"+str(h_sample[i])+"_"+str(h_sample[0])+"_"+str(hiritu))
                            h_sample[i]=y2+round((h_sample_o[i]-h_sample_o[0])*hiritu)
                        i+=1
                    i=0
                    last_i=0
                    for c in h_sample:
                        if i<(len(h_sample)) and i>0 :
                              h=t1[last_i][4]-round(t1[last_i][2])
                              h=t1[last_i][2]+round(h/2)
                              y2=round(h*h_sample[i]/h_sample[last_i])
                              an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper['characters'],0,y2,line,t1[0][3]+10,round(c_h*2/3),textmaxx,False,False,True,self.kojin_tri[page])
                              t1.append([an,first_x1,first_y1,last_x2,last_y2,page])
                              if an is not None :
                                  last_i=i
                        i+=1

                  ###########################################################################################################
                  #############青色申告2段####################################################################################
                  text,x1,y1,x2,y2,c_h=get_right_characters(paper['characters'],"消耗品費",0.6) 
                  if x1 is None :
                      text,x1a,y1,x2a,y2,c_h=get_right_characters(paper['characters'],"減価償却費",0.6) 
                      text,x1,y1a,x2,y2a,c_h=get_right_characters(paper['characters'],"福利厚生費",0.6) 
                      if y1a is not None and y1 is not None :
                        y1=y1-y1a+y1
                        y2=y2-y2a+y2
                      else :
                         y1=None
                         y2=None 
                      if x1 is None :
                        text,x1,y1a,x2,y2a,c_h=get_right_characters(paper['characters'],"利子割引料",0.6) 
                  otext,ox1,oy1,ox2,oy2,oc_h=get_right_characters(paper['characters'],"貸倒引当金",0.6) 

                  A2text,A2x1,A2y1,A2x2,A2y2,A2c_h=get_right_characters(paper['characters'],"損害保険料",0.6) 
                  A3text,A3x1,A3y1,A3x2,A3y2,A3c_h=get_right_characters(paper['characters'],"修繕費",0.6) 

                  A4text,A4x1,A4y1,A4x2,A4y2,A4c_h=get_right_characters(paper['characters'],"接待交際費",0.6) 

                  A0text,A0x1,A0y1,A0x2,A0y2,A0c_h=get_right_characters(paper['characters'],"利子割引料",0.6) 
                  A1text,A1x1,A1y1,A1x2,A1y2,A1c_h=get_right_characters(paper['characters'],"地代家賃",0.7) 
                  print("A0y2 is")
                  print(A0y2)
                  print("<<<<<<<<<<<<")
                  h_sample_o=[1338,1434,1524,1620,1719,1812,1901,2000,2097,2196,2290,2379,2478,2577,2670,2768,2913]
                  h_sample=  [1338,1434,1524,1620,1719,1812,1901,2000,2097,2196,2290,2379,2478,2577,2670,2768,2913]
                  h_sample_m=[None,None,None,None,None,None,None,None,2097,2196,2290,2379,2478,2577,None,None,None]
                  if self.xym.get(page) is not None and len(self.xym[page])>1 :
                    m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"消耗品費",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"減価償却費",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"福利厚生費",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"給料賃金",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"外注工賃",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"利子割引料",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"地代家賃",0.8)
                    addx1x2=True
                    i=0
                    xys=self.xym[page]
                    for c in xys:
                        y=(c[3]+c[1])/2
                        c_h=c[3]-c[1]
                        an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(self.xyl[1000],0,y,c[0],c[2],0-(c[3]-c[1])/2-20,c_h*2,False,True,False,self.kojin_tri[page])
                        if an is None :
                            t1.append([None,c[0],c[1],c[2],c[3],page])
                        else :
                            t1.append([an,c[0],c[1],c[2],c[3],page])
                        if m_x1 is None :
                            m_x2=c[0]-(2214-2100)+100
                            m_x1=c[0]-(2214-1450)
                            addx1x2=False
                        elif addx1x2 :
                            m_x1=m_x1-35
                            m_x2=m_x2+40+100
                            addx1x2=False
                        
                        if h_sample_m[i] is not None and m_x1 is not None and m_x2 is not None :
                            an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],m_x1,y,0,m_x2,(c[1]-c[3])/2)
                            m1.append([an,first_x1,first_y1,last_x2,last_y2])
                        else :
                            m1.append([None,None,None,None,None])
                        
                        i=i+1
                  elif x1 is not None and y1 is not None and ox1 is not None and ((A2x1 is not None and A3x1 is not None) or A4text is not None or A4text is not None or A0x1 is not None or A1x1 is not None) :
                      #消耗品費の数字を検索するｙ座標
                      y2=y2-round(c_h/2)
                      #数値を検索する距離
                      line=round(c_h*4)
                      line=line+x2
                      end_x=ox1-3*oc_h

                      if answer is not None :
                          #損害保険料　修繕費がある場合
                          if A2x1 is not None and A3x1 is not None :
                            #現在比較項目のY座標
                            ny=(A2y2+A3y2)/2-round(A2c_h/2)
                            #原始表の長さ
                            oh=h_sample_o[16]-h_sample_o[0]
                            #現在表の長さ
                            nh=ny-y2
                          #接待交際費がある場合
                          elif A4text is not None :
                            #現在比較項目のY座標
                            ny=A4y2-round(A4c_h/2)
                            #原始表の長さ
                            oh=h_sample_o[15]-h_sample_o[0]
                            #現在表の長さ
                            nh=ny-y2
                          #利子割引料がある場合
                          elif A0x1 is not None :
                            #現在比較項目のY座標
                            ny=A0y2-round(A0c_h/2)
                            #原始表の長さ
                            oh=h_sample_o[5]-h_sample_o[0]
                            #現在表の長さ
                            nh=ny-y2
                          #地代家賃がある場合
                          elif A1x1 is not None :
                            #現在比較項目のY座標
                            ny=A1y2-round(A1c_h/2)
                            #原始表の長さ
                            oh=h_sample_o[6]-h_sample_o[0]
                            #現在表の長さ
                            nh=ny-y2

                          #比率
                          hiritu=1
                          if nh is not None :
                            hiritu=nh/oh

                          i=0
                          for c in h_sample_o:
                            if i==0 :
                              h_sample[i]=y2
                            else :
                              h_sample[i]=y2+round((h_sample_o[i]-h_sample_o[0])*hiritu)
                            i+=1
                          print("h_sample is")
                          print(h_sample)
                          print("<<<<<<<<<<<<")
                          i=0
                          last_i=0
                          for c in h_sample:
                              if i<(len(h_sample)) :
                                  if i>0 :
                                    if t1[last_i+16][0] is None :
                                      h=h_sample[0]
                                    else :
                                      h=t1[last_i+16][4]-round(t1[last_i+16][2])
                                      h=t1[last_i+16][2]+round(h/2)
                                    y2=round(h*h_sample[i]/h_sample[last_i])
                                  else :
                                    x=y2-1246
                                    xi=0    
                                    for c in h_sample:
                                      h_sample[xi]=h_sample[xi]+x
                                      xi+=1
                                  an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper['characters'],0,y2,line,end_x,round(c_h*2/3),textmaxx,False,False,True,self.kojin_tri[page])
                                  if an is None and i==0 :
                                      t1.append([None,line,y1,end_x,y2,page])
                                      last_i=i
                                  else :
                                      t1.append([an,first_x1,first_y1,last_x2,last_y2,page])
                                  if an is not None :
                                      last_i=i
                                  
                                  if h_sample_m[i] is not None :
                                      an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],x1-c_h,y2,0,x2+8,round(c_h*2/3))
                                      m1.append([an,first_x1,first_y1,last_x2,last_y2])
                                  else :
                                      m1.append([None,None,None,None,None])
                              i+=1
                  elif self.xym.get(page) is not None and len(self.xym[page])>1 :
                    m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"消耗品費",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"減価償却費",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"福利厚生費",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"給料賃金",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"外注工賃",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"利子割引料",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"地代家賃",0.8)
                    addx1x2=True
                    xys=self.xym[page]
                    for c in xys:
                        y=(c[3]+c[1])/2
                        c_h=c[3]-c[1]
                        an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(self.xyl[1000],0,y,c[0],c[2],0-(c[3]-c[1])/2-20,c_h*2,False,True,False,self.kojin_tri[page])
                        if an is None :
                            t1.append([None,c[0],c[1],c[2],c[3],page])
                        else :
                            t1.append([an,c[0],c[1],c[2],c[3],page])
                        if m_x1 is None :
                            m_x2=c[0]-(2214-2100)+100
                            m_x1=c[0]-(2214-1450)
                            addx1x2=False
                        elif addx1x2 :
                            m_x1=m_x1-35
                            m_x2=m_x2+40+100
                            addx1x2=False
                        if h_sample_m[i] is not None and m_x1 is not None and m_x2 is not None :
                            an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],m_x1,y,0,m_x2,(c[1]-c[3])/2)
                            m1.append([an,first_x1,first_y1,last_x2,last_y2])
                        else :
                            m1.append([None,None,None,None,None])
                  else :
                      #予想していない動作
                      print ("予想していない動作")
                      debug_print("青色申告書読み込み予想しない問題  4707",level=DEBUG_ROWS_INFO)
                      for c in h_sample:
                          t1.append([None,None,None,None,None,page])
                          m1.append([None,None,None,None,None])
                  ###########################################################################################################
                  #############青色申告3段####################################################################################
                  text,x1,y1,x2,y2,c_h=get_right_characters(paper['characters'],"貸倒引当金",0.6) 
                  A0text,A0x1,A0y1,A0x2,A0y2,A0c_h=get_right_characters(paper['characters'],"青色申告特別控除前の所得金額",0.8) 
                  A1text,A1x1,A1y1,A1x2,A1y2,A1c_h=get_right_characters(paper['characters'],"青色申告特別控除額",0.8) 

                  h_sample_o=  [1338,1434,1524,1620,1719,1812,1901,2000,2097,2196,2290,2440]
                  h_sample=  [1338,1434,1524,1620,1719,1812,1901,2000,2097,2196,2290,2440]
                  h_sample_m =[None,1434,1524,None,None,None,1901,2000,None,None,None,None]
                  h_sample_mr=[None,1434,1524,None,None,None,1901,2000,None,None,None,None]
                  if self.xyr.get(page) is not None and len(self.xyr[page])>1 :
                    r_text,r_x1,r_y1,r_x2,r_y2,r_c_h=get_right_characters(paper['characters'],"貸倒引当金",0.8)
                    if r_text is None :
                        r_text,r_x1,r_y1,r_x2,r_y2,r_c_h=get_right_characters(paper['characters'],"専従者給与",0.8)
                    addx1x2=True
                    i=0
                    xys=self.xyr[page]
                    for c in xys:
                        y=(c[3]+c[1])/2
                        c_h=c[3]-c[1]
                        an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(self.xyl[1000],0,y,c[0],c[2],0-(c[3]-c[1])/2,c_h*2,False,True,False,self.kojin_tri[page])
                        if an is None :
                            t1.append([None,c[0],c[1],c[2],c[3],page])
                        else :
                            t1.append([an,c[0],c[1],c[2],c[3],page])

                        if r_x1 is None :
                            r_x2=c[0]-(2214-2100)
                            r_x1=c[0]-(2214-1450)
                            addx1x2=False
                        elif addx1x2 :
                            r_x1=r_x1-35
                            r_x2=r_x2+40
                            addx1x2=False
                        if h_sample_mr[i] is not None and r_x1 is not None and r_x2 is not None :
                            an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],r_x1,y,0,r_x2,(c[1]-c[3])/2)
                            m1.append([an,first_x1,first_y1,last_x2,last_y2])
                        else :
                            m1.append([None,None,None,None,None])
                        i=i+1
                  elif x1 is not None :
                      #消耗品費の数字を検索するｙ座標
                      y2=y2-round(c_h/2)
                      #数値を検索する距離
                      line=round(c_h*100/40)
                      line=line+x2

                      if answer is not None :

                          #青色申告特別控除前の所得金額がある場合
                          if A0x1 is not None :
                            #現在比較項目のY座標
                            ny=A0y2+round(A0c_h/2)
                            #原始表の長さ
                            oh=h_sample_o[9]-h_sample_o[0]
                            #現在表の長さ
                            nh=ny-y2
                          #青色申告特別控除額がある場合
                          elif A1x1 is not None :
                            #現在比較項目のY座標
                            ny=A1y2-round(A1c_h/2)
                            #原始表の長さ
                            oh=h_sample_o[10]-h_sample_o[0]
                            #現在表の長さ
                            nh=ny-y2

                          #比率
                          hiritu=1
                          if nh is not None :
                            hiritu=nh/oh

                          i=0
                          for c in h_sample_o:
                            if i==0 :
                              h_sample[i]=y2
                            else :
                              h_sample[i]=y2+round((h_sample_o[i]-h_sample_o[0])*hiritu)
                            i+=1

                          i=0
                          last_i=0
                          for c in h_sample:
                              print (str(c))
                              if i<(len(h_sample)) :
                                  if i>0 :
                                    if t1[last_i+33][0] is None :
                                      h=h_sample[0]
                                    else :
                                      h=t1[last_i+33][4]-round(t1[last_i+33][2])
                                      h=t1[last_i+33][2]+round(h/2)
                                    y2=round(h*h_sample[i]/h_sample[last_i])
                                  if i==9 :
                                        an,first_x1,first_y1,last_x2,last_y2=get_right_number(paper['characters'],0,y2,line,round(c_h*2/3),textmaxx,True,True,self.kojin_tri[page])
                                  else :
                                    an,first_x1,first_y1,last_x2,last_y2=get_right_number(paper['characters'],0,y2,line,round(c_h*2/3),textmaxx,False,True,self.kojin_tri[page])
                                  if an is None and i==0 :
                                      t1.append([None,line,y1,line+textmaxx*5,y2,page])
                                      last_i=i
                                  else :
                                      t1.append([an,first_x1,first_y1,last_x2,last_y2,page])
                                  if an is not None :
                                      last_i=i

                                  if h_sample_m[i] is not None :
                                      an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],x1-c_h,y2,0,x2+8,round(c_h*2/3))
                                      m1.append([an,first_x1,first_y1,last_x2,last_y2])
                                  else :
                                      m1.append([None,None,None,None,None])
                              i+=1
                  elif self.xyr.get(page) is not None and len(self.xyr[page])>1 :
                    xys=self.xyr[page]
                    r_text,r_x1,r_y1,r_x2,r_y2,r_c_h=get_right_characters(paper['characters'],"貸倒引当金",0.8)
                    if r_text is None :
                        r_text,r_x1,r_y1,r_x2,r_y2,r_c_h=get_right_characters(paper['characters'],"専従者給与",0.8)
                    addx1x2=True
                    for c in xys:
                        y=(c[3]+c[1])/2
                        c_h=c[3]-c[1]
                        an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(self.xyl[1000],0,y,c[0],c[2],0-(c[3]-c[1])/2,textmaxx,False,True,False,self.kojin_tri[page])
                        if an is None :
                            t1.append([None,c[0],c[1],c[2],c[3],page])
                        else :
                            t1.append([an,c[0],c[1],c[2],c[3],page])
                        if r_x1 is None :
                            r_x2=c[0]-(2214-2100)
                            r_x1=c[0]-(2214-1450)
                            addx1x2=False
                        elif addx1x2 :
                            r_x1=r_x1-35
                            r_x2=r_x2+40
                            addx1x2=False
                        if h_sample_mr[i] is not None and r_x1 is not None and r_x2 is not None :
                            an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],r_x1,y,0,r_x2,(c[1]-c[3])/2)
                            m1.append([an,first_x1,first_y1,last_x2,last_y2])
                        else :
                            m1.append([None,None,None,None,None])
                  else :
                      #予想していない動作
                      print ("予想していない動作")
                      debug_print("青色申告書読み込み予想しない問題  4794",level=DEBUG_ROWS_INFO)
                      for c in h_sample:
                          t1.append([None,None,None,None,None,page])
                          m1.append([None,None,None,None,None])
              else :
                  if self.xyl.get(page) is not None and len(self.xyl[page])>1 :
                    xys=self.xyl[page]
                    for c in xys:
                        y=(c[3]+c[1])/2
                        c_h=c[3]-c[1]
                        an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(self.xyl[1000],0,y,c[0],c[2],0-(c[3]-c[1])/2,c_h*2,False,True,False,self.kojin_tri[page])
                        if an is None :
                            t1.append([None,c[0],c[1],c[2],c[3],page])
                        else :
                            t1.append([an,c[0],c[1],c[2],c[3],page])
                        m1.append([None,None,None,None,None])
                  if self.xym.get(page) is not None and len(self.xym[page])>1 :
                    m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"消耗品費",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"減価償却費",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"福利厚生費",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"給料賃金",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"外注工賃",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"利子割引料",0.8)
                    if m_text is None :
                        m_text,m_x1,m_y1,m_x2,m_y2,m_c_h=get_right_characters(paper['characters'],"地代家賃",0.8)
                    addx1x2=True
                    xys=self.xym[page]
                    for c in xys:
                        y=(c[3]+c[1])/2
                        c_h=c[3]-c[1]
                        an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(self.xyl[1000],0,y,c[0],c[2],0-(c[3]-c[1])/2,c_h*2,False,False,True,self.kojin_tri[page])
                        if an is None :
                            t1.append([None,c[0],c[1],c[2],c[3],page])
                        else :
                            t1.append([an,c[0],c[1],c[2],c[3],page])
                        if m_x1 is None :
                            m_x2=c[0]-(2214-2100)+100
                            m_x1=c[0]-(2214-1450)
                            addx1x2=False
                        elif addx1x2 :
                            m_x1=m_x1-35
                            m_x2=m_x2+40+100
                            addx1x2=False
                        if h_sample_m[i] is not None and m_x1 is not None and m_x2 is not None :
                            an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],m_x1,y,0,m_x2,(c[1]-c[3])/2)
                            m1.append([an,first_x1,first_y1,last_x2,last_y2])
                        else :
                            m1.append([None,None,None,None,None])
                  if self.xyr.get(page) is not None and len(self.xyr[page])>1 :
                    r_text,r_x1,r_y1,r_x2,r_y2,r_c_h=get_right_characters(paper['characters'],"貸倒引当金",0.8)
                    if r_text is None :
                        r_text,r_x1,r_y1,r_x2,r_y2,r_c_h=get_right_characters(paper['characters'],"専従者給与",0.8)
                    addx1x2=True
                    xys=self.xyr[page]
                    for c in xys:
                        y=(c[3]+c[1])/2
                        c_h=c[3]-c[1]
                        an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(self.xyl[1000],0,y,c[0],c[2],0-(c[3]-c[1])/2,c_h*2,False,False,True,self.kojin_tri[page])
                        if an is None :
                            t1.append([None,c[0],c[1],c[2],c[3],page])
                        else :
                            t1.append([an,c[0],c[1],c[2],c[3],page])
                        if r_x1 is None :
                            r_x2=c[0]-(2214-2100)
                            r_x1=c[0]-(2214-1450)
                            addx1x2=False
                        elif addx1x2 :
                            r_x1=r_x1-35
                            r_x2=r_x2+40
                            addx1x2=False
                        if h_sample_mr[i] is not None and r_x1 is not None and r_x2 is not None :
                            an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],r_x1,y,0,r_x2,(c[1]-c[3])/2)
                            m1.append([an,first_x1,first_y1,last_x2,last_y2])
                        else :
                            m1.append([None,None,None,None,None])
              for c in t1:
                print(c)
              print('item:::::::::::::::::::::::::::::::::::')
              for c in m1:
                print(c)
            
            if isTaisyakuTaisyou :
              print("###############"+page_str+"は貸借対照表##################")
              #貸借対照表の中身
              ###########################################################################################################
              text,x1,y1,x2,y2,c_h=get_right_characters(paper['characters'],"支払手形",0.7) 
              if text is None :
                text,x1,y1,x2,y2,c_h=get_right_characters(paper['characters'],"原材料仕入高",0.7) 
              text,x1,y1x,x2,y2x,c_h2=get_right_characters(paper['characters'],"当座預金",0.7) 
              if x1 is None :
                  text,x1,y1x,x2,y2x,c_h2=get_right_characters(paper['characters'],"受取手形",0.7) 
              if x1 is None :
                  text,x1,y1x,x2,y2x,c_h2=get_right_characters(paper['characters'],"有価証券",0.7) 
              if x1 is None :
                  text,x1,y1x,x2,y2x,c_h2=get_right_characters(paper['characters'],"建物附属設備",0.7) 
              if x1 is None :
                  text,x1,y1x,x2,y2x,c_h2=get_right_characters(paper['characters'],"機械装置",0.7) 
              A0text,A0x1,A0y1,A0x2,A0y2,A0c_h=get_right_characters(paper['characters'],"製品製造原価",0.8) 
              A1text,A1x1,A1y1,A1x2,A1y2,A1c_h=get_right_characters(paper['characters'],"事業主貸",0.8) 
              A2text,A2x1,A2y1,A2x2,A2y2,A2c_h=get_right_characters(paper['characters'],"期首半製品",0.8) 
              A3text,A3x1,A3y1,A3x2,A3y2,A3c_h=get_right_characters(paper['characters'],"期末半製品",0.8) 
              atext,ax1,ay1,ax2,ay2,ac_h=get_right_characters(paper['characters'],"支払手形",0.7) 
              btext,bx1,by1,bx2,by2,bc_h=get_right_characters(paper['characters'],"買掛金",0.7) 
              ctext,cx1,cy1,cx2,cy2,cc_h=get_right_characters(paper['characters'],"借入金",0.7) 
              print ("4687>>>>>>>>>>>>>"+str(x1)+"_"+str(y1)+"__"+str(x2)+"__"+str(y2)+"__"+str(text))
              for c in paper['characters']:
                print(c['text'])
              if c_h is not None :
                textmaxx=c_h*2
              if c_h2 is not None :
                textmaxx=c_h2*2
              if c_h is None :
                  c_h = c_h2
              if btext is not None and ctext is not None :
                  y1=by1-cy1+by1
                  y2=by2-cy2+by2
              basey2=0

              h_sample_o= [620 ,720 ,820 ,924 ,1024,1124,1224,1324,1426,1525,1626,1725,1825,1924,2030,2130,2230,2330,2430,2530,2630,2730,2830,2940,3036]
              h_sample=   [620 ,720 ,820 ,924 ,1024,1124,1224,1324,1426,1525,1626,1725,1825,1924,2030,2130,2230,2330,2430,2530,2630,2730,2830,2940,3036]
              h_sample_m1= [None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,2230,2330,2430,2530,2630,2730,2830,None,None]
              h_sample_m2=[None,None,None,None,None,None,1224,1324,1426,1525,1626,1725,1825,None,2030,2130,2230,2330,2430,2530,2630,None,None,None,None]
              h_sample_m3=[None,None,None,None,None,None,None,None,None,None,1626,1725,1825,1924,2030,2130,2230,2330,None,None,None,None,None,None,None]
            
              if self.xybs.get(page) is not None and len(self.xybs[page])>49:
                xys=self.xybs[page]
                for num in reversed(range(len(xys))):
                    if xys[num][3]-xys[num][1] <3 :
                        del xys[num]
                
                if len(xys)>50 :
                    if len(xys)==52 :
                        del xys[1]
                        del xys[0]
                    if len(xys)==54 :
                        del xys[3]
                        del xys[2]
                        del xys[1]
                        del xys[0]
                t2_1=[]
                m2=[]
                i=0
                xys_2=[]
                for c in xys:
                    if i%2 ==0 :
                        xys_2.append(c)
                    i=i+1
                i=0
                for c in xys:
                    if i%2 ==1 :
                        xys_2.append(c)
                    i=i+1
                i=0
                xys=xys_2
                for c in xys:
                    if i<len(h_sample) :
                        y=(c[3]+c[1])/2
                        c_h=c[3]-c[1]
                        an_2,first_x1_2,first_y1_2,last_x2_2,last_y2_2=get_right_number_endx(paper['characters'],0,y,c[0],c[2],0-(c[3]-c[1])/2,c_h,False,True,False,self.kojin_tri[page])
                        if an_2 is None and i==0 :
                            t2_1.append([None,c[0],c[1],c[2],c[3],page])
                        else :
                            t2_1.append([an_2,first_x1_2,first_y1_2,last_x2_2,last_y2_2,page])
                        x1=c[0]-(c[2]-c[0])*2
                        x2=c[2]-(c[2]-c[0])*2
                        if h_sample_m1[i] is not None and x1 is not None and x2 is not None :
                            an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],x1,y,0,x2,(c[1]-c[3]))
                            m2.append([an,first_x1,first_y1,last_x2,last_y2])
                        else :
                            m2.append([None,None,None,None,None])
                    if i>=len(h_sample) :
                        y=(c[3]+c[1])/2
                        c_h=c[3]-c[1]
                        an_2,first_x1_2,first_y1_2,last_x2_2,last_y2_2=get_right_number_endx(paper['characters'],0,y,c[0]-50,c[2],0-(c[3]-c[1])/2,c_h,False,True,False,self.kojin_tri[page])
                        if an_2 is None :
                            t2_1.append([None,c[0],c[1],c[2],c[3],page])
                        else :
                            t2_1.append([an_2,first_x1_2,first_y1_2,last_x2_2,last_y2_2,page])
                        x1=c[0]-(c[2]-c[0])*2
                        x2=c[2]-(c[2]-c[0])*2
                        if h_sample_m2[i-25] is not None and x1 is not None and x2 is not None :
                            an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],x1,y,0,x2,(c[1]-c[3]))
                            m2.append([an,first_x1,first_y1,last_x2,last_y2])
                        else :
                            m2.append([None,None,None,None,None])
                    i=i+1
                # --- 常に0で初期化してから数える ---
                countt2_1 = sum(1 for r in t2_1 if r and r[0] is not None)
                countt2_1_old = sum(1 for r in t2_1_old if r and r[0] is not None)
                debug_print('############### 5858 : {} : {}'.format(countt2_1, countt2_1_old), level=DEBUG_ROWS_INFO)
                def format_row(i, row):
                    if isinstance(row, (list, tuple)):
                        elems = ", ".join(repr(c) for c in row)
                        return f"[{i:03d}] {elems}"
                    else:
                        return f"[{i:03d}] {repr(row)}"

                def dump_rows(rows):
                    try:
                        lines = [format_row(i, row) for i, row in enumerate(rows)]
                        return "\n".join(lines)
                    except Exception as e:
                        return f"(error while printing {type(rows).__name__}: {e!r})"

                alias_same_obj = (t2_1 is t2_1_old)

                debug_print(
                    "t2_1 summary: len={}, non_none_first={}, id={}, alias_with_t2_1_old={}\n{}".format(
                        len(t2_1), countt2_1, id(t2_1), alias_same_obj, dump_rows(t2_1)
                    ),
                    level=DEBUG_ROWS_INFO
                )

                debug_print(
                    "t2_1_old summary: len={}, non_none_first={}, id={}\n{}".format(
                        len(t2_1_old), countt2_1_old, id(t2_1_old), dump_rows(t2_1_old)
                    ),
                    level=DEBUG_ROWS_INFO
                )

                def shallow_copy_rows(rows):
                    # 行が list/tuple ならスライスで浅いコピー、その他はそのまま
                    return [(row[:] if isinstance(row, (list, tuple)) else row) for row in rows]

                def has_valid_anchor(rows, idx):
                    """rows[idx][0] が安全に評価できるかを確認"""
                    try:
                        row = rows[idx]
                        return isinstance(row, (list, tuple)) and len(row) >= 1 and row[0] is not None
                    except Exception:
                        return False

                use_new = (
                    countt2_1 > countt2_1_old
                    and len(t2_1) >= 50           # 0..49 を参照するため
                    and has_valid_anchor(t2_1, 24)
                    and has_valid_anchor(t2_1, 49)
                )

                if use_new:
                    t2_1_old = shallow_copy_rows(t2_1)   # 新の方が良い → 旧を更新
                    m2_old = shallow_copy_rows(m2)
                    debug_print('############### use new : {} : {}'.format(countt2_1, countt2_1_old), level=DEBUG_ROWS_INFO)
                else:
                    t2_1 = shallow_copy_rows(t2_1_old)   # 旧の方が良い or 同点 → 新を旧で上書き
                    m2 = shallow_copy_rows(m2_old)
                    debug_print('############### use old : {} : {}'.format(countt2_1, countt2_1_old), level=DEBUG_ROWS_INFO)

              elif x1 is not None and y1 is not None and c_h is not None and  (ax1 is not None or bx1 is not None) and ( A0x1 is not None or A1x1 is not None and  A2x1 is not None or A3x1 is not None ):
                  #現金の数字を検索するｙ座標
                  y2=y2-round(c_h/2)
                  basey2=y2
                  print ("4692>>>>>>>>>>>>>"+str(basey2))
                  #数値を検索する距離
                  line=2*c_h+x2
                  mx0=None
                  mx1=None
                  if ax1 is not None :
                      mx0=round((ax1-2*c_h-line)/2)+line
                      #mx1=ax1
                      mx1=ax1
                  elif bx1 is not None :
                      mx0=round((bx1-2*c_h-line)/2)+line
                      #mx1=bx1-c_h2*2
                      mx1=bx1
                  else :
                      mx0=line+x2-x1
                      mx1=line+(x2-x1)*2
                  if bx2 is not None or ax2 is not None:
                      
                      #工具器具備品がある場合
                      if A0x1 is not None :
                        #現在比較項目のY座標
                        ny=A0y2-round(A0c_h/2)
                        #原始表の長さ
                        oh=h_sample_o[24]-h_sample_o[0]
                        #現在表の長さ
                        nh=ny-y2
                      #企業主貸がある場合
                      elif A1x1 is not None :
                        #現在比較項目のY座標
                        ny=A1y2-round(A1c_h/2)
                        #原始表の長さ
                        oh=h_sample_o[23]-h_sample_o[0]
                        #現在表の長さ
                        nh=ny-y2
                      elif A2x1 is not None :
                        #現在比較項目のY座標
                        ny=A2y2-round(A2c_h/2)
                        #原始表の長さ
                        oh=h_sample_o[21]-h_sample_o[0]
                        #現在表の長さ
                        nh=ny-y2
                      elif A3x1 is not None :
                        #現在比較項目のY座標
                        ny=A3y2-round(A3c_h/2)
                        #原始表の長さ
                        oh=h_sample_o[23]-h_sample_o[0]
                        #現在表の長さ
                        nh=ny-y2

                      #比率
                      hiritu=1
                      if nh is not None :
                        hiritu=nh/oh

                      i=0
                      for c in h_sample_o:
                        if i==0 :
                          h_sample[i]=y2
                        else :
                          h_sample[i]=y2+round((h_sample_o[i]-h_sample_o[0])*hiritu)
                          print("4749>>>>>>"+str(h_sample[i])+"__"+str(h_sample_o[i]-h_sample_o[0])+"__"+str(hiritu))
                        i+=1
                      
                      
                      i=0
                      last_i=0
                      last_i_2=0
                      for c in h_sample:
                          if i<(len(h_sample)) :
                              if i>0 :
                                if t2_0[last_i][0] is None :
                                  h=h_sample[0]
                                else :
                                  h=t2_0[last_i][4]-round(t2_0[last_i][2])
                                  h=t2_0[last_i][2]+round(h/2)
                                if last_i>4 :
                                    y2=round(h*h_sample[i]/h_sample[last_i])
                                else :
                                    y2=h_sample[i]
                                    
                              an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper['characters'],0,y2,line,mx0,round(c_h/2),textmaxx,True,False,False,self.kojin_tri[page])
                              if an is None and i==0 :
                                  t2_0.append([None,None,y1,None,y2,page])
                                  last_i=i
                              else :
                                  t2_0.append([an,first_x1,first_y1,last_x2,last_y2,page])
                              if an is not None :
                                  last_i=i

                              an_2,first_x1_2,first_y1_2,last_x2_2,last_y2_2=get_right_number_endx(paper['characters'],0,y2,mx0,mx1,round(c_h/2),textmaxx,True,True,False,self.kojin_tri[page])
                              if i==0 and an_2 is not None and len(an_2)>1:
                                  if an_2[-2:] =="19" or an_2[-2:] =="14" :
                                      an_2=an_2[0:len(an_2)-2]
                              if an_2 is None and i==0 :
                                  t2_1.append([None,mx0,y1,mx1,y2,page])
                                  last_i_2=i
                              else :
                                  t2_1.append([an_2,first_x1_2,first_y1_2,last_x2_2,last_y2_2,page])
                              if an_2 is not None :
                                  last_i_2=i

                              if h_sample_m1[i] is not None :
                                  print("4774>>>>>>>>>>>>>>")
                                  print(str(y2))
                                  an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],x1-2*c_h,y2,0,x2+2*c_h,round(c_h/2))
                                  m2.append([an,first_x1,first_y1,last_x2,last_y2])
                              else :
                                  m2.append([None,None,None,None,None])
                          i+=1
                      #第2列の検索#############################################################################################
                      mx0=None
                      mx1=None
                      basew=x2-x1
                      if ax1 is not None :
                        #数値を検索する距離
                        line=2*c_h+ax2
                        x1=ax1
                        x2=ax2
                      elif bx2 is not None :
                          line=2*c_h+bx2
                          x1=bx1
                          x2=bx2
                      else :
                          line=line+basew*3
                          x1=line+basew*2
                          x2=line+basew*3

                      atext,ax1,ay1,ax2,ay2,ac_h=get_right_characters(paper['characters'],"期首原材料棚卸高",0.8) 
                      btext,bx1,by1,bx2,by2,bc_h=get_right_characters(paper['characters'],"原材料仕入高",0.7) 
                      ctext,cx1,cy1,cx2,cy2,cc_h=get_right_characters(paper['characters'],"期末原材料棚卸高",0.8)
                      dtext,dx1,dy1,dx2,dy2,dc_h=get_right_characters(paper['characters'],"水道光熱費",0.8)
                      y2=basey2
                      mx0=None
                      mx1=None
                      if ax1 is not None :
                          mx0=round((ax1-3*c_h-line)/2)+line
                          mx1=ax1
                      elif bx1 is not None :
                          mx0=round((bx1-3*c_h-line)/2)+line
                          mx1=bx1
                      elif cx1 is not None :
                          mx0=round((cx1-3*c_h-line)/2)+line
                          mx1=cx1
                      elif dx1 is not None :
                          mx0=round((dx1-3*c_h-line)/2)+line
                          mx1=dx1
                      else :
                          mx0=line+basew*3/2
                          mx1=line+basew*3
                      i=0
                      last_i=0
                      last_i_2=0
                      for c in h_sample:
                          if i<(len(h_sample)) :
                              if i>0 :
                                if t2_0[last_i+25][0] is None :
                                  h=h_sample[0]
                                else :
                                  h=t2_0[last_i+25][4]-round(t2_0[last_i+25][2])
                                  h=t2_0[last_i+25][2]+round(h/2)
                                if last_i>4 :
                                    y2=round(h*h_sample[i]/h_sample[last_i])
                                else :
                                    y2=h_sample[i]
                              print("4823>>>>>>")
                              print(str(y2))
                              an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper['characters'],0,y2,line,mx0,round(c_h/2),textmaxx,True,True,False,self.kojin_tri[page])
                              if an is None and i==0 :
                                  t2_0.append([None,None,y1,None,y2,page])
                                  last_i=i
                              else :
                                  t2_0.append([an,first_x1,first_y1,last_x2,last_y2,page])
                              if an is not None :
                                  last_i=i

                              an_2,first_x1_2,first_y1_2,last_x2_2,last_y2_2=get_right_number_endx(paper['characters'],0,y2,mx0,mx1,round(c_h/2),textmaxx,True,True,False,self.kojin_tri[page])
                              if i==0 and an_2 is not None and len(an_2)>1:
                                  if an_2[-2:] =="19" or an_2[-2:] =="14" :
                                      an_2=an_2[0:len(an_2)-2]
                              if an_2 is None and i==0 :
                                  t2_1.append([None,mx0,y1,mx1,y2,page])
                                  last_i_2=i
                              else :
                                  t2_1.append([an_2,first_x1_2,first_y1_2,last_x2_2,last_y2_2,page])
                              if an_2 is not None :
                                  last_i_2=i

                              if h_sample_m2[i] is not None :
                                  an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],x1-2*c_h,y2,0,x2+2*c_h,round(c_h/2))
                                  m2.append([an,first_x1,first_y1,last_x2,last_y2])
                              else :
                                  m2.append([None,None,None,None,None])
                          i+=1
                      #第3列の検索#############################################################################################
                      #ctext,cx1,cy1,cx2,cy2,cc_h=get_right_characters(paper['characters'],"期末原材料棚卸高",0.8) 
                      #mx0=None
                      #basew=None
                      #if ax1 is not None :
                      #  #数値を検索する距離
                      #  line=4*c_h+ax2
                      #  basew=ax2-ax1
                      #  x1=ax1
                      #  x2=ax2
                      #  mx0=line+basew*2
                      #elif bx2 is not None :
                      #    line=4*c_h+bx2
                      #    basew=bx2-bx1
                      #    x1=bx1
                      #    x2=bx2
                      #    mx0=line+basew*2
                      #else :
                      #    line=4*c_h+cx2
                      #    basew=cx2-cx1
                      #    x1=cx1
                      #    x2=cx2
                      #    mx0=line+basew*2
                      ##y2=basey2
                      #y2=ay2-round(ac_h/2)
                      #print("4885>>>>>>>>>>>>>"+"_"+str(ay2)+"_"+str(ac_h))
                      #h_sample.insert(0, y2)
                      #h_sample_m2.insert(0, None)
                                #
                      #i=0
                      #last_i=0
                      #last_i_2=0
                      #for c in h_sample:
                      #    if i<(len(h_sample)) :
                      #        if i>0 :
                      #          if t2_0[last_i+50][0] is None :
                      #            h=h_sample[0]
                      #          else :
                      #            h=t2_0[last_i+50][4]-round(t2_0[last_i+50][2])
                      #            h=t2_0[last_i+50][2]+round(h/2)
                      #          y2=round(h*h_sample[i]/h_sample[last_i])
                      #          print("4903>>>>>>>>>>>>>"+"_"+str(y2))
                      #        an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper['characters'],0,y2,line,mx0,round(c_h/2),textmaxx,True,False,False,self.kojin_tri[page])
                      #        if an is None and i==0 :
                      #            t2_0.append([None,None,y1,None,y2])
                      #            last_i=i
                      #        else :
                      #            t2_0.append([an,first_x1,first_y1,last_x2,last_y2])
                      #        if an is not None :
                      #            last_i=i
                                #
                      #        if h_sample_m2[i] is not None :
                      #            an,first_x1,first_y1,last_x2,last_y2=get_right_text_endx(paper['characters'],x1-2*c_h,y2,0,x2+2*c_h,round(c_h/2))
                      #            m2.append([an,first_x1,first_y1,last_x2,last_y2])
                      #        else :
                      #            m2.append([None,None,None,None,None])
                      #    i+=1
                  else :
                      #予想していない動作
                      print ("予想していない動作4608")
                      print("文字識別できない場合の処理は開発中")
                      print('失敗5121:::::::::::::::::::::::::::::::::::'+ str(page))
                  print('貸借対照表:::::::::::::::::::::::::::::::::::')
                  for c in t2_0:
                    print(c)
                  for c in t2_1:
                    print(c)
                  print('item:::::::::::::::::::::::::::::::::::')
                  for c in m2:
                    print(c)
              else :
                print("文字識別できない場合の処理は開発中")
                print('失敗4609:::::::::::::::::::::::::::::::::::'+ str(page))
                taisyakuTaisyouPage=9999
            if isZatusyunyu :
              if len(t3) == 0 or t3[0][0] == None :
                t3=[]
                print("###############"+page_str+"は雑収入##################")
                debug_print("###############6027=======",level=DEBUG_ROWS_INFO)
                #貸借対照表の中身
                text,x1,y1,x2,y2,c_h=get_right_characters(paper['characters'],"雑収入",0.6) 
                debug_print(text,level=DEBUG_ROWS_INFO)
                if text is None :
                    t3.append([None,None,y1,None,y2,page])
                else :
                    an,first_x1,first_y1,last_x2,last_y2=get_right_number_endx(paper['characters'],x2,y2-round((y2-y1)/2),c_h,x2+40*c_h,round(c_h/2),c_h*2,True,True,False,self.kojin_tri[page])
                    if an is None :
                        t3.append([None,None,y1,None,y2,page])
                    else :
                        t3.append([an,first_x1,first_y1,last_x2,last_y2,page])
        max_page = len(self.papers)   # max_page = page+1当期商品仕入高
        if max_page == 0:
            max_page = 1
        print(">>>>>>>>>>>>>>>>>>>>>4518>>>>>>>>>>>>>>")

        for text in all_texts:
          print(text['text'])

        max_page = len(self.papers)   # max_page = page+1
        if max_page == 0:
            max_page = 1

        keyword_group = [[]] * (max_page)
        ##########################################################################################
        #結果オブジェクトを生成する###############################################################
        ##########################################################################################
        ret_cols = []   #　空の抽出項目リスト
        i=0
        cl1=[]
        cl1.append(["売上（収入）金額",1,1,0,0,0,1])
        cl1.append(["期首棚卸高",1,2,1,0,4,-1])
        cl1.append(["仕入金額",1,2,2,0,0,-1])
        cl1.append(["小計",1,2,0,0,-3,1])
        cl1.append(["期末棚卸高",1,2,3,0,6,1])
        cl1.append(["差引原価",1,2,0,0,-9,1])
        cl1.append(["差引金額",1,3,0,0,-4,1])
        cl1.append(["租税公課",1,4,2,2,1,-1])
        cl1.append(["荷造運賃",1,4,2,13,4,-1])
        cl1.append(["水道光熱費",1,4,2,3,1,-1])
        cl1.append(["旅費交通費",1,4,2,4,3,-1])
        cl1.append(["通信費",1,4,2,5,1,-1])
        cl1.append(["広告宣伝費",1,4,2,15,1,-1])
        cl1.append(["接待交際費",1,4,2,6,1,-1])
        cl1.append(["損害保険料",1,4,2,7,3,-1])
        cl1.append(["修繕費",1,4,2,8,1,-1])
        cl1.append(["消耗品費",1,4,2,9,1,-1])
        cl1.append(["減価償却費",1,4,2,1,1,-1])
        cl1.append(["福利厚生費",1,4,1,8,1,-1])
        cl1.append(["給料賃金",1,4,1,0,1,-1])
        cl1.append(["外注工賃",1,4,2,14,3,-1])
        cl1.append(["利子割引料",1,7,0,2,9,-1])
        cl1.append(["地代家賃",1,4,2,11,1,-1])
        cl1.append(["貸倒金",1,4,2,38,2,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["雑費",1,4,2,45,1,-1])
        cl1.append(["経費の計",1,20,0,0,1,-1])
        cl1.append(["経費の差引金額",1,5,0,0,-6,-1])
        cl1.append(["貸倒引当金戻入",1,6,0,3,1,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["計",1,6,0,0,-4,-1])
        cl1.append(["専従者給与",1,4,1,0,2,-1])
        cl1.append(["貸倒引当金繰入",1,4,2,36,1,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["",2,999,0,0,0,-1])
        cl1.append(["計",1,7,0,0,-4,-1])
        cl1.append(["青色申告特別控除前の所得金額",1,11,0,0,1,-1])
        cl1.append(["青色申告特別控除額",1,20,0,0,2,-1])
        cl1.append(["所得金額",1,11,0,0,-7,-1])
        if t1 is None or len(t1)==0 :
            t1=[] 
            m1=[]
            for num in range(len(cl1)): 
                t1.append([None,None,None,None,None,0])
                m1.append([None,None,None,None,None,0])
        for cl1_s in cl1 :
            if i<len(t1) :
                ts1=t1[i]
            else :
                ts1=[None,None,None,None,None]
            r = {}
            r['col_id']         = "n"+str(i)
            r['col_name']       = "n"+str(i)
            r['itask_form_id']  = 99999
            candidate=[]
            #if (i<16 or m1[i-16][0] is None) and ts1[0] is not None :
            if (i<16 or m1[i-16][0] is None) :
              if cl1[i] is not None :
                candidate_sub={}
                candidate_sub["order"]=cl1[i][1]
                candidate_sub["family"]=cl1[i][2]
                candidate_sub["genus"]=cl1[i][3]
                candidate_sub["species"]=cl1[i][4]
                candidate_sub["variety"]=cl1[i][5]
                candidate_sub["property"]=cl1[i][6]
                candidate_sub["variety_name"]=cl1[i][0]
                candidate.append(candidate_sub)
                if cl1[i][2]==999 :
                    r["kotei"]="m1_"+str(i)
                else :
                    r["kotei"]="kotei_1_"+str(i)
              else :
                candidate_sub={}
                candidate_sub["order"]=1
                candidate_sub["family"]=9
                candidate_sub["genus"]=9
                candidate_sub["species"]=9
                candidate_sub["variety"]=999
                candidate_sub["property"]=-1
                candidate_sub["variety_name"]="予期せぬ項目"
                candidate.append(candidate_sub)
                r["kotei"]="m1_"+str(i)
            elif i>=16 and m1[i-16][0] is not None:
            #elif i>=16 and m1[i-16][0] is not None and ts1[0] is not None :
              #print("4999>>>>>>>>>>>>>>>>>>>>>>>>>")
              #print(m1[i-16])
              debug_print( '##############################6140 m is '+m1[i-16][0]+'#############################',level=DEBUG_ROWS_INFO)
              close=self.account_db.search_variety_title_syou(m1[i-16][0])
              for xi, xc in enumerate(close):
                if "車両費"==xc or "車輛費"==xc or "車輌費"==xc :
                    close[0], close[xi] = close[xi], close[0]
              r["kotei"]="m1_"+str(i)
              candidate=[]
              for c in close :
                code = self.account_db.search_variety_code(c,code=(1,4),between=(1,35))
                #print("5008>>>>>>>>>>>>>>>>>>>>>>>>>")
                #print(code)
                candidate_sub={}
                if code is not None and len(code)>0 and code[0] is not None :
                  if code[0]==2 and code[1]==40 and code[2]==2 and code[3]==0 and code[4]==29 :
                    candidate_sub["order"]=2
                    candidate_sub["family"]=50
                    candidate_sub["genus"]=0
                    candidate_sub["species"]=5
                    candidate_sub["variety"]=1
                    candidate_sub["property"]=1
                    candidate_sub["variety_name"]="長期借入金"
                  else :
                    # safety: ensure code has >=6 elements before unpacking
                    if not _code_len_ok(code, 6):
                        continue
                    candidate_sub["order"]=code[0]
                    candidate_sub["family"]=code[1]
                    candidate_sub["genus"]=code[2]
                    candidate_sub["species"]=code[3]
                    candidate_sub["variety"]=code[4]
                    candidate_sub["property"]=code[5]
                    candidate_sub["variety_name"]=c
                  if i>16 and i<33 :
                      if _code_len_ok(code, 2) and code[0] == 1 and (code[1] in (2, 4, 7, 10)) :
                        if c=="支払手数料" :
                            candidate_sub["order"]=1
                            candidate_sub["family"]=4
                            candidate_sub["genus"]=2
                            candidate_sub["species"]=18
                            candidate_sub["variety"]=1
                            candidate_sub["property"]=-1
                            candidate_sub["variety_name"]=c
                            candidate.append(candidate_sub)
                        elif _code_len_ok(code, 2) and code[1] == 4:
                            candidate.append(candidate_sub)
                  elif i>33 and i<48 :
                      if _code_len_ok(code, 2) and code[0] == 1 and (code[1]==4 or code[1]==7 or code[1]==10) :
                          candidate.append(candidate_sub)
            if len(candidate)==0 :
              if len(cl1)>i and cl1[i] is not None :
                candidate=[]
                candidate_sub={}
                candidate_sub["order"]=cl1[i][1]
                candidate_sub["family"]=cl1[i][2]
                candidate_sub["genus"]=cl1[i][3]
                candidate_sub["species"]=cl1[i][4]
                candidate_sub["variety"]=cl1[i][5]
                candidate_sub["property"]=cl1[i][6]
                candidate_sub["variety_name"]=cl1[i][0]
                candidate.append(candidate_sub)
                if cl1[i][2]==999 :
                    r["kotei"]="m1_"+str(i)
                else :
                    r["kotei"]="kotei_1_"+str(i)
              else :
                candidate_sub={}
                candidate_sub["order"]=1
                candidate_sub["family"]=9
                candidate_sub["genus"]=9
                candidate_sub["species"]=9
                candidate_sub["variety"]=999
                candidate_sub["property"]=-1
                candidate_sub["variety_name"]="予期せぬ項目"
                candidate.append(candidate_sub)
            r["candidate"]=candidate
            r["amount_pre_year"]=""
            if ts1[0] is None :
                r["amount_this_year"]=""
            else :
                r["amount_this_year"]=ts1[0]
            r["db_exist"]="1.00"
            r["start_x"]=ts1[1]
            r["start_y"]=ts1[2]
            if m1[i-16][0] is not None :
                r["realtext"]=m1[i-16][0]
            r["end_x"]=ts1[3]
            r["end_y"]=ts1[4]
            r["tabindex"]=2
            r["page"]=ts1[5]
            if ts1[1] is None :
                r["start_x"]=0
            if ts1[2] is None :
                r["start_y"]=0
            if ts1[3] is None :
                r["end_x"]=0
            if ts1[4] is None :
                r["end_y"]=0
            r["start_x"]=int(r["start_x"])
            r["start_y"]=int(r["start_y"])
            r["end_x"]=int(r["end_x"])
            r["end_y"]=int(r["end_y"])
            ret_cols.append(r)
            i+=1

        cl2=[]
        cl2.append(["現金",2,10,1,1,6,1])
        cl2.append(["当座預金",2,10,1,1,13,1])
        cl2.append(["定期預金",2,10,1,1,15,1])
        cl2.append(["その他の預金",2,10,1,1,42,1])
        cl2.append(["受取手形",2,10,2,3,1,1])
        cl2.append(["売掛金",2,10,2,0,7,1])
        cl2.append(["有価証券",2,10,1,3,1,1])
        cl2.append(["棚卸資産",2,10,3,1,2,1])
        cl2.append(["前払い金",2,10,4,0,5,1])
        cl2.append(["貸付金",2,10,4,9,2,1])
        cl2.append(["建物",2,20,1,6,2,1])
        cl2.append(["建物付属設備",2,20,1,6,3,1])
        cl2.append(["機械装置",2,20,1,4,2,1])
        cl2.append(["車輌運搬具",2,20,1,9,2,1])
        cl2.append(["工具器具備品",2,20,1,8,2,1])
        cl2.append(["土地",2,20,1,12,1,1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append(["事業主貸 ",2,10,4,0,7,1])
        cl2.append(["資産の部合計",2,35,0,0,0,1])
        cl2.append(["支払手形",2,40,1,1,1,1])
        cl2.append(["買掛金",2,40,1,0,1,1])
        cl2.append(["借入金",2,40,2,0,2,1])
        cl2.append(["未払金",2,40,3,15,1,1])
        cl2.append(["前受金",2,40,3,8,1,1])
        cl2.append(["預り金",2,40,3,20,1,1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append(["貸倒引当金",2,10,2,0,3,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append([None,2,999,0,0,0,-1])
        cl2.append(["事業主借",2,40,3,1,5,1])
        cl2.append(["元入金",2,40,3,1,6,1])
        cl2.append(["青色申告特別控除前の所得金額",2,70,3,2,9,1])
        cl2.append(["合計",2,120,0,0,-8,1])
        if t2_1 is None or len(t2_1)==0 :
            t2_1=[]
            m2=[]
            for num in range(len(cl2)): 
                t2_1.append([None,None,None,None,None,0])
                m2.append([None,None,None,None,None,0])
        i=0
        for cl2_s in cl2 :
            if i<len(t2_1) :
                ts2_1=t2_1[i]
            else :
                ts2_1=[None,None,None,None,None]
            r = {}
            r['col_id']         = "n"+str(i)
            r['col_name']       = "n"+str(i)
            r['itask_form_id']  = 99999
            candidate=[]
            if m2[i][0] is None :
            #if m2[i][0] is None and ts2_1[0] is not None :
              if cl2[i] is not None :
                candidate_sub={}
                candidate_sub["order"]=cl2[i][1]
                candidate_sub["family"]=cl2[i][2]
                candidate_sub["genus"]=cl2[i][3]
                candidate_sub["species"]=cl2[i][4]
                candidate_sub["variety"]=cl2[i][5]
                candidate_sub["property"]=cl2[i][6]
                candidate_sub["variety_name"]=cl2[i][0]
                candidate.append(candidate_sub)
                if cl2[i][2]==999 :
                    r["kotei"]="m2_"+str(i)
                else :
                    r["kotei"]="kotei_2_"+str(i)
              else :
                candidate_sub={}
                candidate_sub["order"]=1
                candidate_sub["family"]=9
                candidate_sub["genus"]=9
                candidate_sub["species"]=9
                candidate_sub["variety"]=999
                candidate_sub["property"]=-1
                candidate_sub["variety_name"]="予期せぬ項目"
                candidate.append(candidate_sub)
                r["kotei"]="m2_"+str(i)
            #elif m2[i][0] is not None and ts2_1[0] is not None :
            elif m2[i][0] is not None :
              #print("4999>>>>>>>>>>>>>>>>>>>>>>>>>")
              #print(m2[i-16])
              r["kotei"]="m2_"+str(i)
              close=self.account_db.search_variety_title_syou(m2[i][0])
              for xi, xc in enumerate(close):
                if "車両費"==xc or "車輛費"==xc or "車輌費"==xc :
                    close[0], close[xi] = close[xi], close[0]
              candidate=[]
              for c in close :
                code = self.account_db.search_variety_code(c,code=(2,))
                candidate_sub={}
                if code is not None and len(code)>0 and code[0] is not None :
                  if code[0]==2 and code[1]==40 and code[2]==2 and code[3]==0 and code[4]==29 :
                    candidate_sub["order"]=2
                    candidate_sub["family"]=50
                    candidate_sub["genus"]=0
                    candidate_sub["species"]=5
                    candidate_sub["variety"]=1
                    candidate_sub["property"]=1
                    candidate_sub["variety_name"]="長期借入金"
                  else :
                    # safety: ensure code has >=6 elements before unpacking
                    if not _code_len_ok(code, 6):
                        continue
                    candidate_sub["order"]=code[0]
                    candidate_sub["family"]=code[1]
                    candidate_sub["genus"]=code[2]
                    candidate_sub["species"]=code[3]
                    candidate_sub["variety"]=code[4]
                    candidate_sub["property"]=code[5]
                    candidate_sub["variety_name"]=c
                  if i<25 :
                      if _code_len_ok(code, 2) and code[0] == 2 and (code[1] in (10, 20, 30)):
                          candidate.append(candidate_sub)
                  elif i>25 :
                      if code[0]==2 and (code[1]>=40) or cl2[i][0]=="貸倒引当金":
                          candidate.append(candidate_sub)
            if len(candidate)==0 :
              if len(cl2)>i and cl2[i] is not None :
                candidate=[]
                candidate_sub={}
                candidate_sub["order"]=cl2[i][1]
                candidate_sub["family"]=cl2[i][2]
                candidate_sub["genus"]=cl2[i][3]
                candidate_sub["species"]=cl2[i][4]
                candidate_sub["variety"]=cl2[i][5]
                candidate_sub["property"]=cl2[i][6]
                candidate_sub["variety_name"]=cl2[i][0]
                candidate.append(candidate_sub)
                if cl2[i][2]==999 :
                    r["kotei"]="m2_"+str(i)
                else :
                    r["kotei"]="kotei_2_"+str(i)
              else :
                candidate_sub={}
                candidate_sub["order"]=1
                candidate_sub["family"]=9
                candidate_sub["genus"]=9
                candidate_sub["species"]=9
                candidate_sub["variety"]=999
                candidate_sub["property"]=-1
                candidate_sub["variety_name"]="予期せぬ項目"
                candidate.append(candidate_sub)
                r["kotei"]="m2_"+str(i)
            r["candidate"]=candidate
            r["amount_pre_year"]=""
            if t2_1[i][0] is None :
                r["amount_this_year"]=""
            else :
                r["amount_this_year"]=t2_1[i][0]
            r["db_exist"]="1.00"
            if m2[i][0] is not None :
                r["realtext"]=m2[i][0]
            if t2_1[i][0] is not None :
              r["start_x"]=ts2_1[1]
              r["start_y"]=ts2_1[2]
              r["end_x"]=t2_1[i][3]
              r["end_y"]=t2_1[i][4]
            else :
              r["end_x"]=0
              r["end_y"]=0
              r["start_x"]=0
              r["start_y"]=0
            r["start_x"]=int(r["start_x"])
            r["start_y"]=int(r["start_y"])
            r["end_x"]=int(r["end_x"])
            r["end_y"]=int(r["end_y"])
            r["tabindex"]=1
            r["page"]=ts2_1[5]
            ret_cols.append(r)
            i+=1


        i=0
        if t3 is None or len(t3)==0 :
            t3=[]
            t3.append([None,None,None,None,None,0])
        for ts3 in t3 :
            r = {}
            r['col_id']         = "n"+str(i)
            r['col_name']       = "n"+str(i)
            r['itask_form_id']  = 99999
            candidate=[]
            candidate_sub={}
            candidate_sub["order"]=1
            candidate_sub["family"]=1
            candidate_sub["genus"]=0
            candidate_sub["species"]=0
            candidate_sub["variety"]=64
            candidate_sub["property"]=1
            candidate_sub["variety_name"]="雑収入"
            candidate.append(candidate_sub)
            r["candidate"]=candidate
            r["amount_pre_year"]=""
            if ts3[0] is None :
                r["amount_this_year"]=""
            else :
                r["amount_this_year"]=ts3[0]
            r["db_exist"]="1.00"
            r["start_x"]=ts3[1]
            r["start_y"]=ts3[2]
            r["end_x"]=ts3[3]
            r["end_y"]=ts3[4]
            if r["start_x"] is None :
                r["start_x"]=0
            if r["start_y"] is None :
                r["start_y"]=0
            if r["end_x"] is None :
                r["end_x"]=0
            if r["end_y"] is None :
                r["end_y"]=0
            if m2[i][0] is not None :
                r["realtext"]="NONE"
            r["start_x"]=int(r["start_x"])
            r["start_y"]=int(r["start_y"])
            r["end_x"]=int(r["end_x"])
            r["end_y"]=int(r["end_y"])
            r["tabindex"]=3
            r["page"]=ts3[5]
            r["kotei"]="kotei_3_"+str(i)
            if ts3[0] is not None :
              ret_cols.append(r)
            else :
              r["amount_this_year"]=""
              ret_cols.append(r)
            i+=1

        block_result={}
        closing_date={}
        closing_date["date"]=""
        closing_date["page"]=1
        closing_date["start_x"]=0
        closing_date["start_y"]=0
        closing_date["end_x"]=0
        closing_date["end_y"]=0
        block_result["closing_date"]=closing_date

        company={}
        company["candidate"]=[]
        company["page"]=1
        company["start_x"]=0
        company["start_y"]=0
        company["end_x"]=0
        company["end_y"]=0
        block_result["company"]=company

        block_result["detail"]=ret_cols
        cols=[]
        cols_sub={}
        cols_sub["col_id"]=""
        cols_sub["col_name"]=""
        cols_sub["itask_form_id"]=""
        cols_sub["block_result"]=block_result
        cols.append(cols_sub)
        if self.special_handling=="special_handling0" or  self.special_handling=="special_handling1":
            self.outData['special_handling']                    = "NONE"
        self.outData['root_str']                    = self.root_str
        self.outData['number_of_images']            = self.number_of_images
        self.outData['open_page_list']              = self.open_page_list
        self.outData['analyze']                     = self.analyze
        self.outData['calibration']                 = self.out_calibration
        self.outData['format_info']                 = {}
        self.outData['format_info']['format_id']    = self.inData['format_info']['format_id']
        self.outData['format_info']['cols']         = cols
        self.outData['document_judgment_flag']      = self.document_judgment_flag


#１-1)stats
def adjust_contrast(input_image, factor):

    # Ensure input is a PIL Image
    if isinstance(input_image, np.ndarray):
        # Convert numpy array to PIL Image
        input_image = Image.fromarray(input_image)

    # Enhance the contrast of the image
    enhancer = ImageEnhance.Contrast(input_image)
    enhanced_image = enhancer.enhance(factor)  # Adjust contrast based on factor

    # Convert PIL Image to numpy array (OpenCV format)
    image = np.array(enhanced_image)

    # Calculate the mean pixel value of the grayscale image
    mean_val = np.mean(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY))

    # Interpolate between the image and the mean value
    adjusted = cv2.addWeighted(image, factor, np.zeros_like(image, dtype=np.uint8), 0, mean_val * (1 - factor))

    # Apply Canny edge detection
    edges = cv2.Canny(adjusted, 200, 250)
    # Invert the colors of the edge-detected image
    inverted_edges = cv2.bitwise_not(edges)
    return inverted_edges

def get_hv_line(img):
  #画像を濃く
  # Increase the contrast by a factor > 1.0 to make it darker
  # contrast_factor = 10  # You can adjust this factor to get the desired contrast
  # darker_image = adjust_contrast(img, contrast_factor)

  # # 画像がグレースケールの場合、RGBに変換
  # if len(darker_image.shape) == 2 or darker_image.shape[2] == 1:
  #   darker_image = cv2.cvtColor(darker_image, cv2.COLOR_GRAY2RGB)
  # gray = cv2.cvtColor(darker_image,cv2.COLOR_BGR2GRAY)
  grayimage = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
  # print('grayA')
  print('before')
  # cv2_imshow(grayimage)
  #途切れをなくす
  # 二値化(二値化して白黒反転、下限値120が')'を読めるかポイント)
  retval, grayimage_inv = cv2.threshold(grayimage, 200, 255, cv2.THRESH_BINARY_INV)
  print('grayimage_inv')
  # cv2_imshow(grayimage_inv)
  # クロージング処理（細切れ状態を防ぐため）
  kernelc = np.ones((3, 3), np.uint8)
  grayimage_inv = cv2.morphologyEx(grayimage_inv, cv2.MORPH_CLOSE, kernelc, iterations=3)
  grayimage=255-grayimage_inv.astype(np.uint8)
  print('after2')
  # cv2_imshow(grayimage)
  #kernel
  kernel = np.zeros((5,5), np.uint8)
  kernel[2, :] = 1
  kernel2 = np.zeros((5,5), np.uint8)
  kernel2[:,2] = 1

  # print('grayB')
  # cv2_imshow(grayimage)
  grayimage2=grayimage.copy()
  # print('gray')
  # cv2_imshow(gray2)

  #横線
  img_h = cv2.dilate(grayimage, kernel, iterations=15)
  # print('2')
  # cv2_imshow(img_h)
  img_h = 255-img_h
  #img_h>5の影響大
  img_h=np.where(img_h>50,255,0)
  img_h.astype('uint8')
  img_h = np.array(img_h, dtype=np.uint8)
  # img_h  = cv2.dilate(img_h, kernel3)
  #横線を太く
  # img_h = cv2.morphologyEx(img_h, cv2.MORPH_OPEN, kernel3)
  img_h=255-img_h
  # img_h = cv2.erode(img_h, kernel4, iterations=5)
  # print('4')
  # cv2_imshow(img_h)

  #縦線
  img_v = cv2.dilate(grayimage, kernel2, iterations=15)
  # print('v2')
  # cv2_imshow(img_v)
  img_v = 255-img_v
  # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite('img_v.jpg',img_v)
  #img_h>5の影響大
  img_v=np.where(img_v>10,255,0)
  img_v.astype('uint8')
  img_v = np.array(img_v, dtype=np.uint8)

  #縦線を太く
  # img_v = cv2.morphologyEx(img_v, cv2.MORPH_OPEN, kernel3)
  img_v=255-img_v
  # img_v = cv2.erode(img_v, kernel4, iterations=5)
  # print('img_v:**')
  # cv2_imshow(img_v)
  grayimage,grayimage2=[],[]
  return img_h,img_v

def get_stats(img):
  # 画像表示用に入力画像をカラーデータに変換する
  kernel2 = np.zeros((5,5), np.uint8)
  kernel2[:,2] = 1
  # gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
  gray2=255-img
  h,w=gray2.shape

  # ラベリング
  retval, labels, stats, centroids = cv2.connectedComponentsWithStats(gray2)
  stats=stats.tolist()
  stats=sorted(stats,key=lambda x:(x[0]))
  # stats=stats_split(stats,img)
  #結果表示
  # print('stats::',stats)
  gray,gray2=[],[]
  return stats

#数字とそれ以外の文字判別
def num_judge(fname):

  import numpy as np

  #visionAPIでテキストデータ取得
  source_texts,source_characters=visionAPI(fname)

  #描画エリア準備
  im0 = Image.new('RGB', (4680,3309), (255, 255, 255))
  im1 = Image.new('RGB', (4680,3309), (255, 255, 255))
  draw0 = ImageDraw.Draw(im0)
  draw1 = ImageDraw.Draw(im1)
  nums,moji=[],[]
  for sc in source_characters:
    text=sc['text']
    x1,x2,y1,y2=sc['bounds'].get_left(),sc['bounds'].get_right(),sc['bounds'].get_top(),sc['bounds'].get_bottom()
    x1,x2,y1,y2=int(x1),int(x2),int(y1),int(y2)

    if text.isdecimal() or text==',':
      flg=0 #'数字'
      nums.append([text,x1,y1,x2,y2,x2-x1,y2-y1])
    else:
      flg=1 #'文字'
      moji.append([text,x1,y1,x2,y2,x2-x1,y2-y1])
#テキストを描画
def cv2_putText(img,txt,xs,ye):
  cv2.putText(img,text=txt,
            org=(xs,ye),fontFace=cv2.FONT_HERSHEY_SIMPLEX,fontScale=2.5,
            color=(0, 0, 0),thickness=3,lineType=cv2.LINE_4)
  return img
#横線の開始位置xを含む線を抽出
def get_h_line_include_x(line,xs,xe):
  ls=[]
  for l in line:
    if l[0]<xe+5:
      ls.append(l)
  return ls
#縦線の開始位置yを含む線を抽出
def get_v_line_include_y(line,ys,ye):
  ls=[]
  for l in line:
    if l[1]<ye+5:
      ls.append(l)
  return ls

# 出力サイズ（幅、高さ）を指定してリサイズ
def imshow(img,w,h):
  img = cv2.resize(img, (w, h))
  # return img

# 配列の最初と最後を基準に各値の比率を算出
def ratio(data):
  delta=data[-1]-data[0]
  ratio=[]
  for i in range(1,len(data)):
    ratio.append(int((data[i]-data[0])/delta*1000)/1000)
  return ratio

#電化のコヤマ対策（線が取得できない画像）
def koyama(image):
  # Invert the image
  inverted_image = cv2.bitwise_not(image)
  h,w =inverted_image.shape[0],inverted_image.shape[1]
  print('inverted_image')
  cv2_imshow(inverted_image)
  #除外エリア
  inverted_image=cv2.rectangle(inverted_image,(0,0),(w,int(0.3*h)),(0,0,0),cv2.FILLED)
  inverted_image=cv2.rectangle(inverted_image,(int(0.67*w),int(0.78*h)),(w,h),(0,0,0),cv2.FILLED)
  print('inverted_image')
  cv2_imshow(inverted_image)
  # cv2.imwrite('inverted_image.jpg',inverted_image)

  r,c=[],[]
  # Calculate the projection on the x and y axis
  x_projection = np.sum(inverted_image, axis=0)
  y_projection = np.sum(inverted_image, axis=1)
# Find the threshold crossings for both projections
  xstart,xend = find_threshold_crossings(y_projection)
  ystart,yend = find_threshold_crossings(x_projection)
  r.append(xstart)
  r.append(xend)
  c.append(ystart)
  c.append(yend)

  return r,c

def find_threshold_crossings(projection, threshold_factor=0.3):
    """
    Find the x or y coordinates where the projection first and last exceeds
    the threshold which is set as a factor of the peak value.
    """
    # Find the peak value
    peak = np.max(projection)
    # Calculate the threshold
    threshold = peak * threshold_factor

    # Find where the projection first and last exceeds the threshold
    crossing_indices = np.where(projection > threshold)[0]
    if crossing_indices.size == 0:  # No crossings found
        return None, None
    first_crossing = crossing_indices[0]
    last_crossing = crossing_indices[-1]

    return first_crossing, last_crossing

#visionAPIによるOCR
def visionAPI(fname):
  account_file = '/content/drive/MyDrive/pys/engine/service-account-file.json'
  client = vision.ImageAnnotatorClient.from_service_account_json(account_file)
  img = cv2.imread(fname)
  # メモリ上のイメージをjpgエンコード
  _, content = cv2.imencode('.jpg', img)
  content = content.tobytes()
  image = types.Image(content=content)
  response = client.document_text_detection(image=image,image_context={"language_hints":["ja-t-i0-handwrit"]})
  # print(response)
  document = response.full_text_annotation
  source_texts = []
  source_characters = []
  for page in document.pages:
      for block in page.blocks:
          for paragraph in block.paragraphs:
              for word in paragraph.words:
                  for symbol in word.symbols:
                      text = {}
                      text['text'] = symbol.text
                      text['bounds'] = Bound(symbol.bounding_box.vertices)
                      # debug_print( '{}({},{})({},{})'.format(symbol.text,text['bounds'].get_left(),text['bounds'].get_top(),text['bounds'].get_right(),text['bounds'].get_bottom()),level=DEBUG_CHAR_INFO)
                      source_characters.append(text)
  return source_texts,source_characters

#for PL
################################################################
#PL用
################################################################

def get_rc(img,div,img_h,img_v):
  # print('get_rcのimg_h,img_v',img_h,img_v)
  # cv2_imshow(img_h)
  # cv2_imshow(img_v)
  #横線
  # img=cv2.imread(path)
  #横線の長さが書類の横幅の90%以上のものがあるか
  stats_h=get_stats(img_h)
  img_h=cv2.cvtColor(img_h, cv2.COLOR_BGR2RGB)
  width,height=stats_h[0][2],stats_h[0][3]
  y_s,x_s,r,c=[],[],[],[]
  xmin,xmax=100000,0
  # print('xmin,xmax',xmin,xmax)
  print('stats_h',stats_h)
  for i,s in enumerate(stats_h):
    #PL用の条件
    if s[0]<width*0.2 and s[2]>width*0.2 and s[2]<width*0.95 and s[1]>height*0.15 :
      y_s.append(s)
      cv2.line(img_h,pt1=(s[0], s[1]+s[3]),pt2=(s[0]+s[2],s[1]+s[3]),color=(255, 0, 0),thickness=5,lineType=cv2.LINE_4,shift=0)
      # print('i,s[0]',i,s[0])
      if xmin>s[0]:
        xmin=s[0]
        # print('xmin:',i,xmin)
      if xmax<s[0]+s[2]:
        xmax=s[0]+s[2]
  print('xmin,xmax:',i,xmin,xmax)
  # print('y_s',y_s)
  if y_s==[]:
    pass
    # print('y_s',y_s)
  else:
    #左の列の横線を取得（xs>0,xe<0.2w)
    y_s_left=get_h_line_include_x(y_s,0,0.2*width)
    #yで並べ変え
    y_s_left_sorted=sorted(y_s_left, key = lambda x:x[1])
    # print('len(y_s_left_sorted)',len(y_s_left_sorted))
    # print(y_s_left_sorted)
    #rのy座標をプロット
    r=[]
    for i,ys in enumerate(y_s_left_sorted):
      xs,ye=ys[0],ys[1]-10
      txt='r'+str(i)+'='+str(ye)
      cv2_putText(img_h,txt,xs,ye)
      r.append(ye)
    #出力確認
    # print('r[0],r[-1]',r[0],r[-1])


    cv2_imshow(img_h)

  ################################################################
  #縦線　開始位置y>=r0-5　and y<r4 （若干の傾きを考慮し-5）

  stats_v=get_stats(img_v)
  # print('stats_v',stats_v)
  img_v=cv2.cvtColor(img_v, cv2.COLOR_BGR2RGB)
  ymin,ymax=100000,0
  # print('ymin0',ymin)
  for i,s in enumerate(stats_v):
    # print('s in stats_v:',s)
    # print('s[3]>height*0.1',s[3],height*0.1)
    # print('s[1]>height*0.2',s[1],height*0.2)
    # print('s[3]<height*0.75',s[1],s[3],height*0.75)
    # print('s[0]<width*0.98',s[0],width*0.98)
    if s[3]>height*0.1 and s[1]>height*0.2  and s[1]<height*0.6 and s[3]<height*0.62 and s[0]<width*1:
    # if s[3]>height*0.2 and s[3]<height and s[0]>r[0]-5 and s[0]<r[4]:
      x_s.append(s)
      # print('縦線stats',s[0],s[2])
      cv2.line(img_v,pt1=(s[0]+s[2], s[1]),pt2=(s[0]+s[2],s[1]+s[3]),color=(0, 255, 0),thickness=10,lineType=cv2.LINE_4,shift=0)
      # print('i,s[1]',i,s[1])
      if ymin>s[1]:
        ymin=s[1]
      if ymax<s[1]+s[3] and s[0]<width*0.5:
        ymax=s[1]+s[3]
      # print('i,ymin',i,ymin)
  # print('ymin,ymax',ymin,ymax)
  # print('x_s',x_s)
  if x_s==[] or y_s==[] or r==[]:
    # print('y_s,x_s',y_s,x_s)
    return None
  else:

    #y方向でソートし最初と最後のyを取得
    x_s_sorted_y=sorted(x_s,key = lambda x:x[1])
    # print('x_s_sorted_y',x_s_sorted_y)
    ys=x_s_sorted_y[0][1]
    ye=x_s_sorted_y[-1][1]
    ye=ys+int(0.42*(ye-ys))
    x_s_left=get_v_line_include_y(x_s,r[0]-5,ye)
    # print('len(x_s_left),x_s_left',len(x_s_left),x_s_left)
    #xで並べ変え
    x_s_left_sorted=sorted(x_s_left, key = lambda x:x[0])
    # print('x_s_left_sorted',x_s_left_sorted)
    #cのx座標をプロット
    c=[]
    print('**********')
    for i,xs in enumerate(x_s_left_sorted):
      xs,ye=xs[0],xs[1]
      txt='c'+str(i)+'='+str(xs)
      cv2_putText(img_v,txt,xs-60,ye-10)
      c.append(xs)
    #出力確認
    print('c[0],c[-1]',c[0],c[-1])
    cv2_imshow(img_v)
    # imshow(img_v,800,600)
    # cv2.imwrite('img_v.jpg',img_v)
    # print('c000',c)
    # print('ｒとｃ',len(r),len(c))

    #ｒからのyminの情報
    if r[0]>ymin:
      # print('r[0],ymin',r[0],ymin)
      r[0]=ymin
    #ｒからのymaxの情報
    if r[-1]<ymax:
      # print('r[-1],ymax',r[-1],ymax)
      r[-1]=ymax
    #cからのxminの情報
    print('A:c[0],xmin',c[0],xmin)
    if c[0]>xmin:
      if len(c)==0:
        c.append(xmin)
      else:
        c[0]=xmin
      print('B:c[0],xmin',c[0],xmin)
    #cからのxmaxの情報
    if c[-1]<xmax:
      if len(c)<2:
        c.append(xmax+10)
      else:
        c[-1]=xmax+10
      print('c[-1],xmax',c[-1],xmax)
    #確認
    print('xmin,ymin,xmax,ymax',xmin,ymin,xmax,ymax)
    return r,c,stats_v
  
#列方向cのチェックと正規化
def check_c(c):
  chk=[0.1522,0.3341,0.4863,0.6672,0.8199,1.000]
  # print('c***',c)
  # print('c[0],c[-1]',c[0],c[-1])
  # print('chk',chk)
  num_c=[]
  w = c[-1]-c[0]
  for i in range(6):
    #左中右列の開始と終了位置xの比率をc[0]とc[-1]から算出
    # print('chk[i]',chk[i])
    x = round(c[0] + chk[i] * w)
    num_c.append(x)
  # print('num_c',num_c)
  return num_c

def cv2_imshow(img):
    return False

#20231204追加　各行の数値の左右の縦線を検出してフィットさせる
def reset_col_vline(position,row,iy_str,iy_end,num_c,img,img_h,img_v,len_c,pt):
  #縦線横線射影取得用
  # img_h,img_v=get_hv_line(img)
  #position（左=L、中=M、右=R) Row(行番号)
  # print('position,row',position,row)
  #各列の一番下の縦線の高さを縮める
  if (position!='R' and row ==15) or (position=='R' and row==11):
    s1y1=iy_str-15
    s1y2=iy_end-15
  # elif position=='R' and row==11:
  #   s1y1=iy_str-15
  #   s1y2=iy_end+15
  else:
    s1y1=iy_str-15
    s1y2=iy_end-15
  # print('s1y1,s1y2',s1y1,s1y2)
  c_new_left,c_new_mid,c_new_right,numc=[],[],[],[]
  sx1=0
  numc=[]
  for i in range(6):
    numc.append(num_c[i])
  # print('numc*****',numc)
  if position=="L":
    #左列左の縦線確認用
    # print('A:numc[0]',numc[0])
    s1x1=numc[0]-int(pt*0.35)
    s1x2=numc[0]+int(pt*0.35)

    img_s1=img.copy()
    cv2.rectangle(img_s1, (s1x1,s1y1), (s1x2,s1y2), (255, 0,0), cv2.FILLED)
    # print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    # print('img_s1')
    # imshow(img_s1,600,400)
    # cv2_imshow(img_s1)
    # print('img_v')
    # cv2_imshow(img_v)
    # img[top : bottom, left : right]
    img1=[],img2L=[],[]
    if len_c<10:
      img1 = img[s1y1 : s1y2, s1x1: s1x2]
    else:
      img1 = img_v[s1y1 : s1y2, s1x1: s1x2]
    # print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    img2L=255-img1
    img1=[]
    # print('r_new',r_new)
    try:
      sx1=v_line_check(img2L)[0]
      # print('C:sx1',sx1)
      # cv2_imshow(img2L)
      # cv2.imwrite('img2L.jpg',img2L)
    except:
      sx1=0
      # print('except')
    # print('左列左s1x1,sx1L,s1x1+sx1[1]',s1x1,sx1,s1x1+sx1)
    numc[0]=s1x1+sx1-8
    # print('B:numc[0]',numc[0])
    #左列右の縦線確認用
    s1x1=numc[1]-int(pt*0.3)
    s1x2=numc[1]+int(pt*0.3)
    # s1y1=r_new[0]+int(pt*1.2)
    # s1y2=r_new[0]+int(pt*1.7)
    # print('numc[1]',numc[1])
    img_s=img.copy()
    cv2.rectangle(img_s, (s1x1,s1y1), (s1x2,s1y2), (255, 0,0), cv2.FILLED)
    # print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    # print('img_s')
    # imshow(img_s,600,400)
    # cv2_imshow(img_s)
    # img[top : bottom, left : right]
    img1=[]
    if len_c<10:
      img1 = img[s1y1 : s1y2, s1x1: s1x2]
    else:
      img1 = img_v[s1y1 : s1y2, s1x1: s1x2]
    # print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    img2=255-img1
    # print('左列右')
    # cv2_imshow(img2)
    # cv2.imwrite('img2.jpg',img2)
    img1=[]
    # print('r_new',r_new)
    sx1=v_line_check(img2)[1]
    # print('左列右sx1',sx1)
    numc[1]=s1x1+sx1-4
    # print('numc[1],s1x1,sx1',numc[1],s1x1,sx1)
  elif(position=='M'):
    #中列左の縦線確認用
    s1x1=numc[2]-int(pt*0.3)
    s1x2=numc[2]+int(pt*0.3)
    # s1y1=r_new[0]+int(pt*0.6)
    # s1y2=r_new[0]+int(pt*1)
    # print('numc[2]',numc[2])
    img_s1=img.copy()
    # cv2.rectangle(img_s1, (s1x1,s1y1), (s1x2,s1y2), (255, 0,0), cv2.FILLED)
    # print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    # print('img_s1中')

    # img[top : bottom, left : right]
    img1=[],img2L=[],[]
    if len_c<10:
      img1 = img[s1y1 : s1y2, s1x1: s1x2]
    else:
      img1 = img_v[s1y1 : s1y2, s1x1: s1x2]
    img2L=255-img1
    # print('img2L')
    # cv2_imshow(img2L)
    # print('r_new',r_new)
    try:
      sx1=v_line_check(img2L)[0]
      # cv2_imshow(img2L)
      # cv2.imwrite('img2中L.jpg',img2L)
    except:
      sx1=0
    # print('sx1中L',sx1)
    numc[2]=s1x1+sx1
    # print('中列左numc[2],sx1',numc[2],sx1)
    #中列右の縦線確認用
    s1x1=numc[3]-int(pt*0.2)
    s1x2=numc[3]+int(pt*0.5)
    # s1y1=r_new[0]+int(pt*0.6)
    # s1y2=r_new[0]+int(pt*1)
    # print('numc[3]',numc[3])
    # img_s=img.copy()
    # cv2.rectangle(img_s, (s1x1,s1y1), (s1x2,s1y2), (255, 0,0), cv2.FILLED)
    # print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    # print('img_s')
    # cv2_imshow(img_s)
    # img[top : bottom, left : right]
    img1=[]
    if len_c<10:
      img1 = img[s1y1 : s1y2, s1x1: s1x2]
    else:
      img1 = img_v[s1y1 : s1y2, s1x1: s1x2]
    img2R=255-img1
    # print('img2R')
    # cv2_imshow(img2R)
    # cv2.imwrite('img2.jpg',img2)
    img1=[]
    # print('r_new',r_new)
    sx1=v_line_check(img2R)[1]
    # print('中列右numc[3],sx1',numc[3],sx1)
    numc[3]=s1x1+sx1-4
    # print('numc[3]',numc[3])
    #各列の開始と終了位置からx座標を計算
    # print('222')
    # c_new_left  = num_x(numc[0],numc[1])
    # c_new_mid   = num_x(numc[2],numc[3])
    # c_new_right = num_x(numc[4],numc[5])
    # print('c_new_left',c_new_left)
  elif(position=='R'):
    #右列左の縦線確認用
    s1x1=numc[4]-int(pt*0.3)
    s1x2=numc[4]+int(pt*0.4)
    # s1y1=r_new[0]+int(pt*0.6)
    # s1y2=r_new[0]+int(pt*1)
    # print('numc[4]',numc[4])
    img_s1=img.copy()
    # cv2.rectangle(img_s1, (s1x1,s1y1), (s1x2,s1y2), (255, 0,0), cv2.FILLED)
    # print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    # print('img_s1中')
    # cv2_imshow(img_s1)
    # imshow(img_s1,600,400)
    # img[top : bottom, left : right]
    img1=[],img2L=[],[]
    # img1 = img_v[s1y1 : s1y2, s1x1: s1x2]
    if len_c<10:
      img1 = img[s1y1 : s1y2, s1x1: s1x2]
    else:
      img1 = img_v[s1y1 : s1y2, s1x1: s1x2]
    # print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    img2L=255-img1
    # cv2_imshow(img2L)
    img1=[]
    # print('r_new',r_new)
    try:
      sx1=v_line_check(img2L)[0]
      # cv2_imshow(img2L)
      # cv2.imwrite('img2中L.jpg',img2L)
    except:
      sx1=0
    # print('右列左sx1',sx1)
    numc[4]=s1x1+sx1
    # print('中numc[4]',numc[4])
    #右列右の縦線確認用
    s1x1=numc[5]-int(pt*0.2)
    s1x2=numc[5]+int(pt*0.5)
    # s1y1=r_new[0]+int(pt*0.6)
    # s1y2=r_new[0]+int(pt*1)
    # print('numc[5]',numc[5])
    img_s=img.copy()
    print('img_s1.shape',img_s1.shape)
    img_s1=cv2.cvtColor(img_s,cv2.COLOR_GRAY2BGR)
    cv2.rectangle(img_s1, (s1x1,s1y1), (s1x2,s1y2), (255, 0,0), cv2.FILLED)
    print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    print('img_s')
    imshow(img_s1,600,400)
    print('img_v')
    imshow(img_v,600,400)
    # img[top : bottom, left : right]
    img1=[]
    if len_c<10:
      img1 = img[s1y1 : s1y2, s1x1: s1x2]
    else:
      img1 = img_v[s1y1 : s1y2, s1x1: s1x2]
    print('s1x1,s1y1,s1x2,s1y2',s1x1,s1y1,s1x2,s1y2)
    img2=255-img1
    cv2_imshow(img2)
    # cv2.imwrite('img2.jpg',img2)
    img1=[]
    # print('r_new',r_new)
    sx1=v_line_check(img2)[1]
    # print('右列右:sx1',sx1)
    numc[5]=s1x1+sx1-4

  #各列の開始と終了位置からx座標を計算
  # print('各列の開始と終了位置からx座標を計算：numc[0],numc[1]',numc[0],numc[1])
  c_new_left  = num_x(numc[0],numc[1])
  # print('c_new_left',c_new_left)
  c_new_mid   = num_x(numc[2],numc[3])
  # print('c_new_mid',c_new_left)
  c_new_right = num_x(numc[4],numc[5])
  # print('c_new_right',c_new_left)
  return c_new_left,c_new_mid,c_new_right

def hosei(top,bottom,left,right,gray):
  #r[0]補正に使用するエリアimg1r    #img[top : bottom, left : right]
  # print('gray in hosei')
  # cv2_imshow(gray)
  # print('top : bottom',top, bottom)
  img1r=gray[top : bottom, left : right]
  # cv2_imshow(img1r)
  img1r_inv=255-img1r
  # print('img1r_inv in hosei')
  # cv2_imshow(img1r_inv)
  hosei_y=h_line_check(img1r_inv)
  # print('hosei_y',hosei_y)
  # print('top in hosei',top)
  return hosei_y

# Function to find ranges of consecutive numbers above a certain threshold
def find_consecutive_ranges(data, threshold=0):
    above_threshold = np.where(data > threshold)[0]
    ranges = np.split(above_threshold, np.where(np.diff(above_threshold) != 1)[0] + 1)
    return [(r[0], r[-1]) for r in ranges if r.size > 0]

# Function to perform vertical projection and find ranges
def vertical_projection_ranges(img, threshold_ratio=0.04, max_range_length=7):
    # Invert the image to make text white and background black
    # print('in vertical_projection_ranges')
    print('shape',img.shape)
    gray_img=cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    inverted_img = 255 - gray_img
    # cv2_imshow(inverted_img)
    # Perform vertical projection
    vertical_projection = np.sum(inverted_img, axis=1)

    # Determine the threshold
    threshold = np.max(vertical_projection) * threshold_ratio

    # Find the ranges of consecutive numbers above the threshold
    ranges = find_consecutive_ranges(vertical_projection, threshold)

    # Filter the ranges based on the maximum length
    filtered_ranges = [(start, end) for start, end in ranges if end - start <= max_range_length]

    return filtered_ranges

#画像をグレースケールで読み込み、cv2.bitwise_not() で色を反転。
#その後、画像を水平方向に射影し、最も幅が広いX座標の連続範囲を求める

def largest_continuous_range_cv2(img):
    # print('shape',img.shape)
    w,h,_=img.shape
    grayimg=cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Invert the image
    image_inverted = cv2.bitwise_not(grayimg)
    # Projecting the image horizontally (axis=0)
    horizontal_projection = np.sum(image_inverted, axis=0)
    # Finding the x-coordinates where the frequency is greater than 0
    x_coords = np.where(horizontal_projection > 0)[0]

    # Identifying the largest continuous range of x-coordinates
    def largest_continuous_range(coords):
        if len(coords) == 0:
            return None

        max_range = []
        current_range = [coords[0]]

        for i in range(1, len(coords)):
            if coords[i] == coords[i - 1] + 1:
                current_range.append(coords[i])
            else:
                if len(current_range) > len(max_range):
                    max_range = current_range
                current_range = [coords[i]]

        if len(current_range) > len(max_range):
            max_range = current_range

        return (max_range[0], max_range[-1])

    return largest_continuous_range(x_coords)

def v_line_cut(before_cut,cut_ratio):
  import cv2
  import numpy as np

  # Convert to grayscale
  gray = cv2.cvtColor(before_cut, cv2.COLOR_BGR2GRAY)
  h, w = gray.shape
  cv2_imshow(gray)
  # Invert the image
  inverted_image = cv2.bitwise_not(gray)

  # Project the inverted image along axis=0 (summing up the pixel values along the columns)
  projection = np.sum(inverted_image, axis=0)
  # print('projection',projection)
  # Calculate cut_ratio of the maximum peak value
  half_max_peak_value = 255 * h * cut_ratio

  #ピーク値がある場合、そのピーク値に対してpeak_threshold_ratio以上の値をとるx座標を取得
  peak_threshold_ratio=0.92
  peak_value = np.max(projection)
  if(peak_value>half_max_peak_value):
		# Find the peak value
    peak_value = np.max(projection)
    print('projection',projection)
    # Calculate the threshold value for significant peaks
    threshold_value = peak_value * peak_threshold_ratio
    print('threshold_value',threshold_value)
    # Find the ranges where the projection is above the threshold
    peak_ranges = []
    in_peak_range = False
    for i, value in enumerate(projection):
      if value >= threshold_value:
        if not in_peak_range:
					# Start of a new peak range
          start = i
          in_peak_range = True
          print('start',i)
      else:
        if in_peak_range:
					# End of a peak range
          end = i - 1
          peak_ranges.append((start, end))
          in_peak_range = False
          print('end',end)
      # If we were in a peak at the end of the projection, close the last range
    if in_peak_range:
      peak_ranges.append((start, len(projection) - 1))
    return peak_ranges
  else:
    return []


#列方向cのチェックと正規化
def check_c_bs(c):
  chk=[0.1522,0.3341,0.4863,0.6672,0.8199,1.000]
  print('c',c)
  print('c[0],c[-1]',c[0],c[-1])
  print('chk',chk)
  num_c=[]
  w = c[-1]-c[0]
  for i in range(6):
    #左中右列の開始と終了位置xの比率をc[0]とc[-1]から算出
    print('chk[i]',chk[i])
    x = round(c[0] + chk[i] * w)
    num_c.append(x)
  # print('num_c',num_c)
  return num_c


#数値エリア（x方向）
def num_x_bs(c0,c1):
  # print('c0,c1',c0,c1)
  c_new=[]
  #case0=left 1=mid 2=right
  c_list=[0.041,0.216,0.243,0.324,0.351,0.432,0.459,0.541,0.568,0.649,0.676,0.757,0.784,0.865,0.892,0.973,1.000]

  c_dist=c1-c0
  cx=c0
  # print('c_dist',c_dist)
  # print('c_list[0]',c_list[0])
  for i in range(len(c_list)):
    # print('round(c_dist * c_list[i])',round(c_dist * c_list[i]))
    cx = round(c0 + round(c_dist * c_list[i]))
    # print('cx',cx) 列方向の正規化座標x
    c_new.append(cx)
  # print('c_new',c_new)
  return c_new


#ｒの確認
def check_r(r,flg):
  #左の列用
  if flg==0:
    chk=[0.053 ,0.159 ,0.21 ,0.266 ,0.318 ,0.371 ,0.422 ,0.527 ,0.581 ,0.634 ,0.687 ,0.74 ,0.792 ,0.845 ,0.895 ,0.95]
  #真ん中と右の列用
  elif flg==1 or flg==2:
    chk=[0.055,0.107,0.159,0.212,0.264,0.317,0.369,0.422,0.474,0.526,0.579,0.631,0.684,0.736,0.789,0.841,0.896,1]
  l,r_new=[],[]
  #高さ
  h=r[-1]-r[0]
  # print('r',len(r),r)
  # print('*',int((r[1]-r[0])/100))
  sum_r,pt,y=0,0,0
  for i in range(len(r)-1):
    row_d=round((r[i+1]-r[i])/100)
    l.append(row_d)
    # print('line',i,row_d)
    sum_r += row_d
  #行間の平均値pt
  pt =round((r[-1]-r[0]) / sum_r)
  # print('sum_r',sum_r)
  #pt=17の場合線が読めている
  # print('pitch',pt)
  # print('l',l)
  #左left
  # seikika=[1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1 ,1]
  # print('len(seikika左)',len(seikika),seikika)

  y = r[0]
  # print('sum_r',sum_r)
  # if(sum_r>=17):
  if flg==0:
    t=0
  elif flg==1:
    t=1
  elif flg==2:
    t=-4

  for j in range(16+t):
    #ｒの正規化（横線が足りない部分があれば補完）
    # print('seikika',j,seikika[j])
    # print('chk',chk[j])
    y = r[0] + round(h * chk[j])
    r_new.append(y)
  # print('check_r：flg,rnew',flg,r_new)
  return r_new,pt

#列方向cのチェックと正規化
def check_c(c):
  chk=[0.1522,0.3341,0.4863,0.6672,0.8199,1.000]
  # print('c***',c)
  # print('c[0],c[-1]',c[0],c[-1])
  # print('chk',chk)
  num_c=[]
  w = c[-1]-c[0]
  for i in range(6):
    #左中右列の開始と終了位置xの比率をc[0]とc[-1]から算出
    # print('chk[i]',chk[i])
    x = round(c[0] + chk[i] * w)
    num_c.append(x)
  # print('num_c',num_c)
  return num_c


def recheck_c(r,num_c0,gray):
  print('★r',r)
  print('num_c0',num_c0)
  num_c=[]
  for i in range(6):
    img_div=255-gray[r[0]+5:r[1],num_c0[i]-50:num_c0[i]+100]
    print('img_div')
    cv2_imshow(img_div)
    print('v_line_check(img_div)',v_line_check(img_div))
    c=num_c0[i]-50+v_line_check(img_div)[0]
    print('c,num_c0[i]-50,v_line_check(img_div)[0]',c,num_c0[i]-50,v_line_check(img_div)[0])
    num_c.append(c)
    img_div=[]
  return num_c

#数値エリア（x方向）
def num_x(c0,c1):
  # print('c0,c1',c0,c1)
  c_new=[]
  #case0=left 1=mid 2=right
  c_list=[0.041,0.216,0.243,0.324,0.351,0.432,0.459,0.541,0.568,0.649,0.676,0.757,0.784,0.865,0.892,0.973,1.000]

  c_dist=c1-c0
  cx=c0
  # print('c_dist',c_dist)
  # print('c_list[0]',c_list[0])
  for i in range(len(c_list)):
    # print('round(c_dist * c_list[i])',round(c_dist * c_list[i]))
    cx = round(c0 + round(c_dist * c_list[i]))
    # print('cx',cx) 列方向の正規化座標x
    c_new.append(cx)
  # print('c_new',c_new)
  return c_new




################################################################
#　BS（貸借対照表）TAB1
################################################################

def get_rc_BS(img):
  #横線
  # img=cv2.imread(path)
  img_h,img_v=get_hv_line_bs(img)
  # cv2_imshow(img_h)
  xmin,xmax=100000,0
  stats_h=get_stats(img_h)
  img_h=cv2.cvtColor(img_h, cv2.COLOR_BGR2RGB)
  width,height=stats_h[0][2],stats_h[0][3]
  y_s,x_s,r,c=[],[],[],[]
  for s in stats_h:
    if s[2]>width*0.3 and s[2]<width*0.99 and s[1]>height*0.1:
    # if s[2]>width*0.3 and s[2]<width*0.99 and s[1]>height*0.01:
      y_s.append(s)
      cv2.line(img_h,pt1=(s[0], s[1]+s[3]),pt2=(s[0]+s[2],s[1]+s[3]),color=(255, 0, 0),thickness=10,lineType=cv2.LINE_4,shift=0)
      if xmin>s[0]:
        xmin=s[0]
      if xmax<s[0]+s[2]:
        xmax=s[0]+s[2]
  if y_s==[]:
    pass
    # print('y_s',y_s)
  else:
    #左の列の横線を取得（xs>0,xe<0.2w)
    y_s_left=get_h_line_include_x_bs(y_s,0,0.2*width)
    #yで並べ変え
    y_s_left_sorted=sorted(y_s_left, key = lambda x:x[1])
    # print('len(y_s_left_sorted)',len(y_s_left_sorted))
    # print(y_s_left_sorted)
    #rのy座標をプロット
    r=[]
    for i,ys in enumerate(y_s_left_sorted):
      xs,ye=ys[0],ys[1]-10
      txt='r'+str(i)+'='+str(ye)
      cv2_putText_bs(img_h,txt,xs,ye)
      r.append(ye)
    # print('r---->',r)
    #出力確認
    imshow(img_h,800,600)

  ################################################################
  #縦線　開始位置y>=r0-5　and y<r4 （若干の傾きを考慮し-5）

  stats_v=get_stats_bs(img_v)
  img_v=cv2.cvtColor(img_v, cv2.COLOR_BGR2RGB)
  ymin,ymax=100000,0
  stats_v_first=0
  for s in stats_v:
    if s[3]>height*0.5 and s[3]<height and s[1]<height*0.5 and s[0]<width*0.97:
      x_s.append(s)
      if stats_v_first==0 :
        stats_v_first=s[0]+s[2]
      cv2.line(img_v,pt1=(s[0]+s[2], s[1]),pt2=(s[0]+s[2],s[1]+s[3]),color=(0, 255, 0),thickness=10,lineType=cv2.LINE_4,shift=0)
      # print('ymin,s[1]',ymin,s[1])
      if ymin>s[1]:
        ymin=s[1]
      if ymax<s[1]+s[3]:
        ymax=s[1]+s[3]
  # print('ymin',ymin)
  # print('x_s:',x_s)
  if x_s==[] or y_s==[] or r==[]:
    # print('y_s,x_s',y_s,x_s)
    return None
  else:

    #y方向でソートし最初と最後のyを取得
    x_s_sorted_y=sorted(x_s,key = lambda x:x[1])
    ys=x_s_sorted_y[0][1]
    ye=x_s_sorted_y[-1][1]
    # ye=ys+int(0.42*(ye-ys))
    # x_s_left=get_v_line_include_y_bs(x_s,r[0]-5,ye)
    x_s_left=get_v_line_include_y_bs(x_s,r[0],ye)
    # print('len(x_s_left),x_s_left',len(x_s_left),x_s_left)
    #xで並べ変え
    x_s_left_sorted=sorted(x_s_left, key = lambda x:x[0])
    # print(x_s_left_sorted)
    #cのx座標をプロット
    c=[]
    for i,xs in enumerate(x_s_left_sorted):
      xs,ye=xs[0],xs[1]
      txt='c'+str(i)+'='+str(xs)
      if i==10:
          ye+=60
      cv2_putText_bs(img_v,txt,xs-60,ye-10)
      c.append(xs)

    imshow(img_v,800,600)

    #ｒの一番上の線が読めない場合の対応
    # print('r[0]::::',r[0])
    #rにデータが１つ以上ある場合の処理
    if len(r)>1:
      if r[0]==0 or r[0]>ymin:
        # print('r[0],ymin',r[0],ymin)
        r[0]=ymin
        # print('r[0],ymin',r[0],ymin)
      #ｒの一番下の線が読めない場合の対応
      if r[-1]<ymax:
        # print('r[-1],ymax',r[-1],ymax)
        r[-1]=ymax
        # print('r[-1],ymax',r[-1],ymax)
    #rにデータが１つの場合
    elif len(r)==1:
        r[0]=ymin
        r.append(ymax)
    #cの一番左の線が読めない場合の対応
    if c[0]>xmin:
      # print('c[0],xmin',c[0],xmin)
      c[0]=xmin+10
      # print('c[0],xmin',c[0],xmin)
    #cの一番右の線が読めない場合の対応
    if c[-1]<xmax:
      print('c[-1],xmax',c[-1],xmax)
      c[-1]=xmax+10
    # print('***r0',r[0])

    return r,c,stats_v,stats_v_first

def adjust_contrast_bs(input_image, factor):
    """
    Adjusts the contrast of an image by interpolating between the image (factor = 1.0)
    and the average grayscale value (factor = 0.0).
    """
    # Calculate the mean pixel value of the grayscale image
    mean_val = np.mean(input_image)

    # Interpolate between the image and the mean value
    adjusted = cv2.addWeighted(input_image, factor, np.zeros_like(input_image, dtype=np.uint8), 0, mean_val * (1 - factor))

    return adjusted


def get_hv_line_bs(img):
  #画像を濃く
  # Increase the contrast by a factor > 1.0 to make it darker
  contrast_factor = 2.0  # You can adjust this factor to get the desired contrast
  darker_image = adjust_contrast_bs(img, contrast_factor)
  print('img')
  cv2_imshow(img)
  print('darker_image')
  cv2_imshow(darker_image)
  # 画像表示用に入力画像をカラーデータに変換する
  gray = cv2.cvtColor(darker_image,cv2.COLOR_BGR2GRAY)
  #kernel
  kernel = np.zeros((3,3), np.uint8)
  # kernel = np.zeros((5,5), np.uint8)
  kernel[2, :] = 1
  # kernel2 = np.zeros((3,3), np.uint8)
  kernel2 = np.zeros((5,5), np.uint8)
  # kernel2[:,2] = 1
  # print('1')
  # cv2_imshow(gray)
  gray2=gray.copy()
  # print('gray')
  # cv2_imshow(gray2)

  #横線
  img_h = cv2.dilate(gray, kernel, iterations=15)
  # print('2')
  # cv2_imshow(img_h)
  img_h = 255-img_h
  #img_h>5の影響大
  # img_h=np.where(img_h>10,255,0)
  img_h.astype('uint8')
  img_h = np.array(img_h, dtype=np.uint8)
  # img_h  = cv2.dilate(img_h, kernel3)
  #横線を太く
  # img_h = cv2.morphologyEx(img_h, cv2.MORPH_OPEN, kernel3)
  img_h=255-img_h
  # img_h = cv2.erode(img_h, kernel4, iterations=5)
  # print('4')
  # cv2_imshow(img_h)

  #縦線（20250521に、ここを修正）
  kernel_v = np.ones((5,5),np.uint8)
  img_v = cv2.erode(gray,kernel_v,iterations = 1)
  # img_v = cv2.dilate(gray, kernel2, iterations=15)
  print('v2')
  cv2_imshow(img_v)
  img_v = 255-img_v
  #img_h>5の影響大
  img_v=np.where(img_v>10,255,0)
  img_v.astype('uint8')
  img_v = np.array(img_v, dtype=np.uint8)

  #縦線を太く
  #縦方向に長めのカーネルを作成 (幅=1, 高さ=gap_size*2+1)
  kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 10 * 2 + 1))
  # 4. クロージング（膨張→収縮）で隙間を埋める
  img_v = cv2.morphologyEx(img_v, cv2.MORPH_OPEN, kernel_v)
  img_v=255-img_v
  # img_v = cv2.erode(img_v, kernel4, iterations=5)
  print('***')
  cv2_imshow(img_v)
  gray,gray2=[],[]
  return img_h,img_v

def get_stats_bs(img):
  # 画像表示用に入力画像をカラーデータに変換する
  kernel2 = np.zeros((5,5), np.uint8)
  kernel2[:,2] = 1
  # gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
  gray2=255-img
  h,w=gray2.shape

  # ラベリング
  retval, labels, stats, centroids = cv2.connectedComponentsWithStats(gray2)
  stats=stats.tolist()
  stats=sorted(stats,key=lambda x:(x[0]))
  # stats=stats_split(stats,img)
  # 結果表示
  # print('stats::',stats)
  gray,gray2=[],[]
  return stats

#数字とそれ以外の文字判別
def num_judge_bs(fname):
  from PIL import Image, ImageDraw, ImageFont
  import numpy as np

  #visionAPIでテキストデータ取得
  source_texts,source_characters=visionAPI(fname)

  #描画エリア準備
  im0 = Image.new('RGB', (4680,3309), (255, 255, 255))
  im1 = Image.new('RGB', (4680,3309), (255, 255, 255))
  draw0 = ImageDraw.Draw(im0)
  draw1 = ImageDraw.Draw(im1)
  nums,moji=[],[]
  for sc in source_characters:
    text=sc['text']
    x1,x2,y1,y2=sc['bounds'].get_left(),sc['bounds'].get_right(),sc['bounds'].get_top(),sc['bounds'].get_bottom()
    x1,x2,y1,y2=int(x1),int(x2),int(y1),int(y2)

    if text.isdecimal() or text==',':
      flg=0 #'数字'
      nums.append([text,x1,y1,x2,y2,x2-x1,y2-y1])
    else:
      flg=1 #'文字'
      moji.append([text,x1,y1,x2,y2,x2-x1,y2-y1])

#テキストを描画
def cv2_putText_bs(img,txt,xs,ye):
  cv2.putText(img,text=txt,
            org=(xs,ye),fontFace=cv2.FONT_HERSHEY_SIMPLEX,fontScale=2.5,
            color=(0, 0, 0),thickness=3,lineType=cv2.LINE_4)
  return img
#横線の開始位置xを含む線を抽出
def get_h_line_include_x_bs(line,xs,xe):
  ls=[]
  for l in line:
    if l[0]<xe:
      ls.append(l)
  return ls
#縦線の開始位置yを含む線を抽出
def get_v_line_include_y_bs(line,ys,ye):
  ls=[]
  for l in line:
    if l[1]<ye:
      ls.append(l)
  return ls


# 配列の最初と最後を基準に各値の比率を算出
def ratio_bs(data):
  delta=data[-1]-data[0]
  ratio=[]
  for i in range(1,len(data)):
    ratio.append(int((data[i]-data[0])/delta*1000)/1000)
  return ratio

#ｒの確認
def check_r_bs(r,flg):
  if flg==0:
    chk=[0.053 ,0.159 ,0.21 ,0.266 ,0.318 ,0.371 ,0.422 ,0.527 ,0.581 ,0.634 ,0.687 ,0.74 ,0.792 ,0.845 ,0.895 ,0.95]
  elif flg==1 or flg==2:
    chk=[0.055,0.107,0.159,0.212,0.264,0.317,0.369,0.422,0.474,0.526,0.579,0.631,0.684,0.736,0.789,0.841,0.896,1]
  l,r_new=[],[]
  h=r[-1]-r[0]
  # print('r',len(r),r)
  # print('*',int((r[1]-r[0])/100))
  sum_r,pt,y=0,0,0
  for i in range(len(r)-1):
    row_d=round((r[i+1]-r[i])/100)
    l.append(row_d)
    # print('line',i,row_d)
    sum_r += row_d
  pt =round((r[-1]-r[0]) / sum_r)
  # print('sum_r',sum_r)
  # print('pitch',pt) #pt=17の場合線が読めている
  # print('l',l)
  #左left
  seikika=[1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1 ,1]
  # print('len(seikika左)',len(seikika),seikika)

  y = r[0]
  # print('sum_r',sum_r)
  # if(sum_r>=17):
  if flg==0:
    t=0
  elif flg==1:
    t=1
  elif flg==2:
    t=-4

  for j in range(16+t):
    #ｒの正規化（横線が足りない部分があれば補完）
    # print('seikika',j,seikika[j])
    # print('chk',chk[j])
    y = r[0] + round(h * chk[j])
    r_new.append(y)
  # print('flg,rnew',flg,r_new)
  return r_new,pt

  #elif(pt<17): #visionAPIから数値のエリアを特定
  #  return r

#列方向cのチェックと正規化
def check_c_bs(c):
  chk=[0.1522,0.3341,0.4863,0.6672,0.8199,1.000]
  print('c',c)
  print('c[0],c[-1]',c[0],c[-1])
  print('chk',chk)
  num_c=[]
  w = c[-1]-c[0]
  for i in range(6):
    #左中右列の開始と終了位置xの比率をc[0]とc[-1]から算出
    print('chk[i]',chk[i])
    x = round(c[0] + chk[i] * w)
    num_c.append(x)
  # print('num_c',num_c)
  return num_c


#数値エリア（x方向）
def num_x_bs(c0,c1):
  # print('c0,c1',c0,c1)
  c_new=[]
  #case0=left 1=mid 2=right
  c_list=[0.041,0.216,0.243,0.324,0.351,0.432,0.459,0.541,0.568,0.649,0.676,0.757,0.784,0.865,0.892,0.973,1.000]

  c_dist=c1-c0
  cx=c0
  # print('c_dist',c_dist)
  # print('c_list[0]',c_list[0])
  for i in range(len(c_list)):
    # print('round(c_dist * c_list[i])',round(c_dist * c_list[i]))
    cx = round(c0 + round(c_dist * c_list[i]))
    # print('cx',cx) 列方向の正規化座標x
    c_new.append(cx)
  # print('c_new',c_new)
  return c_new


#射影により横線の位置を特定
# imgには白黒反転した画像を入力
def h_line_check_bs(img):

  # Load the image in grayscale
  # Perform horizontal projection by summing up the pixels along the vertical axis
  projection = np.sum(img, axis=1)

  # Normalize projection to the range [0, 1]
  normalized_projection = projection / np.max(projection)

  # Determine the x-coordinates where the projection is above 50%
  threshold_indices = np.where(normalized_projection >= 0.5)[0]
  print('threshold_indices',threshold_indices)
  # Calculate the range
  y_range_cv2 = (min(threshold_indices), max(threshold_indices))
  # print('射影により横線の位置を特定')
  # cv2_imshow(img)
  # print('yrange_cv2',y_range_cv2)
  return y_range_cv2

def h_line_check(gray):
  # print('gray.shape',gray.shape)
  # cv2_imshow(gray)
  projection_cv = np.sum(gray, axis=1)
  max_freq_cv = np.max(projection_cv)

  # Finding the x-coordinates with the maximum frequency
  y_coords_cv = np.where(projection_cv == max_freq_cv)[0]

  # Range of x-coordinates
  y_range_cv2 = (np.min(y_coords_cv), np.max(y_coords_cv))
  return y_range_cv2

  # # Load the image in grayscale
  # # Perform horizontal projection by summing up the pixels along the vertical axis
  # projection = np.sum(gray, axis=1)

  # # Normalize projection to the range [0, 1]
  # normalized_projection = projection / np.max(projection)

  # # Determine the x-coordinates where the projection is above 50%
  # threshold_indices = np.where(normalized_projection >= 0.5)[0]

  # # Calculate the range
  # y_range_cv2 = (min(threshold_indices), max(threshold_indices))
  # # print('射影により横線の位置を特定')
  # # cv2_imshow(img)
  # # print('yrange_cv2',y_range_cv2)
  # return y_range_cv2

#射影により縦線の位置を特定
# imgには白黒反転した画像を入力
def v_line_check(img):

  # # Load the image in grayscale
  # # Perform horizontal projection by summing up the pixels along the vertical axis
  # projection = np.sum(img, axis=0)

  # # Normalize projection to the range [0, 1]
  # normalized_projection = projection / np.max(projection)
  # print('normalized_projection',normalized_projection)
  # # Determine the x-coordinates where the projection is above 50%
  # try:
  #   threshold_indices = np.where(normalized_projection >= 0.4)[0]
  # # Calculate the range
  #   x_range_cv2 = (min(threshold_indices), max(threshold_indices))
  # # print('射影により縦線の位置を特定')
  # # cv2_imshow(img)
  # # print('xrange_cv2',x_range_cv2)
  # except:
  #   x_range_cv2=(0,0)
  # return x_range_cv2


  # Projecting the image on the vertical axis and finding the maximum frequency using numpy
  projection_cv = np.sum(img, axis=0)
  max_freq_cv = np.max(projection_cv)

  # Finding the x-coordinates with the maximum frequency
  x_coords_cv = np.where(projection_cv == max_freq_cv)[0]

  # Range of x-coordinates
  try:
    x_range_cv2 = (np.min(x_coords_cv), np.max(x_coords_cv))
  except:
    x_range_cv2 =(0,0)
  return x_range_cv2

#射影により縦線の位置を特定
# imgには白黒反転した画像を入力
def v_line_check_bs(img):

  # Load the image in grayscale
  # Perform horizontal projection by summing up the pixels along the vertical axis
  projection = np.sum(img, axis=0)

  # Normalize projection to the range [0, 1]
  normalized_projection = projection / np.max(projection)

  # Determine the x-coordinates where the projection is above 50%
  threshold_indices = np.where(normalized_projection >= 0.4)[0]
  threshold_indices = threshold_indices[threshold_indices > 0]  # exclude 0

  # Calculate the range
  try:
    x_range_cv2 = (min(threshold_indices), max(threshold_indices))
  except:
    x_range_cv2 =(0,0)
  print('射影により縦線の位置を特定')
  cv2_imshow(img)
  print('xrange_cv2',x_range_cv2)
  return x_range_cv2


def noicelock_bs(img):
  r,c,stats_v,stats_v_first=get_rc_BS(img)
  cv2.rectangle(img, (0, 0), (stats_v_first-50, img.shape[0]), (255,255,255), cv2.FILLED)
  # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite('/home/ec2-user/syoutest/pys/pdf/content_1.7493.jpg', img)
  r,c,stats_v,stats_v_first=get_rc_BS(img)

  # cv2.rectangle(img, (0, 0), (c[0]-10, img.shape[0]), (255,0,0), cv2.FILLED)
  cv2_imshow(img)
  # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite('/home/ec2-user/syoutest/pys/pdf/content_1.7498.jpg', img)
  print('c',c)
  print('r',r)

  w=c[-1]-c[0]
  h=(r[-1]-r[0])/27
  print('w,h',w,h,c[-1],c[0])
  r_bs,c_bs,boxes=[],[],[]

  #r[0],r[-1]補正
  img1r,img2r=[],[]
  #r[0]補正に使用するエリアimg1r    #img[top : bottom, left : right]
  top=r[0]-int(h/2)
  bottom=r[0]+int(h/2)
  left=round(c[0]+w*2*0.118+40)
  right=round(c[0]+w*3*0.118-20)
  print('left,right',left,right)
  img1r=img[top : bottom, left : right]
  img1r_inv=255-img1r
  cv2_imshow(img1r_inv)
  # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite('/home/ec2-user/syoutest/pys/pdf/content_1.7518.jpg', img1r_inv)
  try:
    hosei_y=h_line_check_bs(img1r_inv)
  except:
    hosei_y=(0,0)
  print(hosei_y)
  r[0]=top+round((hosei_y[0]+hosei_y[1])/2)
  # print('r[0]',r[0])
  #r[-1]補正に使用するエリアimg2r
  top=r[-1]-int(h/2)
  bottom=r[-1]+int(h/2)
  left=round(c[0]+w*5*0.118+40)
  right=round(c[0]+w*6*0.118-20)
  img2r=img[top : bottom, left : right]
  img2r_inv=255-img2r
  cv2_imshow(img2r_inv)
  # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite('/home/ec2-user/syoutest/pys/pdf/content_1.7518.jpg', img1r_inv)
  try:
    hosei_y=h_line_check_bs(img2r_inv)
  except:
    hosei_y=(0,0)
  print(hosei_y)
  r[-1]=top+round((hosei_y[0]+hosei_y[1])/2)
  # print('r[-1]',r[-1])
  #補正後を適用
  h=(r[-1]-r[0])/27


  #数値エリアを連番で取得
  #行方向
  x1,x2,x3,x4=0,0,0,0
  for i in range(26):
    # r_bs.append(round(r[0]+h*(2+i)+10))
    top=round(r[0]+h*(2+i)+10)
    bottom=round(r[0]+h*(3+i))
    left1=round(c[0]+w*2*0.118)
    right1=round(c[0]+w*3*0.118)
    left2=round(c[0]+w*5*0.118)
    right2=round(c[0]+w*6*0.118)
    print('１左１右',left1,right1)
    #1列目左の補正エリア　imgl1
    img1l=255-img[top : bottom, left1-25 : left1+25]
    cv2_imshow(img1l)
    print('i,x1,v_line_check_bs(img1l)[1]',i,x1,v_line_check_bs(img1l)[1])
    x1=left1-25+v_line_check_bs(img1l)[1]
    print('x1_after',x1)
    #1列目右の補正エリア　imgl2
    img1r=255-img[top : bottom, right1-25 : right1+35]
    print('i,x2',i,x2)
    x2=right1-25+v_line_check_bs(img1r)[0]
    print('x2_after',x2)
    #2列目左の補正エリア　imgr1
    img2l=255-img[top : bottom, left2-25 : left2+25]
    # print('i,x3',i,x3)
    try:
      x3=left2-25+v_line_check_bs(img2l)[1]
    except:
      x3=left2
    #2列目右の補正エリア　imgr2
    img2r=255-img[top : bottom, right2-25 : right2+35]
    # print('i,x4',i,x4)
    try:
      x4=right2-25+v_line_check_bs(img2r)[0]
    except:
      x4=right2
    r_bs.append(round(r[0]+h*(2+i)))
    #列方向
    #1列目の左を補正
    c_bs.append([x1,x2,x3,x4])
    # c_bs.append(x1)
    # c_bs.append(x2)
    # c_bs.append(x3)
    # c_bs.append(x4)
  #最後の行分を追加
  r_bs.append(round(r[0]+h*(2+i)))
  c_bs.append([x1,x2,x3,x4])

  #数値エリアの(x,y)座標
  for i in range(26):
    boxes.append([c_bs[i][0]+15,r_bs[i],c_bs[i][1],r_bs[i+1]])
    boxes.append([c_bs[i][2]+15,r_bs[i],c_bs[i][3],r_bs[i+1]])
  # print(boxes)
  #"円"削除
  #
  for i in range(2):
    x1,y1,x2,y2=boxes[i]
    ptx=int(0.1*(x2-x1))+5
    pty=int(0.12*(x2-x1))-5
    xc1,yc1,xc2,yc2=x2-ptx,y1+8,x2+10,y1+pty
    cv2.rectangle(img, (xc1+8, yc1), (xc2, yc2-8), (255,255,255), cv2.FILLED)
    xc1,yc1,xc2,yc2=x1-ptx,y1+8,x1+10,y1+pty
    cv2.rectangle(img, (xc1, yc1), (xc2-15, yc2-8), (255,255,255), cv2.FILLED)
    # cv2.rectangle(img, (xc1+8, yc1), (xc2, yc2-8), (255,255,255), cv2.FILLED)


  #確認
  img2=img.copy()
  for box in boxes:
    x1,y1,x2,y2=box
    cv2.rectangle(img2, (x1, y1), (x2, y2), (255, 250,0), cv2.LINE_AA)
  #確認用（色付）
  # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite('/home/ec2-user/syoutest/pys/pdf/content_1.noisy.jpg', img2)

  return img,boxes





def noicelock(img):
    div='left'
    rdata,c_new_left,c_new_mid,c_new_right=[],[],[],[]
    original_image=cv2pil(img)
    img=enhanced(original_image)
    height,width,_=img.shape
    print(width,height)
    try:
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    except:
        gray =img
    # print(img.shape)
    # imshow(img,800,600)
    # cv2_imshow(img)
    #grayから細かいノイズを削除
    stats = get_stats(gray)
    # print('stats',stats[1:])
    color_img=cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for i, s in enumerate(stats[1:]):
        if s[4]<10:
            cv2.rectangle(color_img, (s[0], s[1]), (s[0]+s[2], s[1]+s[3]), (255, 255,255), cv2.FILLED)
    # print('color_img_after')
    cv2_imshow(color_img)
    gray=cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)
    #縦線横線取得用の画像
    kernel = np.ones((5,5),np.uint8)
    img_h,img_v=get_hv_line(img)
    try:
        r,c,stats_v=get_rc(img,div,img_h,img_v)
        # print('c--->',c)
    except:
        erosion1 = cv2.erode(img,kernel,iterations = 1)
        # imshow(erosion1,800,600)
        print('except')
        cv2_imshow(erosion1)
        r,c,stats_v=get_rc(erosion1,div,img_h,img_v)
    len_c=len(c)
    print('len(c)',len(c))
    # print('r:y',r)
    # print('c:x',c)
    #補正用画像
    kernel_size =7  # 半径 r に対して、カーネルサイズは 2r+1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    kernel_hv = np.ones((5,5), np.uint8)
    # kernel_hv[2, :] = 1
    # kernel_hv[:,2] = 1

    gray_hv = cv2.erode(gray, kernel_hv, iterations=1)

    # print('gray_hv')
    # cv2_imshow(gray_hv)

    #決算書の位置情報ix_end
    xyl=[]
    xym=[]
    xyr=[]
    #num_c[1]の射影 #num_c[3]の射影
    #射影範囲　(s1x1,s1y1,s1x2,s1y2),(s2x1,s2y1,s2x2,s2y2)

    #rの確認
    r_new,pt=check_r(r,0)
    print('r_new',r_new)
    #暫定c取得
    num_c0=check_c(c)
    print('num_c0',num_c0)
    #ｃの精査
    num_c=recheck_c(r,num_c0,gray)
    print('@@@num_c',num_c)
    pt0=int(pt*0.75)
    pt1=int(pt*0.75)
    pt2=int(pt*0.28)
    pt3=int(pt*0.78)
    ###20231204追加###

    #枠を初期化
    boxes,boxes_2,ix_str,ix_end,iy_str,iy_end=[],[],0,0,0,0

    ##左列
    # 数字の枠
    position='L'
    #行
    for j in range(16):
        if j==0 or j==6:
            adjust=pt3
        else:
            adjust=pt2
        #横線の調整
        # print('gray.shape',gray.shape)
        # cv2_imshow(gray)

        # print('座標',top-10,top+10,left+10,right-10)

        # print('横線の補正',hosei_y)
        #行補正（r_newの補正）
        #上の線を補正（上の線の±20）
        top,bottom,left,right=r_new[j]+adjust,r_new[j]+adjust+pt1,num_c[0],num_c[1]
        # print('bottom1',bottom,pt)
        # hosei_y=hosei(top-25,top+20,left-20,right+20,gray)
        hosei_y=hosei(top-25,top+20,left+40,right-40,gray_hv)
        # iy_str=top+hosei_y[0]-15
        iy_str=top+hosei_y[1]-25
        iy_str2=iy_str-10
        #下の線を補正
        a,b,c,d=bottom-20,bottom+20,left+40,right-40
        hosei_y=hosei(a,b,c,d,gray_hv)

        #文字枠用
        iy_end=bottom-20+hosei_y[0]
        #文字間消去用
        iy_end2=iy_end

        #縦線補正
        # print('position,j,iy_str,iy_end,num_c',position,j,iy_str,iy_end,num_c)
        c_new_left,_,_=reset_col_vline(position,j,iy_str,iy_end,num_c,img,img_h,img_v,len_c,pt)

        #列
        for i in range(8):
            ix_str=c_new_left[2*i]
            ix_end=c_new_left[2*i+1]
            # ix_end=c_new_left[2*i+1]
            ix_str2=c_new_left[2*i+1]
            # ix_str2=c_new_left[2*i+1]
            ix_end2=c_new_left[2*i+2]
            boxes.append([ix_str,iy_str,ix_end,iy_end])
            boxes_2.append([ix_str2,iy_str2,ix_end2,iy_end2])

            if i==0 :
                ix_str_str=ix_str
            if i==7 :
                ix_end_end=ix_end
        xyl.append([ix_str_str,iy_str,ix_end_end,iy_end])

    #真ん中の列
    position='M'
    # print(' ')
    # print(' ')
    # print(' ')
    # print('真ん中の列################################')
    #数字の枠
    # print(c_new_mid)
    # cv2_imshow(img_v)
    r_new,pt=check_r(r,1)

    for j in range(17):
        if j==16:
            adjust=pt3
        else:
            adjust=pt2
        # print('adjust',j,adjust)
        # print('num_c',num_c)

        # print('横線の補正',hosei_y)
        #行補正（r_newの補正）

        #上の線を補正（上の線の±15）
        top,bottom,left,right=r_new[j]+adjust,r_new[j]+adjust+pt1,num_c[2],num_c[3]
        # print('iy_str,left,right,pt',iy_str,left,right,pt)
        if j==16:
            hosei_y=hosei(top-40,top+40,left+40,right-40,gray_hv)
            iy_str=top+hosei_y[1]-40
            iy_str2=iy_str-5
        else:
            hosei_y=hosei(top-20,top+20,left+40,right-40,gray_hv)
            iy_str=top+hosei_y[1]-16
            iy_str2=iy_str-10
        #下の線を補正
        a,b,c,d=bottom-40,bottom+40,left+40,right-40
        hosei_y=hosei(a,b,c,d,gray_hv)


        if j==16:
            #文字枠用
            iy_end=bottom+hosei_y[0]-40
            #文字間消去用
            iy_end2=iy_end+20
        else:
            #文字枠用
            iy_end=bottom+hosei_y[0]-40
            #文字間消去用
            iy_end2=iy_end+15

        #縦線補正
        _,c_new_mid,_=reset_col_vline(position,j,iy_str,iy_end,num_c,gray_hv,img_h,img_v,len_c,pt)
        # print('c_new_mid',c_new_mid)

        for i in range(8):
            if i==0:
                ix_str=c_new_mid[2*i]+5
                ix_str2=c_new_mid[2*i+1]+2
            else:
                ix_str=c_new_mid[2*i]
                # ix_str=c_new_mid[2*i]-20
                ix_str2=c_new_mid[2*i+1]
            ix_end=c_new_mid[2*i+1]
            # ix_end=c_new_mid[2*i+1]+15
            ix_end2=c_new_mid[2*i+2]

            boxes.append([ix_str,iy_str,ix_end,iy_end])
            # iy_str2=r_new[j]+adjust
            # iy_end2=iy_str2+pt0
            boxes_2.append([ix_str2,iy_str2,ix_end2,iy_end2])
            if i==7 :
                xym.append([c_new_mid[0]+5,iy_str,ix_end,iy_end])

    #右の列
    position='R'
    # print(' ')
    # print(' ')
    # print(' ')
    # print('右の列################################')
    #数字の枠
    # print(c_new_right)
    r_new,pt=check_r(r,flg=2)
    for j in range(12):
        if j==11:
            adjust=pt3
        else:
            adjust=pt2

        # print('横線の補正',hosei_y)
        #行補正（r_newの補正）
        #上の線を補正（上の線の±15）
        # print('pt1,adjust********>>>',pt1,adjust)
        top,bottom,left,right=r_new[j]+adjust,r_new[j]+adjust+pt1,num_c[4],num_c[5]
        # print('top,bottom,adjust,pt1',top,bottom,adjust,pt1)
        hosei_y=hosei(top-15,top+20,left+40,right-40,gray_hv)
        if j==11:
            iy_str=top+hosei_y[1]-20
        else:
            iy_str=top+hosei_y[1]-17
        # print('iy_str',iy_str)
        #下の線を補正
        if j==11:
            a,b,c,d=bottom-15,bottom+40,left+40,right-40
        else:
            a,b,c,d=bottom-40,bottom+40,left+40,right-40
        hosei_y=hosei(a,b,c,d,gray_hv)

        if j==11:
            #文字枠用
            iy_end=bottom+hosei_y[0]-15
            #文字間消去用
            iy_end2=iy_end+10
        else:
            #文字枠用
            iy_end=bottom+hosei_y[0]-40
            #文字間消去用
            iy_end2=iy_end+10

        #縦線補正
        # c_new_right = num_x(num_c[4],num_c[5])
        _,_,c_new_right=reset_col_vline(position,j,iy_str,iy_end,num_c,gray_hv,img_h,img_v,len_c,pt)

        for i in range(8):
            ix_str=c_new_right[2*i]
            ix_end=c_new_right[2*i+1]
            ix_str2=c_new_right[2*i+1]
            ix_end2=c_new_right[2*i+2]
            #文字枠用
            if i<11:
                iy_str_=iy_str+4
                iy_end_=iy_end-14
            else:
                # print('i',i)
                iy_str_=iy_str
                iy_end_=iy_end+22
            boxes.append([ix_str,iy_str_,ix_end,iy_end_])
            #枠消し用
            if i==11:
                iy_str2=r_new[j]+adjust
                iy_end2=iy_str2+pt0
            else:
                iy_str2=r_new[j]+adjust
                iy_end2=iy_str2+pt0
            boxes_2.append([ix_str2,iy_str2,ix_end2,iy_end2])
            if i==7 :
                xyr.append([c_new_right[0],iy_str,ix_end,iy_end])


    # print(boxes)

    #■を描画
    img_2=img.copy()
    # 100pitchの縦線描画・確認用
    # for i in range(46):
    #   cv2.rectangle(img_2,(i*100+1,0),(i*100+1,3300),(0,255,0),3)
    #
    #白紙を作成
    dt,num_dt=[],[]
    white_image = np.full((height, width, 3), 255, dtype=np.uint8)
    for i,box in enumerate(boxes_2):
        #文字間消去用
        # if i==16*7:確認用
        x1,y1,x2,y2=box
        # print('box',box)
        cv2.rectangle(img_2, (x1-4, y1-4), (x2+6, y2+4), (255, 255,255), cv2.FILLED)
        # cv2.rectangle(img_2, (x1-4, y1-4), (x2+6, y2+4), (255, 0,0), cv2.FILLED)
    for i,box in enumerate(boxes):
        # if i==16*7:確認用
        x1,y1,x2,y2=box
        # print('box',box)
        # cv2.rectangle(img_2, (x1, y1), (x2, y2), (0, 0,255), 3)
        cv2.rectangle(img_2, (x1, y1), (x2, y2), (255, 255,255), 5)
        cv2.rectangle(img_2, (x1, y1-20), (x2, y1+1), (255, 255,255), cv2.FILLED)
        cv2.rectangle(img_2, (x1, y2-8), (x2, y2+15), (255, 255,255),cv2.FILLED)
        # cv2.rectangle(img_2, (x1, y1), (x2, y2), (255, 0,0), 5)
        # cv2.rectangle(img_2, (x1, y1-20), (x2, y1+5), (0, 0,255), cv2.FILLED)
        # cv2.rectangle(img_2, (x1, y2-8), (x2, y2+15), (0, 255,0),cv2.FILLED)
    ######ここから
    # print('img_2 縦線ノイズを消去')
    # cv2_imshow(img_2)
    for i,box in enumerate(boxes):
        x1,y1,x2,y2=box
        dt.append([8-i%8,x1,y1,x2,y2])

        if i % 8 ==7:
            sorted_dt = sorted(dt, key=lambda x: x[0])
            num_dt.append(sorted_dt)
            dt,sorted_d=[],[]

    #白紙に数字のみを転写
    color_img=img_2.copy()
    # color_img=cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    base,d,x2d,cnt,block,num_data=[],[],0,0,[],[]
    # print('num_dt',num_dt)
    for j,dt in enumerate(num_dt):
        cnt=cnt+1
        #左、中、右ブロックのx座標
        if cnt==1 or cnt==17 or cnt==34:
            # print('[dt[7][1],dt[0][1]]',[dt[7][1],dt[0][1]])
            block.append([dt[7][1],dt[0][1]])

        for d in dt:
            # print('d',d)
            i,x1,y1,x2,y2=d
            print("SSSSSS"+str(i)+"_"+str(y2-y1)+"_"+str(x2-x1))
            #縦方向の射影で縦線ノイズをカット★★★
            before_cut=[]
            if y2-y1<=0 or x2-x1<=0 :
                continue
            newimg=np.full((y2-y1, x2-x1, 3), 255, dtype=np.uint8)

            before_cut=np.full((y2-y1, x2-x1, 3), 255, dtype=np.uint8)
            before_cut=color_img[y1:y2,x1:x2]
            # if cnt==1 and i==7:
                # print('i,before_cut.shape*****',i,before_cut.shape)
                # cv2_imshow(before_cut)
                # fname='before_cut_'+str(cnt)+'_'+str(i)+'.jpg'
                # cv2.imwrite(fname,before_cut)
            cut_x=v_line_cut(before_cut,cut_ratio=0.78)
            # if cnt==1 and i==7:
            #   print('i,cut_x',i,cut_x)
            if len(cut_x)>0 :
                for ct in cut_x:
                    # print('ct',ct[0],ct[1],x1,x1+ct[0], x1+ct[1])
                    cv2.rectangle(color_img, (x1+ct[0], y1), (x1+ct[1]+1, y2), (255,255,255),  cv2.FILLED)
                    # cv2.rectangle(color_img, (x1+ct[0], y1), (x1+ct[1], y2), (0,0,255),  cv2.FILLED)
            # if cnt==1 :# or cnt==17 or cnt==34:
                # cv2_imshow(color_img)
            #縦方向のノイズをstatsによりカット
            before_cut_gray=cv2.cvtColor(before_cut, cv2.COLOR_RGB2GRAY)
            stats=get_stats(before_cut_gray)
            for st in stats:
                x,y,w,h,a=st
                if cnt ==9 and h<4 and w>10:
                    print('st',st)
                if x>0 and a<60 and w<6 :
                    # cv2.rectangle(color_img, (x1+x, y1+y), (x1+x+w, y1+y+h), (255,0,0), cv2.FILLED)
                    cv2.rectangle(color_img, (x1+x, y1+y), (x1+x+w, y1+y+h), (255,255,255), cv2.FILLED)

            newimg[0:y2-y1,0:x2-x1]=color_img[y1:y2,x1:x2]
            if cnt==38 :
                # print('newimg.shape',newimg.shape)
                print('i,cnt',i,cnt)
                cv2_imshow(newimg)
            try:
                x_start,x_end=largest_continuous_range_cv2(newimg)
                p_left,p_right=x_start,x2-x1-x_end
            except:
                x_start,x_end,p_left,p_right=0,0,0,0
            # print('x1,x_start,x2,x_end',x1,x_start,x2,x_end)
            # if i==8:
            #   print('x_start,x_end,p_left,p_right',x_start,x_end,p_left,p_right)
            #各列を右詰
            if i==1:
                x1d,x2d=x1+p_left,x2-p_right
                x1d_before,p_left_before=x1d,p_left
                # print('j,i,x1d,x2d,x1,x2',j,i,x1d,x2d,x1,x2,y1,y2)
                distance=0
            else:
                distance=distance+x1d_before-(x2-p_left_before)
                x2d=x1d_before-7
                if i==8:
                    x1d=x2d-(x2-x1)
                else:
                    x1d=x2d-((x2-p_right)-(x1+p_left))
                x1d_before=x1d
                # print('j,i,x1d,x2d,x1,x2',j,i,x1d,x2d,x1,x2,y1,y2)

            # if cnt==1 and i==7:
            # print('i,x1,x1d,x2,x2d',i,x1,x1d,x2,x2d)
            # cv2.rectangle(white_image, (x1d, y1), (x2d, y2), (0, 0,255), 3)
            # if cnt==1 and i==7:
            #   cv2_imshow(white_image)

            # print('x2d,x1d,x2-x1',x2d,x1d,x2-p_right,x1+p_left,)
            if i==8:
                white_image[y1:y2,x1d:x2d]=color_img[y1:y2,x1:x2]
            else:
                white_image[y1:y2,x1d:x2d]=color_img[y1:y2,x1+p_left:x2-p_right]
            num_data.append([x1d,y1,x2d,y2])
            #blockデータを取得
    # print('num_data',num_data)
    # print('block',block)
    #block座標を用いて水平方向に射影し、横方向のノイズをカット
    #左l_block
    l_block=white_image[0:height,block[0][0]:block[0][1]+50]
    # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite('aaa.jpg',l_block)
    resulting_ranges = vertical_projection_ranges(l_block)
    print('resulting_ranges',resulting_ranges)

    if len(resulting_ranges)>0:
        # print('横方向のノイズ消し（左）',len(resulting_ranges))

        for rr in resulting_ranges:
            if cnt ==9:
                print('rr********************',rr)
            cv2.rectangle(white_image, (block[0][0], rr[0]), (block[0][1]+50, rr[1]), (255, 255,255), cv2.FILLED)
            # cv2.rectangle(white_image, (block[0][0], rr[0]), (block[0][1]+50, rr[1]), (255, 0,0), cv2.FILLED)
            cnt=cnt+1

    #中m_block
    # print('block[1][0]',block[1][0])
    m_block=white_image[0:height,block[1][0]:block[1][1]+50]
    resulting_ranges = vertical_projection_ranges(m_block)
    if len(resulting_ranges)>0:
        # print('横方向のノイズ消し（中）',len(resulting_ranges))
        for rr in resulting_ranges:
            cv2.rectangle(white_image, (block[1][0], rr[0]), (block[1][1]+50, rr[1]), (255, 255,255), cv2.FILLED)
    #右block
    r_block=white_image[0:height,block[2][0]:block[2][1]+50]
    resulting_ranges = vertical_projection_ranges(r_block)
    if len(resulting_ranges)>0:
        # print('横方向のノイズ消し（右）',len(resulting_ranges))
        for rr in resulting_ranges:
            cv2.rectangle(white_image, (block[2][0], rr[0]), (block[2][1]+50, rr[1]), (255, 255,255), cv2.FILLED)
    cnt=0
    #１文字ずつ射影して横の余白を削る
    #文字がある範囲のx座標を取得する
    # for nd in num_data:
    #   x1,y1,x2,y2=nd
    #   cv2.rectangle(white_image, (x1, y1), (x2, y2), (0, 0,255), 3)

    #赤枠追加
    # for nd in num_data:
    #   x1,y1,x2,y2=nd
    #   cv2.rectangle(white_image, (x1, y1), (x2, y2), (0, 0,255), 3)
    return img_2,xyl,xym,xyr,white_image
#列方向cのチェックと正規化/★OCR書式外
def check_c2(c):
  chk=[0.215,0.332,0.547,0.667,0.879,1.000]
  # print('c***',c)
  # print('c[0],c[-1]',c[0],c[-1])
  # print('chk',chk)
  num_c=[]
  w = c[-1]-c[0]
  for i in range(6):
    #左中右列の開始と終了位置xの比率をc[0]とc[-1]から算出
    # print('chk[i]',chk[i])
    x = round(c[0] + chk[i] * w)
    num_c.append(x)
  # print('num_c',num_c)
  return num_c
def kojin_special_handling0(img) :
  #########　ＰＬ　###############
  #　数値の枠書込みPL　OCR書式外#
  ################################
  div='left'
  height,width,_=img.shape
  print(width,height)
  try:
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
  except:
    gray =img
  # print(img.shape)
  # imshow(img,800,600)
  #grayから細かいノイズを削除
  stats = get_stats_bs(gray)
  # print('stats',stats[1:])
  color_img=cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
  for i, s in enumerate(stats[1:]):
    if s[4]<10:
      cv2.rectangle(color_img, (s[0], s[1]), (s[0]+s[2], s[1]+s[3]), (255, 255,255), cv2.FILLED)
  # print('color_img_after')
  # cv2_imshow(color_img)
  gray=cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)
  #縦線横線取得用の画像
  kernel = np.ones((5,5),np.uint8)
  img_h,img_v=get_hv_line(img)
  try:
    r,c,stats_v=get_rc(img,div,img_h,img_v)
    print('c--->',c)
  except:
    erosion1 = cv2.erode(img,kernel,iterations = 1)
    # imshow(erosion1,800,600)
    print('except')
    r,c,stats_v=get_rc(erosion1,div,img_h,img_v)
    return r,c,stats_v,img_v

  # print('r:y',r)
  # print('c:x',c)
  #補正用画像
  kernel_size =7  # 半径 r に対して、カーネルサイズは 2r+1
  kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
  kernel_hv = np.ones((5,5), np.uint8)
  # kernel_hv[2, :] = 1
  # kernel_hv[:,2] = 1

  gray_hv = cv2.erode(gray, kernel_hv, iterations=1)

  # print('gray_hv')
  # cv2_imshow(gray_hv)


  #num_c[1]の射影 #num_c[3]の射影
  #射影範囲　(s1x1,s1y1,s1x2,s1y2),(s2x1,s2y1,s2x2,s2y2)

  #rの確認
  r_new,pt=check_r(r,0)
  print('r_new',r_new)
  #暫定c取得★
  num_c0=check_c2(c)
  print('num_c0',num_c0)

#枠を初期化
  boxes,boxes_2,ix_str,ix_end,iy_str,iy_end=[],[],0,0,0,0

  ##左列
  # 数字の枠
  position='L'
  #行　19分割
  #行の高さ
  row_h=int((r[-1]-r[0])/19)
  print('row_h',row_h)

# boxes作成
  pt_x,pt_y=30,30
  for i in range(16):
    ##左列
    ix_str=num_c0[0]+ pt_x
    ix_end=num_c0[1]-5
    if i==0:
      iy_str=int(r[1]+row_h*0.3)
      iy_end=int(iy_str+row_h*1.5)
    elif i>0 and i<6:
      iy_str=r[1]+row_h*(i+1)+pt_y
      iy_end=iy_str+row_h-pt_y
    elif i==6:
      iy_str=int(r[1]+row_h*7.3)
      iy_end=int(iy_str+row_h*1.5)
    elif i>6 and i<16:
      iy_str=r[1]+row_h*(i+2)+pt_y
      iy_end=iy_str+row_h-pt_y

    boxes.append([ix_str,iy_str,ix_end,iy_end])
  for i in range(16,33):
     ##中列
    ix_str=num_c0[2]+ pt_x
    ix_end=num_c0[3]-5
    if i<32:
      iy_str=r[1]+row_h*(i-16)+pt_y
      iy_end=iy_str+row_h-pt_y
    elif i==32:
      iy_str=int(r[1]+row_h*16.3)
      iy_end=int(iy_str+row_h*1.5)
    boxes.append([ix_str,iy_str,ix_end,iy_end])
  for i in range(33,45):
     ##右列
    ix_str=num_c0[4]+ pt_x
    ix_end=num_c0[5]-5
    if i<44:
      iy_str=r[1]+row_h*(i-33)+pt_y
      iy_end=iy_str+row_h-pt_y
    elif i==44:
      iy_str=int(r[1]+row_h*11.3)
      iy_end=int(iy_str+row_h*1.5)
    boxes.append([ix_str,iy_str,ix_end,iy_end])
  # print('boxes',boxes)
  for i in range(16):
    b=boxes[i]
    print('左列',b[1],b[3])

  #枠を描画
  img_2=img.copy()
  for i,box in enumerate(boxes):
    x1,y1,x2,y2=box
    # cv2.rectangle(img_2, (x1-4, y1-4), (x2+6, y2+4), (255, 0,0), cv2.FILLED)
    # cv2.rectangle(img_2, (x1-4, y1-4), (x2+6, y2+4), (255, 255,255), cv2.FILLED)
    cv2.rectangle(img_2,(x1,y1),(x2,y2),(255,0,0),3)
  cv2_imshow(img_2)

  #白紙に数字のみを転写
  # white_image = np.full((height, width, 3), 255, dtype=np.uint8)
  # for i,box in enumerate(boxes):
  return r,c,stats_v,boxes,img_2

def hikaku_characters_shikokub(source_characters) :
    if hikaku_characters(source_characters,"配偶者の合計所得金額",0.8) == False and hikaku_characters(source_characters,"申告書B",0.8) == False and hikaku_characters(source_characters,"特殊事情",0.8) == False and hikaku_characters(source_characters,"災害減免額",0.8) == False :
        return False
    else :
        return True

def enhanced(original_image):

  # Enhance the image by increasing contrast
  # This will make the image "sharper" and potentially improve readability
  enhancer = ImageEnhance.Contrast(original_image)
  enhanced_image = enhancer.enhance(2)  # increase contrast

  # Convert image to numpy array
  image_array = np.array(enhanced_image)

  # Apply threshold to set all values below 250 to 0 (black)
  # This will make the lighter parts of the image to become black and may enhance visibility of darker text
  thresholded_image_array = np.where(image_array < 250, 0, image_array)

  return thresholded_image_array

def cv2pil(image):
    ''' OpenCV型 -> PIL型 '''
    new_image = image.copy()
    if new_image.ndim == 2:  # モノクロ
        pass
    elif new_image.shape[2] == 3:  # カラー
        new_image = new_image[:, :, ::-1]
    elif new_image.shape[2] == 4:  # 透過
        new_image = new_image[:, :, [2, 1, 0, 3]]
    new_image = Image.fromarray(new_image)
    return new_image

def kojin_special_handling1(img) :
  #########　ＰＬ　###############
  #　数値の枠書込みPL　OCR書式外　前期有#
  ################################
  div='left'
  height,width,_=img.shape
  try:
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
  except:
    gray =img
  #grayから細かいノイズを削除
  stats = get_stats_hd1(gray)
  color_img=cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
  for i, s in enumerate(stats[1:]):
    if s[4]<10:
      cv2.rectangle(color_img, (s[0], s[1]), (s[0]+s[2], s[1]+s[3]), (255, 255,255), cv2.FILLED)
  gray=cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)
  #縦線横線取得用の画像
  kernel = np.ones((5,5),np.uint8)
  img_h,img_v=get_hv_line_hd1(img)
  try:
    r,c,stats_v=get_rc_hd1(img,div,img_h,img_v)
    print('c--->',c)
  except:
    erosion1 = cv2.erode(img,kernel,iterations = 1)
    print('except')
    cv2_imshow(erosion1)
    r,c,stats_v=get_rc_hd1(erosion1,div,img_h,img_v)
  #補正用画像
  kernel_size =7  # 半径 r に対して、カーネルサイズは 2r+1
  kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
  kernel_hv = np.ones((5,5), np.uint8)

  gray_hv = cv2.erode(gray, kernel_hv, iterations=1)


  #num_c[1]の射影 #num_c[3]の射影
  #射影範囲　(s1x1,s1y1,s1x2,s1y2),(s2x1,s2y1,s2x2,s2y2)

  #rの確認
  r_new,pt=check_r_hd1(r,0)
  print('r_new',r_new)
  #暫定c取得★
  num_c0=check_c3_hd1(c)

#枠を初期化
  boxes,boxes_2,ix_str,ix_end,iy_str,iy_end=[],[],0,0,0,0

  ##左列
  # 数字の枠
  position='L'
  #行　19分割
  #行の高さ
  row_h=int((r[-1]-r[0])/19)
  print('row_h',row_h)

# boxes作成
  pt_x,pt_y=30,30
  for i in range(16):
    ##左列
    ix_str=num_c0[0]+ pt_x
    ix_end=num_c0[1]-5
    if i==0:
      iy_str=int(r[1]+row_h*0.3)
      iy_end=int(iy_str+row_h*1.5)
    elif i>0 and i<6:
      iy_str=r[1]+row_h*(i+1)+pt_y
      iy_end=iy_str+row_h-pt_y
    elif i==6:
      iy_str=int(r[1]+row_h*7.3)
      iy_end=int(iy_str+row_h*1.5)
    elif i>6 and i<16:
      iy_str=r[1]+row_h*(i+2)+pt_y
      iy_end=iy_str+row_h-pt_y

    boxes.append([ix_str,iy_str,ix_end,iy_end])
  for i in range(16,33):
     ##中列
    ix_str=num_c0[2]+ pt_x
    ix_end=num_c0[3]-5
    if i<32:
      iy_str=r[1]+row_h*(i-16)+pt_y
      iy_end=iy_str+row_h-pt_y
    elif i==32:
      iy_str=int(r[1]+row_h*16.3)
      iy_end=int(iy_str+row_h*1.5)
    boxes.append([ix_str,iy_str,ix_end,iy_end])
  for i in range(33,45):
     ##右列
    ix_str=num_c0[4]+ pt_x
    ix_end=num_c0[5]-5
    if i<44:
      iy_str=r[1]+row_h*(i-33)+pt_y
      iy_end=iy_str+row_h-pt_y
    elif i==44:
      iy_str=int(r[1]+row_h*11.3)
      iy_end=int(iy_str+row_h*1.5)
    boxes.append([ix_str,iy_str,ix_end,iy_end])
  # print('boxes',boxes)
  for i in range(16):
    b=boxes[i]
    print('左列',b[1],b[3])

  #枠を描画
  img_2=img.copy()
  for i,box in enumerate(boxes):
    x1,y1,x2,y2=box
    # cv2.rectangle(img_2, (x1-4, y1-4), (x2+6, y2+4), (255, 0,0), cv2.FILLED)
    # cv2.rectangle(img_2, (x1-4, y1-4), (x2+6, y2+4), (255, 255,255), cv2.FILLED)
    cv2.rectangle(img_2,(x1,y1),(x2,y2),(255,0,0),3)
  cv2_imshow(img_2)

  #白紙に数字のみを転写
  # white_image = np.full((height, width, 3), 255, dtype=np.uint8)
  # for i,box in enumerate(boxes):

  #最も長い横線の範囲に縦線の範囲を収める
  #やや上部にある短めの線は除外する
  return r,c,stats_v,boxes,img_2
def get_stats_hd1(img):
  # 画像表示用に入力画像をカラーデータに変換する
  kernel2 = np.zeros((5,5), np.uint8)
  kernel2[:,2] = 1
  # gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
  gray2=255-img
  h,w=gray2.shape

  # ラベリング
  retval, labels, stats, centroids = cv2.connectedComponentsWithStats(gray2)
  stats=stats.tolist()
  stats=sorted(stats,key=lambda x:(x[0]))
  # stats=stats_split(stats,img)
  #結果表示
  # print('stats::',stats)
  gray,gray2=[],[]
  return stats

def get_hv_line_hd1(img):
  #画像を濃く
  grayimage = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
  #途切れをなくす
  # 二値化(二値化して白黒反転、下限値120が')'を読めるかポイント)
  retval, grayimage_inv = cv2.threshold(grayimage, 200, 255, cv2.THRESH_BINARY_INV)
  # クロージング処理（細切れ状態を防ぐため）
  kernelc = np.ones((3, 3), np.uint8)
  grayimage_inv = cv2.morphologyEx(grayimage_inv, cv2.MORPH_CLOSE, kernelc, iterations=3)
  grayimage=255-grayimage_inv.astype(np.uint8)
  print('after2')
  # cv2_imshow(grayimage)
  #kernel
  kernel = np.zeros((5,5), np.uint8)
  kernel[2, :] = 1
  kernel2 = np.zeros((5,5), np.uint8)
  kernel2[:,2] = 1

  grayimage2=grayimage.copy()

  #横線
  img_h = cv2.dilate(grayimage, kernel, iterations=15)
  img_h = 255-img_h
  #img_h>5の影響大
  img_h=np.where(img_h>50,255,0)
  img_h.astype('uint8')
  img_h = np.array(img_h, dtype=np.uint8)
  # img_h  = cv2.dilate(img_h, kernel3)
  #横線を太く
  # img_h = cv2.morphologyEx(img_h, cv2.MORPH_OPEN, kernel3)
  img_h=255-img_h
  # img_h = cv2.erode(img_h, kernel4, iterations=5)
  # print('4')
  # cv2_imshow(img_h)

  #縦線
  img_v = cv2.dilate(grayimage, kernel2, iterations=15)
  # print('v2')
  # cv2_imshow(img_v)
  img_v = 255-img_v
  # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite('img_v.jpg',img_v)
  #img_h>5の影響大
  img_v=np.where(img_v>10,255,0)
  img_v.astype('uint8')
  img_v = np.array(img_v, dtype=np.uint8)

  #縦線を太く
  # img_v = cv2.morphologyEx(img_v, cv2.MORPH_OPEN, kernel3)
  img_v=255-img_v
  # img_v = cv2.erode(img_v, kernel4, iterations=5)
  # print('img_v:**')
  # cv2_imshow(img_v)
  grayimage,grayimage2=[],[]
  return img_h,img_v


def get_rc_hd1(img,div,img_h,img_v):
    # print('get_rcのimg_h,img_v',img_h,img_v)
    # cv2_imshow(img_h)
    # cv2_imshow(img_v)
    #横線
    # img=cv2.imread(path)
    #横線の長さが書類の横幅の90%以上のものがあるか
    stats_h=get_stats(img_h)
    img_h=cv2.cvtColor(img_h, cv2.COLOR_BGR2RGB)
    width,height=stats_h[0][2],stats_h[0][3]
    y_s,x_s,r,c=[],[],[],[]
    xmin,xmax=100000,0
    # print('xmin,xmax',xmin,xmax)
    print('stats_h',stats_h)
    for i,s in enumerate(stats_h):
        #PL用の条件
        if s[0]<width*0.2 and s[2]>width*0.2 and s[2]<width*0.95 and s[1]>height*0.15 :
            y_s.append(s)
            cv2.line(img_h,pt1=(s[0], s[1]+s[3]),pt2=(s[0]+s[2],s[1]+s[3]),color=(255, 0, 0),thickness=5,lineType=cv2.LINE_4,shift=0)
            print('i,s[0],s[2]',i,s[0],s[2])
            if xmin>s[0]:
                xmin=s[0]
                # print('xmin:',i,xmin)
            if xmax<s[0]+s[2]:
                xmax=s[0]+s[2]
    print('xmin,xmax:',i,xmin,xmax)
    # print('y_s',y_s)
    if y_s==[]:
        pass
        # print('y_s',y_s)
    else:
        #左の列の横線を取得（xs>0,xe<0.2w)
        y_s_left=get_h_line_include_x(y_s,0,0.2*width)
        #yで並べ変え
        y_s_left_sorted=sorted(y_s_left, key = lambda x:x[1])
        print('len(y_s_left_sorted)',len(y_s_left_sorted))
        print(y_s_left_sorted)
        #rのy座標をプロット
        r=[]
        for i,ys in enumerate(y_s_left_sorted):
            xs,ye=ys[0],ys[1]-0
            txt='r'+str(i)+'='+str(ye)
            cv2_putText(img_h,txt,xs,ye)
            r.append(ye)
        #出力確認
        # print('r[0],r[-1]',r[0],r[-1])

        print('img_h')
        cv2_imshow(img_h)

    ################################################################
    #縦線　開始位置y>=r0-5　and y<r4 （若干の傾きを考慮し-5）

    stats_v=get_stats(img_v)
    # print('stats_v',stats_v)
    img_v=cv2.cvtColor(img_v, cv2.COLOR_BGR2RGB)
    ymin,ymax=100000,0
    # print('ymin0',ymin)
    for i,s in enumerate(stats_v):
        # print('s in stats_v:',s)
        # print('s[3]>height*0.1',s[3],height*0.1)
        # print('s[1]>height*0.2',s[1],height*0.2)
        # print('s[3]<height*0.75',s[1],s[3],height*0.75)
        # print('s[0]<width*0.98',s[0],width*0.98)
        #★PLすべてに共通の修正（20240411）s[3]>height*0.1→s[3]>height*0.2
        if s[3]>height*0.2 and s[1]>height*0.2  and s[1]<height*0.6 and s[3]<height*0.62 and s[0]<width*1:
            # if s[3]>height*0.2 and s[3]<height and s[0]>r[0]-5 and s[0]<r[4]:
            x_s.append(s)
            # print('縦線stats',s[0],s[2])
            cv2.line(img_v,pt1=(s[0]+s[2], s[1]),pt2=(s[0]+s[2],s[1]+s[3]),color=(0, 255, 0),thickness=10,lineType=cv2.LINE_4,shift=0)
            # print('i,s[1]',i,s[1])
            if ymin>s[1]:
                ymin=s[1]
            if ymax<s[1]+s[3] and s[0]<width*0.5:
                ymax=s[1]+s[3]
            # print('i,ymin',i,ymin)
    # print('ymin,ymax',ymin,ymax)
    # print('x_s',x_s)
    if x_s==[] or y_s==[] or r==[]:
        # print('y_s,x_s',y_s,x_s)
        return None
    else:

        #y方向でソートし最初と最後のyを取得
        x_s_sorted_y=sorted(x_s,key = lambda x:x[1])
        print('x_s_sorted_y',x_s_sorted_y)
        ys=x_s_sorted_y[0][1]
        ye=x_s_sorted_y[-1][1]
        ye=ys+int(0.42*(ye-ys))
        x_s_left=get_v_line_include_y(x_s,r[0]-5,ye)
        # print('len(x_s_left),x_s_left',len(x_s_left),x_s_left)
        #xで並べ変え
        x_s_left_sorted=sorted(x_s_left, key = lambda x:x[0])
        # print('x_s_left_sorted',x_s_left_sorted)
        #cのx座標をプロット
        c=[]
        print('**********')
        for i,xs in enumerate(x_s_left_sorted):
            xs,ye=xs[0],xs[1]
            txt='c'+str(i)+'='+str(xs)
            cv2_putText(img_v,txt,xs-60,ye-10)
            c.append(xs)
        #出力確認
        print('c[0],c[-1]',c[0],c[-1])
        cv2_imshow(img_v)
        # imshow(img_v,800,600)
        # cv2.imwrite('img_v.jpg',img_v)
        # print('c000',c)
        # print('ｒとｃ',len(r),len(c))

        #ｒからのyminの情報
        if r[0]>ymin:
            r[0]=ymin
        #ｒからのymaxの情報
        if r[-1]<ymax:
            # print('r[-1],ymax',r[-1],ymax)
            r[-1]=ymax
        #cからのxminの情報
        print('A:c[0],xmin',c[0],xmin)
        if c[0]>xmin:
            c[0]=xmin
            print('B:c[0],xmin',c[0],xmin)
        #cからのxmaxの情報
        if c[-1]<xmax:
            if len(c)<2:
                c.append(xmax+10)
            else:
                c[-1]=xmax+10
            print('c[-1],xmax',c[-1],xmax)
        #確認
        print('xmin,ymin,xmax,ymax',xmin,ymin,xmax,ymax)
        return r,c,stats_v

#ｒの確認
def check_r_hd1(r,flg):
  #左の列用
  if flg==0:
    chk=[0.053 ,0.159 ,0.21 ,0.266 ,0.318 ,0.371 ,0.422 ,0.527 ,0.581 ,0.634 ,0.687 ,0.74 ,0.792 ,0.845 ,0.895 ,0.95]
  #真ん中と右の列用
  elif flg==1 or flg==2:
    chk=[0.055,0.107,0.159,0.212,0.264,0.317,0.369,0.422,0.474,0.526,0.579,0.631,0.684,0.736,0.789,0.841,0.896,1]
  l,r_new=[],[]
  #高さ
  h=r[-1]-r[0]
  print('r-->',len(r),r)
  print('*',int((r[1]-r[0])/100))
  sum_r,pt,y=0,0,0
  for i in range(len(r)-1):
    row_d=round((r[i+1]-r[i])/100)
    l.append(row_d)
    # print('line',i,row_d)
    sum_r += row_d
  #行間の平均値pt
  pt =round((r[-1]-r[0]) / sum_r)
  # print('sum_r',sum_r)
  #pt=17の場合線が読めている
  # print('pitch',pt)
  # print('l',l)
  #左left
  # seikika=[1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1 ,1]
  # print('len(seikika左)',len(seikika),seikika)

  y = r[0]
  # print('sum_r',sum_r)
  # if(sum_r>=17):
  if flg==0:
    t=0
  elif flg==1:
    t=1
  elif flg==2:
    t=-4

  for j in range(16+t):
    #ｒの正規化（横線が足りない部分があれば補完）
    # print('seikika',j,seikika[j])
    # print('chk',chk[j])
    y = r[0] + round(h * chk[j])
    r_new.append(y)
  return r_new,pt

  #elif(pt<17): #visionAPIから数値のエリアを特定
  #  return r


#列方向cのチェックと正規化/★OCR書式外（前期あり）20240411追記
def check_c3_hd1(c):
  chk=[0.153,0.244,0.486,0.576,0.819,.909]
  # print('c***',c)
  # print('c[0],c[-1]',c[0],c[-1])
  # print('chk',chk)
  num_c=[]
  w = c[-1]-c[0]
  for i in range(6):
    #左中右列の開始と終了位置xの比率をc[0]とc[-1]から算出
    # print('chk[i]',chk[i])
    x = round(c[0] + chk[i] * w)
    num_c.append(x)
  # print('num_c',num_c)
  return num_c


def plot_labeling_box(img, labeling_box):
    RectColorRGB = (0, 255, 0)

    for i, lb in enumerate(labeling_box):
        aaa = 0
        for j, b in enumerate(lb):
            cv2.rectangle(img,(int(b[1]), int(b[2])),(int(b[1]+b[3]), int(b[2]+b[4])), RectColorRGB ,thickness=2)
            cv2.putText(img, f'{i}', (int(b[1])-8, int(b[2])+20), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(img, f'{j}', (int(b[1])-8, int(b[2])+44), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2, cv2.LINE_AA)