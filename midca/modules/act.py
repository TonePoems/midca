from midca.modules._plan.asynch import asynch
from midca import base
import copy
import json
import sys

try:
    import stomp
    from midca.domains.rpa_domain import API
except:
    pass


class AsynchronousAct(base.BaseModule):

    '''
    MIDCA module that "executes" plans in which the individual actions will be conducted
    asynchronously. This was originally designed to allow MIDCA to work as a robot
    controller in communication with ROS sensor and effector nodes.
    '''

    def run(self, cycle, verbose = 2):
        self.verbose = verbose
        try:
            goals = self.mem.get(self.mem.CURRENT_GOALS)[-1]
        except:
            goals = []
        if not goals:
            if verbose >= 2:
                print "No Active goals. Act phase will do nothing"
            return

        try:
            plan = self.mem.get(self.mem.GOAL_GRAPH).getMatchingPlan(goals)
        except:
            if verbose >= 1:
                print "Error loading plan. Skipping act phase."
            return

        if not plan:
            if verbose > 2:
                print "No current plan. Skipping Act phase"
            return
        i = 0
        if plan.finished():
            print "Plan", plan, "has already been completed"
            return
        #ideally MIDCA should check for other valid plans, but for now it doesn't.

        while i < len(plan):
            action = plan[i]
            try:
                if action.status != asynch.FAILED and action.status != asynch.COMPLETE:
                    completed = action.check_complete()
                    if completed:
                        if verbose >= 2:
                            print "Action", action, "completed"
            except AttributeError:
                if verbose >= 1:
                    print "Action", action, "Does not seem to have a valid check_complete() ",
                    "method. Therefore MIDCA cannot execute it."
                    action.status = asynch.FAILED
            try:
                if action.status == asynch.NOT_STARTED:
                    if verbose >= 2:
                        print "Beginning action execution for", action
                    action.execute()
            except AttributeError:
                if verbose >= 1:
                    print "Action", action, "Does not seem to have a valid execute() ",
                    "method. Therefore MIDCA cannot execute it"
                    action.status = asynch.FAILED
            if action.status == asynch.COMPLETE:
                i += 1
            elif not action.blocks:
                i += 1
            else:
                break


