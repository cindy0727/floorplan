#!/usr/bin/env python3

'''
This is the main file in the evacuation simulation project.
people: Nick B., Matthew J., Aalok S.

In this file we define a useful class to model the building floor, 'Floor'

Also in this file, we proceed to provide a main method so that this file is
meaningfully callable to run a simulation experiment
'''

# stdlib imports
from time import sleep
import numpy
import simulus
import sys
import pickle
import random
import pprint
from argparse import ArgumentParser
try:
    from randomgen import PCG64, RandomGenerator as Generator
except ImportError:
    from randomgen import PCG64, Generator

# local project imports
from person import Person
from bottleneck import Bottleneck
from floorparse import FloorParser
#畫圖
import matplotlib.pyplot as plt

from functools import lru_cache

pp = pprint.PrettyPrinter(indent=4).pprint

class FireSim:
    sim = None
    graph = None # dictionary (x,y) --> attributes
    gui = False
    r = None
    c = None

    numpeople = 0
    numdead = 0
    numsafe = 0
    nummoving = 0
    numexit = 0

    bottlenecks = dict()
    fires = set()
    people = []

    exit_times = []
    exit_loc = []
    avg_exit = 0 # tracks sum first, then we divide

    def __init__(self, input,
                 strategy_generator=lambda: random.uniform(.5, 1.),
                 rate_generator=lambda: abs(random.normalvariate(1, .5)),
                 person_mover=random.uniform, fire_mover=random.sample,
                 fire_rate=2, bottleneck_delay=1, animation_delay=.1,
                 verbose=False,b=.1,
                 **kwargs,):
        
        '''
        constructor method
        ---
        graph (dict): a representation of the floor plan as per our
                      specification
        n (int): number of people in the simulation
        '''     
        self.sim = simulus.simulator()
        self.parser = FloorParser() 
        self.animation_delay = animation_delay
        self.verbose = verbose

        with open(input, 'r') as f:
            self.graph = self.parser.parse(f.read())

        self.strategy_generator = strategy_generator
        self.rate_generator = rate_generator
        self.person_mover = person_mover
        self.fire_mover = fire_mover
        
        self.fire_rate = fire_rate
        self.bottleneck_delay = bottleneck_delay
        self.kwargs = kwargs
        self.b = b

        self.setup()

    def whichdoor(loc):
        if loc == (42,1):
            return 0
        elif loc == (92,14):
            return 1      
        elif loc == (92,62):
            return 2
        elif loc == (39,75):
            return 3

    def precompute(self):
        '''
        precompute stats on the graph, e.g. nearest safe zone, nearest fire
        '''
  
        graph = self.graph
        
        def bfs(target, pos, i):
            def whichdoor(loc):
                if loc == (42,1):
                    return 0
                elif loc == (92,14):
                    return 1      
                elif loc == (92,62):
                    return 2
                elif loc == (39,75):
                    return 3
                
            distance = [0,0,0,0]
            door = [(-1,-1),(-1,-1),(-1,-1),(-1,-1)]
            
            if graph[pos]['W']: 
                distance = [float('inf'),float('inf'),float('inf'),float('inf'),float('inf')]
                return distance, door
            
            if graph[pos]['S']:
                return distance, door
            
            q = [(pos, 0, (-1, -1))]
            visited = set()
            i_count = 0
            
            while q:
                node, dist, last_loc = q.pop()
                if node in visited: continue
                visited.add(node)

                temp=node
                node = graph[node]
                if node['W'] or node['F']: continue
                
                if node[target]: 
                    if i_count == i:
                        door[i_count] = last_loc
                        distance[whichdoor(last_loc)] = dist  
                        return distance,door
                    
                    else:
                        door[i_count] = last_loc
                        distance[whichdoor(last_loc)] = dist
                        i_count +=1
                        for n in node['nbrs']:
                            if graph[n]['S']:
                                visited.add(n)
                        for n in graph[last_loc]['nbrs']:
                            if graph[n]['S']:
                                visited.add(n)   
                        continue
                
                for n in node['nbrs']:
                    if n in visited: 
                        continue
                    q = [(n, dist+1, temp)] + q

            # unreachable
            distance = [float('inf'),float('inf'),float('inf'),float('inf'),float('inf')]
            return distance,door
        
        
        for loc in graph:
            graph[loc]['distF'] = bfs('F', loc, 3)
            graph[loc]['distS'],graph[loc]['door'] = bfs('S', loc, 3)
            #print(loc, "distS", graph[loc]['distS'], "door", graph[loc]['door'],"\n")
            graph[loc]['density'] = 0
  
        '''
        #計算人口密度
        for loc in graph:
            if graph[loc]['P']:
                graph[graph[loc]['door'][0]]['density'] += 1
        
        #將距離加入權重
        for loc in graph:
            if graph[loc]['S']:
                graph[loc]['dist_weight'] = 0
            else:
                graph[loc]['dist_weight'] = float('inf')
                
            if graph[loc]['door'] != (-1, -1):
                graph[loc]['dist_weight'] = graph[loc]['distS'] + self.b * graph[graph[loc]['door']]['density']
        
        #更新每個點的距離使得每個點的距離和最小鄰居的值只會差1
        for loc in graph:
            for loc in graph:
                if graph[loc]['S'] or graph[loc]['W'] or graph[loc]['F'] or graph[loc]['density'] != 0:
                  continue
                min_dist=float('inf')
                for n in graph[loc]['nbrs']:
                    if min_dist > graph[n]['dist_weight'] and graph[n]['S']==0:
                        min_dist = graph[n]['dist_weight']
                        graph[loc]['door'] = graph[n]['door']
                        graph[loc]['dist_weight'] = min_dist + 1
        '''               

        self.graph = dict(graph.items())

        return self.graph

    
    def setup(self):
        '''
        once we have the parameters and random variate generation methods from
        __init__, we can proceed to create instances of: people and bottlenecks
        '''
        self.precompute()
        
        
        av_locs = []
        av_locs_copy = []
        bottleneck_locs = []
        fire_locs = []

        r, c = 0, 0
        for loc, attrs in self.graph.items():
            r = max(r, loc[0])
            c = max(c, loc[1])
            if attrs['P']: av_locs += [loc]
            elif attrs['B']: bottleneck_locs += [loc]
            elif attrs['F']: fire_locs += [loc]
        self.numpeople=len(av_locs)
        av_locs_copy = av_locs
        assert len(av_locs) > 0, 'ERR: no people placement locations in input'
        for i in range(self.numpeople):
            location=av_locs_copy.pop()
            p = Person(i, self.rate_generator(),
                       self.strategy_generator(),
                       location)
            self.people += [p]

        for loc in bottleneck_locs:
            b = Bottleneck(loc)
            self.bottlenecks[loc] = b
        self.fires.update(set(fire_locs))

        self.r, self.c = r+1, c+1

        '''
        print(
              '='*79,
              'initialized a {}x{} floor with {} people in {} locations'.format(
                    self.r, self.c, len(self.people), len(av_locs)
                  ),
              'initialized {} bottleneck(s)'.format(len(self.bottlenecks)),
              'detected {} fire zone(s)'.format(len([loc for loc in self.graph
                                                     if self.graph[loc]['F']])),
              '\ngood luck escaping!', '='*79, 'LOGS', '\nb={}\n'.format(self.b),sep='\n',
             )
        '''

    def visualize(self, t):
        '''
        '''
        if self.gui:
            self.plotter.visualize(self.graph, self.people, t)


    def update_bottlenecks(self):
        '''
        handles the bottleneck zones on the grid, where people cannot all pass
        at once. for simplicity, bottlenecks are treated as queues
        '''

        for key in self.bottlenecks:
            #print(key, self.bottlenecks[key])
            personLeaving = self.bottlenecks[key].exitBottleNeck()
            if(personLeaving != None):
                self.sim.sched(self.update_person, personLeaving.id, offset=0)

        if self.numsafe + self.numdead >= self.numpeople:
            return

        if self.maxtime and self.sim.now >= self.maxtime:
            return
        else:
            self.sim.sched(self.update_bottlenecks, 
                           offset=self.bottleneck_delay)



    def update_fire(self):
        '''
        method that controls the spread of fire. we use a rudimentary real-world
        model that spreads fire exponentially faster proportional to the amount
        of fire already on the floor. empty nodes are more likely to get set
        on fire the more lit neighbors they have. empty plain nodes are more
        likely to burn than walls.
        fire spreads proportional to (grid_area)/(fire_area)**exp
        the method uses the 'fire_rate' instance variable as the 'exp' in the
        expression above.
        fire stops spreading once it's everywhere, or when all the people have
        stopped moving (when all are dead or safe, not moving)
        '''
        if self.numsafe + self.numdead >= self.numpeople:
            #print('INFO:', 'people no longer moving, so stopping fire spread')
            return
        if self.maxtime and self.sim.now >= self.maxtime:
            return

        no_fire_nbrs = [] # list, not set because more neighbors = more likely
        for loc in self.fires:
            # gets the square at the computed location
            square = self.graph[loc]

            # returns the full list of nbrs of the square
            nbrs = [(coords, self.graph[coords]) for coords in square['nbrs']]

            # updates nbrs to exclude safe zones and spaces already on fire
            no_fire_nbrs += [(loc, attrs) for loc, attrs in nbrs
                             if attrs['S'] == attrs['F'] == 0]
            # more likely (twice) to spread to non-wall empty zone
            no_fire_nbrs += [(loc, attrs) for loc, attrs in nbrs
                             if attrs['W'] == attrs['S'] == attrs['F'] == 0]

        try:
            (choice, _) = self.fire_mover(no_fire_nbrs)
        except ValueError as e:
            #print('INFO:', 'fire is everywhere, so stopping fire spread')
            return

        self.graph[choice]['F'] = 1
        self.fires.add(choice)

        self.precompute()
        rt = self.fire_rate
        self.sim.sched(self.update_fire,
                       offset=len(self.graph)/max(1, len(self.fires))**rt)

        self.visualize(self.animation_delay/max(1, len(self.fires))**rt)

        return choice


    def update_person(self, person_ix):
        '''
        handles scheduling an update for each person, by calling move() on them.
        move will return a location decided by the person, and this method will
        handle the simulus scheduling part to keep it clean
        '''
        if self.maxtime and self.sim.now >= self.maxtime:
            return

        p = self.people[person_ix]
        if self.graph[p.loc]['F'] or not p.alive:
            p.alive = False
            self.numdead += 1
            if self.verbose:
                print('{:>6.2f}\tPerson {:>3} at {} could not make it'.format(
                                                                  self.sim.now,
                                                                  p.id, p.loc))
            return
        if p.safe:
            self.numsafe += 1
            p.exit_time = self.sim.now
            self.exit_times += [p.exit_time]
            #self.avg_exit += p.exit_time
            self.avg_exit = p.exit_time
            #print(self.sim.now, "\n")
            if self.verbose:
                print('{:>6.2f}\tPerson {:>3} is now SAFE!'.format(self.sim.now, 
                                                               p.id))
            return

        loc = p.loc
        square = self.graph[loc]
        nbrs = [(coords, self.graph[coords]) for coords in square['nbrs']]

        target = p.move(nbrs)
        if not target:
            p.alive = False
            self.numdead += 1
            if self.verbose:
                print('{:>6.2f}\tPerson {:>3} at {} got trapped in fire'.format(
                                                                   self.sim.now,
                                                                   p.id, p.loc))
            return
        square = self.graph[target]
        if square['B']:
            b = self.bottlenecks[target]
            b.enterBottleNeck(p)
        elif square['F']:
            p.alive = False
            self.numdead += 1
            return
        else:
            t = 1/p.rate
            if self.sim.now + t >= (self.maxtime or float('inf')):
                if square['S']:
                    self.nummoving += 1
                else:
                    self.numdead += 1
            else:
                self.sim.sched(self.update_person, person_ix, offset=1/p.rate)

        if (1+person_ix) % int(self.numpeople**.5) == 0:
            self.visualize(t=self.animation_delay/len(self.people)/2)

        # self.sim.show_calendar()
    



    def simulate(self, maxtime=None, spread_fire=False, gui=False):
        '''
        sets up initial scheduling and calls the sim.run() method in simulus
        '''

        self.gui = gui
        if self.gui: 
            from viz import Plotter
            self.plotter = Plotter()

        # set initial movements of all the people
        for i, p in enumerate(self.people):
            loc = tuple(p.loc)
            square = self.graph[loc]
            nbrs = square['nbrs']
            self.sim.sched(self.update_person, i, offset=1/p.rate)

        #updates fire initially
        if spread_fire:
            self.sim.sched(self.update_fire,
                           offset=1)#len(self.graph)/max(1, len(self.fires)))
        else:
            print('INFO\t', 'fire won\'t spread around!')
        self.sim.sched(self.update_bottlenecks, offset=self.bottleneck_delay)

        self.maxtime = maxtime
        self.sim.run()

        #self.avg_exit /= max(self.numsafe, 1)


    def stats(self):
        '''
        computes and outputs useful stats about the simulation for nice output
        '''
        '''
        print('\n\n', '='*79, sep='')
        print('STATS')

        def printstats(desc, obj):
            print('\t',
                  (desc+' ').ljust(30, '.') + (' '+str(obj)).rjust(30, '.'))

        printstats('total # people', self.numpeople)
        printstats('# people safe', self.numsafe)
        printstats('# people dead', self.numpeople-self.numsafe-self.nummoving)
        printstats('# people gravely injured', self.nummoving)
        print()
        #printstats('total simulation time', '{:.3f}'.format(self.sim.now))
        if self.avg_exit:
            printstats('time to safe', '{:.3f}'.format(self.avg_exit))
        else:
            printstats('average time to safe', 'NA')
        print()
        '''
        if self.avg_exit:
            print('{:.3f}'.format(self.avg_exit))
        else:
            print('average time to safe', 'NA')
        self.visualize(5)

        if self.plotter:
            self.plotter.close()
        self = None
        #return self.avg_exit
    
