# Ver.008

import cv2
#from google.colab.patches import cv2_imshow
import numpy as np
# from IPython.display import Image, display
# from matplotlib import pyplot as plt
import glob
import gc
def _cv2_imshow(img):
    # cv2_imshow(img)
    pass
def _cv2_imwrite(fname,img):
  # cv2.imwrite(fname,img)
    pass
def _print(*txt):
    # print(txt)
    pass

import os
# サンプル画像のパスを生成
def _get_sample_img_path(fname):

    # 水野さんの単体debugではこちらをコメントにして
    return os.path.join(os.path.dirname(__file__),fname)

    # こちらを使用してください（呼び出し側を変更する必要はありません）
    # return f'/content/{fname}'

# v2ac 画像読み込み直後の処理 tilt より前の処理を書いてください
def preprocess_loaded_image_v2ac(img):
    #マーカー除去
    img = del_yellow(img)
    return img

# v2ac 画像の処理 tilt より後、del_line_str_rightより前の処理を書いてください
def preprocess_image_v2ac(img):
    #マーカー除去
    img = del_yellow(img)
    img_bk = img.copy()

    #地色除去
    img = del_gr_color(img)
    #file_name='/home/ec2-user/pdf/'
    #filename0 = file_name + '_img0.jpg'
    #print('filename0---->',filename0)
    #cv2.imwrite(filename0, img)

    return img, img_bk

def del_yellow(img):
  # _cv2_imshow(img)
  result=img.copy()
  # 黄色除去
  after_color = [255, 255, 255]
  before_color1 = [0, 140, 180]
  result[np.where((result >= before_color1).all(axis=2))] = after_color
  # _cv2_imshow(result)
  del img
  return result

def del_gr_color(result):
  # 地色除去
  ave=np.mean(result)
  _print('ave=',ave)

  # 地色の平均値によって処理を分岐
  if ave <210:
    p=150
    # _print('ave <210')
  elif ave>=210 and ave <220:
  # 24#用
    p=160
    # print('ave>=210 and ave <220')
  elif ave>=220 and ave <230:
    p=170
    # print('ave>=220 and ave <230')
  elif ave>=230 and ave <240:
    p=250
    # print('ave>=230 and ave <240')
  elif ave>=240 and ave <250:
    p=250
    _print('ave>=240 and ave <250')
  elif ave>=250 :
    p=-1
    # print('ave>=250')
  if p>=0:
    after_color = [255, 255, 255]
    before_color1 = [p, p, p]
    result[np.where((result >= before_color1).all(axis=2))] = after_color

  # 薄い文字をクリアに
  # result=cleary2(result, clip_limit=3, grid=(8, 8), thresh=225)
  if p==-1:
    result=cleary2(result, clip_limit=3, grid=(8, 8), thresh=225)
    for i in range(100):
      result=cleary(result, clip_limit=3, grid=(8, 8), thresh=225)
    result=np.where(result<253,0,result)
    result=cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
  _print('ave2=',np.mean(result))

  # result = clear_image(result)
  _cv2_imwrite('result.jpg',result)
  _cv2_imshow(result)
  return result

def make_sharp_kernel(k: int):
  return np.array([
    [-k / 9, -k / 9, -k / 9],
    [-k / 9, 1 + 8 * k / 9, k / 9],
    [-k / 9, -k / 9, -k / 9]
  ], np.float32)

def clear_image(img):

  kernel = make_sharp_kernel(1)
  img = cv2.filter2D(img, -1, kernel).astype("uint8")
  img2 = 255-img

  # カーネルを作成する。
  kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

  dst = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel, iterations=2)

  # # 2値画像を収縮する。
  # dst = cv2.dilate(img2, kernel)
  # dst=np.where(dst>100,255,dst)
  # dst=255-dst
  # # cv2_imshow(dst)
  # # 2値画像を収縮する。
  # dst = cv2.erode(dst, kernel)
  # # cv2_imshow(dst)
  del img
  del img2
  return dst

def remove_hahen_noise(img):
    # count,aaa,bbb=0,0,0
    # 入力画像、テンプレート画像を読み込む。
    # img = cv2.imread("content_1.jpg")  # 入力画像
    # _cv2_imshow(img)
    path = _get_sample_img_path('hahen/*.jpg')
    # path = os.path.join(os.path.dirname(__file__),'hahen/*.jpg')

    files = glob.glob(path)         # 削除対象の画像を置くフォルダ
    # _print(files)

    dst2 = img.copy() # 作業用に元画像を複製  S.I

    for file in files:
        # テンプレートマッチングを行う。
        templ = cv2.imread(file)          #削除対象読込
        result = cv2.matchTemplate(img, templ, cv2.TM_CCOEFF_NORMED)
        # count+=1
        # print('count=',count,file)
        # 最も類似度が 0.9 以上の位置を取得する。
        ys, xs = np.where(result >= 0.92)

        # # 描画する。
        # dst = img.copy()
        # for x, y in zip(xs, ys):
        #     cv2.rectangle(
        #         dst,
        #         (x, y),
        #         (x + templ.shape[1], y + templ.shape[0]),
        #         color=(0, 255, 0),
        #         thickness=2,
        #     )
        # # _cv2_imshow(dst)

        # 類似画像を消す
        # dst2 = img.copy() # ループの外へ移動 S.I
        for x, y in zip(xs, ys):
            _print('file,x,y=',file,x,y)
            cv2.rectangle(
                dst2,
                (x, y),
                (x + templ.shape[1], y + templ.shape[0]),
                color=(255, 255, 255),
                thickness=-1,
            )
            # aaa+=1
            # print('aaa=',aaa)
        # _cv2_imshow(dst2)
        del templ
        del result       
        gc.collect()
    return dst2 # 作業した画像を返す S.I
    # return img

def replace_triangle(img):
    #　画像の置換（△→-）
    # 入力画像、テンプレート画像を読み込む。

    path = _get_sample_img_path('triangle/*.jpg')
    files = glob.glob(path)         # 削除対象の画像を置くフォルダ
    triangle_xy,tr=[],[]

    for file in files:
      # print(file)
      # テンプレートマッチングを行う。
      templ = cv2.imread(file)          #削除対象読込
      result = cv2.matchTemplate(img, templ, cv2.TM_CCOEFF_NORMED)
      # print(result)
      if len(result)!=0:
        # 最も類似度が 0.9 以上の位置を取得する。
        ys, xs = np.where(result >= 0.8)
        # print(ys,xs)
        #近傍の点は省く１
        i=0
        for x,y in zip(xs,ys):
          i+=1
          if i==1:
            x0,y0=x,y
            triangle_xy.append([x,y,templ.shape[1],templ.shape[0]])
            # print('x,y',x,y)
          if abs(x-x0)+abs(y-y0)<10:
            continue
          else:
            x0,y0=x,y
            triangle_xy.append([x,y,templ.shape[1],templ.shape[0]])
        # _print('x,y',triangle_xy)
      del templ
      del result
    #近傍の点は省く２（１７の２ページ目の'貸倒引当金'の行のように'△'が２個ある場合の対策）
    triangle_xy = sorted(triangle_xy,key=lambda x:(x[0],x[1]))

    #近傍の対象点を1とする
    trflg=np.zeros(len(triangle_xy))
    tri=[]
    for i in range(len(triangle_xy)):
      for j in range(i+1,len(triangle_xy)):
        x0,y0,_,_=triangle_xy[i]
        x1,y1,_,_=triangle_xy[j]
        d=distance((x0,y0),(x1,y1))
        if d<10:
          trflg[j]=1
    _print(trflg)
    for k,tf in enumerate(trflg):
      if int(tf)==0:
        tri.append(triangle_xy[k])
    # _print(tri)

    # 類似画像を消す１
    dst2 = img.copy()
    # print(triangle_xy)
    triangle_xy=sorted(triangle_xy,key=lambda x:(x[1],x[0]))
    # print('111',len(triangle_xy),triangle_xy)
    for x, y,w,h in  triangle_xy:
        # print(x,y,x + w, y + h)
        cv2.rectangle(
            dst2,(x, y),(x+w+1 , y + h),
            color=(255, 255, 255),
            thickness=-1,
        )

    # for x, y,w,h in  triangle_xy:
    #   #マイナス表示
    #     cv2.rectangle(
    #         dst2,
    #         (x , y+int(h/2)+2),
    #         (x+w-4,y+int(h/2)+4),
    #         color=(0, 0, 0),
    #         thickness=-1,
    #         )
    _print('tri',tri)
    # _cv2_imshow(dst2)
    del img
    return dst2,tri