class SimpleAct(base.BaseModule):
    '''
    MIDCA module that selects the plan, if any, that achieves the most current goals, then selects the next action from that plan. The selected action is stored in a two-dimensional array in mem[mem.ACTIONS], where mem[mem.ACTIONS][x][y] returns the yth action to be taken at time step x. So mem[mem.ACTIONS][-1][0] is the last action selected. Note that this will throw an index error if no action was selected.
    To have MIDCA perform multiple actions in one cycle, simple add several actions to mem[mem.ACTIONS][-1]. So mem[mem.ACTIONS][-1][0] is the first action taken, mem[mem.ACTIONS][-1][1] is the second, etc.
    '''

    # returns the plan that achieves the most current goals, based on simulation.
    def get_best_plan(self, world, goals, verbose):
        plan = None
        goalsAchieved = set()
        goalGraph = self.mem.get(self.mem.GOAL_GRAPH)
        for nextPlan in goalGraph.allMatchingPlans(goals):
            achieved = world.goals_achieved(nextPlan, goals)
            if len(achieved) > len(goalsAchieved):
                goalsAchieved = achieved
                plan = nextPlan
            if len(achieved) == len(goals):
                break
            elif verbose >= 2:
                print "Retrieved plan does not achieve all goals. Trying to retrieve a different plan..."
                if verbose >= 3:
                    print "  Retrieved Plan:"
                    for a in nextPlan:
                        print "  " + str(a)
                    print "Goals achieved:", [str(goal) for goal in achieved]
        if plan == None and verbose >= 1:
            print "No valid plan found that achieves any current goals."
        elif len(goalsAchieved) < len(goals) and verbose >= 1:
            print "Best plan does not achieve all goals."
            if verbose >= 2:
                print "Plan:", str(plan)
                print "Goals achieved:", [str(goal) for goal in goalsAchieved]
        return plan

    def run(self, cycle, verbose=2):
        self.verbose = verbose
        max_plan_print_size = 5
        world = self.mem.get(self.mem.STATES)[-1]
        try:
            goals = self.mem.get(self.mem.CURRENT_GOALS)[-1]
        except:
            goals = []
        plan = self.get_best_plan(world, goals, verbose)
        trace = self.mem.trace
        if trace:
            trace.add_module(cycle, self.__class__.__name__)
            trace.add_data("WORLD", copy.deepcopy(world))
            trace.add_data("GOALS", copy.deepcopy(goals))
            trace.add_data("PLAN", copy.deepcopy(plan))

        if plan != None:
            action = plan.get_next_step()
            if not action:
                if verbose >= 1:
                    print "Plan to achieve goals has already been completed. Taking no action."
                self.mem.add(self.mem.ACTIONS, [])
            else:
                if verbose == 1:
                    print "Action selected:", action
                elif verbose >= 2:
                    if len(plan) > max_plan_print_size:
                        # print just the next 3 actions of the plan
                        print "Selected action", action, "from plan:\n"
                        if verbose >= 3:
                            for a in plan:
                                print "  " + str(a)
                    else:
                        # print the whole plan
                        print "Selected action", action, "from plan:\n", plan
                self.mem.add(self.mem.ACTIONS, [action])
                actions = self.mem.get(self.mem.ACTIONS)
                if len(actions) > 400:
                    actions = actions[200:]  # trim off old stale actions
                    self.mem.set(self.mem.ACTIONS, actions)
                    # print "Trimmed off 200 old stale actions to save space"
                plan.advance()

                if trace: trace.add_data("ACTION", action)
        else:
            if verbose >= 1:
                print "MIDCA will not select an action this cycle."
            self.mem.add(self.mem.ACTIONS, [])
            if goals:
                for g in goals:
                    self.mem.get(self.mem.GOAL_GRAPH).remove(g)

            if trace: trace.add_data("ACTION", None)


