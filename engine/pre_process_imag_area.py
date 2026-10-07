# Ver.001

import cv2
#from google.colab.patches import cv2_imshow
import numpy as np
# from IPython.display import Image, display
# from matplotlib import pyplot as plt
import glob
import gc

################  <<<<<<<<<<<<<<<<<<<<<  >>>>>>>>>>>>>>>>>>>  ##############
# v2ac 画像の処理 tilt より後、del_line_str_rightより前の処理を書いてください
def _cv2_imshow(img):
    pass
    # cv2_imshow(img)
def cv2_imshow(img):
    pass
    # cv2_imshow(img)
def _print(*txt):
    pass
    # print(txt)
def preprocess_image_v2ac(img):
    #マーカー除去
    img = del_yellow(img)
    img_bk = img.copy()
    #地色除去
    img = del_gr_color(img)
    return img, img_bk

def del_yellow(img):
  # _cv2_imshow(img)
  result=img.copy()
  # 黄色除去
  after_color = [255, 255, 255]
  before_color1 = [0, 140, 180]
  result[np.where((result >= before_color1).all(axis=2))] = after_color
  # _cv2_imshow(result)
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
  cv2.imwrite('result.jpg',result)
  _cv2_imshow(result)
  return result

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

#同じ行を(x座標+w)の小さい順にソートしまとめる
def select_str(resortdata):
  #print('select_str:resortdata',resortdata)
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

  # for i,r2 in enumerate(rs):
  #   if i==12:
  #     print('i=12',r2)
  #print('select_str:rs',rs)
  #rs 行番号,x,y,w,h,area
  r=[]
  return rs

def sort_right_alighnment(rs2):
  rs3=[]
  for r2 in rs2:
    r3=sorted(r2,key=lambda x:(x[0],-x[1]))
    rs3.append(sorted(r2,key=lambda x:(x[0],-x[1])))
  return rs3

#白紙画像作成
def new_palette(img):
  w,h=img.shape[1],img.shape[0]
  import numpy as np
  img_white = np.ones((h,w, 3),np.uint8)*255
  imgwhite=pil2cv(img_white)
  dst = cv2.resize(imgwhite, dsize=(int(w/1),int(h/1)))
  return dst


def str_right(img_disp,img_bk,stats_v,img_th3):
  print('img_disp.shape',img_disp.shape)
  cv2_imshow(img_disp)
  img_disp_o=img_disp.copy()
  h,w=img_disp.shape[0],img_disp.shape[1]
  w_left,w_right=int(w*0.03),int(w*0.97)
  print('w_left,w_right',w_left,w_right)

  #文字位置をラベリング
  #print('★★★　★★★')
  strdata2,dst=extract_str(img_disp)
  print('1',len(strdata2))
  cv2_imshow(dst)
  strdata3,dst=re_extract_str(dst,strdata2)
  cv2_imshow(dst)

  #y方向でソート
  #print('ddddd----strdata3------>',strdata3)
  resortdata2,rs2_yminmax=scan_rows(dst,strdata3)
  #print('resortdata2-------->',resortdata2)
  #print('rs2_yminmax＊＊＊',rs2_yminmax)
  # for re in resortdata2:
  #   print(re)

  #行を作成
  rs=select_str(resortdata2)

  # for i,r in enumerate(rs):
  #   if i==14:
  #     print(i,r)

  # 行間をチェック＆クリア
  if len(stats_v) >0:
    rs,img2=check_row(rs2_yminmax,stats_v,img_disp_o,img_bk,img_th3)

    #2回目ループ#文字位置をラベリング
    _print('☆彡')
    img2=cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    # img2=255-img2
    _cv2_imshow(img2)
    strdata,dst=extract_str(img2)
    # print('1',len(strdata))
    _print('dst2')
    _cv2_imshow(dst)
    strdata2,dst=re_extract_str(dst,strdata)

  ##2y方向でソート
  resortdata3,rs2_yminmax=scan_rows(dst,strdata2)

  ##2行を作成
  rs=select_str(resortdata3)

  #文字内包
  rs2=marge_string(rs)
  # for r2 in rs2:
  #   _print(r2)
  #元データx昇順
  rs2_ascend=rs2
  #print("rs2_acsend------->",rs2_ascend)
  #元データx降順
  rs3_descend=sort_right_alighnment(rs2_ascend)
  new_img=new_palette(img2)
  #白紙に右寄せしてプロット
  newimg,rs3_ascend,_=copy_pack_position(img_bk,rs3_descend)

  # for i,r3 in enumerate(rs3_ascend):
  #   print(i,r3)

  #新イメージと元データ、移動後データを返す
  triangle_xy=[]
  return newimg,rs2_ascend,rs3_ascend,triangle_xy

