from MIDCA.modules._plan import pyhop

def point_at_m(state, objectID):
	return [("block_until_seen", objectID), ("point_to", objectID)]
def pickup(state, objectID):
	#return [("block_until_seen", objectID),("wait_to_see", objectID), ("grab", objectID)]
	return [("block_until_seen", objectID), ("reach", objectID), ("grab", objectID), ("raising", objectID)]
	#return [("block_until_seen", objectID), ("reach", objectID)]

def achieve_goals_m(state, goals):
	if goals:
		goal = goals[0]
		if goal["objective"] == "show-loc":
			return [("point_at", goal["directObject"]), ("achieve_goals", goals[1:])]
		if goal["objective"] == "holding":
			return [("pickup", goal["directObject"]), ("achieve_goals", goals[1:])]
		else:
			return False #fail if goal is not of known type
	return [] #return empty plan if no goals.

def declare_methods():
	pyhop.declare_methods("point_at", point_at_m)
	pyhop.declare_methods("pickup", pickup)
	pyhop.declare_methods("achieve_goals", achieve_goals_m)