class SimpleAct_temporary(base.BaseModule):
    '''
    For both construction and restaurant domain
    MIDCA module that selects the plan, if any, that achieves the most current goals, then selects the next action from that plan. The selected action is stored in a two-dimensional array in mem[mem.ACTIONS], where mem[mem.ACTIONS][x][y] returns the yth action to be taken at time step x. So mem[mem.ACTIONS][-1][0] is the last action selected. Note that this will throw an index error if no action was selected.
    To have MIDCA perform multiple actions in one cycle, simple add several actions to mem[mem.ACTIONS][-1]. So mem[mem.ACTIONS][-1][0] is the first action taken, mem[mem.ACTIONS][-1][1] is the second, etc.
    '''

    # returns the plan that achieves the most current goals, based on simulation.
    def get_best_plan(self, world, goals, verbose):
        plan = None
        goalsAchieved = set()
        goalGraph = self.mem.get(self.mem.GOAL_GRAPH)
        for nextPlan in goalGraph.allMatchingPlans(goals):
            achieved = world.goals_achieved(nextPlan, goals)
            if len(achieved) > len(goalsAchieved):
                goalsAchieved = achieved
                plan = nextPlan
            if len(achieved) == len(goals):
                break
            elif verbose >= 2:
                print "Retrieved plan does not achieve all goals. Trying to retrieve a different plan..."
                if verbose >= 3:
                    print "  Retrieved Plan:"
                    for a in nextPlan:
                        print "  " + str(a)
                    print "Goals achieved:", [str(goal) for goal in achieved]
        if plan == None and verbose >= 1:
            print "No valid plan found that achieves any current goals."
        elif len(goalsAchieved) < len(goals) and verbose >= 1:
            print "Best plan does not achieve all goals."
            if verbose >= 2:
                print "Plan:", str(plan)
                print "Goals achieved:", [str(goal) for goal in goalsAchieved]
        return plan

    def run(self, cycle, verbose=2):
        self.verbose = verbose
        max_plan_print_size = 5
        world = self.mem.get(self.mem.STATES)[-1]
        try:
            goals = self.mem.get(self.mem.CURRENT_GOALS)
        except:
            goals = []
        plan = self.get_best_plan(world, goals, verbose)
        trace = self.mem.trace
        if trace:
            trace.add_module(cycle, self.__class__.__name__)
            trace.add_data("WORLD", copy.deepcopy(world))
            trace.add_data("GOALS", copy.deepcopy(goals))
            trace.add_data("PLAN", copy.deepcopy(plan))

        if plan != None:
            action = plan.get_next_step()
            if not action:
                if verbose >= 1:
                    print "Plan to achieve goals has already been completed. Taking no action."
                self.mem.add(self.mem.ACTIONS, [])
            else:
                if verbose == 1:
                    print "Action selected:", action
                elif verbose >= 2:
                    if len(plan) > max_plan_print_size:
                        # print just the next 3 actions of the plan
                        print "Selected action", action, "from plan:\n"
                        if verbose >= 3:
                            for a in plan:
                                print "  " + str(a)
                    else:
                        # print the whole plan
                        print "Selected action", action, "from plan:\n", plan
                self.mem.add(self.mem.ACTIONS, [action])
                actions = self.mem.get(self.mem.ACTIONS)
                if len(actions) > 400:
                    actions = actions[200:]  # trim off old stale actions
                    self.mem.set(self.mem.ACTIONS, actions)
                    # print "Trimmed off 200 old stale actions to save space"
                plan.advance()

                if trace: trace.add_data("ACTION", action)
        else:
            if verbose >= 1:
                print "MIDCA will not select an action this cycle."
            self.mem.add(self.mem.ACTIONS, [])
            if goals:
                for g in goals:
                    self.mem.get(self.mem.GOAL_GRAPH).remove(g)

            if trace: trace.add_data("ACTION", None)

class NBeaconsSimpleAct(base.BaseModule):

    '''
    MIDCA module that selects the plan, if any, that achieves the most current goals, then selects the next action from that plan. The selected action is stored in a two-dimensional array in mem[mem.ACTIONS], where mem[mem.ACTIONS][x][y] returns the yth action to be taken at time step x. So mem[mem.ACTIONS][-1][0] is the last action selected. Note that this will throw an index error if no action was selected.
    To have MIDCA perform multiple actions in one cycle, simple add several actions to mem[mem.ACTIONS][-1]. So mem[mem.ACTIONS][-1][0] is the first action taken, mem[mem.ACTIONS][-1][1] is the second, etc.
    '''
    
    def get_first_plan(self, goals):
        goalGraph = self.mem.get(self.mem.GOAL_GRAPH)
        plans = goalGraph.allMatchingPlans(goals)
        for p in plans:
            if p.finished():
                goalGraph.removePlan(p)
                if self.verbose >= 1:
                    print "Just removed finished plan "
                    for ps in p:
                        print "  "+str(ps)
            else:
                return p
        if self.verbose >= 1: print "Could not find an unfinished plan in get_first_plan() for goals "+str(goals)
        return None
        
    def run(self, cycle, verbose = 2):
        self.verbose = verbose
        max_plan_print_size = 10
        world = self.mem.get(self.mem.STATES)[-1]
        try:
            goals = self.mem.get(self.mem.CURRENT_GOALS)[-1]
        except:
            goals = []
        plan = self.get_first_plan(goals)

        trace = self.mem.trace
        if trace:
            trace.add_module(cycle,self.__class__.__name__)
            trace.add_data("WORLD", copy.deepcopy(world))
            trace.add_data("GOALS", copy.deepcopy(goals))
            trace.add_data("PLAN", copy.deepcopy(plan))

        if plan != None:
            action = plan.get_next_step()
            if not action:
                if verbose >= 1:
                    print "Plan to achieve goals has already been completed. Taking no action."
                self.mem.add(self.mem.ACTIONS, [])
            else:
                if verbose == 1:
                    print "Action selected:", action
                elif verbose >= 2:
                    if len(plan) > max_plan_print_size:
                        # print just the next 3 actions of the plan
                        print "Selected action", action, "from plan:\n"
                        if verbose >= 3:
                            for a in plan:
                                if action == a:
                                    print "   *"+str(a)
                                else:
                                    print "  "+str(a)
                    else:
                        # print the whole plan
                        print "Selected action", action, "from plan:\n"
                        for a in plan:
                            if action == a:
                                print "   *"+str(a)
                            else:
                                print "  "+str(a)
                                
                self.mem.add(self.mem.ACTIONS, [action])
                plan.advance()

                if trace: trace.add_data("ACTION", action)
        else:
            if verbose >= 1:
                print "MIDCA will not select an action this cycle."
            self.mem.add(self.mem.ACTIONS, [])

            if trace: trace.add_data("ACTION", None)