####　横線を消し、縦線を増強
# 直線をimgに描画する関数
def del_lines(img):
  # 画像表示用に入力画像をカラーデータに変換する
  img_disp =img.copy()
  #横線を消す
  #horizontal kernel
  kernel = np.zeros((5,5), np.uint8)
  kernel[2, :] = 1
  kernel2 = np.zeros((5,5), np.uint8)
  kernel2[:,2] = 1
  kernel3 = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
  gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
  gray2=gray.copy()
  _cv2_imshow(gray2)
  h,w=gray.shape
  #クリア
  #gray = cleary(gray, clip_limit=3, grid=(8, 8), thresh=255)

#   _cv2_imshow(gray)
  img_th = cv2.dilate(gray, kernel, iterations=20)
  img_th = cv2.erode(img_th, kernel, iterations=20)
  img_th = 255-img_th
  #img_th>20の影響大
  img_th=np.where(img_th>20,255,0)
  img_th.astype('uint8')
  img_th2 = np.array(img_th, dtype=np.uint8)
  img_th3  = cv2.dilate(img_th2, kernel3)
  #横線を太く
  img_th4 = cv2.morphologyEx(img_th3, cv2.MORPH_OPEN, kernel3)
  _print('横線を太く')
  _cv2_imshow(img_th4)
  img_th4 = cv2.morphologyEx(img_th4, cv2.MORPH_OPEN, kernel3)

  # # ラベリング(横)Statsベース
  retval, labels, stats, centroids = cv2.connectedComponentsWithStats(img_th4)
  _print('横stats',stats)
  stats_h=[]
  #結果表示（横線を消去）
  for st in stats:
    x, y, width, height, area = st
    if width>200 and x!=0:
      stats_h.append([x, y, width, height, area])
  #print('stats_h',stats_h,len(stats_h))
  for i in range(0, len(stats_h)):
      x, y, width, height, area = stats_h[i] # x座標, y座標, 幅, 高さ, 面積
      if i>0:
        x0, y0, width0, height0, area0 = stats_h[i-1]
        _print('x,y,width,height,img.shape[1],gray.shape[0]*0.1',x,y,width,height,img.shape[1],gray.shape[0]*0.1)
        if y-y0<17 and y>gray.shape[0]*0.1:
          # cv2.rectangle(img,(0,y),(img.shape[1],y0),(255,255,255),-1)
          aaa=0
        else:
          cv2.rectangle(img,(0,y),(img.shape[1],y+5),(255,255,255),-1)
      if width > 200 and height<24:
        cv2.rectangle(img,(x+2,y-1),(x+width-8,y+height),(255,255,255),-1)
        # cv2.rectangle(img,(0,y-1),(img.shape[1],y+4),(255,255,255),-1)


  _cv2_imshow(img)
  #元画像のディメンションを合わせる
  img_disp2 = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

  #縦線を書く
  # _cv2_imshow(gray2)

  img_th2 = cv2.dilate(gray2, kernel2, iterations=20)
#  img_th2 = cv2.erode(img_th2, kernel2, iterations=20)
  img_th2 = 255-img_th2
  _print('img_th2')
  _cv2_imshow(img_th2)
  # 2値画像を収縮する。(縦線を太くする　20230713追記)
  img_th2 = cv2.dilate(img_th2, kernel3,iterations=7)
  print('img_th2:1')
  #cv2_imshow(img_th2)
  #cv2.imwrite('img_th2_1.jpg',img_th2)
  # 縦線を上下に伸ばす(20230731追記)
  img_th2 = cv2.dilate(img_th2, kernel2,iterations=20)
  img_th3 = 255-img_th2
  # _cv2_imshow(img_th3)
  # img_th3=np.where(img_th3>50,255,0)
  # _cv2_imshow(img_th3)
  img_th3=np.where(img_th3>250,255,0)
  img_disp3=np.where(img_th3<img_disp2,img_th3,img_disp2)

  #ラベリング（縦）Stats
  retval, labels, stats, centroids = cv2.connectedComponentsWithStats(img_th2)
  stats=stats.tolist()
  stats=sorted(stats,key=lambda x:(x[0]))

  # ラベリング（縦）Hogh
  lines = cv2.HoughLinesP(img_th2,rho=1,theta=np.pi/360,threshold=100,minLineLength=200,maxLineGap=6)
  #print(lines)

  # 結果表示（縦）
  cnt=0
  img_disp3=img_disp3.astype(np.uint8)
  #print('aaa',img_disp3.shape)
  img_disp3 = cv2.cvtColor(img_disp3, cv2.COLOR_GRAY2BGR)

  # _print('縦：img_disp3')
  # _cv2_imshow(img_disp3)
  ##############　20230711　縦線を消す　###################
  img_th3=np.where(img_th3>250,255,0)
  img_disp3=np.where(img_th3==0,255,img_disp2)
  del gray
  del gray2
  del img_th
  del img_th2
  return img_disp3,stats,img_th3,lines

def get_stats(img):
  # 画像表示用に入力画像をカラーデータに変換する
  kernel2 = np.zeros((5,5), np.uint8)
  kernel2[:,2] = 1
  gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
  gray2=255-gray
  _cv2_imshow(gray2)
  h,w=gray2.shape
  #縦線を書く
  # _cv2_imshow(gray2)
  img_th2 = cv2.dilate(gray2, kernel2, iterations=20)
  img_th2 = cv2.erode(img_th2, kernel2, iterations=20)
  img_th2 = 255-img_th2
  # _cv2_imshow(img_th2)
  # ラベリング（縦）
  retval, labels, stats, centroids = cv2.connectedComponentsWithStats(img_th2)
  stats=stats.tolist()
  stats=sorted(stats,key=lambda x:(x[0]))
  stats=stats_split(stats,img)
  # print('get_vline stats',stats)
  # 結果表示（縦）
  cnt=0
  del gray
  del gray2
  return stats

def cleary(img, clip_limit=3, grid=(8, 8), thresh=225):
    # print('1cleary_before',img.shape)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid)
    dst = clahe.apply(img)
    th = dst.copy()
    th[dst > thresh] = 255
    # print('1cleary_after',th.shape)
    return th

def cleary2(img, clip_limit=3, grid=(8, 8), thresh=225):
    # print('2cleary_before',img.shape)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid)
    grayimg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    dst = clahe.apply(grayimg)
    th = dst.copy()
    th[dst > thresh] = 255
    # print('2cleary_after',th.shape)
    return th

#Pillow → OpenCV
def pil2cv(image):
    from PIL import Image
    ''' PIL型 -> OpenCV型 '''
    new_image = np.array(image, dtype=np.uint8)
    if new_image.ndim == 2:  # モノクロ
        pass
    elif new_image.shape[2] == 3:  # カラー
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGB2BGR)
    elif new_image.shape[2] == 4:  # 透過
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGBA2BGRA)
    return new_image

####　文字エリア右寄せ
def create_contours(img):
  width,height = img.shape[1],img.shape[0]
  kernel = np.ones((3,3), np.uint8)
  img = cv2.erode(img, kernel, iterations=2)
  # BGR -> グレースケール
  gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
  # エッジ抽出 (Canny)
  edges = cv2.Canny(gray, 1, 100, apertureSize=3)
   # 膨張処理
  kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
  edges = cv2.dilate(edges, kernel,2)
  # 輪郭抽出
  contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
  del gray
  del edges
  return contours,hierarchy,width,height,img

#２点間の距離
def distance(dst1,dst2):
    d=np.linalg.norm(np.array(dst2)-np.array(dst1))
    return int(d)

#画像内の左上取得（中心座標）
def start_str_position(contours,hierarchy):
  d0=10000
  for cnt, hrchy in zip(contours, hierarchy[0]):
    x,y,w,h = cv2.boundingRect(cnt)
    dst1=(x,y)
    dst2=(0,0)
    d=distance(dst1,dst2)
    if d0>d:
      d0=d
      x0,y0,w0,h0=x,y,w,h
      xc,yc=int(x0+w0/2),int(y0+h0/2)
  ssp=(xc,yc)
  return ssp

# 面積でフィルタリング
def area_filtering(contours,hierarchy,img,min_area,max_area):
    aaa=0

