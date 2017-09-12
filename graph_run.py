#! /usr/bin/python3

import random

from graph_types import Run


def _chose_transition(applicable_transitions):
    return random.choice(applicable_transitions) if len(applicable_transitions) > 0 else None


def automaton_run(automaton, graph):
    """
    :param automaton: @require applicable_transitions(edge, run)
                               transitions_to_run(transition)
                               check_run_graph_semantics
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

    automaton.check_run_graph_semantics(graph, run)
    print("Final run:")
    print(run)
    return run
