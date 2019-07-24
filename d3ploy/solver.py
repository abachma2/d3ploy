import random
import copy
import math
from collections import defaultdict
from collections import OrderedDict
import numpy as np

"""
This solver.py file contains auxillary functions that
aid `timeseries_inst.py'.
"""


def deploy_solver(commodity_supply, commodity_dict, commod, diff, time):
    """ This function optimizes prototypes to deploy to minimize over
        deployment of prototypes.
    Paramters:
    ----------
    comomdity_supply: dictionary
        key: commod
        value: dictionary
            key: time
            value: amount of supply of commod at time
    commodity_dict: dictionary
        key: str
            commodity name
        value: dictionary
            key: str
                prototype name
            value: float
                prototype capacity
    commod: str
        commodity driving deployment
    diff: float
        lack in supply
    time: int
        time of evaluation

    Returns:
    --------
    deploy_dict: dict
        key: prototype name
        value: # to deploy
    """
    diff = -1.0 * diff
    proto_commod = commodity_dict[commod]

    # checks if the commodity has a sharing percentage
    # it should check the constraint first. <---- bug
    # need to change this, if pref>0 then check share
    # if pref<0 then don't deploy anything.
    # if pref>0 but they are different, use share
    # if one of them is >0 and the others are not,
    # just deploy that one, ignore share.

    # if the preference is defined
    eval_pref_fac = evaluate_preference(proto_commod, time)
    eval_pref_fac, proto_commod = check_constraint(proto_commod,
                                                   commodity_supply,
                                                   eval_pref_fac,
                                                   time)
    commodity_dict[commod] = proto_commod
    filtered_pref_fac = {}
    for key, val in eval_pref_fac.items():
        if val >= 0:
            filtered_pref_fac[key] = val
        else:
            filtered_pref_fac[key] = -1
    # check if the preference values are different   
    if len(set(filtered_pref_fac.values())) != 1:
        # if there is a difference, deploys the one with highest
        # preference until it oversupplies
        # if all the preferences are negative it does not deploy anything
        return preference_deploy(proto_commod, eval_pref_fac,
                                 diff), commodity_dict
    else:
        # if all the preferences are equal checks if there sign
        if list(filtered_pref_fac.values())[0] < 0:
            # if the preferences are negative, does not deploy anything
            return preference_deploy(proto_commod, eval_pref_fac,
                                     diff), commodity_dict
        else:
            # if the preferences are positive, checks first if there are
            # sharing preferences given.
            for proto, proto_dict in proto_commod.items():
                if proto_dict['share'] != 0:
                    # if there are sharing percentages defined
                    return sharing_deploy(proto_commod, diff), commodity_dict
                else:
                    # deploys to minimize number of
                    # facilities deployed. It deploys first the one with
                    # largest capacities.
                    return minimize_number_of_deployment(proto_commod,
                                                         diff), commodity_dict


def evaluate_preference(proto_commod, time):
    t = time
    eval_pref_fac = {}
    for proto, val_dict in proto_commod.items():
        t = time
        pref = eval(val_dict['pref'])
        eval_pref_fac[proto] = pref
    return eval_pref_fac


def check_constraint(proto_commod, commodity_supply, eval_pref_fac, time):
    for proto, val_dict in proto_commod.items():
        if val_dict['constraint_commod'] != '0':
            current_supply = commodity_supply[val_dict['constraint_commod']][time]
            if current_supply < float(val_dict['constraint']):
                eval_pref_fac[proto] = -1e299
            else:
                proto_commod[proto]['constraint'] = '0'
    return eval_pref_fac, proto_commod


def preference_deploy(proto_commod, pref_fac, diff):
    """ This function deploys the facility with the highest preference only.
    Paramters:
    ----------
    proto_commod: dictionary
        key: prototype name
        value: dictionary
            key: 'cap', 'pref', 'constraint_commod', 'constraint'
            value
    pref_fac: dictionary
        key: prototype name
        value: preference value
    diff: float
        amount of capacity that is needed

    Returns:
    --------
    deploy_dict: dictionary
        key: prototype name
        value: number of prototype to deploy
    """

    # get the facility with highest preference
    deploy_dict = {}
    proto = sorted(pref_fac,
                   key=pref_fac.get, reverse=True)[0]
    if pref_fac[proto] < 0:
        return deploy_dict
    if diff >= proto_commod[proto]['cap']:
        deploy_dict[proto] = 1
        diff -= proto_commod[proto]['cap']
        while diff > proto_commod[proto]['cap']:
            deploy_dict[proto] += 1
            diff -= proto_commod[proto]['cap']
        if diff == 0:
            return deploy_dict
        else:
            deploy_dict[proto] += 1
    elif diff > 0:
        deploy_dict[proto] = 1

    return deploy_dict


def minimize_number_of_deployment(proto_commod, remainder):
    """ This function deploys facilities to meet the lack in
    capacity by deploying the least number of facilities.

    Parameters:
    ----------
    proto_commod: dictionary
        key: prototype name
        value: prototype capacity
    remainder: float
        amount of capacity that is needed

    Returns:
    --------
    deploy_dict: dictionary
        key: prototype name
        value: number of prototype to deploy
    """
    deploy_dict = {}
    cap_dict = {}
    for proto, val_dict in proto_commod.items():
        cap_dict[proto] = val_dict['cap']
    min_cap = min(cap_dict.values())
    key_list = sorted(cap_dict, key=cap_dict.get, reverse=True)
    for proto in key_list:
        # if diff still smaller than the proto capacity,
        if remainder >= proto_commod[proto]['cap']:
            deploy_dict[proto] = 1
            remainder -= proto_commod[proto]['cap']
            while remainder > proto_commod[proto]['cap']:
                deploy_dict[proto] += 1
                remainder -= proto_commod[proto]['cap']
    if remainder == 0:
        return deploy_dict

    # i have to check this
    for proto in list(reversed(key_list)):
        # see if the prototype cap is bigger than remainder
        if remainder > proto_commod[proto]['cap']:
            continue
        if proto in deploy_dict.keys():
            deploy_dict[proto] += 1
        else:
            deploy_dict[proto] = 1
        break

    return deploy_dict
        

def sharing_deploy(proto_commod, remainder):
    """ This functions deploys facilities based on the sharing percentages

    Parameters:
    ----------
    proto_commod: dictionary
        key: prototype name
        value: dictionary
            key: 'cap', 'pref', 'constraint_commod', 'constraint', 'share'
            value
    remainder: float
        amount of capacity that is needed

    Returns:
    --------
    deploy_dict: dictionary
        key: prototype name
        value: number of prototype to deploy
    """
    deploy_dict = {}
    share_dict = {}
    remain = {}
    for proto, proto_dict in proto_commod.items():
        # print(proto, proto_dict['share'])
        # I need to add something that checks that the percentages add to 100
        remain[proto] = proto_dict['share'] * remainder/100.0
        deploy_dict[proto] = 0

    for proto in remain:
        while remain[proto] > 0:
            deploy_dict[proto] += 1
            remain[proto] -= proto_commod[proto]['cap']
    print("sharing: ", deploy_dict)

    return deploy_dict