# img画像内の文字の範囲を全て抽出して変数に格納
def extract_str(img_disp):
# 8ビット1チャンネルのグレースケールとして画像を読み込む
  #img2 = img.copy()
  #img3 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
  #img3=np.where(img3<180,0,img3)
  # 画像表示用に入力画像をカラーデータに変換する
  img_disp=img_disp.astype(np.uint8)
  img_color = cv2.cvtColor(img_disp, cv2.COLOR_GRAY2BGR)

  h,w=img_disp.shape[0],img_disp.shape[1]

  # 二値化(二値化して白黒反転、下限値120が')'を読めるかポイント)
  retval, img3 = cv2.threshold(img_disp, 150, 255, cv2.THRESH_BINARY_INV)
  _cv2_imshow(img3)
  #オープニング処理
  #kernel_open = np.ones((5,5),np.uint8)
  #opening = cv2.morphologyEx(img3, cv2.MORPH_OPEN, kernel_open)
  #print('opening')
  #cv2_imshow(opening)

  # クロージング処理（細切れ状態を防ぐため）
  kernel = np.ones((3, 3), np.uint8)
  # img4 = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=3)
  img4 = cv2.morphologyEx(img3, cv2.MORPH_CLOSE, kernel, iterations=3)
  img4=img4.astype(np.uint8)



  # ラベリング
  retval, labels, stats, centroids = cv2.connectedComponentsWithStats(img4)

  #元画像のディメンションを合わせる
  img_2 = cv2.cvtColor(img_disp, cv2.COLOR_GRAY2RGB)

  str_data=[]
  #削除するべきY座標
  exindexs=[]
  #すべてのY座標標準
  exdankai={}
  #点線の数
  extensensu=15
  '''
  max_2=90
  for i in range(1, retval):
      x, y, width, height, area = stats[i] # x座標, y座標, 幅, 高さ, 面積
      center_x,center_y=centroids[i]
      center_x,center_y=int(center_x),int(center_y)
      ratio=width/height
      if area < max_2 and ratio>0.1 and ratio < 10 and height <90 and x/w>0.06: #20231007
        addfalg=True
        kkk=0
        for k in exdankai.keys():
          if k+5>y and k-5<y:
            addfalg=False
            kkk=k
        if addfalg :
          exdankai[y] = 1
        else :
          exdankai[kkk] = exdankai[kkk]+1
  deleteklist=[]
  for k in exdankai.keys():
    if exdankai[k]<extensensu :
      deleteklist.append(k)
  for item in deleteklist:
    exdankai.pop(item)
  for i in range(1, retval):
      x, y, width, height, area = stats[i] # x座標, y座標, 幅, 高さ, 面積
      center_x,center_y=centroids[i]
      center_x,center_y=int(center_x),int(center_y)
      ratio=width/height
      if area < max_2 and ratio>0.1 and ratio < 10 and height <90 and x/w>0.06: #20231007
        for k in exdankai.keys():
          if k+5>y and k-5<y:
            exindexs.append(i)
  '''      

  # 結果表示
  for i in range(1, retval):
      x, y, width, height, area = stats[i] # x座標, y座標, 幅, 高さ, 面積
      center_x,center_y=centroids[i]
      center_x,center_y=int(center_x),int(center_y)
      ratio=width/height

      # if area<40000 and area > 150 and ratio>0.05 and ratio < 10 : # 面積がxxx00画素以上の部分,縦横比で絞込
      #if area<40000 and area > 60 and ratio>0.04 and ratio < 10 and height <80 and x/w>0.08: # 面積がxxx00画素以上の部分,縦横比で絞込
      if area<100000 and area > 60 and ratio>0.1 and ratio < 10 and height <90 and x/w>0.06: #20231007
      #if area<100000 and area > 90 and ratio>0.1 and ratio < 10 and height <90 and x/w>0.06 and i not in exindexs: #20231007
          # cv2.rectangle(img4,(x,y),(x+width,y+height),(0,0,0),-1)
          cv2.rectangle(img_color,(x,y),(x+width,y+height),(0,0,255),-1)
          # cv2.putText(img_colorp, f"{i}", (x-15, y), cv2.FONT_HERSHEY_PLAIN, 1, (50, 50, 50), 1, cv2.LINE_AA)
          # cv2.putText(img_color, f"{x}", (x, y), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1, cv2.LINE_AA)
          # cv2.putText(img_colorp, f"{y}", (x, y+12), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1, cv2.LINE_AA)
          # cv2.putText(img_color, f"{height}", (x, y+24), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 0), 1, cv2.LINE_AA)
          # cv2.putText(img_color, f"{y+height}", (x, y+36), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 255), 1, cv2.LINE_AA)
          str_data.append([x, y, width, height,center_x,center_y])

  dst = cv2.resize(img_color, dsize=(w,h))
  str_data2=sorted(str_data,key=lambda x:(x[1],x[0]))
  # print('ラベリング１')
  _cv2_imshow(dst)
  _cv2_imwrite('dst.jpg',dst)
  # print('strdata1',str_data2)
  del img_disp
  del img3
  del img4
  del img_color
  return str_data2,dst

def re_extract_str(dst,str_data2):
##追加の読取処理
# 灰色除去
  dst=cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
  result=np.where(dst>=40 ,255,dst)
  result=255-result
  _cv2_imshow(result)
  kernel = np.ones((3,3), np.uint8)
  result = cv2.dilate(result, kernel, iterations=2)
  # _print('2回目')
  _cv2_imshow(result)
  # print('result.shape',result.shape)
  # ラベリング
  retval, labels, stats, centroids = cv2.connectedComponentsWithStats(result)
  # _print(stats)
  #元画像のディメンションを合わせる
  img_2 = cv2.cvtColor(result, cv2.COLOR_GRAY2RGB)
  h,w=img_2.shape[0],img_2.shape[1]
  for i in range(1, retval):
      x, y, width, height, area = stats[i] # x座標, y座標, 幅, 高さ, 面積
      center_x,center_y=centroids[i]
      center_x,center_y=int(center_x),int(center_y)
      ratio=width/height

      # if area<40000 and area > 150 and ratio>0.05 and ratio < 10 : # 面積がxxx00画素以上の部分,縦横比で絞込

      #if area<40000 and area > 60 and ratio>0.04 and ratio < 10 and height <80 and x/w>0.08: # 面積がxxx00画素以上の部分,縦横比で絞込          cv2.rectangle((img_2),(x,y),(x+width,y+height),(0,0,255),-1)
      if area<40000 and area > 60 and ratio>0.1 and ratio < 10 and height <90 and x/w>0.05: # 面積がxxx00画素以上の部分,縦横比で絞込

          cv2.rectangle((img_2),(x,y),(x+width,y+height),(0,0,255),-1)
          #cv2.putText(img_2, f"{x}", (x, y), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1, cv2.LINE_AA)
          #cv2.putText(img_2, f"{y}", (x, y+12), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1, cv2.LINE_AA)
          #cv2.putText(img_2, f"{height}", (x, y+24), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 0), 1, cv2.LINE_AA)
          #cv2.putText(img_2, f"{y+height}", (x, y+36), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 255), 1, cv2.LINE_AA)
          str_data2.append([x, y, width, height,center_x,center_y])

  # dst = cv2.resize(result, dsize=(w,h))
  str_data3=sorted(str_data2,key=lambda x:(x[1],x[0]))
  _print('img_2')
  _cv2_imshow(img_2)
  _cv2_imwrite('img_2.jpg',img_2)
  # print('strdata3',str_data3)
  del dst
  del result
  return str_data3,img_2

