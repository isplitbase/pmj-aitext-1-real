
if False:
    #Release #if True:
    DEBUG_PRINT_LEVEL = 999 # Release
    DEBUG_BOUND_INFO = 0
    #DEBUG_PRINT_LEVEL_MAIN = 100
    DEBUG_STR_INFO = 0
    DEBUG_CHAR_INFO = 0
    DEBUG_ROWS_INFO = 0

    DEBUG_PRINT = 0
    DEBUG_PRINT_IN_JSON = 0
    DEBUG_PRINT_OUT_JSON = 0

    DEBUG_PRINT_TO_FILE = False
    DEBUG_FILE_FIX_NAME = True

else:
    #Debug #if False:
    DEBUG_PRINT_LEVEL = 10   # Debug
    DEBUG_BOUND_INFO = 0
    #DEBUG_PRINT_LEVEL_MAIN = 100
    DEBUG_STR_INFO = 10
    DEBUG_CHAR_INFO = 10
    DEBUG_ROWS_INFO = 10

    DEBUG_PRINT = 10

    DEBUG_PRINT_IN_JSON = 10
    DEBUG_PRINT_OUT_JSON = 10

    DEBUG_PRINT_TO_FILE = True #False
    DEBUG_FILE_FIX_NAME = False # 水野さん

AI_KERAS_PROCESS = False # True
AI_GINZA_PROCESS = False #True

PROPN_ADDR    = 1 # 住所
PROPN_COMPANY = 2 # 会社
PROPN_NAME    = 3 # 名前
PROPN_DATE    = 4
PROPN_OTHER   = 5 # 上記以外

# 解析コマンド
ANALYZE_get_all_text        = 'get_all_text'
ANALYZE_analysis_by_format  = 'analysis_by_format'
ANALYZE_get_all_character   = 'get_all_character'
ANALYZE_change_database     = 'change_database'
ANALYZE_version             = 'version'

REGEX_SEARCH_DATE     = '__@REGEX_SEARCH_DATE'      # 日付検索
REGEX_SEARCH_AMOUNT   = '__@REGEX_SEARCH_AMOUNT'    # 金額検索
REGEX_SEARCH_NUMBER   = '__@REGEX_SEARCH_NUMBER'    # ゆるい数字検索（金額を含めカンマ無の数字、電話番号、郵便番号）
REGEX_SEARCH_NON      = '__@REGEX_SEARCH_NON'       # 指定無し

WORD_SPLIT_OPT_NON          = 0

WORD_SPLIT_OPT_ADDR         = 10      # 住所:14,15
WORD_SPLIT_OPT_DATE         = 20      # 日付:12,13

WORD_SPLIT_OPT_AREA         = 30      # 面積:16,17
#WORD_SPLIT_OPT_TERM         = 31     # 期間:18,19
WORD_SPLIT_OPT_TERM_MONTH   = 31      # 期間(月):18,19
WORD_SPLIT_OPT_TERM_PRIOR   = 32      # 期間(前):20,21
WORD_SPLIT_OPT_TERM_YEAR_MONTH = 33   # 期間(旧):24,25　[復活]WORD_SPLIT_OPT_TERM
WORD_SPLIT_OPT_UNIT         = 35      # 単位:22,23
WORD_SPLIT_OPT_UNIT_BUILDING = 36     # 単位:26,27     階、F、号室

WORD_SPLIT_OPT_ARTICLE      = 50      # :28,29     条文を全文
WORD_SPLIT_OPT_CONTRACT_INFO= 60      # :30,31     会社名・氏名（組織）・住所
WORD_SPLIT_OPT_CONTRACT_NAME= 61      # :32,33     甲・乙・丙


WORD_SPLIT_OPT_YEN          = 81      # 金額(円):8,9
WORD_SPLIT_OPT_AMOUNT       = 82      # 金額:10,11
WORD_SPLIT_OPT_TEL          = 83      # 電話:
WORD_SPLIT_OPT_ZIP          = 84      # 郵便:
WORD_SPLIT_OPT_NUMBER       = 89      # 数値:

WORD_SPLIT_OPT_REGEX         = 99

WORD_SPLIT_DONE_NON         = 0x00
WORD_SPLIT_DONE_ADDRESS     = 0x01
WORD_SPLIT_DONE_ALL         = 0x10

# conditions_id -> WORD_SPLIT_OPTに変換　int(x/2)
CONDITION_TO_WORD_OPT = [0, 0, 0, 0,
                         WORD_SPLIT_OPT_YEN, WORD_SPLIT_OPT_AMOUNT,
                         WORD_SPLIT_OPT_DATE, WORD_SPLIT_OPT_ADDR,
                         WORD_SPLIT_OPT_AREA, WORD_SPLIT_OPT_TERM_MONTH,
                         WORD_SPLIT_OPT_TERM_PRIOR, WORD_SPLIT_OPT_UNIT,
                         WORD_SPLIT_OPT_TERM_YEAR_MONTH,WORD_SPLIT_OPT_UNIT_BUILDING,
                         WORD_SPLIT_OPT_ARTICLE, WORD_SPLIT_OPT_CONTRACT_INFO,
                         WORD_SPLIT_OPT_CONTRACT_NAME]

CONDITION_FIND_TYPE_AFTER  = [8,10,12,14,16,18,20,22,24,26,28,30,32]
CONDITION_FIND_TYPE_BEFORE = [9,11,13,15,17,19,21,23,25,27,29,31,33]

# 派生クラス固有のcondition_id 100以上
SPECIAL_CONDITION_ID = 100

# 縦の縮小 find_rows()の串刺し処理で使用
DEFAULT_FIND_ROWS_SCALE = 0.35

# KEYWORD 単位指定
KEYWORD_OPT_PRIOR    = '~'  # 優先
KEYWORD_OPT_SPECIFIC = '!'  # 限定

# 明細行の列見出し
BOX_HEADING_TYPE_NON        = 0
BOX_HEADING_TYPE_STR        = 1 # 文字列(商品名)
BOX_HEADING_TYPE_QUANTITY   = 2 # 数量
BOX_HEADING_TYPE_AMOUNT     = 3 # 金額


CSV_CHAR_CODE = 'cp932'
PDF_ENCODING = 'UTF-8'
PDF_FILE_EXT = '.PDF'

CACHE_FILE_EXT = '.vsn'

TILT_FILE = '.tilt.jpg'
ADJUST_FILE = '.adjust.jpg'

DEBUG_FILE_PATH       = '/var/www/tmp/'
# DEBUG_PRINT_FILE_PATH = '/home/ec2-user/apache/debug_file_v1.txt' # apacheのwriteパーミッションが必要
DEBUG_PRINT_FILE_NAME = '/var/www/tmp/debug_file' # apacheのwriteパーミッションが必要
DEBUG_PRINT_FILE_PATH = '/var/www/tmp/' # apacheのwriteパーミッションが必要
DEBUG_PRINT_FILE_EXT  = '.txt'

FILE_PARMITION = 0o666

# 数字の誤認識対策
NORMALIZE_DICTIONARY = str.maketrans({'i':'1', 'I':'1', 'l':'1', 'B':'8', 'b':'6', 'O':'0', 'o':'0', '。':'0', 'Z':'2', 'A':'4', 'E':'6', 'S':'5'})