#文字をくっつけて白紙にコピー(右寄)
def copy_pack_position(im,rs):
  # for i,r in enumerate(rs):
    # if i==39:
    #   print('////',i,r)
  _print('shape',im.shape)
  # cv2.imwrite('im.jpg',im)
  # im=remove_hahen_noise(im)
  # im,triangle_xy = replace_triangle(im) # △の処理
  # im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

  _print('shape',im.shape)
  #文字間隔:pitch
  #列間隔:c_width
  pitch=1
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
        # if i==12:
        #   print('i,xn,x0,y0,w0,h0',i,xn,x0,y0,w0,h0)
        # rs2.append([i,x0,y0,w0,h0])
        rs2_ascend=sorted(rs2,key=lambda x:(x[0],-x[1]))
        if j==len(ds)-2:
          xn=xn-w1-pitch
          obj=im[y1:y1+h1,x1:x1+w1]
          new_img[y1:y1+h1,xn:xn+w1]=obj
          rs2.append([i,xn,y1,w1,h1])
          # if i==12:
            # print('*i,xn,x0,y0,w0,h0',i,xn,x0,y0,w0,h0)
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
  _cv2_imshow(new_img)
  triangle_xy = []
  del im
  return new_img,rs3_ascend,triangle_xy

################  <<<<<<<<<<<<<<<<<<<<<  >>>>>>>>>>>>>>>>>>>  ##############

# img画像内の文字の範囲を全て抽出して変数に格納
def extract_str(img_disp):
  img_disp=img_disp.astype(np.uint8)
  img_color = cv2.cvtColor(img_disp, cv2.COLOR_GRAY2BGR)

  h,w=img_disp.shape[0],img_disp.shape[1]

  # 二値化(二値化して白黒反転、下限値120が')'を読めるかポイント)
  # retval, img3 = cv2.threshold(img_disp, 120, 255, cv2.THRESH_BINARY_INV)
  retval, img3 = cv2.threshold(img_disp, 150, 255, cv2.THRESH_BINARY_INV)
  print('img3************************************')
  cv2_imshow(img3)

  # クロージング処理（細切れ状態を防ぐため）
  kernel = np.ones((3, 3), np.uint8)
  img4 = cv2.morphologyEx(img3, cv2.MORPH_CLOSE, kernel, iterations=3)
  img4=img4.astype(np.uint8)
  # img4=255-img4
  # img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
  print('クロージング処理')
  cv2_imshow(img4)
  # print('img4',img4.shape)

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

  # 結果表示
  for i in range(1, retval):
      x, y, width, height, area = stats[i] # x座標, y座標, 幅, 高さ, 面積
      center_x,center_y=centroids[i]
      center_x,center_y=int(center_x),int(center_y)
      ratio=width/height

      # if area<40000 and area > 150 and ratio>0.05 and ratio < 10 : # 面積がxxx00画素以上の部分,縦横比で絞込
      # areaを大きくすると1が読めなくなるので注意
      # if area<100000 and area > 60 and ratio>0.04 and ratio < 10 and height <80 and x/w>0.08: # 面積がxxx00画素以上の部分,縦横比で絞込
      if area<100000 and area > 2 and ratio>0.04 and ratio < 10 and height <80 : #20231007
          # cv2.rectangle(img4,(x,y),(x+width,y+height),(0,0,0),-1)
        cv2.rectangle(img_color,(x,y),(x+width,y+height),(0,0,255),-1)
        # if i<= 4:
        #     cv2.putText(img_color, f"{i}", (x-100, y), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 0), 1, cv2.LINE_AA)
        #     cv2.putText(img_color, f"{x}", (x-80, y+30), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 1, cv2.LINE_AA)
        #     cv2.putText(img_color, f"{y}", (x-80, y+60), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 1, cv2.LINE_AA)
        #     cv2.putText(img_color, f"{height}", (x-80, y+90), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 0), 1, cv2.LINE_AA)
        #     cv2.putText(img_color, f"{width}", (x-80, y+120), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 1, cv2.LINE_AA)
        str_data.append([x, y, width, height,center_x,center_y])

  # dst = cv2.resize(img4, dsize=(w,h))
  dst = cv2.resize(img_color, dsize=(w,h))
  str_data2=sorted(str_data,key=lambda x:(x[1],x[0]))
  # print('ラベリング１')
  cv2_imshow(dst)
  #cv2.imwrite('dst.jpg',dst)
  # print('strdata1',str_data)
  print(str_data)
  print(str_data2)
  # for i,std in enumerate(str_data2):
  #   print(i,std)
  img2,img3,img4,img_color=[],[],[],[]
  return str_data2,dst