# 行判定
def scan_rows(img,strdata):
  width,height=img.shape[1],img.shape[0]
  _print(width)
 #y方向でソート
  # strdata_sorted = sorted(strdata,key=lambda y:min( y for y in strdata[1]))
  dsrt=sorted(strdata,key=lambda y:(y[5],y[1]))

  re_sort_data =[]

  # 行方向の隙間を探す
  row_num= 0

  #y座標が重複している部分があるか、又は近接しているものを抽出し同一行とする
  for i in range(len(dsrt)-1):
    y01,y02=dsrt[i][1],dsrt[i][1]+int(dsrt[i][3])
    y11,y12=dsrt[i+1][1],dsrt[i+1][1]+int(dsrt[i+1][3])
    #
    if (y01<=y11 and y11<=y02) and ((y02-y11)/max(y02-y01,y12-y11)>0.1):
      d=(y02-y11)/max(y02-y01,y12-y11)
    elif (y01<=y12 and y12<=y02) and((y12-y01)/max(y02-y01,y12-y11)>0.1) :
      d=(y12-y01)/max(y02-y01,y12-y11)
    elif (y01<=y11 and y02>=y12) or (y01>=y11 and y02<=y12) :
      d=1.00
    else:
      d=0.00

    if d>0:
      re_sort_data.append([row_num,dsrt[i][0],dsrt[i][1],dsrt[i][2],dsrt[i][3],dsrt[i][4]])
    else:
      re_sort_data.append([row_num,dsrt[i][0],dsrt[i][1],dsrt[i][2],dsrt[i][3],dsrt[i][4]])
      row_num += 1
    #最終data追加
    if i==len(dsrt)-2:
      re_sort_data.append([row_num,dsrt[i+1][0],dsrt[i+1][1],dsrt[i+1][2],dsrt[i+1][3],dsrt[i][4]])

  # 各行毎にx方向で並べ替え
  re_sort_data2=sorted(re_sort_data,key=lambda re_sort_data:(re_sort_data[0],re_sort_data[1]))

  # dst0=img.copy()
  # dst0_inv=255-dst0
  # for i,rstd in enumerate(re_sort_data1):
  #   rnum,a,b,c,d,e=rstd
  #   if i>=0:
  #     cv2.rectangle((dst0_inv),(a,b),(a+c,b+d),(0,255,0),3)
  #   cv2.putText(dst0_inv, f"{rnum}", (a-25, b), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1, cv2.LINE_AA)
  #   cv2.putText(dst0_inv, f"{i}", (a-35, b+12), cv2.FONT_HERSHEY_PLAIN, 1, (50, 50, 50), 1, cv2.LINE_AA)
  # cv2.imwrite('dst0_inv.jpg',dst0_inv)
  # print('*zzz*',re_sort_data1[:-1])
  # dst2,dst_inv=[],[]

  # for d in re_sort_data1:
  #   print(d)


  ###############################################################################################
  #20230704ここから追加----->
  #（★）各行のx,yの最大値と最小値を取得し、かぶっている行があれば同一行とみなして再配置する（★）
  #各行のy座標のmin、maxを取得
  rs2_yminmax,cnt,flg,d=[],0,0,0
  rnum=re_sort_data2[0][0]
  rnum_last=re_sort_data2[-1][0]
  ymin=re_sort_data2[0][2]
  ymax=re_sort_data2[0][2]+re_sort_data2[0][4]
  for i,r3 in enumerate(re_sort_data2):
    if rnum == re_sort_data2[i][0]:
      # print('i,ymin,r3[2]',i,ymin,r3[2])
      if ymin >r3[2]:
        ymin=r3[2]
        # print('a:i,rnum,ymin',i,rnum,ymin)
      if ymax <r3[2]+r3[4]:
        ymax=r3[2]+r3[4]
      #最終行の場合
      if rnum_last==re_sort_data2[i][0] and i==len(re_sort_data2)-1:
        rs2_yminmax.append([rnum,ymin,ymax])
    else:
      rs2_yminmax.append([rnum,ymin,ymax])
      # print('b:i,rnum,ymin',i,rnum,ymin)
      ymin=r3[2]
      ymax=r3[2]+r3[4]
      #最終行の場合
      if rnum_last==re_sort_data2[i][0] and i==len(re_sort_data2)-1:
        rs2_yminmax.append([rnum_last,ymin,ymax])
    rnum=re_sort_data2[i][0]
  # print('Yminmax',rs2_yminmax)
  # print('re_sort_data2',re_sort_data2)

  #rs2_yminmax各行のy座標のかぶりをチェックしかぶっている行をマージしてリナンバリング
  rs2_marge,cnt,flg,dr=[],0,0,0
  for i in range(len(rs2_yminmax)-1):
    # print('i:len1',i,len(rs2_yminmax))
    y0min=rs2_yminmax[i][1]
    y0max=rs2_yminmax[i][2]
    y1min=rs2_yminmax[i+1][1]
    y1max=rs2_yminmax[i+1][2]
    #かぶりパターン分類とかぶり率dr
    if (y0min<=y1min and y0max>=y1max):
      dr=1
      # print('i:dr',i,dr)
    elif (y0min>=y1min and y0min<=y1max):
      d0=y1max-y0min
      dr=d0/(y0max-y0min)
      # print('i:dr',i,dr)
    elif (y0min<=y1min and y0max>=y1min):
      d0=y0max-y1min
      dr=d0/(y1max-y1min)
      # print('i:dr',i,dr)
    elif (y0min>=y1min and y0max<=y1max):
      dr=1
      # print('i:dr',i,dr)
    else:
      dr=0
      # print('else:i',i)

    # print('y0min,y0max,y1min,y1max',y0min,y0max,y1min,y1max)
    #かぶっている行
    # if (y0min<=y1min and y0max>=y1max) or (y0min>=y1min and y0min<=y1max) or (y0min<=y1min and y0max>=y1min) or (y0min>=y1min and y0max<=y1max) or (y0min<=y1max and y0max>=y1max) or (y0max>=y1min and y0max<=y1max):
    if dr>0.09:
      # print('a1,i,dr',i,dr)
      for j,re in enumerate(re_sort_data2):
        if i==re_sort_data2[j][0] or i+1==re_sort_data2[j][0]:
          # print('a2:j,dr',j,dr)
          rs2_marge.append([cnt,re_sort_data2[j][1],re_sort_data2[j][2],re_sort_data2[j][3],re_sort_data2[j][4],re_sort_data2[j][5]])
          # print('AAA',i,cnt,re_sort_data2[j][1],re_sort_data2[j][2],re_sort_data2[j][3],re_sort_data2[j][4],re_sort_data2[j][5])
      flg=1
      cnt+=1
      # print('i',i)
    #かぶっていない行
    else:
      if flg==0:
        # print('a3',i)
        for j,re in enumerate(re_sort_data2):
          if i==re_sort_data2[j][0]:
            # print('a4',i,j)
            rs2_marge.append([cnt,re_sort_data2[j][1],re_sort_data2[j][2],re_sort_data2[j][3],re_sort_data2[j][4],re_sort_data2[j][5]])
            # print('BBB',i,cnt,re_sort_data2[j][1],re_sort_data2[j][2],re_sort_data2[j][3],re_sort_data2[j][4],re_sort_data2[j][5])
        cnt+=1
        if i == len(rs2_yminmax)-2:
          # print('a5')
          #最終行追加
          for j,re in enumerate(re_sort_data2):
            if i+1==re_sort_data2[j][0]:
              # print('a6')
              rs2_marge.append([cnt,re_sort_data2[j][1],re_sort_data2[j][2],re_sort_data2[j][3],re_sort_data2[j][4],re_sort_data2[j][5]])
              # print('BBB',i,cnt,re_sort_data2[j][1],re_sort_data2[j][2],re_sort_data2[j][3],re_sort_data2[j][4],re_sort_data2[j][5])
      else:
        flg=0
        #最終行追加
        if i == len(rs2_yminmax)-2:
          for j,re in enumerate(re_sort_data2):
              if i+1==re_sort_data2[j][0]:
                # print('a_last')
                rs2_marge.append([cnt,re_sort_data2[j][1],re_sort_data2[j][2],re_sort_data2[j][3],re_sort_data2[j][4],re_sort_data2[j][5]])     
  
  # print('rs2_marge',rs2_marge)
  dst1=img.copy()
  dst1_inv=255-dst1
  for i,rstd in enumerate(rs2_marge):
    # print('i,len',i,len(rstd),rstd)
    rnum,a,b,c,d,e=rstd
    # if rnum==104:
      # print('rstd',rstd)
    if i>=0:
      # print(i,a,b,c,d)
      cv2.rectangle((dst1_inv),(a,b),(a+c,b+d),(0,255,0),3)
      cv2.putText(dst1_inv, f"{rnum}", (a-25, b), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1, cv2.LINE_AA)
      cv2.putText(dst1_inv, f"{i}", (a-35, b+12), cv2.FONT_HERSHEY_PLAIN, 1, (50, 50, 50), 1, cv2.LINE_AA)
  #cv2.imwrite('dst1_inv.jpg',dst1_inv)
  ######################################################################################################
  # 各行毎にx方向(x+w)で並べ替え
  re_sort_data22=[]
  re_sort_data22=sorted(rs2_marge,key=lambda x:(x[0],x[1]+x[3]))
  # print('len',len(re_sort_data22))
  # print('re_sort_data22',re_sort_data22)
  # x方向でかぶっている,文字をマージ
  rx_marge,flg=[],0
  for i in range(len(re_sort_data22)-1):
    if i==flg and i!=0:
      # print('continue',i)
      continue
    #同一行の場合
    if re_sort_data22[i][0]==re_sort_data22[i+1][0]:
      x0min=re_sort_data22[i][1]
      x0max=re_sort_data22[i][1]+re_sort_data22[i][3]
      x1min=re_sort_data22[i+1][1]
      x1max=re_sort_data22[i+1][1]+re_sort_data22[i+1][3]
      #x方向が被っている
      if (x0min<=x1min and x0max>=x1max) or (x0min>=x1min and x0min<=x1max) or (x0min<=x1min and x0max>=x1min) or (x0min>=x1min and x0max<=x1max):
        xmin=min(x0min,x1min)
        xmax=max(x0max,x1max)
        ymin=min(re_sort_data22[i][2],re_sort_data22[i+1][2])
        ymax=max(re_sort_data22[i][2]+re_sort_data22[i][4],re_sort_data22[i+1][2]+re_sort_data22[i+1][4])
        w,h=xmax-xmin,ymax-ymin
        rx_marge.append([re_sort_data22[i][0],xmin,ymin,w,h,re_sort_data22[i][5]])
        flg=1
        # print('i1',i)
        if i == len(re_sort_data22)-2:
          #最終行追加
            rx_marge.append([re_sort_data22[i][0],re_sort_data22[i+1][1],re_sort_data22[i+1][2],re_sort_data22[i+1][3],re_sort_data22[i+1][4],re_sort_data22[i+1][5]])
      #x方向かぶりなし
      else:
        if flg==0:
          # print('i2',i)
          rx_marge.append([re_sort_data22[i][0],re_sort_data22[i][1],re_sort_data22[i][2],re_sort_data22[i][3],re_sort_data22[i][4],re_sort_data22[i][5]])
          if i == len(re_sort_data22)-2:
          #最終行追加
            rx_marge.append([re_sort_data22[i+1][0],re_sort_data22[i+1][1],re_sort_data22[i+1][2],re_sort_data22[i+1][3],re_sort_data22[i+1][4],re_sort_data22[i+1][5]])
        else:
          # print('i3',i)
          flg=0
    #同一行ではない場合
    else:
      # print('i4',i)
      rx_marge.append([re_sort_data22[i][0],re_sort_data22[i][1],re_sort_data22[i][2],re_sort_data22[i][3],re_sort_data22[i][4],re_sort_data22[i][5]])
      if i == len(re_sort_data22)-2:
          #最終行追加
          rx_marge.append([re_sort_data22[i+1][0],re_sort_data22[i+1][1],re_sort_data22[i+1][2],re_sort_data22[i+1][3],re_sort_data22[i+1][4],re_sort_data22[i+1][5]])
          # print('i5',i)
  # print('rx_marge',rx_marge)


  # dst2=img.copy()
  # dst2_inv=255-dst2
  # for i,rstd in enumerate(rx_marge):
  #   # print('i,len',i,len(rstd),rstd)
  #   rnum,a,b,c,d,e=rstd
  #   # if rnum==104:
  #     # print('rstd',rstd)
  #   if i>=0:
  #     # print(i,a,b,c,d)
  #     cv2.rectangle((dst2_inv),(a,b),(a+c,b+d),(0,255,0),3)
  #   cv2.putText(dst2_inv, f"{rnum}", (a-25, b), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1, cv2.LINE_AA)
  #   cv2.putText(dst2_inv, f"{i}", (a-35, b+12), cv2.FONT_HERSHEY_PLAIN, 1, (50, 50, 50), 1, cv2.LINE_AA)
  # cv2.imwrite('dst2_inv.jpg',dst2_inv)
  # _cv2_imshow(dst2)

  # dst2,dst_inv=[],[]
  #return rx_marge

  #20230704ここまで追加<-----
  # print('rs2_descend_2',rs2_descend_2)
  #################################################################################################################

  #################>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
  #行間チェック＆ノイズ削除
  #各行のy座標のmin、maxを取得（再）
  del re_sort_data2
  re_sort_data2=rx_marge
  rs2_yminmax,cnt,flg,d=[],0,0,0
  rnum=re_sort_data2[0][0]
  rnum_last=len(re_sort_data2)
  ymin=re_sort_data2[0][2]
  ymax=re_sort_data2[0][2]+re_sort_data2[0][4]
  for i,r3 in enumerate(re_sort_data2):
    if rnum == re_sort_data2[i][0]:
      # print('i,ymin,r3[2]',i,ymin,r3[2])
      if ymin >r3[2]:
        ymin=r3[2]
        # print('a:i,rnum,ymin',i,rnum,ymin)
      if ymax <r3[2]+r3[4]:
        ymax=r3[2]+r3[4]
      #最終行の場合
      if rnum_last==i+1:
        rs2_yminmax.append([rnum,ymin,ymax])
    else:
      rs2_yminmax.append([rnum,ymin,ymax])
      # print('b:i,rnum,ymin',i,rnum,ymin)
      ymin=r3[2]
      ymax=r3[2]+r3[4]
    rnum=re_sort_data2[i][0]
  # print('rs2_yminmax**',rs2_yminmax)
  # #img の行間に白線を引く
  # img_n=img.copy()
  # for i in range(len(rs2_yminmax)-1):
  #   yc=int((rs2_yminmax[i][2]+rs2_yminmax[i+1][1])/2)
  #   x1,x2=int(img.shape[1]*0.25),int(img.shape[1]*0.75)
  #   cv2.line(img_n,
  #        pt1=(x1, yc),
  #        pt2=(x2, yc),
  #        color=(0, 0, 0),
  #        thickness=3,
  #        lineType=cv2.LINE_4,
  #        shift=0)
  # print('行間ノイズ除去')
  # cv2_imshow(img_n)
  #################<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

  return rx_marge,rs2_yminmax


