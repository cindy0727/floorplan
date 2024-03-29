#!/usr/bin/env python3

'''
This program is Free Software

Introduction
---
A PySimpleGUI-based graphical grid that allows users to annotate locations for
many kinds of terrains/members:
    N (normal/none)
    F (fire/danger)
    P (people)
    W (wall)
    S (safe zone)
    H (Hot)
    M (Medinum)

A square in the grid may be 
    0 or 1 of {N, F}
  AND 
    0 or 1 of {W, P}
If nothing, a square must have at least the 'N' attribute


Usage
---
1. Annotate
To annotate a square, click on a square in the grid. Click again to undo.

2. Select mode
To choose the attribute you wish to annotate with using Options > Editing mode.

3. Save to file
Choose File > Save in order to save the layout to txt (default: floor.txt)

4. Load and edit from file
(NotImplemented)
'''

import PySimpleGUI as sg
from random import randint
import argparse
from collections import defaultdict
import pickle
import pprint
from functools import lru_cache


pp = pprint.PrettyPrinter(indent=4)

class FloorGUI:

    def __init__(self, R, C, output=None):
        self.mode = 'Walls'
        self.R = R
        self.C = C
        self.output = output
        self.window = None
        self.graph = None


    def setup(self):
        '''
        makes the initial setup of the floor plan with R rows and C cols
        '''
        mode, R, C = self.mode, self.R, self.C 
        layout = []
      
        menu_def = [['File', ['Reset', 'Open', 'Save', 'Exit']],      
                    ['Options', ['Editing mode', 
                                 ['Walls', 'Bottleneck', 'Danger', 'People', 'Hot', 'Medinum'],]],
                    ['Help', '(NotImplemented) About...'], ]
        layout += [[sg.Menu(menu_def, tearoff=True)]]
        
        def button(i, j):
            '''
            short helper to create a button object with preset params
            '''
            #r = max(1, int(((R+C)/2)**.1))
            #a, b = R//2, C//2
            if i == 0 or i == R-1 or j == 0 or j == C-1:
                return sg.Button('S', button_color=('white', 'lightgreen'), 
                                 size=(1, 1), key=(i, j), pad=(0, 0))
            #elif i in range(a-r, a+r) and j in range(b-r, b+r):
            #    return sg.Button('F', button_color=('white', 'red'), 
            #                     size=(1, 1), key=(i, j), pad=(0, 0))
            return sg.Button('N', button_color=('white', 'lightgrey'), size=(1, 1), 
                             key=(i, j), pad=(0, 0))
     

        button_layout = [[button(i, j) for j in range(C)] for i in range(R)]
        button_column = sg.Column(button_layout, scrollable=True, size=(800, 600))

        #bottomrow = [
        #    sg.Button('mode: walls', button_color=('white', 'darkblue'), 
        #              size=(10, 1), key='mode'),
        #    sg.SaveAs('Save'), sg.Cancel()
        #        ]
        #
        layout += [[sg.Text('editing mode: {}'.format(mode), key='mode', size=(30, 1))],
                   [button_column]]
        #layout += [[sg.Text('editing mode: {}'.format(mode), key='mode', size=(30, 1))],
        #           [sg.Slider(range=(0, 100), default_value=50, orientation='h', size=(10, 10), key='-SLIDER-')],
        #           [button_column]]

        self.window = sg.Window('simulation floor layout designer', layout)
        return self.window


    def parse(self, floorlines):
        '''
        method that takes a string representation of the grid and constructs a graph
        useful for a simulation
        '''
        grid = []
        for row in floorlines:
            if not row: continue
            sqs = row.split(';')
            rowattrs = [set(sq.strip().split(',')) for sq in sqs]
            print(rowattrs)
            grid += [rowattrs]


        graph = defaultdict(lambda: {'nbrs': set()})
        meta = dict(bottleneck=set(), danger=set(), wall=set(), safe=set())

        R, C = len(grid), len(grid[0])
       
        for i in range(R):
            for j in range(C):
                attrs = grid[i][j]
                graph[(i,j)].update({att:int(att in attrs) for att in 'WSBFNPHM'})
                
                for off in {-1, 1}:
                    if 0 <= i+off < R:
                        graph[(i,j)]['nbrs'].add((i+off, j))

                    if 0 <= j+off < C:
                        graph[(i,j)]['nbrs'].add((i, j+off))


        def bfs(target, pos): # iterative dfs
            if graph[pos]['W']: return float('inf')
            q = [(pos, 0)]
            visited = set()
            while q:
                node, dist = q.pop()
                if node in visited: continue
                visited.add(node)

                node = graph[node]
                if node['W'] or node['F']: continue
                if node[target]: return dist

                for n in node['nbrs']:
                    if n in visited: continue
                    q = [(n, dist+1)] + q

            return float('inf')
                
        for i in range(R):
            for j in range(C):
                graph[(i,j)]['distF'] = bfs('F', (i,j)) 
                graph[(i,j)]['distS'] = bfs('S', (i,j))

        self.graph = dict(graph.items())
        pp.pprint(self.graph) 
        return self.graph


    def save(self):
        '''
        saves the current layout to a text file for use by a simulation program
        (or just for your own viewing pleasure)
        '''
        print('saving to', self.output)
        window = self.window
        R, C = self.R, self.C

        gridstr = ''
        for i in range(R):
            txts = ['{: >4}'.format(window.Element((i,j)).ButtonText) 
                    for j in range(C)]
            gridstr += ';'.join(txts) + '\n'

        graph = self.parse(gridstr.split('\n'))

        with open(self.output+'.pkl', 'wb') as out:
            pickle.dump(graph, file=out)
        with open(self.output, 'w') as out:
            print(gridstr, file=out)


    def load(self, graph):
        '''
        loads from input.txt.pkl
        '''
        window = self.window
        self.graph = graph 
        for loc, data in self.graph.items():
            square = window.Element(loc)
            attrs = {att for att in data if att is not 'nbrs' and data[att]}
            attrs.intersection_update(set('WSFBNPHM'))
            if 'W' in attrs:
                color = 'grey' if 'F' not in attrs else 'yellow'
            elif 'B' in attrs:
                color = 'lightblue' if 'F' not in attrs else 'aquamarine'
            elif 'F' in attrs:
                color = 'red'
            elif 'S' in attrs:
                color = 'lightgreen' 
            elif 'P' in attrs:
                color = 'purple' if 'F' not in attrs else 'aquamarine'
            elif 'N' in attrs:
                color = 'lightgrey'
            elif 'H' in attrs:
                color = 'pink'
            elif 'M' in attrs:
                color = 'orange'
            square.Update(','.join(reversed(sorted(attrs))), 
                          button_color=('white', color))


    def loadtxt(self):
        '''
        '''
        with open(self.output+'.pkl', 'rb') as pklf:
            graph = pickle.load(pklf)
        self.load(graph) 


    def click(self, event, values):
        '''
        handles a click event on a square in a grid
        '''
        mode, R, C = self.mode, self.R, self.C
        window = self.window
        print('clicked:', event, values)
        
         
        if type(event) is tuple:
            i, j = event
            if i == 0 or i == R-1 or j == 0 or j == C-1:
                print('Cannot alter safe zone! (Tried editing {})'.format((i,j)))
                return
            square = window.Element(event)
            attrs = set(square.ButtonText.split(','))

            if mode == 'Walls':
                if 'W' in attrs:
                    color = 'lightgrey' if 'F' not in attrs else 'red'
                    attrs.remove('W')
                    if 'F' not in attrs: attrs.add('N') 
                elif 'F' in attrs:
                    color = 'orange'
                    attrs.add('W')
                else:
                    color = 'grey'
                    attrs.add('W')
                    attrs.discard('N')

            elif mode == 'Bottleneck':
                if 'W' in attrs or 'P' in attrs:
                    print('Can\'t place a bottleneck in a wall or people!')
                    return
                elif 'B' in attrs:
                    attrs.remove('B')
                    if 'F' not in attrs: attrs.add('N') 
                    color = 'red' if 'F' in attrs else 'lightgrey'
                else:
                    attrs.add('B')
                    attrs.discard('N')
                    color = 'lightblue' if 'F' not in attrs else 'yellow'

            elif mode == 'People':
                if 'W' in attrs or 'B' in attrs:
                    print('Can\'t place a person in a wall or bottleneck!')
                    return
                elif 'P' in attrs:
                    attrs.remove('P')
                    if 'F' not in attrs: attrs.add('N') 
                    color = 'red' if 'F' in attrs else 'lightgrey'
                else:
                    attrs.add('P')
                    attrs.discard('N')
                    color = 'purple' if 'F' not in attrs else 'aquamarine'

            elif mode == 'Danger':
                if 'F' in attrs:
                    attrs.add('N')
                    attrs.remove('F')
                    color = 'grey' if 'W' in attrs else 'lightgrey'
                else:
                    attrs.difference_update({'B', 'N'})
                    attrs.add('F')
                    color = 'aquamarine' if 'W' in attrs else 'red'
            
            #自行新增H
            elif mode == 'Hot':
                if 'W' in attrs or 'B' in attrs:  # 檢查是否為牆壁或瓶頸
                    print('Can\'t place "Hot" in a wall or bottleneck!')
                    return
                elif 'H' in attrs:  # 如果已經是"H" 移除H改為N
                    attrs.remove('H')
                    if 'F' not in attrs:
                        attrs.add('N')
                    color = 'lightgrey' if 'F' not in attrs else 'red'
                else:  # 新增 "Hot"
                    attrs.add('H')
                    attrs.discard('N')
                    color = 'pink' if 'F' not in attrs else 'aquamarine'
            
            #自行新增M
            elif mode == 'Medinum':
                if 'W' in attrs or 'B' in attrs:  # 檢查是否為牆壁或瓶頸
                    print('Can\'t place "Medinum" in a wall or bottleneck!')
                    return
                elif 'M' in attrs:  # 如果已經是"M" 移除M改為N
                    attrs.remove('M')
                    if 'F' not in attrs:
                        attrs.add('N')
                    color = 'lightgrey' if 'F' not in attrs else 'red'
                else:  # 新增 "Medinum"
                    attrs.add('M')
                    attrs.discard('N')
                    color = 'orange' if 'F' not in attrs else 'aquamarine'


            square.Update(','.join(reversed(sorted(attrs))), 
                          button_color=('white', color))

        elif event == 'Save':
            self.save()
        
        elif event == 'Cancel':
            raise SystemExit
        
        elif event in ['Walls', 'Bottleneck', 'Danger', 'People', 'Hot', 'Medinum']:
            #global mode
            window.Element('mode').Update('editing mode: {}'.format(event))
            self.mode = event

        elif event == 'Reset':
            for i in range(1, R-1):
                for j in range(1, C-1):
                    square = window.Element((i,j))
                    square.Update('N', button_color=('white', 'lightgrey'))

        elif event == 'Open':
            self.loadtxt()

        else:
            print('Unknown event:', event)


def main(args):
    '''
    main method: setup board, and handle the event lifecycle
    '''
    R, C = args.rows, args.cols
    assert 1 < R <= 150 and  1 < C <= 150, 'rows and columns must be 1< x <=20'

    grid = FloorGUI(R, C, args.output) 
    window = grid.setup()
        
    while True:
        #如果會卡住 把下面這行改成 event, values = window.Read(timeout=10)
        event, values = window.Read()
        if event in (None, 'Exit'):
            break

        grid.click(event, values)

    window.Close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='design a floor plan for '
                                                 'egress simulation programs')
    parser.add_argument('rows', metavar='R',  type=int,
                        help='number of rows in the grid. max: 150')
    parser.add_argument('cols', metavar='C', type=int,
                        help='number of cols in the grid. max: 150')
    parser.add_argument('-o', '--output', default='floor.txt', type=str,
                        help='name of file to output plan to')
    global args
    args = parser.parse_args()
    
    main(args)