class SimpleAct_rpa(base.BaseModule):
    '''
    MIDCA module that selects the plan, if any, that achieves the most current goals, then selects the next action from that plan. The selected action is stored in a two-dimensional array in mem[mem.ACTIONS], where mem[mem.ACTIONS][x][y] returns the yth action to be taken at time step x. So mem[mem.ACTIONS][-1][0] is the last action selected. Note that this will throw an index error if no action was selected.
    To have MIDCA perform multiple actions in one cycle, simple add several actions to mem[mem.ACTIONS][-1]. So mem[mem.ACTIONS][-1][0] is the first action taken, mem[mem.ACTIONS][-1][1] is the second, etc.
    '''



    def init(self, world, mem):
        # establish ActiveMQ connection
        self.mem = mem
        self.world = world
        self.act_conn = stomp.Connection()
        self.act_conn.start()
        self.act_conn.connect('admin', 'admin', wait=True)


    def run(self, cycle, verbose=2):

        self.verbose = verbose
        world = self.mem.get(self.mem.STATES)[-1]
        try:
            goals = self.mem.get(self.mem.CURRENT_GOALS)[-1]
        except:
            goals = []

        if self.mem.get(self.mem.JSON_ACT):
            message = self.mem.get_and_lock(self.mem.JSON_ACT)
            self.mem.unlock(self.mem.JSON_ACT)
            plan = eval(message)
            instruction = plan["plan"].pop(0)
            if instruction["action"] == "Land":
                sys.exit()
            message = json.dumps(instruction)
            print ("Sent instruction ")
            print (message)
            self.act_conn.send(body=message, destination='/topic/plan', ack='auto')
            #print ("Plan modified")
            self.mem.set(self.mem.JSON_ACT, json.dumps(plan))
            #print(json.dumps(plan))

        '''
        atoms = self.world.get_atoms()

        plan = dict()
        tile = dict()

        tile['location'] = {"type" : "tile" , "X" : 9, "Y": 8}

        for each in atoms:
            if each.predicate.name == "atlocation":
                if each.args[0].name == "RPA":
                    x = int(each.args[1].name)
                    y = int(each.args[2].name) - 1
                    plan['action'] = "Move"
                    plan['name'] = "RPA"
                    plan['target'] = ""
                    tile['location'] = {"type": "tile", "X": x, "Y": y}
                    plan['target'] = tile
                    print json.dumps(plan)
                    self.act_conn.send(body=json.dumps(plan), destination='/topic/plan', ack='auto')
                    break
        '''
    def __del__(self):
        '''
            close ActiveMQ on deletion.
        '''
        self.act_conn.disconnect()