#各行毎に移動すべき文字があるか判定
#対象の文字は、縦横比0.85～1.15、
#１文字目（w1,xc1,yc1）、2文字目（w2,xc2,yc2）とした場合、
#文字間隔xc2-xc1が、w1+w2以上かつw1+w2の5倍以下とする
#移動先のx座標は、xn[]に入れる

#同じ行を(x座標+w)の小さい順にソートしまとめる
def select_str(resortdata):
  _print('resortdata',resortdata)
  row_key=resortdata[0][0]

  r,rs=[],[]
  for i in range(len(resortdata)):
    if resortdata[i][0]==row_key:
      r.append(resortdata[i])
    else:
      rs.append(r)
      row_key=resortdata[i][0]
      r=[]
      r.append(resortdata[i])
  rs.append(r)

  #rs 行番号,x,y,w,h,area
  del r
  return rs

#白紙画像作成
def new_palette(img):
  w,h=img.shape[1],img.shape[0]
  import numpy as np
  img_white = np.ones((h,w, 3),np.uint8)*255
  imgwhite=pil2cv(img_white)
  dst = cv2.resize(imgwhite, dsize=(int(w/1),int(h/1)))
  return dst

#文字のみを白紙にコピー
def copy_same_position(im,rs):
  new_img = new_palette(im)
  for ds in rs:
    for d in ds:
      _,x,y,w,h,_=d
      obj=im[y:y+h,x:x+w]
      new_img[y:y+h,x:x+w]=obj
  return new_img
#各行のwの最大値を省いた平均と２番目に大きい値を取得
def get_max_wh(rs):
  wh_max,wmax,hmax,w_ave,w_sum,i=[],0,0,0,0,0

  #２番目に大きいwを取得
  wmax_2nd,i=0,0
  for r2 in rs:
    after_r2=sorted(r2,key=lambda x:x[-3])
    if len(after_r2)==1:
      wmax_2nd=after_r2[0][3]
    else:
      wmax_2nd=after_r2[1][3]
    h0=r2[0][4]
    for d in r2:
      if d[4]>=h0:
          hmax=d[4]
    wh_max.append([i,wmax_2nd,hmax])
    i+=1
    hmax=0
    wmax,hmax,w_ave,cnt=0,0,0,0
  return wh_max


