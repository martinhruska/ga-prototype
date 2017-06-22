#! /usr/bin/python3

from enum import Enum
import random

from graph_types import Run


# OBSOLETE START HERE
def _verify_jump(graph, jump_node, jump, run):
    todo = _get_successor(graph, jump_node)
    processed = set()

    while len(todo) is not 0:  # search through the graph for target/source of jump
        for act_node in todo:
            assert act_node in run
            if _get_reverse_jump(jump) in run.at(act_node).jumps:  # node found
                print(jump, " has reverse ", run.at(act_node))
                return True
            todo.remove(act_node)
            processed.add(act_node)
            todo += [new_node for new_node in _get_successor(graph, act_node) if
                     new_node not in processed]

    return False


def _verify_jumps_lit(graph, run):
    processed_jumps = set()
    todo = list(graph.root())
    processed_nodes = set()

    while len(todo) > 0:
        node = todo.pop(0)
        if len(run.at(node).jumps) == 0 \
                or all([jump_node in processed_jumps for jump_node in run.at(node).jumps]):
            continue

        assert node in run
        for jump in run.at(node).jumps:
            if not _verify_jump(graph, node, jump, run):
                return False
            processed_jumps.update([jump, _get_reverse_jump(jump)])

        processed_nodes.add(node)
        todo += [new_node for new_node in _get_successor(graph, node) if
                 new_node not in processed_nodes]

    return True


def _verify_connect(graph, var_node, run, var):
    todo = _get_successor(graph, var_node)
    processed = set()

    print("Checking variable ", var, " for node ", var_node)
    while len(todo) > 0:
        for node in todo:
            assert node in run
            if var in run.at(node).forget:  # cut branch
                continue
            if var in run.at(node).vars \
                    and len([edge for edge in graph.edges
                             if edge.parent == node and len(edge.children) > 0]) > 0:
                return False  # we found another node but we look only for leaves with the same var

            todo.remove(node)
            processed.add(node)
            todo += [new_node for new_node in _get_successor(graph, node) if
                     new_node not in processed]

    return True


def _verify_connects_lit(graph, run):
    todo = list(graph.root())
    processed_nodes = set()
    processed_vars = set()

    while len(todo) > 0:
        node = todo.pop()
        if len(run.at(node).vars) == 0 \
                or all([var in processed_vars for var in run.at(node).vars]):
            continue

        assert node in run
        for var in run.at(node).vars:
            if not _verify_connect(graph, node, run, var):
                return False
            processed_vars.add(var)

        processed_nodes.add(node)
        todo += [new_node for new_node in _get_successor(graph, node) if
                 new_node not in processed_nodes]

    return True


# OBSOLETE END HERE


class ConditionResults(Enum):
    CONTINUE = 0
    SUCCESS = 1
    FAIL = 2
    NOTHING = 3


def _map_node_to_trans(run, node, trans):
    run.map(node, trans.parent, trans.vars, trans.forget, trans.jumps)
    return run


def _get_candidate_trans(edge, transitions, run):
    return [trans for trans in transitions if
            edge.symbol == trans.symbol and
            len(edge.children) == len(trans.children) and
            tuple((run.get_state(child) if child in run else False
                   for child in edge.children)) == trans.children]


def _chose_transition(edge, transitions, run):
    candidate_trans = _get_candidate_trans(edge, transitions, run)
    return random.choice(candidate_trans) if len(candidate_trans) > 0 else None


def _get_successor(graph, node):
    return [child for children_tuple in
            [edge.children for edge in graph.edges if edge.parent == node]  # all children tuples
            for child in children_tuple]


def _get_reverse_jump(jump):
    assert jump[-1] in ['-', '+']
    return jump[0:-1] + '-' if jump[-1] == '+' else jump[0:-1] + '+'


def _condition_in_node_jumps(_, node, jump, run):
    if _get_reverse_jump(jump) in run.at(node).jumps:  # node found
        print(jump, " has reverse ", run.at(node))
        return ConditionResults.SUCCESS

    return ConditionResults.NOTHING