def plot_points(x, y):

    plt.plot(x, y)
    plt.scatter(x, y, color='red')  # 绘制散点图

    # 添加标题和坐标轴标签
    plt.title('Plot of Points')
    plt.xlabel('b')
    plt.ylabel('time to safe')

    plt.show()


def main():
    '''
    driver method for this file. the firesim class can be used via imports as
    well, but this driver file provides a comprehensive standalone interface
    to the simulation
    '''
    # set up and parse commandline arguments
    parser = ArgumentParser()
    parser.add_argument('-i', '--input', type=str,
                        default='in/twoexitbottleneck.txt',
                        help='input floor plan file (default: '
                             'in/twoexitbottleneck.py)')
    parser.add_argument('-r', '--random_state', type=int, default=8675309,
                        help='aka. seed (default:8675309)')
    parser.add_argument('-t', '--max_time', type=float, default=None,
                        help='the building collapses at this clock tick. people'
                             ' beginning movement before this will be assumed'
                             ' to have moved away sufficiently (safe)')
    parser.add_argument('-f', '--no_spread_fire', action='store_true',
                        help='disallow fire to spread around?')
    parser.add_argument('-g', '--no_graphical_output', action='store_true',
                        help='disallow graphics?')
    parser.add_argument('-o', '--output', action='store_true',
                        help='show excessive output?')
    parser.add_argument('-d', '--fire_rate', type=float, default=2,
                        help='rate of spread of fire (this is the exponent)')
    parser.add_argument('-b', '--bottleneck_delay', type=float, default=1,
                        help='how long until the next person may leave the B')
    parser.add_argument('-a', '--animation_delay', type=float, default=1,
                        help='delay per frame of animated visualization (s)')
    parser.add_argument('-w', '--weight', type=float, default=0,
                        help='y=x+bw')
    args = parser.parse_args()
    # output them as a make-sure-this-is-what-you-meant
    #print('commandline arguments:', args, '\n')

    # set up random streams
    streams = [numpy.random.Generator(PCG64(args.random_state, i)) for i in range(4)]
    strat_strm, rate_strm, pax_strm, fire_strm = streams

    strategy_generator = lambda: strat_strm.uniform(.5, 1) # used to pick move
    rate_generator = lambda: max(.1, abs(rate_strm.normal(1, .1))) # used to
                                                                   # decide
                                                                   # strategies
    #strategy_generator = 0.5
    #rate_generator = 5
    person_mover = lambda: pax_strm.uniform() #
    fire_mover = lambda a: fire_strm.choice(a) #

    #weight = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    #time = [0,0,0,0,0,0,0,0,0,0,0]
    # create an instance of Floor
    #for i in range(2):
        #b = i/10
    floor = FireSim(args.input,
                    strategy_generator, rate_generator, person_mover,
                    fire_mover, fire_rate=args.fire_rate,
                    bottleneck_delay=args.bottleneck_delay,
                    animation_delay=args.animation_delay, verbose=args.output, b=args.weight)

    # floor.visualize(t=5000)
    # call the simulate method to run the actual simulation
    floor.simulate(maxtime=args.max_time, spread_fire=not args.no_spread_fire,
                   gui=not args.no_graphical_output)

    floor.stats()
    del floor



if __name__ == '__main__':
    main()
