'''
This file accompanies other files in the evacuation simulation project.
people: Nick B., Matthew J., Aalok S.

In this file we define a useful class for the agent, 'Person'
'''

class Person:
    id = None
    rate = None  # 移動一個單位距離所需的時間
    strategy = None  # 代理選擇最近出口的機率
    loc = None, None  # 變數，追踪此代理的位置（xy座標）

    alive = True  # TODO 應該去掉這個變數嗎？我們實際上不太需要它
    safe = False  # 成功退出後標記為安全。有助於追踪還有多少人需要完成

    exit_time = 0  # 這個代理從起點到達安全區所花的時間

    def __init__(self, id, rate: float = 1.0, strategy: float = 0.5, loc: tuple = None):
        '''
        建構方法
        ---
        id: 代理的唯一標識符
        rate: 移動速率，即移動一個單位距離所需的時間
        strategy: 移動策略，即選擇最近出口的機率
        loc: 代理的初始位置（xy座標）
        '''
        self.id = id
        self.rate = rate
        self.strategy = strategy
        self.loc = tuple(loc)

    def move(self, nbrs, rv=None):
        '''
        當這個人完成他們當前的移動時，我們必須安排下一個移動
        ---
        nbrs (list): 附近的鄰居位置及其屬性的列表
        rv: 隨機變數，這裡未使用

        return: tuple，代表該代理選擇移動到的位置
        '''
        nbrs = [(loc, attrs) for loc, attrs in nbrs
                if not(attrs['F'] or attrs['W'])]
        if not nbrs:
            return None

        # 選擇離安全區最近的位置作為目標
        loc, attrs = min(nbrs, key=lambda tup: tup[1]['dist_weight'])
        self.loc = loc  # 更新人的位置

        # 如果移動到了安全區，將安全標誌設為True
        if attrs['S']:
            self.safe = True
        # 如果移動到了火災區，將存活標誌設為False
        elif attrs['F']:
            self.alive = False

        return loc