def _should_process_node_jumps(node, run, processed_jumps):
    return len(run.at(node).jumps) > 0 \
           and any([jump_node not in processed_jumps for jump_node in run.at(node).jumps])


def _process_node_jumps(graph, run, node, processed_jumps):
    for jump in run.at(node).jumps:
        if not _verify_condition_from_node(graph, node, run, jump,
                                           _condition_in_node_jumps, False):
            return False
        processed_jumps.update([jump, _get_reverse_jump(jump)])

    return True


def _verify_jumps(graph, run):
    return _run_graph_traversal(graph, run,
                                _should_process_node_jumps, _process_node_jumps)


def _condition_in_node_connects(graph, node, var, run):
    if var in run.at(node).forget:  # cut branch
        return ConditionResults.CONTINUE
    if var in run.at(node).vars \
            and len([edge for edge in graph.edges
                     if edge.parent == node and len(edge.children) > 0]) > 0:
        # we found another node but we look only for leaves with the same var
        return ConditionResults.FAIL

    return ConditionResults.NOTHING


def _should_process_node_connects(node, run, processed_vars):
    return len(run.at(node).vars) > 0 \
                and any([var not in processed_vars for var in run.at(node).vars])


def _process_node_connects(graph, run, node, processed_vars):
    for var in run.at(node).vars:
        if not _verify_condition_from_node(graph, node, run, var,
                                           _condition_in_node_connects, True):
            return False
        processed_vars.add(var)

    return True


def _verify_connects(graph, run):
    return _run_graph_traversal(graph, run,
                                _should_process_node_connects,
                                _process_node_connects)


def _verify_condition_from_node(graph, node, run, item, condition_checker, default_result):
    todo = _get_successor(graph, node)
    processed = set([node])

    while len(todo) > 0:
        for node in todo:
            assert node in run
            res = condition_checker(graph, node, item, run)
            if res is ConditionResults.CONTINUE:
                todo.remove(node)
                processed.add(node)
                continue
            elif res is ConditionResults.FAIL:
                return False
            elif res is ConditionResults.SUCCESS:
                return True

            todo.remove(node)
            processed.add(node)
            todo += [new_node for new_node in _get_successor(graph, node) if
                     new_node not in processed]

    assert node in processed
    return default_result


def _run_graph_traversal(graph, run, should_process_node, process_node):
    todo = list(graph.root())
    processed_nodes = set()
    processed_items = set()

    while len(todo) > 0:
        node = todo.pop()
        if should_process_node(node, run, processed_items):
            assert node in run
            if not process_node(graph, run, node, processed_items):
                return False

        processed_nodes.add(node)
        todo += [new_node for new_node in _get_successor(graph, node) if
                 new_node not in processed_nodes and new_node not in todo]

    assert processed_nodes == graph.nodes
    return True


def automaton_run(automaton, graph):
    # 1) Create already processed edges and not processed edges
    run = Run()
    processed = []
    todo = list(graph.edges)

    # 2) search for applicable transitions
    while len(todo) is not 0:
        orig_todo_size = len(todo)
        for edge in todo:
            chosen_trans = _chose_transition(edge, automaton.transitions, run)
            if chosen_trans is None:
                continue
            run = _map_node_to_trans(run, edge.parent, chosen_trans)
            processed.append(edge)
            todo.remove(edge)

        if orig_todo_size - len(todo) == 0 and len(todo) is not 0:
            # print("Run: ", run)
            raise RuntimeError("Run failed")

    # 3) verify run conditions
    # 3.1. verify connecting conditions
    if not _verify_connects(graph, run):
        raise RuntimeError("Failed to verify connects")
    # 3.2. verify jumping
    if not _verify_jumps(graph, run):
        raise RuntimeError("Failed to verify jumps")

    assert all([node in run for node in graph.nodes])
    print("Final run:")
    print(run)
    return run