#内包される文字を統合する
def marge_string(rs):
  # rs_new=sorted(rs,key=lambda x:(x[0],x[1]+x[3]))
  # _print('rstest:')
  # n=0
  # for i,r in enumerate(rs):
  #   for j in range(len(r)):
  #     a,b,c,d,e,f=r[j]
  #     _print(n,a,b,c,d,e)
  #     n+=1

  wh_max=get_max_wh(rs)
  r2,rs2,w2=[] ,[],0
  Xmin,Xmax,Ymin,Ymax,span=0,0,0,0,0
  n=0
  for i,r in enumerate(rs):
        flg,x0,y0,w0,h0,area0,x1,y1,w1,h1,area1,x_right=0,0,0,0,0,0,0,0,0,0,0,0
        if len(r)==1:
          _,x0,y0,w0,h0,area0=r[0]
          if w0!=0:
            # print(i,x0,y0,w0,h0,area0)
            r2.append([i,x0,y0,w0,h0,area0])
        maxw=wh_max[i][1]

        for j in range(len(r)-1):
            # if flg==0:
            _print('n,flg',n,flg)
            if j==0:
              _,x0,y0,w0,h0,area0=r[j]

            else:
              if flg==0:
                #範囲そのまま
                _print('aaa',n,x0,w0,x1,w1)
                x0,y0,w0,h0=x1,y1,w1,h1
              else:
                #範囲拡大
                _print('bbb',n)
                #if n>=108 and n<=110:
                #  _print('*/',x0,w0,x1,w1)
                x0,y0,w0,h0=Xmin,Ymin,Xmax-Xmin,Ymax-Ymin
                #if n>=108 and n<=110:
                #  _print('Xmax-Xmin',Xmax-Xmin)
              _print('ccc',n,x0,w0,x1,w1)
            _print('ddd',n,x0,w0,x1,w1)
            _,x1,y1,w1,h1,area1=r[j+1]

            # 次との間隔span
            span=x1-(x0+w0)
            # print('span,x1,x0,w0=',span,x1,x0,w0)

            Xmin,Xmax,Ymin,Ymax=min(x0,x1),max(x0+w0,x1+w1),min(y0,y1),max(y0+h0,y1+h1)
            x_right=x0+w0
            w2=Xmax-Xmin
            if x_right >= x1:
              flg=1
              #if n>=108 and n<=110:
              #  _print('範囲拡大、n,flg',n,flg)
            else:
              flg=0
              _print('append',n,x0,w0,x1,w1)
              if w0!=0:
                # print(i,x0,y0,w0,h0,span)
                r2.append([i,x0,y0,w0,h0,span])
              _print('範囲そのまま,n',n)
            n+=1
        if len(r)>0:
          if flg==1:
            maxw=max(w1,x1+w1-x0)
            maxh=max(rs[i][len(r)-2][4],rs[i][len(r)-1][4])
            _print('append',n,x0,w0,x1,w1,maxw,maxh)

            # r2.append([i,min(xk,rs[i][len(r)-2][1]),min(yk,rs[i][len(r)-2][2]),max(wk,maxw),max(hk,maxh),span])
            if maxw !=0:
              # print(i,rs[i][len(r)-2][1],rs[i][len(r)-2][2],maxw,maxh,span)
              r2.append([i,rs[i][len(r)-2][1],rs[i][len(r)-2][2],maxw,maxh,span])
              #xk,yk,wk,hk=0,0,0,0
          else:
            # print('BBB')
            if w1 !=0:
              # print(i,x1,y1,w1,h1,span)
              r2.append([i,x1,y1,w1,h1,span])
        rs2.append(r2)
        r2=[]
        n+=1
  return rs2

def sort_right_alighnment(rs2):
  rs3=[]
  for r2 in rs2:
    r3=sorted(r2,key=lambda x:(x[0],-x[1]))
    rs3.append(sorted(r2,key=lambda x:(x[0],-x[1])))
  return rs3
  
#文字をくっつけて白紙にコピー(右寄)
def copy_pack_position(im,rs):
  # for i,r in enumerate(rs):
    # if i==39:
    #   print('////',i,r)
  _print('shape',im.shape)
  # cv2.imwrite('im.jpg',im)
  im=remove_hahen_noise(im)
  im,triangle_xy = replace_triangle(im) # △の処理
  # im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

  _print('shape',im.shape)
  #文字間隔:pitch
  #列間隔:c_width
  pitch=6
  rs2,rs2_ascend,rs3_ascend=[],[],[]
  # wh_max=get_max_wh(rs)
  new_img = new_palette(im)
  # new_img = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)

  xn,span=0,0
  width,height=new_img.shape[1],new_img.shape[0]
  whflg,whflg_pre,w_h,dt,dtflg,dtflg2=0,0,0,40,0,0
  mojikan=0
  for i,ds in enumerate(rs):
  #  if i==58:
    rs2 = []
    rs2_ascend = []
    if len(ds)>1:
      for j in range(len(ds)-1):
        _,x0,y0,w0,h0,_=ds[j]
        _,x1,y1,w1,h1,span=ds[j+1]
        # if j<len(ds)-2:
        #   _,x2,y2,w2,h2,span=ds[j+2]
        

        # -用間隔対策
        w_h=w1/h1       
        if 4.0 < w_h and w_h <6.5 : 
          #－
          whflg=1
          # print('whflg=1',i,j)
        elif .085 < w_h and w_h < 1.15 :
          #全角
          whflg=2
        else:
          #それ以外
          whflg=0

        # if i==20 and j>15:
        #   print('dtflg,whflg_pre,whflg,dtflg2,mojikan',i,j,dtflg,whflg_pre,whflg,dtflg2,mojikan)
        #   print('//',i,j,x0,y0,w0,h0,x1,y1,w1,h1)

        span2=x0-(x1+w1)
        _print('★',i,j,x0,y0,w0,h0,x1,y1,w1,h1)
        if j==0:
          xn=width-200-w0
          _print('i,xn,y0,y0+h0,xn,xn+w0',i,xn,y0,y0+h0,xn,xn+w0)
        
        #画像かぶりチェック
        else:
          xn=xn-w0-pitch
         # '-'を判定しflgを立てる　4.0=<w1/h1=<6.5 w_h=1 
        
        #画像をコピー
        #objの範囲が適正かチェック（右にはみ出さない）
        if x0+w0>width:
          # w0=w0+((x0-w0)-width)
          w0=x0-width
          _print('w0_2',w0)
        obj=im[y0:y0+h0,x0:x0+w0]

        if dtflg==1 or dtflg2==1:
          # print('xn',i,j,xn)
          xn=xn-dt
        if whflg_pre==1 and h0<8:       
          obj=np.where(obj>0,0,0)

        #１つ前のwhflg_preが１の場合にdtflg保存
        if whflg_pre==1:
          dtflg=1
        else:
          dtflg=0

        # "造作  1"の1が落ちる対策
        mojikan=x0-x1
        if mojikan>0:
          if mojikan/w0 > 20:
            dtflg2=1
          else:
            dtflg2=0

        #画像コピー
        try:
          new_img[y0:y0+h0,xn:xn+w0]=obj
        except Exception as e:
          import traceback
          traceback.print_exc()

        # cv2_imshow(new_img)
        rs2.append([i,xn,y0,w0,h0])

        rs2_ascend=sorted(rs2,key=lambda x:(x[0],-x[1]))
       
        if j==len(ds)-2:
          xn=xn-w1-pitch
          obj=im[y1:y1+h1,x1:x1+w1]
          new_img[y1:y1+h1,xn:xn+w1]=obj
          rs2.append([i,xn,y1,w1,h1])
          # if i>28:
          #   print('*i,xn,x0,y0,w0,h0',i,j,xn,x0,y0,w0,h0)
        #   rs2.append([i,x1,y1,w1,h1])
          rs2_ascend=sorted(rs2,key=lambda x:(x[0],x[1]))

        #whflgをwhflg_preに保存
        # if i==30:
        #   print('whflg_pre',whflg_pre)
        if whflg==1:
          whflg_pre=1
        else:
          whflg_pre=0
        
      
        

        _print('whflg_pre,whflg',whflg_pre,whflg)
        # xn=xn-w1-pitch
    rs3_ascend.append(rs2_ascend)
  # cv2_imshow(new_img)
  # cv2.imwrite('result.jpg',new_img)
  del im
  return new_img,rs3_ascend,triangle_xy