def re_extract_str(dst,str_data2):
##追加の読取処理
# 灰色除去
  _print('dstshape',dst.shape)
  dst=cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
  result=np.where(dst>=40 ,255,dst)
  result=255-result
  _cv2_imshow(result)
  kernel = np.ones((3,3), np.uint8)
  result = cv2.dilate(result, kernel, iterations=2)
  _print('result2回目')
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
      # areaを大きくすると1が読めなくなるので注意
      if area<40000 and area > 3 and ratio>0.04 and ratio < 10 and height <80 : # 面積がxxx00画素以上の部分,縦横比で絞込
          cv2.rectangle((img_2),(x,y),(x+width,y+height),(0,0,255),-1)
          # cv2.putText(img_2, f"{x}", (x, y), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1, cv2.LINE_AA)
          # cv2.putText(img_2, f"{y}", (x, y+12), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1, cv2.LINE_AA)
          # cv2.putText(img_2, f"{height}", (x, y+24), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 0), 1, cv2.LINE_AA)
          # cv2.putText(img_2, f"{y+height}", (x, y+36), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 255), 1, cv2.LINE_AA)
          str_data2.append([x, y, width, height,center_x,center_y])

  # dst = cv2.resize(result, dsize=(w,h))
  #print('str_data2@re_extract_str--->',len(str_data2))
  str_data3=sorted(str_data2,key=lambda x:(x[1],x[0]))
  _print('img_2')
  _cv2_imshow(img_2)
  cv2.imwrite('img_2.jpg',img_2)
  #print('strdata3----->',str_data3)
  del dst
  del result
  return str_data3,img_2

def del_line_str_right(img,img_bk,leftmost_characters=0):
  #画像を読込
  #img_th3：縦線、img_disp：横線除去後
  img_disp=[]
  img_disp,stats_v,img_th3,lines=del_lines(img)
  # _print('img_disp000',type(img_disp),img_disp.shape)
  print('img_disp')
  # check_image_data(img_disp)
  cv2_imshow(img_disp)

  # 変数をデフォルト値で初期化
  rs2_ascend, rs3_ascend, triangle_xy = None, None, None
  newimg,rs2_ascend,rs3_ascend,_=str_right(img_disp,img_bk,stats_v,img_th3)
  #rs2_ascend, rs3_ascend, triangle_xy = [], [], []  # または他の適切なデフォルト値
  triangle_xy = []  # または他の適切なデフォルト値
  del img_th3
  del img_bk

  return newimg,img_disp,rs2_ascend,rs3_ascend,triangle_xy

