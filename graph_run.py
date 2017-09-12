#! /usr/bin/python3

from enum import Enum
import random

from graph_types import Run


class ConditionResults(Enum):
    CONTINUE = 0
    SUCCESS = 1
    FAIL = 2
    NOTHING = 3


def _chose_transition(applicable_transitions):
    return random.choice(applicable_transitions) if len(applicable_transitions) > 0 else None


def _get_successor(graph, node):
    return [child for children_tuple in
            [edge.children for edge in graph.edges if edge.parent == node]  # all children tuples
            for child in children_tuple]


def _get_reverse_jump(jump):
    assert jump[-1] in ['-', '+']
    return jump[0:-1] + '-' if jump[-1] == '+' else jump[0:-1] + '+'


def _condition_in_node_jumps(_, node, jump, run, explored_jump_pairs):
    assert len([pair for pair in explored_jump_pairs if node in pair]) <= 1

    if _get_reverse_jump(jump) in run.at(node).data.jumps \
            and len([pair for pair in explored_jump_pairs
                     if node in pair]) == 0:  # node found
        print(jump, " has reverse ", run.at(node))
        return ConditionResults.SUCCESS

    return ConditionResults.NOTHING


def _should_process_node_jumps(node, run, processed_jumps):
    return len(run.at(node).data.jumps) > 0 \
           and any([jump_node not in processed_jumps for jump_node in run.at(node).data.jumps])


def _process_node_jumps(graph, run, node, processed_jumps, semantics_info):
    for jump in run.at(node).data.jumps:
        if not _verify_condition_from_node(graph, node, run, jump,
                                           _condition_in_node_jumps, semantics_info, False):
            return False
        processed_jumps.update([jump, _get_reverse_jump(jump)])

    return True


def _jump_final_check(graph, run, semantics_info):
    for jump_pair in semantics_info:
        pair_path = _find_path(graph, jump_pair[0], jump_pair[1])
        jumps = [jump for jump in run[jump_pair[0]].data.jumps
                 if _get_reverse_jump(jump) in run[jump_pair[1]].data.jumps]
        for jump in jumps:
            similar_nodes = [node for node in graph.nodes if jump in run[node].data.jumps]
            for similar_node in similar_nodes:
                similar_pairs = [pair for pair in semantics_info if similar_node in pair]
                for similar_pair in similar_pairs:
                    if similar_pair == jump_pair:
                        continue
                    second_node = list(set(similar_pair) - {similar_node})[0]
                    if _get_reverse_jump(jump) not in run[second_node].data.jumps:
                        continue
                    path_intersection = set(pair_path).intersection(
                        set(_find_path(graph, jump_pair[0], jump_pair[1])))
                    if len(path_intersection) > 0:
                        return False

    return True


def _verify_jumps(graph, run):
    return _run_graph_traversal(graph,
                                run,
                                _should_process_node_jumps,
                                _process_node_jumps,
                                _jump_final_check)


def _condition_in_node_connects(graph, node, var, run, _):
    if var in run.at(node).data.forget:  # cut branch
        return ConditionResults.CONTINUE
    if var in run.at(node).data.vars \
            and len([edge for edge in graph.edges
                     if edge.parent == node and len(edge.children) > 0]) > 0:
        # we found another node but we look only for leaves with the same var
        return ConditionResults.FAIL

    return ConditionResults.NOTHING


def _should_process_node_connects(node, run, processed_vars):
    return len(run.at(node).data.vars) > 0 \
           and any([var not in processed_vars for var in run.at(node).data.vars])


def _process_node_connects(graph, run, node, processed_vars, semantics_info):
    for var in run.at(node).data.vars:
        if not _verify_condition_from_node(graph, node, run, var,
                                           _condition_in_node_connects, semantics_info, True):
            return False
        processed_vars.add(var)

    return True


def _verify_connects(graph, run):
    return _run_graph_traversal(graph, run,
                                _should_process_node_connects,
                                _process_node_connects,
                                lambda g, r, s: True)


def _verify_condition_from_node(graph, top_node, run, item, condition_checker,
                                semantics_info, default_result):
    todo = _get_successor(graph, top_node)
    processed = {top_node}

    while len(todo) > 0:
        for node in todo:
            assert node in run
            res = condition_checker(graph, node, item, run, semantics_info)
            if res is ConditionResults.CONTINUE:
                todo.remove(node)
                processed.add(node)
                continue
            elif res is ConditionResults.FAIL:
                return False
            elif res is ConditionResults.SUCCESS:
                semantics_info.append((top_node, node))
                return True

            todo.remove(node)
            processed.add(node)
            todo += [new_node for new_node in _get_successor(graph, node) if
                     new_node not in processed]

    assert top_node in processed
    return default_result


def _find_path(graph, node1, node2):
    todo = _get_successor(graph, node1)
    prec = {succ: node1 for succ in todo}
    found = False

    while len(todo) > 0 and not found:
        for node in todo:
            found = node == node2
            if found:
                break
            todo.remove(node)
            tmp = _get_successor(graph, node)
            prec.update({succ: node for succ in tmp})
            todo += [n for n in tmp if n not in todo]

    if node2 not in prec.keys():
        return None

    # reconstruct path
    path = []
    node = node2
    while node is not node1:
        path = [node] + path
        node = prec[node]

    path = [node1] + path

    return path


def _run_graph_traversal(graph, run, should_process_node, process_node, final_check):
    todo = list(graph.root())
    processed_nodes = set()
    processed_items = set()
    semantics_info = []

    while len(todo) > 0:
        node = todo.pop()
        if should_process_node(node, run, processed_items):
            assert node in run
            if not process_node(graph, run, node, processed_items, semantics_info):
                return False

        processed_nodes.add(node)
        todo += [new_node for new_node in _get_successor(graph, node) if
                 new_node not in processed_nodes and new_node not in todo]

    assert processed_nodes == graph.nodes
    if not final_check(graph, run, semantics_info):
        return False

    return True


def automaton_run(automaton, graph):
    """
    :param automaton: @require applicable_transitions(edge, run)
                               transitions_to_run(transition)
    :param graph:  @require .edges
    :return: run: @require map: node -> information
    """
    # 1) Create already processed edges and not processed edges
    run = Run()
    processed_edges = []
    todo = list(graph.edges)

    # 2) search for applicable transitions
    while len(todo) is not 0:
        orig_todo_size = len(todo)
        for edge in todo:
            chosen_trans = _chose_transition(automaton.applicable_transitions(edge, run))
            if chosen_trans is None:
                continue
            run.map(edge.parent, automaton.transition_to_run(chosen_trans)[0],
                    automaton.transition_to_run(chosen_trans)[1])

            processed_edges.append(edge)
            todo.remove(edge)

        if orig_todo_size - len(todo) == 0 and len(todo) is not 0:
            raise RuntimeError("Run failed")

    verify_semantics(graph, run)
    print("Final run:")
    print(run)
    return run


def verify_semantics(graph, run):
    # 3) verify run conditions
    # 3.1. verify connecting conditions
    if not _verify_connects(graph, run):
        raise RuntimeError("Failed to verify connects")
    # 3.2. verify jumping
    if not _verify_jumps(graph, run):
        raise RuntimeError("Failed to verify jumps")

    assert all([node in run for node in graph.nodes])