#   return new_img,rs2_ascend
#rs,stats_v,img_disp,img_bk,img_th3
#def check_row(rs,stats_v,img,img_bk,img_th3):
def check_row(rs2_yminmax,stats_v,img_disp_o,img_bk,img_th3):
  stats_v=sorted(stats_v,key=lambda x:(x[0]))
  img_disp_o=cv2.cvtColor(img_disp_o, cv2.COLOR_GRAY2BGR)

  #j行目とj+1行目の縦線の範囲の隙間（x0,y0,x1,y1)
  for j in range(len(rs2_yminmax)-1):
    # print('j',j)
    yc=rs2_yminmax[j][2]+2
    #縦線の範囲でループ
    for i in range(1,len(stats_v)-1):
      x1=stats_v[i][0]+2
      x2=stats_v[i+1][0]-2
      # print('x1,x2,yc',x1,x2,yc)
      cv2.line(img_disp_o,
         pt1=(x1, yc),
         pt2=(x2, yc),
         color=(255, 255, 255),
         thickness=3,
         lineType=cv2.LINE_4,
         shift=0)
      # cv2.putText(img_disp_o, f"{j}", (25, yc), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 0), 1, cv2.LINE_AA)

  return rs2_yminmax,img_disp_o


################  <<<<<<<<<<<<<<<<<<<<<  >>>>>>>>>>>>>>>>>>>  ##############
def str_right(img_disp,img_bk,stats_v,img_th3):
  # print('img_disp.shape',img_disp.shape)
  img_disp_o=img_disp.copy()
  h,w=img_disp.shape[0],img_disp.shape[1]
  w_left,w_right=int(w*0.03),int(w*0.97)
  for stv in stats_v:
    #線の場所が左3%以内の場合
    if stv[0]<w_left and stv[3]>200 and stv[2]<100:
      cv2.rectangle((img_disp),(0,0),(w_left+stv[2],h),(255,255,255),-1)
      cv2.rectangle((img_bk),(0,0),(w_left+stv[2],h),(255,255,255),-1)
      # cv2.rectangle((img_disp),(0,0),(w_left,h),(0,0,255),-1)
    #線の場所が右3%以内の場合
    if stv[0]>w_right and stv[3]>200 and stv[2]<100:
      cv2.rectangle((img_disp),(w_right-stv[2],0),(w,h),(255,255,255),-1)
      cv2.rectangle((img_bk),(w_right-stv[2],0),(w,h),(255,255,255),-1)
      # cv2.rectangle((img_disp),(w_right,0),(w,h),(0,0,255),-1)
  #文字位置をラベリング
  strdata2,dst=extract_str(img_disp)
  # print('1',len(strdata))
  _cv2_imshow(dst)
  strdata3,dst=re_extract_str(dst,strdata2)
  stats=get_stats(dst)
  _print('2')
  _cv2_imshow(dst)

  #y方向でソート
  resortdata2,rs2_yminmax=scan_rows(dst,strdata3)

  _print('resortdata2',resortdata2)

  #行を作成
  rs=select_str(resortdata2)

  # for i,r in enumerate(rs):
  #   if i==14:
  #     print(i,r)

  ## 行間をチェック＆クリア
  if len(stats_v) >0:
    rs,img2=check_row(rs2_yminmax,stats_v,img_disp_o,img_bk,img_th3)


    #2回目ループ#文字位置をラベリング
    img2=cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    strdata,dst=extract_str(img2)
    # print('1',len(strdata))
    _print('dst2')
    _cv2_imshow(dst)
    strdata2,dst=re_extract_str(dst,strdata)
    #２回目のdstをベースに再度縦線を抽出
    # print('2',len(strdata))

  ##2y方向でソート
  resortdata3,rs2_yminmax=scan_rows(dst,strdata2)

  ##2行を作成
  rs=select_str(resortdata3)

  #文字を右寄せ
  rs2=marge_string(rs)
  # for r2 in rs2:
  #   _print(r2)
  #元データx昇順
  rs2_ascend=rs2
  #元データx降順
  rs3_descend=sort_right_alighnment(rs2_ascend)
  # #20230622ここから追加----->
  # #（★）各行のx,yの最大値と最小値を取得し、かぶっている行があれば同一行とみなして再配置する（★）
  # #各行のy座標のmin、maxを取得
  # rs3_yminmax=[]
  # for i,r3 in enumerate(rs3_descend):
  #   ymin=r3[0][2]
  #   ymax=r3[0][2]+r3[0][4]
  #   for r in r3:
  #     if ymin >r[2]:
  #       ymin=r[2]
  #     if ymax <r[2]+r[4]:
  #       ymax=r[2]+r[4]
  #   rs3_yminmax.append([i,ymin,ymax])
  # # print(rs3_yminmax)
  # print('rs3_descend',rs3_descend)
  # #各行のy座標のかぶりをチェックしかぶっている行をマージ
  # rs3_marge,rs3_descend_2,flg=[],[],9999
  # for i in range(len(rs3_yminmax)-1):
  #   y0min=rs3_yminmax[i][1]
  #   y0max=rs3_yminmax[i][2]
  #   y1min=rs3_yminmax[i+1][1]
  #   y1max=rs3_yminmax[i+1][2]
  #   print('O',i)

  #   if (y0min<=y1min and y0max>=y1max) or (y0min>=y1min and y0min<=y1max) or (y0min<=y1min and y0max>=y1min) or (y0min>=y1min and y0max<=y1max) or (y0min<=y1max and y0max>=y1max) or (y0max>=y1min and y0max<=y1max):
  #     for j in range(len(rs3_descend[i])):
  #       # print(rs3_descend[i][j][1],rs3_descend[i][j][2],rs3_descend[i][j][3],rs3_descend[i][j][4])
  #       rs3_marge.append([i,rs3_descend[i][j][1],rs3_descend[i][j][2],rs3_descend[i][j][3],rs3_descend[i][j][4],rs3_descend[i][j][5]])
  #     for j in range(len(rs3_descend[i+1])):
  #       rs3_marge.append([i,rs3_descend[i+1][j][1],rs3_descend[i+1][j][2],rs3_descend[i+1][j][3],rs3_descend[i+1][j][4],rs3_descend[i+1][j][5]])      
  #     flg=i+1
  #     print('A',flg)
  #     #x方向でソート
  #     sort_rs3_marge=sorted(rs3_marge,key=lambda x:(x[0],-x[1]))
  #     rs3_descend_2.append(sort_rs3_marge)
  #     rs3_marge=[]
  #   else:
  #     if i != flg:
  #     #   for j in range(len(rs3_descend[i])-1):
  #     #     rs3_marge.append([i,rs3_descend[i][j][1],rs3_descend[i][j][2],rs3_descend[i][j][3],rs3_descend[i][j][4],rs3_descend[i][j][5]])
  #     #   print('B',i)   
  #     # sort_rs3_marge=sorted(rs3_marge,key=lambda x:(x[0],x[1]))
  #       rs3_descend_2.append(rs3_descend[i])
  # # print('flg,len(rs3_yminmax),i',flg,len(rs3_yminmax),i)
  # # if flg != len(rs3_yminmax) and (i+1 == len(rs3_yminmax)-1):
  # if flg != len(rs3_yminmax)-1:
  #   rs3_descend_2.append(rs3_descend[len(rs3_yminmax)-1])
  # #20230622ここまで追加<-----

  new_img=new_palette(img2)
  #白紙に右寄せしてプロット
  newimg,rs3_ascend,triangle_xy=copy_pack_position(img_bk,rs3_descend)
  #新イメージと元データ、移動後データを返す
  return newimg,rs2_ascend,rs3_ascend,triangle_xy

def stats_split(stats_v,img):
  w,h=img.shape[1],img.shape[0]
  _print('stats_v',stats_v)
  st_v=[]
  min_y=1000
  max_h=0
  if len(stats_v)==1 and stats_v[0][0]==0:
    pass
  else:
    for i in range(len(stats_v)-1):
      _print('**',stats_v[i])
      if i==0:
        x0,y0,w0,h0,a0=stats_v[i]
      x1,y1,w1,h1,a1=stats_v[i+1]
      # if x0/w>0.08:
      #   x1=stats_v[i+1][0]
      _print('x1-x0,h1,y1+h1,h*0.18',x1-x0,h1,y1+h1,h*0.12)
      if x1-x0>100 and h1>100 and (h1+y1)>h*0.12:
          st_v.append(stats_v[i+1])
          x0,y0,w0,h0,a0=x1,y1,w1,h1,a1

      if y0!=0:
        min_y=min(min_y,y0)
      # print('min_y',min_y)
      if h0 > 300:
        max_h=max(max_h,h0)
    # if x1-x0>100 and h0>100:
    #       st_v.append(x1)
  _print('st_v',st_v,min_y)
  return st_v,min_y,max_h