# 行判定
def scan_rows(img,strdata):
  width,height=img.shape[1],img.shape[0]
  # print('-------->',width)
 #y方向でソート
  # strdata_sorted = sorted(strdata,key=lambda y:min( y for y in strdata[1]))
  dsrt=sorted(strdata,key=lambda y:(y[5],y[1]))
  #print('dsrt---->',len(dsrt),dsrt)
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
      #print('*_*---->',row_num,dsrt[i][0],dsrt[i][1],dsrt[i][2],dsrt[i][3],dsrt[i][4])
      row_num += 1
    #最終data追加
    if i==len(dsrt)-2:
      re_sort_data.append([row_num,dsrt[i+1][0],dsrt[i+1][1],dsrt[i+1][2],dsrt[i+1][3],dsrt[i][4]])
      #print('+_+---->',row_num,dsrt[i+1][0],dsrt[i+1][1],dsrt[i+1][2],dsrt[i+1][3],dsrt[i][4])

  # 各行毎にx方向で並べ替え
  re_sort_data2=sorted(re_sort_data,key=lambda re_sort_data:(re_sort_data[0],re_sort_data[1]))

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
        #最終行追加
        if i == len(rs2_yminmax)-2:
          # print('a5')
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

  return rx_marge,rs2_yminmax

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
  kerneldot = np.zeros((5,5), np.uint8)
  kerneldot[2,0] = 1
  kerneldot[2,2] = 1
  kerneldot[2,4] = 1
  #print('kernel2dot',kerneldot)
  kernel3 = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

  gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
  gray2=gray.copy()
  print('gray')
  cv2_imshow(gray2)
  h,w=gray.shape
  #クリア
  # gray = cleary(gray, clip_limit=3, grid=(8, 8), thresh=255)

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
  print('横線を太く')
  cv2_imshow(img_th4)
  # cv2.imwrite('img_th4.jpg',img_th4)
  img_th4 = cv2.morphologyEx(img_th4, cv2.MORPH_OPEN, kernel3)

  ##############　20240911　横線を消す　###################
  img_th4=np.where(img_th4>5,255,0)
  img_th4=np.where(img_th4<=50,gray,255)
  print('img_th4')
  cv2_imshow(img_th4)
  # ラベリング(横)Statsベース
  # retval, labels, stats, centroids = cv2.connectedComponentsWithStats(img_disp3)
  # print('横stats',stats)
  stats_h=[]

  #元画像のディメンションを合わせる
  img_disp2 = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

  #縦線を書く
  _print('gray2')
  _cv2_imshow(gray2)

  img_th2 = cv2.dilate(gray2, kernel2, iterations=20)
  #print('img_th2:dilate')
  _cv2_imshow(img_th2)
  cv2.imwrite('img_th_dilate.jpg',img_th2)

  # img_th2 = cv2.erode(img_th2, kernel2, iterations=20)
  # print('img_th2:erode')
  # cv2_imshow(img_th2)
  img_th2 = 255-img_th2

  # 2値画像を収縮する。(縦線を太くする　20230713追記)
  img_th2 = cv2.dilate(img_th2, kernel3,iterations=4)
  print('img_th2:1')
  cv2_imshow(img_th2)
  cv2.imwrite('img_th2_1.jpg',img_th2)
  # 縦線を上下に伸ばす(20230731追記)
  img_th2 = cv2.dilate(img_th2, kernel2,iterations=20)
  _print('img_th2:2')
  _cv2_imshow(img_th2)
  cv2.imwrite('img_th2_2.jpg',img_th2)
  img_th3 = 255-img_th2
  _print('img_th3:1')
  _cv2_imshow(img_th3)
  #img_th3>200
  img_th3=np.where(img_th3>250,255,0)
  print('img_th3:2')
  cv2_imshow(img_th3)
  img_disp3=np.where(img_th3<50,255,img_th4)
  _print('縦線補完後')
  _cv2_imshow(img_disp3)
  #ラベリング（縦）Stats
  retval, labels, stats, centroids = cv2.connectedComponentsWithStats(img_th2)
  stats=stats.tolist()
  stats=sorted(stats,key=lambda x:(x[0]))

  # ラベリング（縦）Hogh
  lines = cv2.HoughLinesP(img_th2,rho=1,theta=np.pi/360,threshold=100,minLineLength=200,maxLineGap=6)
  _print(lines)

  # print('del_line_stats',stats)
  # 結果表示（縦）
  cnt=0
  img_disp3=img_disp3.astype(np.uint8)
  # img_disp3 = cv2.cvtColor(img_disp3, cv2.COLOR_GRAY2BGR)

  #print('縦：img_disp3')
  ##############　20230711　縦線を消す　###################
  img_th3=np.where(img_th3>5,255,0)
  img_disp3=np.where(img_th3<=50,255,img_disp3)
  #print('202307011縦線消す---->')
  print('img_th3:3　縦線のみ')
  cv2_imshow(img_th3)
  print('img_disp3★　')
  cv2_imshow(img_disp3)
  gray,gray2,img_th,img_th2=[],[],[],[]
  return img_disp3,stats,img_th3,lines

