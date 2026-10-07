import math
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

class Point(object):

    def __init__(self,x=0,y=0):
        self.x  = x
        self.y  = y

    def x(self):
        return self.x

    def y(self):
        return self.y

    def set(self, x=0, y=0):
        self.x = x
        self.y = y

    def get(self):
        return [self.x,self.y]

class Bound(object):

    def __init__(self, vertices=None, np_array=None, left=0, top=0, right=0, bottom=0):
        if vertices:
            self.rect = [999999,999999,0,0]   # [X1:left(0), Y1:top(1), X2:right(3), Y2:bottom(3)]

            for vertex in vertices:
                if vertex.x < self.rect[0]:
                    self.rect[0] = vertex.x
                elif vertex.x > self.rect[2]:
                    self.rect[2] = vertex.x

                if vertex.y < self.rect[1]:
                    self.rect[1] = vertex.y
                elif vertex.y > self.rect[3]:
                    self.rect[3] = vertex.y

        elif np_array is not None:
            self.rect = [999999,999999,0,0]   # [X1:left(0), Y1:top(1), X2:right(3), Y2:bottom(3)]
            try:
                for r in np_array:
                    if r[0] < self.rect[0]:
                        self.rect[0] = r[0]
                    elif r[0] > self.rect[2]:
                        self.rect[2] = r[0]

                    if r[1] < self.rect[1]:
                        self.rect[1] = r[1]
                    elif r[1] > self.rect[3]:
                        self.rect[3] = r[1]
            except:
                pass

        else:
            self.rect = [left, top, right, bottom]   # [X1:left, Y1:top, X2:right, Y2:bottom]

        self.recalc()

    def recalc(self):
        # [X, Y]
        self.size   = [self.rect[2]-self.rect[0],self.rect[3]-self.rect[1]]
        # [X, Y]
        self.center = [self.rect[0]+self.size[0]/2,self.rect[1]+self.size[1]/2]

    def revise(self):
        if self.rect[0] > self.rect[2]: # X
            self.rect[0], self.rect[2] = self.rect[2], self.rect[0]
        if self.rect[1] > self.rect[3]: # Y
            self.rect[1], self.rect[3] = self.rect[3], self.rect[1]

        self.recalc()

    def is_group(self, obj, height, width, char_width):
        if (self.center[1] >= obj.center[1]-height) and (self.center[1] <= obj.center[1]+height):
            space = obj.get_space(self)
            if space < char_width+width: # 文字が離れている?
            #if self.rect[2] + char_width*1.5 >= obj.rect[0]:
            #if (self.rect[0] - obj.rect[2])
            #if self.rect[2] + space + space >= obj.rect[0]:
                return True

        return False

    def is_same_line(self, obj, height):
        if (self.center[1] >= obj.center[1]-height) and (self.center[1] <= obj.center[1]+height):
            return True

        return False

    def is_empty(self):
        return True if self.size == [0,0] else False

    def is_equal(self, bound):
        return self.rect == bound.rect

    # search_part_flag: True=一部, False=包括
    def is_included(self, bound, search_part_flag): #bound に selfが入っているか

        if search_part_flag: # 部分
            if max(self.rect[0],bound.rect[0]) <= min(self.rect[2],bound.rect[2]) and max(self.rect[1],bound.rect[1]) <= min(self.rect[3],bound.rect[3]):
                return True
            else:
                return False
        else:               # 全体
            if self.rect[0] < bound.rect[0]:
                return False
            if self.rect[2] > bound.rect[2]:
                return False
            if self.rect[1] < bound.rect[1]:
                return False
            if self.rect[3] > bound.rect[3]:
                return False

            return True

        #if self.rect[1] <= bound.rect[1] <= self.rect[3]:
        ##if self.rect[1] <= bound.rect[1] and self.rect[3] >= bound.rect[1]:
        #    return True

        #if self.rect[1] <= bound.rect[3] <= self.rect[3]:
        ##if self.rect[1] <= bound.rect[3] and self.rect[3] >= bound.rect[3]:
        #    return True

        #if self.rect[1] >= bound.rect[1] and self.rect[3] <= bound.rect[3]:
        #    return True


        #return False

    def is_topleft_included(self, bound): #boundのtop,left が selfに入っているか

        if self.rect[0] <= bound.rect[0] <= self.rect[2] and self.rect[1] <= bound.rect[1] <= self.rect[3]:
            return True
        else:
            return False

    def is_center_included(self, bound): #boundのcenter が selfに入っているか

        if self.rect[0] <= bound.center[0] <= self.rect[2] and self.rect[1] <= bound.center[1] <= self.rect[3]:
            return True
        else:
            return False

    def get_center_distance(self, bound): #boundのcenter と selfののcenterの距離

        x = self.center[0] - bound.center[0]
        y = self.center[1] - bound.center[1]

        self.dist = math.sqrt((x*x)+(y*y))
        return self.dist

    def get_distance(self, bound, point=0): #boundのrect[point] と selfののrect[point]の距離
        p = self.rect[point] - bound.rect[point]
        self.dist = abs(p)
        return self.dist

    def get_x_overlap(self, bound): #boundのrect[point] と selfののrect[point]の距離
        self.dist = ((self.rect[2] - self.rect[0])+(bound.rect[2] - bound.rect[0])) - (max(self.rect[2],bound.rect[2]) - min(self.rect[0],bound.rect[0]))
        # l1 = self.rect[2] - self.rect[0]
        # l2 = bound.rect[2] - bound.rect[0]
        # l = max(self.rect[2],bound.rect[2]) - min(self.rect[0],bound.rect[0])
        # self.dist = (l1+l2) - l
        return self.dist

    def get_overlap_area(self, bound): #boundのrect[point] と selfののrect[point]の距離
        x_dist = ((self.rect[2] - self.rect[0])+(bound.rect[2] - bound.rect[0])) - (max(self.rect[2],bound.rect[2]) - min(self.rect[0],bound.rect[0]))
        y_dist = ((self.rect[3] - self.rect[1])+(bound.rect[3] - bound.rect[1])) - (max(self.rect[3],bound.rect[3]) - min(self.rect[1],bound.rect[1]))

        self.dist = x_dist * y_dist
        return self.dist

    def expand(self, new):
        if new.rect[0] < self.rect[0]:
            self.rect[0] = new.rect[0]
        # elif new.rect[2] > self.rect[2]:
        if new.rect[2] > self.rect[2]:
            self.rect[2] = new.rect[2]

        if new.rect[1] < self.rect[1]:
            self.rect[1] = new.rect[1]
        # elif new.rect[3] > self.rect[3]:
        if new.rect[3] > self.rect[3]:
            self.rect[3] = new.rect[3]

        self.recalc()

    def expand_wh(self, w, h):
        self.rect[0] -= w
        self.rect[2] += w

        self.rect[1] -= h
        self.rect[3] += h

        self.recalc()

    def offset(self, x, y):
        self.rect[0] += x
        self.rect[1] += y
        self.rect[2] += x
        self.rect[3] += y

        self.recalc()

    def scale(self, sx, sy):

        change = False
        if sx != '1.0':
            self.rect[0] = int(Decimal(str(self.rect[0] * Decimal(sx))).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
            #x0 = int(self.rect[0] * Decimal(sx))
            self.rect[2] = int(Decimal(str(self.rect[2] * Decimal(sx))).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
            #x2 = int(self.rect[2] * Decimal(sx))
            change = True

        if sy != '1.0':
            self.rect[1] = int(Decimal(str(self.rect[1] * Decimal(sy))).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
            y1 = int(self.rect[1] * Decimal(sy))
            self.rect[3] = int(Decimal(str(self.rect[3] * Decimal(sy))).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
            y3 = int(self.rect[3] * Decimal(sy))
            change = True

        if change == True:
            self.recalc()


    def minmax(self, bound):
        self.rect[0] = min(bound.rect[0], self.rect[0])
        self.rect[1] = min(bound.rect[1], self.rect[1])
        self.rect[2] = max(bound.rect[2], self.rect[2])
        self.rect[3] = max(bound.rect[3], self.rect[3])

    def get_rect(self):
        return self.rect
    def get_json_rect(self):
        return [str(self.rect[0]),str(self.rect[1]),str(self.rect[2]),str(self.rect[3])]
    def get_left(self):
        return self.rect[0]
    def get_right(self):
        return self.rect[2]
    def get_top(self):
        return self.rect[1]
    def get_bottom(self):
        return self.rect[3]
    def get_width(self):
        return self.size[0]
    def get_height(self):
        return self.size[1]
    def get_size(self):
        return self.size
    def get_center(self):
        return {'center_x':self.center[0],'center_y':self.center[1]}
        #return self.center
    def get_bound(self, prefix=''):
        return {prefix+'start_x':self.rect[0],prefix+'start_y':self.rect[1],prefix+'end_x':self.rect[2],prefix+'end_y':self.rect[3]}

    def to_string(self):
        return '{}, {}, {}, {}'.format(self.rect[0],self.rect[1],self.rect[2],self.rect[3])

    def is_left(self, obj):
        if self.rect[0] <= obj.rect[0]:
            return True
        return False

    def is_above(self, obj):
        if self.rect[1] <= obj.rect[3]:
            return True
        return False

    def is_left_above(self, obj):
        if self.rect[0] > obj.rect[0] or self.rect[1] > obj.rect[3]:
            return False
        return True

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

    def revise_width(self,left,right):
        if self.rect[0] < left:
            self.rect[0] = left
        if self.rect[2] > right:
            self.rect[2] = right

    def revise_height(self,top,bottom):
        if self.rect[1] < top:
            self.rect[1] = top
        if self.rect[3] > bottom:
            self.rect[3] = bottom