def del_side_noise(st_v,img_disp3,min_y,max_h,lines,leftmost_characters):
  #最初のstatsより左側で5%以内のノイズ削除
  img_disp3=img_disp3.astype(np.uint8)
  # img_disp3=cv2.cvtColor(img_disp3, cv2.COLOR_GRAY2BGR)
  _print('st_v',len(st_v))
  if len(st_v)>1 and st_v[0][0]<img_disp3.shape[0]*0.05:
    cv2.rectangle(img_disp3,(0,0),(st_v[0][0],img_disp3.shape[0]),(255,255,255),-1)

  #右側1%のノイズ削除
  cv2.rectangle(img_disp3,(int(img_disp3.shape[1]*0.99),int(img_disp3.shape[0]*0.12)),(int(img_disp3.shape[1]),int(img_disp3.shape[0])),(255,255,255),-1)

  if img_disp3.shape[1]*0.1>st_v[0][0]:
    cv2.rectangle(img_disp3,(0,st_v[0][1]),(st_v[0][0],img_disp3.shape[0]),(255,255,255),-1)
  if leftmost_characters!=9999 and img_disp3.shape[1]*0.15>leftmost_characters:
    cv2.rectangle(img_disp3,(0,0),(leftmost_characters,img_disp3.shape[0]),(255,255,255),-1)
  # Statsベースで縦線描画
  # for i,st in enumerate(st_v):
  #   print('st',st,st_v[i][0],st_v[i][0]+st_v[i][2],min_y)
  #   pixelValue1 = img_disp3[st_v[i][0], min_y]
  #   print('pixelValue1 = ' + str(pixelValue1))
  #   pixelValue2 = img_disp3[st_v[i][0]+st_v[i][2], min_y]
  #   print('pixelValue1 = ' + str(pixelValue2))
  #   cv2.line(img_disp3, (st_v[i][0], min_y), (st_v[i][0]+st_v[i][2], min_y+max_h), (0, 0, 0), thickness=2, lineType=cv2.LINE_AA)

  # Lines ベースで縦線描画
  if np.any(lines):
      for line in lines:
        x1, y1, x2, y2 = line[0]
        # 縦線を引く
        img_disp3 = cv2.line(img_disp3, (x1,y1), (x2,y2), (255,255,255), 2)

  # img_disp3=cv2.cvtColor(img_disp3, cv2.COLOR_BGR2GRAY)
  # img_disp_o,dst=[],[]
  return img_disp3

def check_image_data(image):
  from PIL import Image
  import numpy as np
  #画像データがNumPyか、Pillowかを調べる'''
  #if isinstance(image, np.ndarray):
      #print("NumPy Image")
  #elif isinstance(image, Image.Image):
        #print("Pillow Image")

def del_line_str_right(img,img_bk,leftmost_characters):
  #画像を読込
  #img=cv2.imread(filename)
  #img_th3：縦線、img_disp：横線除去後　
  img_disp,stats_v,img_th3,lines=del_lines(img)
  #202230711コメントアウト
  #img_disp=cv2.cvtColor(img_disp, cv2.COLOR_BGR2GRAY)
  #check_image_data(img_disp)

  st_v,min_y,max_h=stats_split(stats_v,img)
  _print('stats_v',st_v)
  #左のノイズ除去と縦線描画
  if len(st_v)>0:
    img_disp=del_side_noise(st_v,img_disp,min_y,max_h,lines,leftmost_characters)
  _print('stats_v',stats_v)
  try:
    newimg,rs2_ascend,rs3_ascend,triangle_xy=str_right(img_disp,img_bk,stats_v,img_th3)
    _cv2_imshow(newimg)
  except:
    newimg=img_disp.copy()
    _cv2_imshow(newimg)
  
  del img_th3
  #import psutil
  #mem = psutil.virtual_memory()  
  #print('メモリ使用率1:',int(mem.used/mem.total*1000)/1000)
  #import gc
  #gc.collect()
  #print('メモリ使用率2:',int(mem.used/mem.total*1000)/1000)
  return newimg,img_disp,rs2_ascend,rs3_ascend,stats_v,triangle_xy



if __name__ == "__main__":
    #### メイン ####
    filename='/content/03 (3).jpg'
    # img=del_triangle(cv2.imread(filename))
    img=cv2.imread(filename)

    #マーカー除去
    # #地色除去
    img, img_bk = preprocess_image_v2ac(img)

    _cv2_imshow(img)

    _cv2_imshow(img_bk)
    try:
      newimg,img_disp,rs2_ascend,rs3_ascend,stats_v,triangle_xy=del_line_str_right(img,img_bk)
      _cv2_imshow(newimg)
      _cv2_imwrite(filename+'_out.jpg',newimg)
    except:
      newimg=img.copy()
      _cv2_imshow(img)
      _cv2_imwrite(filename+'_out.jpg',img)
    # _print('triangle_xy',triangle_xy)
    _cv2_imshow(newimg)
    _cv2_imwrite(filename+'_out.jpg',newimg)

# if __name__ == "__main__":
#   import glob
#   import os
#   dir='/content/test/*'
#   path='/content/test/'
#   for i,f in enumerate(glob.glob(dir)):
#     if i==0:
#       filename=os.path.split(f)[1]
#       img=cv2.imread(path+filename)
#       #マーカー除去
#       img=del_yellow(img)
#       # cv2_imshow(img)
#       img_bk=img
#       newimg,img_disp,rs2_ascend,rs3_ascend=del_line_str_right(img)
#       cv2_imshow(newimg)
def replace_triangle_k(img):
    #　画像の置換（△→-）
    # 入力画像、テンプレート画像を読み込む。

    path = _get_sample_img_path('triangle_k/*.jpg')
    #path = '/triangle_k/*.jpg'
    files = glob.glob(path)         # 削除対象の画像を置くフォルダ
    triangle_xy,tr=[],[]

    for file in files:
      print(file)
      # テンプレートマッチングを行う。
      templ = cv2.imread(file)          #削除対象読込
      result = cv2.matchTemplate(img, templ, cv2.TM_CCOEFF_NORMED)
      # print(result)
      if len(result)!=0:
        # 最も類似度が 0.9 以上の位置を取得する。
        ys, xs = np.where(result >= 0.8)
        # print(ys,xs)
        #近傍の点は省く１
        i=0
        for x,y in zip(xs,ys):
          i+=1
          if i==1:
            x0,y0=x,y
            triangle_xy.append([x,y,templ.shape[1],templ.shape[0]])
            print('x,y',x,y)
          if abs(x-x0)+abs(y-y0)<10:
            continue
          else:
            x0,y0=x,y
            triangle_xy.append([x,y,templ.shape[1],templ.shape[0]])
        # _print('x,y',triangle_xy)
        templ,result=[],[]
    #近傍の点は省く２（１７の２ページ目の'貸倒引当金'の行のように'△'が２個ある場合の対策）
    triangle_xy = sorted(triangle_xy,key=lambda x:(x[0],x[1]))

    #近傍の対象点を1とする
    trflg=np.zeros(len(triangle_xy))
    tri=[]
    for i in range(len(triangle_xy)):
      for j in range(i+1,len(triangle_xy)):
        x0,y0,_,_=triangle_xy[i]
        x1,y1,_,_=triangle_xy[j]
        d=distance((x0,y0),(x1,y1))
        if d<10:
          trflg[j]=1
    print(trflg)
    for k,tf in enumerate(trflg):
      if int(tf)==0:
        tri.append(triangle_xy[k])
    # _print(tri)

    # # 類似画像を消す１
    dst2 = img.copy()
    # # print(triangle_xy)
    # triangle_xy=sorted(triangle_xy,key=lambda x:(x[1],x[0]))
    # # print('111',len(triangle_xy),triangle_xy)
    # for x, y,w,h in  triangle_xy:
    #     # print(x,y,x + w, y + h)
    #     cv2.rectangle(
    #         dst2,(x, y),(x+w+1 , y + h),
    #         color=(255, 255, 255),
    #         thickness=-1,
    #     )

    for x, y,w,h in  triangle_xy:
      #マイナス表示を囲う
        #cv2.rectangle(
        #    dst2,(x-2 , y-2),
        #    (x+w+2,y+h+2),
        #    color=(255, 0, 0),
        #    thickness=2,
        #    )
        cv2.rectangle(
          dst2,(x-2 , y-2),
          (x+w+2,y+h+2), (255, 255,255),thickness=-1)
        
    print('tri',tri)
    return dst2,tri