#接近又は内包される文字を統合する
def marge_string(rs):
  #print('marge_string:new_rs:',rs)
  # n=0
  # for i,r in enumerate(rs):
  #   for j in range(len(r)):
  #     if i==12:
  #       a,b,c,d,e,f=r[j]
  #       print(a,b,c,d,e,f)
  #     n+=1

  wh_max=get_max_wh(rs)
  r2,rs2,w2=[] ,[],0
  Xmin,Xmax,Ymin,Ymax,span=0,0,0,0,0

  n=0
  for i,r in enumerate(rs):
        flg,x0,y0,w0,h0,area0,x1,y1,w1,h1,area1,x_right=0,0,0,0,0,0,0,0,0,0,0,0
        if len(r)==1:
          #print('i,r[0]',i,r[0])
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
                _print('aaa範囲そのまま',n,x0,w0,x1,w1)
                x0,y0,w0,h0=x1,y1,w1,h1
              else:
                #範囲拡大
                _print('bbb範囲拡大',n)
                # if n>=108 and n<=110:
                #   print('*/',x0,w0,x1,w1)

                x0,y0,w0,h0=Xmin,Ymin,Xmax-Xmin,Ymax-Ymin
              _print('ccc',n,x0,w0,x1,w1)
            _print('ddd',n,x0,w0,x1,w1)
            _print('minmax:Xmin,Xmax,Ymin,Ymax',Xmin,Xmax,Ymin,Ymax)
            _,x1,y1,w1,h1,area1=r[j+1]

            # 次との間隔span
            span=x1-(x0+w0)
            # print('span,x1,x0,w0=',span,x1,x0,w0)

            Xmin,Xmax,Ymin,Ymax=min(x0,x1),max(x0+w0,x1+w1),min(y0,y1),max(y0+h0,y1+h1)
            _print('minmax',Xmin,Xmax,Ymin,Ymax)
            x_right=x0+w0
            w2=Xmax-Xmin
            if x_right >= x1:
              flg=1
              if n>=151 and n<=152:
                _print('範囲拡大、n,flg',n,flg)
              xk,yk,wk,hk=x0,y0,w0,h0
            else:
              flg=0
              # print('append',n,x0,w0,x1,w1)
              if w0!=0:
                # print(i,x0,y0,w0,h0,span)
                r2.append([i,x0,y0,w0,h0,span])
              _print('範囲そのまま,n',n)
            n+=1
        if len(r)>0:
          if flg==1:
            # print('AAA')
            maxw=max(w1,x1+w1-x0)
            maxh=max(rs[i][len(r)-2][4],rs[i][len(r)-1][4])
            _print('append',i,rs[i][len(r)-2][1],rs[i][len(r)-2][2],maxw,maxh)

            # r2.append([i,min(xk,rs[i][len(r)-2][1]),min(yk,rs[i][len(r)-2][2]),max(wk,maxw),max(hk,maxh),span])
            if maxw !=0:
              # print(i,rs[i][len(r)-2][1],rs[i][len(r)-2][2],maxw,maxh,span)
              r2.append([i,rs[i][len(r)-2][1],rs[i][len(r)-2][2],maxw,maxh,span])
            # xk,yk,wk,hk=0,0,0,0
          else:
            # print('BBB')
            if w1 !=0:
              # print(i,x1,y1,w1,h1,span)
              r2.append([i,x1,y1,w1,h1,span])

        _print('last:flg',flg,r2)
        rs2.append(r2)
        r2=[]
        n+=1
  # print('rs2',rs2)
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
  # im=remove_hahen_noise(im)
  # im,triangle_xy = replace_triangle(im) # △の処理
  # im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

  _print('shape',im.shape)
  #文字間隔:pitch
  #列間隔:c_width
  pitch=1
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
          xn=width-0-w0
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
        if i<=10:
          print('i,xn,x0,y0,w0,h0',i,xn,x0,y0,w0,h0)
        # rs2.append([i,x0,y0,w0,h0])
        rs2_ascend=sorted(rs2,key=lambda x:(x[0],-x[1]))
        if j==len(ds)-2:
          xn=xn-w1-pitch
          obj=im[y1:y1+h1,x1:x1+w1]
          new_img[y1:y1+h1,xn:xn+w1]=obj
          rs2.append([i,xn,y1,w1,h1])
          # if i==12:
            # print('*i,xn,x0,y0,w0,h0',i,xn,x0,y0,w0,h0)
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
  _cv2_imshow(new_img)
  triangle_xy=[]
  del im
  return new_img,rs3_ascend,triangle_xy

