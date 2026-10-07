'''
解析エンジンベース
'''
ENGINE_VERSION = '005-BASE'

import cv2
import numpy as np
import math

from util.defines import *
from util.utility import *
from util.coordinate import Point, Bound

from google.cloud.vision_v1 import types
import pickle

import glob

import engine.pre_process_image as pre_process_image
# from .preprocess_image import preprocess_loaded_image

class engine(object):
    def __init__(self, start_date, main_version='', version=ENGINE_VERSION, id='non', debug_suffix=''):
        self.id     = id
        self.start_date = start_date
        self.main_version = main_version
        self.version = version
        self.debug_suffix = debug_suffix

        print( '-> engine({})'.format(self.version))
        debug_print('-> engine({})'.format(self.version),level=DEBUG_ROWS_INFO)

    def init_AI(self):
        pass

    # 文字列分割　KEYWORD & DATE & AMOUNT
    def keyword_split(self, texts):

        extacted_texts = []
        split_cnt = 0

        for r in texts:
            #if r['text'] == '注文金額':
            #    print('x')

            r['text'] = replace_amount_sig(r['text'])

            #debug_print('\n"{}"({},{},{},{}):{}'.format(r['text'],r['bounds'].get_left(),r['bounds'].get_top(),r['bounds'].get_right(),r['bounds'].get_bottom(),r['char_width']),level=DEBUG_BOUND_INFO)
            # KEYWORD分割
            for separator in self.separators_regex:

                if separator['keyword'] == REGEX_SEARCH_DATE:    # 日付
                    k_found = search_date(r['text'])
                elif separator['keyword'] == REGEX_SEARCH_AMOUNT:# 合計
                    k_found = search_amount(r['text'])
                else:                               # 正規表現
                    k_found = re.search(separator['keyword'], r['text'])

                if k_found:
                    str_len = len(r['text'])
                    char_width = r['bounds'].get_size()[0] / str_len

                    #sp = k_found.span(0)
                    #k = r['text'][sp[0]:sp[1]]
                    k = k_found.group()

                    # KEYWORDのみ？
                    if k == r['text']:
                        if separator['remove'] == True:
                            split_cnt += 1
                            break

                        continue

                    s = r['text'].split(k)

                    left    = r['bounds'].get_left()
                    top     = r['bounds'].get_top()
                    right   = left
                    bottom  = r['bounds'].get_bottom()

                    # 前
                    if s[0] != '':
                        n = {}
                        n['text'] = s[0]
                        right = left + char_width * len(s[0])
                        b = Bound(left=left, top=top, right=right, bottom=bottom)
                        n['bounds'] = b
                        n['char_width'] = r['char_width']
                        extacted_texts.append(n)

                        left = right

                    # KEYWORD
                    if separator['remove'] == False:
                        n = {}
                        n['text'] = k
                        right = left + char_width * len(k)
                        b = Bound(left=left, top=top, right=right, bottom=bottom)
                        n['bounds'] = b
                        n['char_width'] = r['char_width']
                        extacted_texts.append(n)

                        left = right

                    # 後ろ
                    try:
                        if s[1] != '':
                            n = {}
                            n['text'] = s[1]
                            right = left + char_width * len(s[1])
                            b = Bound(left=left, top=top, right=right, bottom=bottom)
                            n['bounds'] = b
                            n['char_width'] = r['char_width']
                            extacted_texts.append(n)

                            left = right
                    except:
                        None

                    split_cnt += 1

                    break
            else:
                n = {}
                n['text'] = r['text']
                n['bounds'] = r['bounds']
                n['char_width'] = r['char_width']
                extacted_texts.append(n)

        return split_cnt, extacted_texts

    # ファイル読み込み直後のイメージ前処理
    def preprocess_loaded_image(self, img, filename=None):
        return pre_process_image.del_yellow(img)
        # return self.remove_yellow_marker(img)
        # image_h, image_w = img.shape[0], img.shape[1]
        # img = cv2.resize(img , (int(image_w*1.5), int(image_h*1.5)))
        # return img

    # VisionAPI直前のイメージ前処理
    def preprocess_image(self, img, filename=None):
        # return self.remove_yellow_marker(img)
        # return self.remove_hahen_image_noise(img)
        return img

    # #黄色マーカー除去
    # def remove_yellow_marker(self, img):
    #     return del_yellow(img) # del_line_str_right.py

    # 画像のノイズ除去
    # def remove_hahen_image_noise(self, img):
    #     # count,aaa,bbb=0,0,0
    #     # 入力画像、テンプレート画像を読み込む。
    #     # img = cv2.imread("content_1.jpg")  # 入力画像
    #     # cv2_imshow(img)
    #     path = os.path.join(os.path.dirname(__file__),'hahen/*.jpg')

    #     files = glob.glob(path)         # 削除対象の画像を置くフォルダ
    #     print(files)
    #     for file in files:
    #         # テンプレートマッチングを行う。
    #         templ = cv2.imread(file)          #削除対象読込
    #         result = cv2.matchTemplate(img, templ, cv2.TM_CCOEFF_NORMED)
    #         # count+=1
    #         # print('count=',count,file)
    #         # 最も類似度が 0.9 以上の位置を取得する。
    #         ys, xs = np.where(result >= 0.92)

    #         # # 描画する。
    #         # dst = img.copy()
    #         # for x, y in zip(xs, ys):
    #         #     cv2.rectangle(
    #         #         dst,
    #         #         (x, y),
    #         #         (x + templ.shape[1], y + templ.shape[0]),
    #         #         color=(0, 255, 0),
    #         #         thickness=2,
    #         #     )
    #         # # cv2_imshow(dst)

    #         # 類似画像を消す
    #         dst2 = img.copy()
    #         for x, y in zip(xs, ys):
    #             print('file,x,y=',file,x,y)
    #             cv2.rectangle(
    #                 dst2,
    #                 (x, y),
    #                 (x + templ.shape[1], y + templ.shape[0]),
    #                 color=(255, 255, 255),
    #                 thickness=-1,
    #             )
    #             # aaa+=1
    #             # print('aaa=',aaa)
    #         img = dst2
    #         # cv2_imshow(dst2)


    # #　画像の置換（△→-）
    #     # 入力画像、テンプレート画像を読み込む。
    #     path2 = os.path.join(os.path.dirname(__file__),'triangle/*.jpg')
    #     files = glob.glob(path2)         # 削除対象の画像を置くフォルダ

    #     for file in files:
    #       # テンプレートマッチングを行う。
    #       templ = cv2.imread(file)          #削除対象読込
    #       result = cv2.matchTemplate(img, templ, cv2.TM_CCOEFF_NORMED)

    #       # 最も類似度が 0.9 以上の位置を取得する。
    #       ys, xs = np.where(result >= 0.92)

    #       # 描画する。
    #       # dst = img.copy()
    #       # for x, y in zip(xs, ys):
    #       #     cv2.rectangle(
    #       #         dst,
    #       #         (x, y),
    #       #         (x + templ.shape[1], y + templ.shape[0]),
    #       #         color=(0, 255, 0),
    #       #         thickness=2,
    #       #     )

    #       # 類似画像を消す
    #       dst2 = img.copy()
    #       for x, y in zip(xs, ys):
    #           cv2.rectangle(
    #               dst2,
    #               (x, y),
    #               (x + templ.shape[1], y + templ.shape[0]),
    #               color=(255, 255, 255),
    #               thickness=-1,
    #           )
    #           #マイナス表示
    #           cv2.rectangle(
    #               dst2,
    #               (x+4 , y+int(templ.shape[0]/2)-1),
    #               (x +templ.shape[1]-4,y+int(templ.shape[0]/2)+1),
    #               color=(0, 0, 0),
    #               thickness=-1,
    #           )
    #           print(file,x,y,templ.shape[1],templ.shape[0])

    #       # for x, y in zip(xs, ys):
    #       #   #マイナス表示
    #       #     cv2.rectangle(
    #       #         dst2,
    #       #         (x , y+int(templ.shape[0]/2)-2),
    #       #         (x +templ.shape[1],y+int(templ.shape[0]/2)+1),
    #       #         color=(0, 0, 0),
    #       #         thickness=-1,
    #       #     )
    #       #     print(file,x,y,templ.shape[1],templ.shape[0])
    #       img = dst2
    #       # bbb+=1
    #       # print('bbb',bbb)

    # #黄色マーカー除去
    #     #テンプレートマッチングを行う。
    #     before_color = [0, 204, 255]
    #     after_color = [255, 255, 255]
    #     before_color1 = [0, 180, 200]
    #     dst2[np.where((dst2 >= before_color1).all(axis=2))] = after_color

    # #erode
    #     kernel = np.zeros((3,3), np.uint8)
    #     dst2 = cv2.erode(dst2, kernel, iterations=1)

    #     return dst2



    # 画像の傾き検出
    # @return 水直からの傾き角度
    def get_degree(self, img):

        # vertical kernel to connect dot line to solid line
        kernel = np.zeros((5,5), np.uint8)
        kernel[:, 2] = 1

        img_th = img.copy()

        img_th = cv2.dilate(img_th, kernel, iterations=4)
        # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite("dilate.jpg",img_th)
        img_th = cv2.erode(img_th, kernel, iterations=2)
        # [pmj-aitext-1] Cloud Run では不要なデバッグ出力のためコメントアウト: cv2.imwrite("erode.jpg",img_th)

        gray_image = cv2.cvtColor(img_th, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_image,50,150,apertureSize = 3)
        minLineLength = 400
        maxLineGap = 40
        lines = cv2.HoughLinesP(edges,1,np.pi/180,100,minLineLength,maxLineGap)

        sum_arg = 0;
        count = 0;
        for line in lines:
            for x1,y1,x2,y2 in line:
                arg = abs(math.degrees(math.atan2((y2-y1), (x2-x1))))
                VERTICAL = 90
                DIFF = 20 # 許容誤差 -> -20 - +20 を本来の水直線と考える
                if arg > VERTICAL - DIFF and arg < VERTICAL + DIFF  and arg!=90:
                    sum_arg += arg;
                    count += 1
                    cv2.line(img,(x1,y1),(x2,y2),(0,255,0),2)

        if count == 0:
            return 0
        else:
            print(sum_arg,count,'lst')
            return ((sum_arg / count) - VERTICAL)*.8;

    def rotate_image(self, img, arg, rotate=None, filename=None):
        if abs(arg) !=0:
            #画像の中心を指定
            height = img.shape[0]
            #幅を定義
            width = img.shape[1]
            #回転の中心を指定
            center = (int(width/2), int(height/2))
            #getRotationMatrix2D関数を使用
            trans = cv2.getRotationMatrix2D(center, arg , 1)
            #print(trans)

            #アフィン変換
            image2 = cv2.warpAffine(img, trans, (width,height),borderValue=(255, 255, 255))

        else:
            image2 = img

        if rotate is not None:
            image2 = cv2.rotate(image2, rotate)

        #画像の保存
        if filename:
            cv2.imwrite(filename, image2)
            os.chmod(filename, FILE_PARMITION)

        return image2

    def revise_tilt(self, img, filename=None):
        img_th = img.copy()

        #横方向用ウカーネル
        a1=np.zeros((1, 5),np.uint8)
        a2=np.ones((1, 5), np.uint8)
        kernel=np.concatenate([a1,a1, a2,a1, a1])

        #膨張・収縮
        img_th = cv2.dilate(img_th, kernel, iterations=10)
        #cv2.imwrite("dilate.jpg",img_th)
        img_th = cv2.erode(img_th, kernel, iterations=10)
        erode=img_th

        # gray処理
        im =img_th
        im_gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        retval, im_bw = cv2.threshold(im_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 輪郭の検出
        contours, hierarchy = cv2.findContours(im_bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        #横長の最大を探す
        max_w=0
        sum_arg=0
        count=0
        i_max = 0
        for i in range(len(contours)):
            x, y, w, h = cv2.boundingRect(contours[i])

            arg = math.degrees(math.atan2(h,w))
            if y>300 and y<2700:
                #print(i,arg)
                sum_arg += arg
                count += 1
                if w>max_w:
                    max_h=h
                    max_w=w
                    x_max=x
                    y_max=y
                    #print(max_h,max_w,x_max,y_max)
                    i_max=i

        ##確認用
        #print('i,w,h,x,y',i_max,max_w,max_h,x_max,y_max)
        #print('ave_arg',sum_arg/count)

        ##以下は確認用なので実装時はコメントアウト願います
        #print(max_h,max_w,x_max,y_max)
        ##cv2.rectangle(erode, (x_max, y_max), (x_max + max_w, y_max + max_h), (0, 255, 0), 1)
        ##cv2.imwrite("erode.jpg",erode)
        #cv2.rectangle(img, (x_max, y_max), (x_max + max_w, y_max + max_h), (0, 255, 0), 1)
        #cv2.imwrite("img.jpg",img)

        arg = 0
        try: # エラーが発生した場合は回転処理をしない
            # 最も大きい輪郭に外接矩形を作成し、画像に重ね書き
            rect = cv2.minAreaRect(contours[i_max])
            box = cv2.boxPoints(rect)
            box = np.int0(box)

            ##確認用
            #img_gaisetu = cv2.drawContours(img,[box],0,(0,0,255),1)
            ##cv2.imwrite('gaisetu.jpg',img_gaisetu)

            # 外接矩形の座標、回転角の表示
            #print('外接矩形の座標')
            #print(box)
            #print('回転角:')
            arg = rect[2]
            if arg < -135:
                arg += 180
            if arg < -45:
                arg += 90
            elif arg > 135:
                arg -= 180
            elif arg > 45:
                arg -= 90
            #if arg < -80:
            #    arg += 90
            #elif arg > 80:
            #    arg -= 90
            #print(arg)
        except:
            arg = 0

        #回転
        image2 = self.rotate_image(img,arg,None,filename)
        # if abs(arg) !=0:
        #     #画像の中心を指定
        #     height = img.shape[0]
        #     #幅を定義
        #     width = img.shape[1]
        #     #回転の中心を指定
        #     center = (int(width/2), int(height/2))
        #     #getRotationMatrix2D関数を使用
        #     trans = cv2.getRotationMatrix2D(center, arg , 1)
        #     #print(trans)

        #     #アフィン変換
        #     image2 = cv2.warpAffine(img, trans, (width,height),borderValue=(255, 255, 255))

        # else:
        #     image2 = img

        # #画像の保存
        # if filename:
        #     cv2.imwrite(filename, image2)
        #     os.chmod(filename, FILE_PARMITION)

        table_bound = None # self.find_table_area(image2) # 未使用

        return image2, contours, arg, table_bound

    def cache_read(self, vsn_file):
        response = None
        cash_data = None
        try:
            if os.path.exists(vsn_file):
                with open(vsn_file, mode='rb') as f:
                    #vsn_response = f.read()
                    #response = AnnotateImageResponse.deserialize(vsn_response)
                    response = pickle.load(f)
                # os.chmod(vsn_file, FILE_PARMITION)

            if type(response) == dict:
                # 通常のresponseに分離
                cash_data  = response
                response = response['response']

        except Exception as e:
            print(str(e))

        return response, cash_data

    def cache_write(self, vsn_file, response, cache_data=None):
        try:
            with open(vsn_file, mode='wb') as f:
                #vsn_response = AnnotateImageResponse.serialize(response)
                #f.write(vsn_response)
                if cache_data is None:
                    pickle.dump(response,f)
                else:
                    cache_data['response'] = response
                    pickle.dump(cache_data,f)

        except Exception as e:
            print(str(e))
        finally:
            os.chmod(vsn_file, FILE_PARMITION)


    # キャッシュファイル名
    def get_cache_file_name(self, file_name):
        vsn_file = os.path.splitext(file_name)[0] + CACHE_FILE_EXT
        return vsn_file

    # VisionAPIもしくはキャッシュ(vsn)から内部データへ
    def get_text_detection(self, no, img, file_name, client, def_cache_data=None, force_detection=False):

        source_texts = []
        source_characters = []

        vsn_file = self.get_cache_file_name(file_name)
        response, cache_data = self.cache_read(vsn_file)

        if response == None or force_detection == True:

            # 直前のイメージ前処理
            img = self.preprocess_image(img, file_name)

            # ファイルを介さずメモリ上のjpgイメージを渡すように変更
            # Loads the image into memory
        #     with io.open(file_name+'.tilt.jpg', 'rb') as image_file:
        # #    with io.open(file_name, 'rb') as image_file:
        #         content2 = image_file.read()
            # メモリ上のイメージをjpgエンコード
            _, content = cv2.imencode('.jpg', img)
            content = content.tobytes()
            image = types.Image(content=content)

            # response = client.text_detection(image=image,image_context={"language_hints":["ja"]})
            # response = client.text_detection(image=image,image_context={"language_hints":["ja-t-i0-handwrit"]})
            #response = client.document_text_detection(image=image)
            # response = client.document_text_detection(image=image,image_context={"language_hints":["ja"]})
            response = client.document_text_detection(image=image,image_context={"language_hints":["ja-t-i0-handwrit"]})

            cache_data = def_cache_data
            self.cache_write(vsn_file, response, cache_data)

        text_annotations = response.text_annotations

        debug_print( 'text_annotation({}) -->'.format(no),level=DEBUG_STR_INFO)
        for cnt, item in enumerate(text_annotations):
            if cnt <= 0:
                continue

            text = {}
            text['text'] = item.description
            text['bounds'] = Bound(item.bounding_poly.vertices)
            debug_print( '{}\t{}\t{}\t{}\t{}'.format(item.description,text['bounds'].get_left(),text['bounds'].get_top(),text['bounds'].get_right(),text['bounds'].get_bottom()),level=DEBUG_STR_INFO)
            #debug_print( '{}({},{})({},{})'.format(item.description,text['bounds'].get_left(),text['bounds'].get_top(),text['bounds'].get_right(),text['bounds'].get_bottom()),level=DEBUG_STR_INFO)

            source_texts.append(text)
        debug_print( 'text_annotation({}) <--'.format(no),level=DEBUG_STR_INFO)

        if True: #self.character_bound or self.character_center:
            debug_print( 'full_text_annotation({}) -->'.format(no),level=DEBUG_CHAR_INFO)
            document = response.full_text_annotation
            for page in document.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            for symbol in word.symbols:
                                text = {}
                                text['text'] = symbol.text
                                text['bounds'] = Bound(symbol.bounding_box.vertices)

                                debug_print( '{}\t{}\t{}\t{}\t{}'.format(symbol.text,text['bounds'].get_left(),text['bounds'].get_top(),text['bounds'].get_right(),text['bounds'].get_bottom()),level=DEBUG_CHAR_INFO)
                                #debug_print( '{}({},{})({},{})'.format(symbol.text,text['bounds'].get_left(),text['bounds'].get_top(),text['bounds'].get_right(),text['bounds'].get_bottom()),level=DEBUG_CHAR_INFO)

                                source_characters.append(text)
            debug_print( 'full_text_annotation({}) <--'.format(no),level=DEBUG_CHAR_INFO)

        return source_texts, source_characters, response, cache_data, None, None # None = imgの変更は無い

    def Texts(self):

        ret_papers = []   #　空のTEXT項目リスト

        for paper in self.papers:
            debug_print('Text:{}'.format(paper['path']),level=DEBUG_BOUND_INFO)

            r = {}
            r['path']   = paper['path']

            if self.analyze == ANALYZE_get_all_text:
                t = ''
                b = []
                for text in paper['texts']:
                    debug_print('\n"{}" {}'.format(text['text'], text['bounds'].get_rect()),level=DEBUG_BOUND_INFO)

                    t += (text['text'] + '\n')
                    b.append(text['bounds'].get_bound())

                r['text']   = t
                r['points'] = b

            if self.character_bound or self.character_center:
            #if self.analyze == ANALYZE_get_all_character or self.character_bound or self.character_center:
                characters = []
                for character in paper['characters']:
                    c = {}
                    c['text'] = character['text']

                    c['pos'] = {}
                    if self.character_bound:
                        c['pos'].update(character['bounds'].get_bound())
                    if self.character_center:
                        c['pos'].update(character['bounds'].get_center())

                    characters.append(c)

                r['characters'] = characters

            ret_papers.append(r)

        self.outData['root_str']                    = self.root_str
        self.outData['number_of_images']            = self.number_of_images
        self.outData['open_page_list']              = self.open_page_list
        self.outData['analyze']                     = self.analyze
        self.outData['calibration']                 = self.out_calibration
        #self.outData['format_info']                 = {}
        #self.outData['format_info']['format_id']    = self.inData['format_info']['format_id']
        self.outData['papers']                      = ret_papers

    def ChangeDatabase(self):
        return 0

    def OpenPapers(self):

        if self.analyze == ANALYZE_change_database:
            self.ChangeDatabase()

        if self.analyze != ANALYZE_version:
            # Cloud VisionでOCRを実行
            self.OCR()

            if self.analyze == ANALYZE_get_all_text or self.analyze == ANALYZE_get_all_character: # if self.analyze == 0: # OCRのみ
                self.Texts()
            elif self.analyze == ANALYZE_analysis_by_format: #elif self.analyze == 1: # 解析
              if self.document_judgment_flag == 'lines' :
                recode = self.Analyze_lines()
                self.outData['recode'] = recode
              elif self.document_judgment_flag == 'kojin' or self.document_judgment_flag == 'konjinaoiro' or self.document_judgment_flag == 'konjinshiroiro' :
                self.Analyze_kojin()
                try:
                    a=1
                    #self.Analyze_kojin()
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    debug_print("err is :::",level=DEBUG_ROWS_INFO)
                    debug_print(e,level=DEBUG_ROWS_INFO)
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
                    cl1.append(["外注工賃",1,2,2,1,6,-1])
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
                    cl1.append(["青色申告特別控除前の所得金額",2,70,3,2,9,-1])
                    cl1.append(["青色申告特別控除額",1,10,0,0,1,-1])
                    cl1.append(["所得金額",1,11,0,0,-7,-1])
                    for cls1 in cl1 :
                        r = {}
                        r['col_id']         = "n"+str(i)
                        r['col_name']       = "n"+str(i)
                        r['itask_form_id']  = 99999
                        candidate=[]
                        if cl1[i] is not None :
                            candidate_sub={}
                            candidate_sub["order"]=cls1[1]
                            candidate_sub["family"]=cls1[2]
                            candidate_sub["genus"]=cls1[3]
                            candidate_sub["species"]=cls1[4]
                            candidate_sub["variety"]=cls1[5]
                            candidate_sub["property"]=cls1[6]
                            candidate_sub["variety_name"]=cls1[0]
                            candidate.append(candidate_sub)
                            if cl1[i][2]==999 :
                                r["kotei"]="m1_"+str(i)
                            else :
                                r["kotei"]="kotei_1_"+str(i)
                        r["candidate"]=candidate
                        r["amount_pre_year"]=""
                        r["amount_this_year"]=""
                        r["db_exist"]="1.00"
                        r["start_x"]=0
                        r["start_y"]=0
                        r["end_x"]=0
                        r["end_y"]=0
                        r["tabindex"]=2
                        r["page"]=1
                        ret_cols.append(r)
                    cl2=[]
                    cl2.append(["現金",2,10,1,1,6,1])
                    cl2.append(["当座預金",2,10,1,1,13,1])
                    cl2.append(["定期預金",2,10,1,1,15,1])
                    cl2.append(["その他の預金",2,10,1,1,42,1])
                    cl2.append(["受取手形",2,10,2,3,1,1])
                    cl2.append(["売掛金",2,10,2,0,7,1])
                    cl2.append(["有価証券",2,10,1,3,1,1])
                    cl2.append(["棚卸資産",2,10,3,1,-1,1])
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
                    for cls2 in cl2 :
                        r = {}
                        r['col_id']         = "n"+str(i)
                        r['col_name']       = "n"+str(i)
                        r['itask_form_id']  = 99999
                        candidate=[]
                        candidate_sub={}
                        candidate_sub["order"]=cls2[1]
                        candidate_sub["family"]=cls2[2]
                        candidate_sub["genus"]=cls2[3]
                        candidate_sub["species"]=cls2[4]
                        candidate_sub["variety"]=cls2[5]
                        candidate_sub["property"]=cls2[6]
                        candidate_sub["variety_name"]=cls2[0]
                        candidate.append(candidate_sub)
                        if cl2[i][2]==999 :
                            r["kotei"]="m2_"+str(i)
                        else :
                            r["kotei"]="kotei_2_"+str(i)
                        r["candidate"]=candidate
                        r["amount_pre_year"]=""
                        r["amount_this_year"]=""
                        r["db_exist"]="1.00"
                        r["end_x"]=0
                        r["end_y"]=0
                        r["start_x"]=0
                        r["start_y"]=0
                        r["tabindex"]=1
                        r["page"]=1
                        ret_cols.append(r)
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
                    r["amount_this_year"]=""
                    r["db_exist"]="1.00"
                    r["start_x"]=0
                    r["start_y"]=0
                    r["end_x"]=0
                    r["end_y"]=0
                    r["tabindex"]=3
                    r["page"]=1
                    r["kotei"]="kotei_3_"+str(i)
                    ret_cols.append(r)

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
                
              else:
                self.Analyze()

        return 0

    def getResultJson(self):
        self.outData['version'] = f'{self.main_version}+{self.version}'
        return self.outData