class RPA_Act(base.BaseModule):
    '''
    MIDCA module that selects the plan, if any, that achieves the most current goals, then selects the next action from that plan. The selected action is stored in a two-dimensional array in mem[mem.ACTIONS], where mem[mem.ACTIONS][x][y] returns the yth action to be taken at time step x. So mem[mem.ACTIONS][-1][0] is the last action selected. Note that this will throw an index error if no action was selected.
    To have MIDCA perform multiple actions in one cycle, simple add several actions to mem[mem.ACTIONS][-1]. So mem[mem.ACTIONS][-1][0] is the first action taken, mem[mem.ACTIONS][-1][1] is the second, etc.
    '''

    def init(self, world, mem):
        # establish ActiveMQ connection
        self.mem = mem
        self.world = world
        self.act_conn = stomp.Connection()
        self.act_conn.start()
        self.act_conn.connect('admin', 'admin', wait=True)


    # returns the plan that achieves the most current goals, based on simulation.
    def get_best_plan(self, world, goals, verbose):
        plan = None
        goalGraph = self.mem.get(self.mem.GOAL_GRAPH)
        plan = self.mem.get(self.mem.GOAL_GRAPH).getMatchingPlan(goals)
        if plan == None and verbose >= 1:
            print "No valid plan found that achieves any current goals."

        return plan

    def check_action_invalid(self,action):
        if not action:
            return False
        location = {}
        for atom in self.world.atoms:
            if 'atlocation' == atom.predicate.name:
                if atom.args[0].name == "RPA":
                    location["X"] = atom.args[1].name
                    location["Y"] = atom.args[2].name
                    break
        if location["X"] == action.args[1] and \
            location["Y"] == action.args[2]:
            return True

        return False

    def run(self, cycle, verbose=2):
        self.verbose = verbose
        max_plan_print_size = 5
        world = self.mem.get(self.mem.STATES)[-1]
        try:
            goals = self.mem.get(self.mem.CURRENT_GOALS)[-1]
        except:
            goals = []
        plan = self.get_best_plan(world, goals, verbose)
        print plan
        trace = self.mem.trace
        if trace:
            trace.add_module(cycle, self.__class__.__name__)
            trace.add_data("WORLD", copy.deepcopy(world))
            trace.add_data("GOALS", copy.deepcopy(goals))
            trace.add_data("PLAN", copy.deepcopy(plan))

        if plan is not None:
            action = plan.get_next_step()
            #if self.check_action_invalid(action):
            #    plan.advance()
            #    action = plan.get_next_step()
            if not action:
                if verbose >= 1:
                    print "Plan to achieve goals has already been completed. Taking no action."
                self.mem.add(self.mem.ACTIONS, [])
            else:
                instruction = API.actoutput_json(action)
                message = json.dumps(instruction)
                self.act_conn.send(body=message, destination='/topic/plan', ack='auto')
                if instruction["action"] == "Land":
                    sys.exit()
                if verbose == 1:
                    print "Action selected:", action

                elif verbose >= 2:
                    if len(plan) > max_plan_print_size:
                        # print just the next 3 actions of the plan
                        print "Selected action", action, "from plan:\n"
                        if verbose >= 3:
                            for a in plan:
                                print "  " + str(a)
                    else:
                        # print the whole plan
                        print "Selected action", action, "from plan:\n", plan

                self.mem.add(self.mem.ACTIONS, [action])
                actions = self.mem.get(self.mem.ACTIONS)
                if len(actions) > 400:
                    actions = actions[200:]  # trim off old stale actions
                    self.mem.set(self.mem.ACTIONS, actions)
                    # print "Trimmed off 200 old stale actions to save space"


                if trace: trace.add_data("ACTION", action)
        else:
            if verbose >= 1:
                print "MIDCA will not select an action this cycle."
            self.mem.add(self.mem.ACTIONS, [])
            if trace: trace.add_data("ACTION", None)

    def __del__(self):
        '''
            close ActiveMQ on deletion.
        '''
        self.act_conn.disconnect()