#各行のwの最大値を省いた平均と２番目に大きい値を取得
def get_max_wh(rs):
  wh_max,wmax,hmax,w_ave,w_sum,i=[],0,0,0,0,0

  #２番目に大きいwを取得
  wmax_2nd,i=0,0
  for r2 in rs:
    after_r2=sorted(r2,key=lambda x:(x[-3]))
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

def check_row(rs2_yminmax,stats_v,img_disp_o,img_bk,img_th3):
  stats_v=sorted(stats_v,key=lambda x:(x[0]))
  #print('stats_v',stats_v)
  img_disp_o=cv2.cvtColor(img_disp_o, cv2.COLOR_GRAY2BGR)
  #print('shape',img_disp_o.shape)
  _print('img_disp_o:1')
  _cv2_imshow(img_disp_o)
  # gap,a,b,x0,y0,x1,y1=[],[],[],[],[],[],[]
  #j行目とj+1行目の縦線の範囲の隙間（x0,y0,x1,y1)
  for j in range(len(rs2_yminmax)-1):
    #print('j',j)
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

  _print('img_disp_o:2')
  _cv2_imshow(img_disp_o)
  return rs2_yminmax,img_disp_o


#白紙画像作成
def new_palette(img):
  w,h=img.shape[1],img.shape[0]
  import numpy as np
  img_white = np.ones((h,w, 3),np.uint8)*255
  imgwhite=pil2cv(img_white)
  dst = cv2.resize(imgwhite, dsize=(int(w/1),int(h/1)))
  return dst

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

if __name__ == "__main__":
    filename='scrnli_2024_9_11 20-47-47.png'

    # img=del_triangle(cv2.imread(filename))
    img=cv2.imread(filename)
    #マーカー除去
    # #地色除去
    img, img_bk = preprocess_image_v2ac(img)

    cv2_imshow(img)
    # cv2_imshow(img_bk)
    img_disp=[]
    newimg,img_disp,rs2_ascend,rs3_ascend,_=del_line_str_right(img,img_bk)
    print('newimg')
    cv2_imshow(newimg)
    cv2.imwrite('migiyose.jpg',newimg)