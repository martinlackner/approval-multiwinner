"""
Unit tests for: abcrules.py, abcrules_gurobi.py, abcrules_mip.py and abcrules_cvxpy.py
"""
import pytest
import os
import re
import random
from abcvoting.abcrules_gurobi import _gurobi_thiele_methods
from abcvoting.output import VERBOSITY_TO_NAME, WARNING, INFO, DETAILS, DEBUG, output
from abcvoting.preferences import Profile, Voter, CandidateSet
from abcvoting import abcrules, misc, scores, fileio
from itertools import combinations

MARKS = {
    "gurobi": [pytest.mark.gurobi],
    # "cvxpy_scip": [pytest.mark.cvxpy, pytest.mark.scip],
    # "cvxpy_glpk_mi": [pytest.mark.cvxpy, pytest.mark.glpk_mi],
    # "cvxpy_cbc": [pytest.mark.cvxpy, pytest.mark.cbc],
    # "cvxpy_gurobi": [pytest.mark.cvxpy, pytest.mark.gurobi],
    "ortools-cp": [pytest.mark.ortools],
    # "ortools-cbc": [pytest.mark.ortools, pytest.mark.cbc],
    # "ortools-gurobi": [pytest.mark.ortools, pytest.mark.gurobi],
    # "ortools-scip": [pytest.mark.ortools, pytest.mark.scip],
    "mip-cbc": [pytest.mark.mip],  # does not require cbc because cbc is included in mip
    "mip-gurobi": [pytest.mark.mip, pytest.mark.gurobi],
    "brute-force": [],
    "branch-and-bound": [],
    "standard": [],
    "standard-fractions": [],
    "gmpy2-fractions": [pytest.mark.gmpy2],
    "float-fractions": [],
    "fastest": [],
}
random.seed(24121838)


class CollectRules:
    """
    Collect all ABC rules that are available for unittesting.
    Exclude Gurobi-based rules if Gurobi is not available
    """

    def __init__(self):
        self.rule_algorithm_resolute = []
        self.rule_algorithm_onlyresolute = []
        self.rule_algorithm_onlyirresolute = []
        for rule_id in abcrules.MAIN_RULE_IDS:
            rule = abcrules.get_rule(rule_id)
            for algorithm in list(rule.algorithms) + ["fastest"]:
                for resolute in rule.resolute_values:
                    if algorithm in MARKS:
                        if algorithm == "fastest":
                            try:
                                actual_algorithm = rule.fastest_available_algorithm()
                            except abcrules.NoAvailableAlgorithm:
                                continue  # no available algorithm for `rule`
                        else:
                            actual_algorithm = algorithm
                        instance = pytest.param(
                            rule_id, algorithm, resolute, marks=MARKS[actual_algorithm]
                        )
                        instance_no_resolute_param = pytest.param(
                            rule_id, algorithm, marks=MARKS[actual_algorithm]
                        )
                    else:
                        raise ValueError(
                            f"Algorithm {algorithm} (for {rule_id}) "
                            f"not known in unit tests "
                            f"(pytest marks are missing)."
                        )

                    self.rule_algorithm_resolute.append(instance)
                    if resolute:
                        self.rule_algorithm_onlyresolute.append(instance_no_resolute_param)
                    else:
                        self.rule_algorithm_onlyirresolute.append(instance_no_resolute_param)


class CollectInstances:
    def __init__(self):
        self.instances = []
        alltests = {}
        profiles = {}

        # first profile
        name = "profile1"
        profiles[name] = Profile(6)
        committeesize = 4
        approval_sets = [{0, 4, 5}, {0}, {1, 4, 5}, {1}, {2, 4, 5}, {2}, {3, 4, 5}, {3}]
        profiles[name].add_voters(approval_sets)
        alltests[name] = {
            "committeesize": committeesize,
            "seqpav": [
                {0, 1, 4, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "av": [
                {0, 1, 4, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "sav": [
                {0, 1, 2, 3},
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 1, 3, 4},
                {0, 1, 3, 5},
                {0, 1, 4, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "pav": [
                {0, 1, 4, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "geom2": [
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 1, 3, 4},
                {0, 1, 3, 5},
                {0, 1, 4, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "revseqpav": [
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 1, 3, 4},
                {0, 1, 3, 5},
                {0, 1, 4, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "minimaxav": [
                {0, 1, 2, 3},
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 1, 3, 4},
                {0, 1, 3, 5},
                {0, 1, 4, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "lexminimaxav": [
                {0, 1, 4, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "seqphragmen": [
                {0, 1, 4, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "minimaxphragmen": [{0, 1, 2, 3}],
            "leximinphragmen": [{0, 1, 2, 3}],
            "cc": [{0, 1, 2, 3}],
            "lexcc": [{0, 1, 2, 3}],
            "seqcc": [
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 1, 3, 4},
                {0, 1, 3, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
            ],
            "revseqcc": [{0, 1, 2, 3}],
            "monroe": [{0, 1, 2, 3}],
            "greedy-monroe": [{0, 2, 3, 4}],
            "slav": [
                {0, 1, 2, 3},
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 1, 3, 4},
                {0, 1, 3, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
            ],
            "seqslav": [
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 1, 3, 4},
                {0, 1, 3, 5},
                {0, 1, 4, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "rule-x": [
                {0, 1, 4, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "rule-x-without-phragmen-phase": [{4, 5}],
            "phragmen-enestroem": [
                {0, 1, 4, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "consensus-rule": [
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 1, 3, 4},
                {0, 1, 3, 5},
                {0, 1, 4, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {0, 3, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
                {1, 3, 4, 5},
                {2, 3, 4, 5},
            ],
            "trivial": [
                set(committee)
                for committee in combinations(profiles[name].candidates, committeesize)
            ],
        }

        # first profile now with reversed list of voters
        name = "profile1-reversed"
        approval_sets.reverse()
        profiles[name] = Profile(6)
        profiles[name].add_voters(approval_sets)
        # Greedy Monroe yields a different result
        # for a different voter ordering
        alltests[name] = dict(alltests["profile1"])
        alltests[name]["greedy-monroe"] = [{0, 1, 2, 4}]
        committeesize = 4

        # second profile
        name = "profile2"
        profiles[name] = Profile(5)
        committeesize = 3
        approval_sets = [
            {0, 1, 2},
            {0, 1, 2},
            {0, 1, 2},
            {0, 1, 2},
            {0, 1, 2},
            {0, 1},
            {3, 4},
            {3, 4},
            {3},
        ]
        profiles[name].add_voters(approval_sets)
        alltests[name] = {
            "committeesize": committeesize,
            "seqpav": [{0, 1, 3}],
            "av": [{0, 1, 2}],
            "sav": [{0, 1, 3}],
            "pav": [{0, 1, 3}],
            "geom2": [{0, 1, 3}],
            "revseqpav": [{0, 1, 3}],
            "minimaxav": [{0, 1, 3}, {0, 2, 3}, {1, 2, 3}],
            "lexminimaxav": [{0, 1, 3}],
            "seqphragmen": [{0, 1, 3}],
            "minimaxphragmen": [{0, 1, 3}, {0, 2, 3}, {1, 2, 3}],
            "leximinphragmen": [{0, 1, 3}, {0, 2, 3}, {1, 2, 3}],
            "cc": [{0, 1, 3}, {0, 2, 3}, {0, 3, 4}, {1, 2, 3}, {1, 3, 4}],
            "lexcc": [{0, 1, 3}],
            "seqcc": [{0, 1, 3}, {0, 2, 3}, {0, 3, 4}, {1, 2, 3}, {1, 3, 4}],
            "revseqcc": [{0, 1, 3}, {0, 2, 3}, {0, 3, 4}, {1, 2, 3}, {1, 3, 4}],
            "monroe": [{0, 1, 3}, {0, 2, 3}, {1, 2, 3}],
            "greedy-monroe": [{0, 1, 3}],
            "seqslav": [{0, 1, 3}],
            "slav": [{0, 1, 3}],
            "rule-x": [{0, 1, 3}],
            "rule-x-without-phragmen-phase": [{0, 1, 3}],
            "phragmen-enestroem": [{0, 1, 3}],
            "consensus-rule": [{0, 1, 3}],
            "trivial": [
                set(committee)
                for committee in combinations(profiles[name].candidates, committeesize)
            ],
        }

        # and a third profile
        name = "profile3"
        profiles[name] = Profile(6)
        committeesize = 4
        approval_sets = [
            {0, 3, 4, 5},
            {1, 2},
            {0, 2, 5},
            {2},
            {0, 1, 2, 3, 4},
            {0, 3, 4},
            {0, 2, 4},
            {0, 1},
        ]
        profiles[name].add_voters(approval_sets)
        alltests[name] = {
            "committeesize": committeesize,
            "seqpav": [{0, 1, 2, 4}],
            "av": [{0, 1, 2, 4}, {0, 2, 3, 4}],
            "sav": [{0, 1, 2, 4}],
            "pav": [{0, 1, 2, 4}],
            "geom2": [{0, 1, 2, 4}],
            "revseqpav": [{0, 1, 2, 4}],
            "minimaxav": [{0, 1, 2, 3}, {0, 1, 2, 4}, {0, 2, 3, 4}, {0, 2, 3, 5}, {0, 2, 4, 5}],
            "lexminimaxav": [{0, 1, 2, 4}],
            "seqphragmen": [{0, 1, 2, 4}],
            "minimaxphragmen": [
                {0, 1, 2, 3},
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
            ],
            "leximinphragmen": [
                {0, 1, 2, 3},
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
            ],
            "cc": [
                {0, 1, 2, 3},
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
            ],
            "lexcc": [{0, 1, 2, 4}],
            "seqcc": [
                {0, 1, 2, 3},
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
            ],
            "revseqcc": [
                {0, 1, 2, 3},
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
            ],
            "monroe": [
                {0, 1, 2, 3},
                {0, 1, 2, 4},
                {0, 1, 2, 5},
                {0, 2, 3, 4},
                {0, 2, 3, 5},
                {0, 2, 4, 5},
                {1, 2, 3, 4},
                {1, 2, 3, 5},
                {1, 2, 4, 5},
            ],
            "greedy-monroe": [{0, 1, 2, 4}],
            "seqslav": [{0, 1, 2, 4}],
            "slav": [{0, 1, 2, 4}],
            "rule-x": [{0, 1, 2, 4}],
            "rule-x-without-phragmen-phase": [{0, 2}],
            "phragmen-enestroem": [{0, 1, 2, 4}],
            "consensus-rule": [{0, 1, 2, 4}],
            "trivial": [
                set(committee)
                for committee in combinations(profiles[name].candidates, committeesize)
            ],
        }

        # and a fourth profile
        name = "profile4"
        profiles[name] = Profile(4)
        committeesize = 2
        approval_sets = [{0, 1, 3}, {0, 1}, {0, 1}, {0, 3}, {2, 3}]
        profiles[name].add_voters(approval_sets)
        alltests[name] = {
            "committeesize": committeesize,
            "seqpav": [{0, 3}],
            "av": [{0, 1}, {0, 3}],
            "sav": [{0, 1}, {0, 3}],
            "pav": [{0, 3}],
            "geom2": [{0, 3}],
            "revseqpav": [{0, 3}],
            "minimaxav": [{0, 3}, {1, 3}],
            "lexminimaxav": [{0, 3}],
            "seqphragmen": [{0, 3}],
            "minimaxphragmen": [{0, 3}, {1, 3}],
            "leximinphragmen": [{0, 3}, {1, 3}],
            "cc": [{0, 2}, {0, 3}, {1, 3}],
            "lexcc": [{0, 3}],
            "seqcc": [{0, 2}, {0, 3}],
            "revseqcc": [{0, 2}, {0, 3}, {1, 3}],
            "monroe": [{0, 3}, {1, 3}],
            "greedy-monroe": [{0, 3}],
            "seqslav": [{0, 3}],
            "slav": [{0, 3}],
            "rule-x": [{0, 3}],
            "rule-x-without-phragmen-phase": [{0}],
            "phragmen-enestroem": [{0, 3}],
            "consensus-rule": [{0, 3}],
            "trivial": [
                set(committee)
                for committee in combinations(profiles[name].candidates, committeesize)
            ],
        }

        # add a fifth profile
        # this tests a corner case of minimax
        name = "profile4"
        profiles[name] = Profile(10)
        committeesize = 2
        approval_sets = [range(5), range(5, 10)]
        profiles[name].add_voters(approval_sets)
        one_each = [{i, j} for i in range(5) for j in range(5, 10)]
        all_possibilities = [{i, j} for i in range(10) for j in range(10) if i != j]
        alltests[name] = {
            "committeesize": committeesize,
            "seqpav": one_each,
            "av": all_possibilities,
            "sav": all_possibilities,
            "pav": one_each,
            "geom2": one_each,
            "revseqpav": one_each,
            "minimaxav": one_each,
            "lexminimaxav": one_each,
            "seqphragmen": one_each,
            "minimaxphragmen": one_each,
            "leximinphragmen": one_each,
            "cc": one_each,
            "lexcc": one_each,
            "seqcc": one_each,
            "revseqcc": one_each,
            "monroe": one_each,
            "greedy-monroe": one_each,
            "seqslav": one_each,
            "slav": one_each,
            "rule-x": one_each,
            "rule-x-without-phragmen-phase": one_each,
            "phragmen-enestroem": one_each,
            "consensus-rule": one_each,
            "trivial": [
                set(committee)
                for committee in combinations(profiles[name].candidates, committeesize)
            ],
        }

        for (rule_id, algorithm, resolute), marks, _ in testrules.rule_algorithm_resolute:
            for name, tests in alltests.items():
                if algorithm == "fastest":
                    continue  # redundant
                if rule_id not in tests:
                    if rule_id == "rsd":
                        continue  # randomized results
                    raise RuntimeError(f"rule {rule_id} not considered in {name}")
                if rule_id == "leximinphragmen" and (
                    name in ["profile2", "profile3"] or (name == "profile1" and not resolute)
                ):
                    marks += [pytest.mark.slow]
                self.instances.append(
                    pytest.param(
                        rule_id,
                        algorithm,
                        resolute,
                        profiles[name],
                        name,
                        tests[rule_id],
                        tests["committeesize"],
                        marks=marks,
                    )
                )


def _list_abc_yaml_compute_instances():
    _abc_yaml_instances = []
    currdir = os.path.dirname(os.path.abspath(__file__))
    filenames = [
        currdir + "/test_instances/" + filename
        for filename in os.listdir(currdir + "/test_instances/")
        if filename.endswith(".abc.yaml")
    ]
    for filename in filenames:
        for rule_id in abcrules.MAIN_RULE_IDS:
            rule = abcrules.get_rule(rule_id)
            for algorithm in rule.algorithms:
                if "instanceS" in filename:
                    marks = []  # small instances, rather fast
                    if algorithm in ["mip-cbc"]:
                        marks = [pytest.mark.slow]
                elif "instanceVL" in filename:
                    marks = [pytest.mark.slow, pytest.mark.veryslow]  # very large instances
                elif rule_id == "monroe" and algorithm in ["mip-cbc"]:
                    marks = [pytest.mark.slow, pytest.mark.veryslow]
                elif rule_id == "leximinphragmen":
                    marks = [pytest.mark.slow, pytest.mark.veryslow]
                else:
                    marks = [pytest.mark.slow]
                _abc_yaml_instances.append(
                    pytest.param(filename, rule_id, algorithm, marks=marks + MARKS[algorithm])
                )
    return filenames, _abc_yaml_instances


def id_function(val):
    if isinstance(val, dict):
        return "|".join(str(x for x in val.values()))
    if isinstance(val, tuple):
        return "/".join(map(str, val))
    if isinstance(val, abcrules.Rule):
        return val.rule_id
    return str(val)


testrules = CollectRules()
testinsts = CollectInstances()
abc_yaml_filenames, abc_yaml_compute_instances = _list_abc_yaml_compute_instances()


def remove_solver_output(out):
    """Remove extra, unwanted solver output (e.g. from Gurobi)."""
    filter_patterns = (
        (
            "\n--------------------------------------------\n"
            "Warning: your license will expire in .*\n"
            "--------------------------------------------\n\n"
        ),
        "Using license file.*\n",
        "Set parameter Username.*\n",
        "Academic license - for non-commercial use only.*\n",
    )

    for filter_pattern in filter_patterns:
        out = re.sub(filter_pattern, "", out)

    return out


@pytest.mark.parametrize("rule_id", abcrules.MAIN_RULE_IDS)
def test_resolute_parameter(rule_id):
    rule = abcrules.get_rule(rule_id)
    for algorithm in rule.algorithms:
        resolute_values = rule.resolute_values
        assert len(resolute_values) in [1, 2]
        # raise NotImplementedError if value for resolute is not implemented
        for resolute in [False, True]:
            if resolute not in resolute_values:
                profile = Profile(5)
                committeesize = 1
                approval_sets = [{0, 1, 2}, {1}, {1, 2}, {0}]
                profile.add_voters(approval_sets)

                with pytest.raises(NotImplementedError):
                    abcrules.compute(
                        rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
                    )


@pytest.mark.parametrize("rule_id", abcrules.MAIN_RULE_IDS)
def test_resolute_parameter_default(rule_id):
    rule = abcrules.get_rule(rule_id)
    resolute_values = rule.resolute_values
    profile = Profile(5)
    committeesize = 1
    approval_sets = [{0}, {1}, {2}]
    profile.add_voters(approval_sets)
    try:
        committees1 = abcrules.compute(
            rule_id, profile, committeesize, resolute=resolute_values[0]
        )
        committees2 = abcrules.compute(
            rule_id, profile, committeesize  # using default value for resolute
        )
    except abcrules.NoAvailableAlgorithm:
        pytest.skip("no supported algorithms for " + abcrules.get_rule(rule_id).shortname)

    if rule_id == "rsd":
        assert len(committees1) == len(committees2)  # RSD is randomized

    assert misc.compare_list_of_committees(committees1, committees2)


@pytest.mark.parametrize("rule_id, algorithm, resolute", testrules.rule_algorithm_resolute)
def test_abcrules_toofewcandidates(rule_id, algorithm, resolute):
    profile = Profile(5)
    committeesize = 4
    approval_sets = [{0, 1, 2}, {1}, {2}, {0}]
    profile.add_voters(approval_sets)

    committees = abcrules.get_rule(rule_id).compute(
        profile,
        committeesize,
        algorithm=algorithm,
        resolute=resolute,
    )
    if resolute:
        assert len(committees) == 1
        assert committees[0] in [{0, 1, 2, 3}, {0, 1, 2, 4}]
    else:
        if rule_id == "trivial":
            assert len(committees) == 5
        else:
            assert len(committees) == 2
            assert misc.compare_list_of_committees(committees, [{0, 1, 2, 3}, {0, 1, 2, 4}])


@pytest.mark.parametrize("rule_id, algorithm, resolute", testrules.rule_algorithm_resolute)
def test_abcrules_noapprovedcandidates(rule_id, algorithm, resolute):
    def _check(profile):
        committees = abcrules.get_rule(rule_id).compute(
            profile,
            committeesize=4,
            algorithm=algorithm,
            resolute=resolute,
        )
        if resolute:
            assert len(committees) == 1
        else:
            assert len(committees) == 5

    profile = Profile(5)
    approval_sets = [{}]
    profile.add_voters(approval_sets)
    _check(profile)

    profile.add_voters(approval_sets)
    _check(profile)


def test_abcrules_wrong_rule_id():
    profile = Profile(3)
    with pytest.raises(abcrules.UnknownRuleIDError):
        abcrules.compute("a_rule_that_does_not_exist", profile, 3)


@pytest.mark.parametrize("rule_id, algorithm, resolute", testrules.rule_algorithm_resolute)
def test_abcrules_weightsconsidered(rule_id, algorithm, resolute):
    profile = Profile(3)
    profile.add_voter(Voter([0]))
    profile.add_voter(Voter([0]))
    profile.add_voter(Voter([1], 5))
    profile.add_voter(Voter([0]))
    committeesize = 1

    if rule_id in [
        "lexminimaxav",
        "rule-x",
        "phragmen-enestroem",
        "rsd",
        "monroe",
        "greedy-monroe",
    ]:
        with pytest.raises(ValueError):
            abcrules.compute(rule_id, profile, committeesize, algorithm=algorithm)
        return

    result = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
    )

    if rule_id == "minimaxav":
        # Minimax AV ignores weights by definition
        if resolute:
            assert result == [{0}] or result == [{1}] or result == [{2}]
        else:
            assert result == [{0}, {1}, {2}]
    elif rule_id == "trivial":
        # the trivial rule ignores weights by definition
        if resolute:
            assert result == [{0}]
        else:
            assert result == [{0}, {1}, {2}]
    else:
        assert len(result) == 1
        assert result[0] == {1}


@pytest.mark.parametrize("rule_id, algorithm, resolute", testrules.rule_algorithm_resolute)
def test_abcrules_correct_simple(rule_id, algorithm, resolute):
    def simple_checks(_committees):
        for comm in _committees:
            assert isinstance(comm, CandidateSet)
        if resolute:
            assert len(_committees) == 1
        else:
            assert len(_committees) == 6

    profile = Profile(4)
    profile.add_voters([{0}, {1}, {2}, {3}])
    committeesize = 2

    committees = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
    )
    simple_checks(committees)

    # call abcrules function differently, results should be the same
    committees = abcrules.get_rule(rule_id).compute(
        profile,
        committeesize,
        algorithm=algorithm,
        resolute=resolute,
    )
    simple_checks(committees)

    # using the default algorithm
    committees = abcrules.compute(rule_id, profile, committeesize, resolute=resolute)
    simple_checks(committees)


@pytest.mark.parametrize("rule_id, algorithm, resolute", testrules.rule_algorithm_resolute)
def test_abcrules_correct_simple2(rule_id, algorithm, resolute):
    profile = Profile(6)
    profile.add_voters([{0, 1, 2}, {1, 3}])
    committeesize = 4

    committees = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
    )
    if rule_id not in ["monroe", "trivial", "cc", "seqcc"]:
        assert committees == [{0, 1, 2, 3}]


@pytest.mark.parametrize("rule_id, algorithm, resolute", testrules.rule_algorithm_resolute)
def test_abcrules_return_lists_of_sets(rule_id, algorithm, resolute):
    profile = Profile(4)
    profile.add_voters([{0}, [1], [2], {3}])
    committeesize = 2

    committees = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
    )
    assert len(committees) >= 1
    for committee in committees:
        assert isinstance(committee, set)


@pytest.mark.parametrize("rule_id, algorithm, resolute", testrules.rule_algorithm_resolute)
def test_abcrules_handling_empty_ballots(rule_id, algorithm, resolute):
    profile = Profile(4)
    profile.add_voters([{0}, {1}, {2}])
    committeesize = 3

    committees = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
    )

    if rule_id == "trivial" and not resolute:
        assert committees == [{0, 1, 2}, {0, 1, 3}, {0, 2, 3}, {1, 2, 3}]
    else:
        assert committees == [{0, 1, 2}]

    profile.add_voters([[]])

    committees = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
    )

    if rule_id == "trivial" and not resolute:
        assert committees == [{0, 1, 2}, {0, 1, 3}, {0, 2, 3}, {1, 2, 3}]
    else:
        assert committees == [{0, 1, 2}]


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(algorithm, marks=MARKS[algorithm])
        for algorithm in abcrules.get_rule("monroe").algorithms
    ],
)
def test_monroe_indivisible(algorithm):
    profile = Profile(4)
    profile.add_voters([[0], [0], [0], [1, 2], [1, 2], [1], [3]])
    committeesize = 3

    assert abcrules.compute_monroe(
        profile, committeesize, algorithm=algorithm, resolute=False
    ) == [{0, 1, 2}, {0, 1, 3}, {0, 2, 3}]


@pytest.mark.parametrize("rule_id", ["geom1.5"] + [f"geom{i}" for i in range(2, 13)])
@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(algorithm, marks=MARKS[algorithm])
        for algorithm in abcrules.get_rule("geom2").algorithms
    ],
)
def test_geom_rules_special_instance(rule_id, algorithm):
    # this instance failed for geom10 at some point with gurobi
    # in general, geom-p with large p will not work well because very small numbers
    # arise in the calculations --> numerical problems
    # in this instance, problems start with p >= 16.
    profile = Profile(8)
    committeesize = 6
    profile.add_voters(
        [
            [1, 3, 4, 5],
            [0, 1, 6, 7],
            [2, 4, 5, 7],
            [0, 2, 4, 6],
            [0, 3, 4, 7],
            [0, 1, 4, 5],
            [0, 4, 5, 7],
            [1, 2, 3, 6],
            [2, 5, 6, 7],
            [3, 4, 5, 6],
            [2, 3, 4, 6],
            [2, 4, 6, 7],
            [0, 3, 5, 6],
            [3, 5, 6, 7],
            [0, 5, 6, 7],
            [0, 2, 3, 7],
            [1, 3, 4, 6],
            [0, 4, 6, 7],
            [2, 5, 6, 7],
            [0, 3, 6, 7],
            [1, 3, 6, 7],
            [0, 2, 4, 6],
            [1, 2, 3, 6],
            [1, 2, 3, 7],
            [0, 5, 6, 7],
        ]
    )
    # parameter = float(rule_id[len("geom") :])
    # if parameter < 18:
    expected_output = [{0, 2, 3, 4, 6, 7}]
    committees = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=False
    )
    assert committees == expected_output


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(algorithm, marks=MARKS[algorithm])
        for algorithm in abcrules.get_rule("minimaxphragmen").algorithms
    ],
)
def test_minimaxphragmen_does_not_use_lexicographic_optimization(algorithm):
    # this test shows that lexicographic optimization is not (yet)
    # implemented for opt-Phragmen (as it is described in
    # http://martin.lackner.xyz/publications/phragmen.pdf)

    profile = Profile(7)
    profile.add_voters([[6], [6], [1, 3], [1, 3], [1, 4], [2, 4], [2, 5], [2, 5]])
    committeesize = 3

    # without lexicographic optimization, this profile has 12 winning committees
    # (with lexicographic optimization only {1, 2, 6} is winning)
    committees = abcrules.compute(
        "minimaxphragmen", profile, committeesize, algorithm=algorithm, resolute=False
    )
    assert len(committees) == 12


@pytest.mark.parametrize(
    "rule_id, algorithm, resolute, profile, profilename, expected_result, committeesize",
    testinsts.instances,
)
def test_abcrules_correct(
    rule_id, algorithm, resolute, profile, profilename, expected_result, committeesize
):
    if rule_id.startswith("geom") and rule_id != "geom2":
        return  # correctness tests only for geom2
    if rule_id.startswith("seq") and rule_id not in ("seqpav", "seqslav", "seqcc"):
        return  # correctness tests only for selected sequential rules
    if rule_id.startswith("revseq") and rule_id != "revseqpav":
        return  # correctness tests only for selected reverse sequential rules (only for revseqpav)
    if rule_id == "rsd":
        return  # correctness tests do not have much sense due to random nature of RSD
    print(profile)
    committees = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
    )
    print(f"output: {committees}")
    print(f"expected: {expected_result}")
    if resolute:
        assert len(committees) == 1
        assert committees[0] in expected_result
    else:
        # test unordered equality, this requires sets of sets, only possible with frozensets
        committees_ = {frozenset(committee) for committee in committees}
        expected_result_ = {frozenset(committee) for committee in expected_result}
        assert committees_ == expected_result_


@pytest.mark.parametrize(
    "rule_id, algorithm, resolute, profile, profilename, expected_result, committeesize",
    testinsts.instances,
)
@pytest.mark.parametrize("max_num_of_committees", [1, 2, 3])
def test_abcrules_correct_with_max_num_of_committees(
    rule_id,
    algorithm,
    resolute,
    profile,
    profilename,
    expected_result,
    committeesize,
    max_num_of_committees,
):
    if rule_id.startswith("geom") and rule_id != "geom2":
        return  # correctness tests only for geom2
    if rule_id.startswith("seq") and rule_id not in ("seqpav", "seqslav", "seqcc"):
        return  # correctness tests only for selected sequential rules
    if rule_id.startswith("revseq") and rule_id != "revseqpav":
        return  # correctness tests only for selected reverse sequential rules (only for revseqpav)
    if rule_id == "rsd":
        return  # correctness tests do not have much sense due to random nature of RSD
    print(profile)
    print(f"expected: {expected_result}")
    for max_num_of_committees in [1, 2, 3]:
        committees = abcrules.compute(
            rule_id,
            profile,
            committeesize,
            algorithm=algorithm,
            resolute=resolute,
            max_num_of_committees=max_num_of_committees,
        )
        print(f"with max_num_of_committees={max_num_of_committees} output: {committees}")
        if resolute:
            assert len(committees) == 1
        else:
            assert len(committees) == min(max_num_of_committees, len(expected_result))
        for comm in committees:
            assert comm in expected_result


def test_seqphragmen_irresolute():
    profile = Profile(3)
    profile.add_voters([[0, 1], [0, 1], [0], [1, 2], [2]])
    committeesize = 2
    committees = abcrules.compute("seqphragmen", profile, committeesize, resolute=False)
    assert committees == [{0, 1}, {0, 2}]

    committees = abcrules.compute("seqphragmen", profile, committeesize, resolute=True)
    assert committees == [{0, 2}]


def test_seqpav_irresolute():
    profile = Profile(3)
    profile.add_voters([[0, 1]] * 3 + [[0], [1, 2], [2], [2]])
    committeesize = 2

    committees = abcrules.compute("seqpav", profile, committeesize, resolute=False)
    assert committees == [{0, 1}, {0, 2}, {1, 2}]

    committees = abcrules.compute("seqpav", profile, committeesize, resolute=True)
    assert committees == [{0, 2}]


@pytest.mark.parametrize("parameter", [1.001, "1.1", 1.5, 5, 10, 100.901, "100.901"])
@pytest.mark.parametrize("resolute", [True, False])
@pytest.mark.parametrize(
    "prefix,algorithm",
    [
        pytest.param(prefix, algorithm, marks=MARKS[algorithm])
        for prefix in ["", "seq", "revseq"]
        for algorithm in abcrules.get_rule(prefix + "geom2").algorithms
    ],
)
def test_geometric_rules_with_arbitrary_parameter(parameter, prefix, algorithm, resolute):
    profile = Profile(4)
    profile.add_voters([{0}, {1}, {2}, {3}])
    committeesize = 2

    rule_id = f"{prefix}geom{parameter}"
    committees = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
    )
    if resolute:
        assert len(committees) == 1
    else:
        assert len(committees) == 6

    rule = abcrules.get_rule(rule_id)
    committees = rule.compute(profile, committeesize, algorithm=algorithm, resolute=resolute)
    if resolute:
        assert len(committees) == 1
    else:
        assert len(committees) == 6


def test_gurobi_cant_compute_av():
    profile = Profile(4)
    profile.add_voters([[0, 1], [1, 2]])
    committeesize = 2

    with pytest.raises(ValueError):
        _gurobi_thiele_methods(
            profile, committeesize, "av", resolute=False, max_num_of_committees=None
        )


def test_consensus_fails_lower_quota():
    profile = Profile(31)
    profile.add_voters(
        [[0]]
        + [[1, 2]] * 3
        + [[3, 4, 5]] * 5
        + [[6, 7, 8, 9, 10, 11, 12, 13, 14, 15]] * 18
        + [[16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 30]] * 27
    )
    committeesize = 30

    committees = abcrules.compute("consensus-rule", profile, committeesize, resolute=True)
    for committee in committees:
        assert not all(
            cand in committee
            for cand in [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
        )
    # .. and thus the Consensus rule fails lower quota (and PJR and EJR):
    # the quota of the 27 voters is 15, but not all of their 15 approved candidates
    # are contained in a winning committee.


@pytest.mark.slow
@pytest.mark.parametrize(
    "rule_id, algorithm",
    [
        pytest.param(rule_id, algorithm, marks=MARKS[algorithm])
        for rule_id in ["phragmen-enestroem", "seqphragmen", "pav", "seqpav", "revseqpav"]
        for algorithm in abcrules.get_rule(rule_id).algorithms
    ],
)
def test_jansonexamples(rule_id, algorithm):
    # example from Janson's survey (https://arxiv.org/pdf/1611.08826.pdf),
    # Example 3.7, 18.1
    profile = Profile(6)
    a = 0
    b = 1
    c = 2
    p = 3
    q = 4
    r = 5
    profile.add_voters(
        [[a, b, c]] * 1034 + [[p, q, r]] * 519 + [[a, b, q]] * 90 + [[a, p, q]] * 90
    )
    committeesize = 3

    committees = abcrules.compute(
        rule_id, profile, committeesize, algorithm=algorithm, resolute=False
    )
    assert committees == [{a, b, q}]


@pytest.mark.parametrize("rule_id", abcrules.MAIN_RULE_IDS)
@pytest.mark.parametrize("resolute", [True, False])
def test_unspecified_algorithms(rule_id, resolute):
    rule = abcrules.get_rule(rule_id)
    if resolute not in rule.resolute_values:
        return
    profile = Profile(3)
    profile.add_voters([[0, 1], [1, 2]])
    committeesize = 2
    with pytest.raises(abcrules.UnknownAlgorithm):
        rule.compute(
            profile,
            committeesize,
            algorithm="made-up-algorithm",
            resolute=resolute,
        )


@pytest.mark.parametrize("rule_id", abcrules.MAIN_RULE_IDS)
def test_fastest_available_algorithm(rule_id):
    profile = Profile(4)
    profile.add_voters([[0, 1], [1, 2], [0, 2, 3]])
    committeesize = 2
    try:
        algorithm = abcrules.get_rule(rule_id).fastest_available_algorithm()
    except abcrules.NoAvailableAlgorithm:
        pytest.skip("no supported algorithms for " + abcrules.get_rule(rule_id).shortname)
    for resolute in abcrules.get_rule(rule_id).resolute_values:
        abcrules.compute(rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute)
    # second possibility
    abcrules.compute(rule_id, profile, committeesize, algorithm="fastest")


@pytest.mark.parametrize("sizemultiplier", [1, 2, 3, 4, 5])
def test_revseqpav_fails_EJR(sizemultiplier):
    # from "A Note on Justified RepresentationUnder the Reverse Sequential PAV rule"
    # by Haris Aziz
    # Proposition 2 for k=5

    num_cand = 12
    # candidates
    c, x1, x2, x3, x4, x5, x6, y1, y2, y3, y4, y5 = reversed(list(range(num_cand)))
    # reversed because c should be removed first in case of ties
    profile = Profile(num_cand)
    profile.add_voters([{c, x1, x3, x5}] * 4 * sizemultiplier)
    profile.add_voters([{c, x2, x4, x6}] * 4 * sizemultiplier)
    profile.add_voters([{x1}, {x2}, {x3}, {x4}, {x5}, {x6}] * sizemultiplier)
    profile.add_voters([[y1, y2, y3, y4, y5]] * 26 * sizemultiplier)
    assert len(profile) == 40 * sizemultiplier
    assert abcrules.compute_revseqpav(profile, 5) == [{y1, y2, y3, y4, y5}]


def test_seqphragmen_fails_ejr():
    # seq-Phragmen fails Extended Justified Representation
    # from "Phragmén's Voting Methods and Justified Representation"
    # by Markus Brill, Rupert Freeman, Svante Janson and Martin Lackner

    num_cand = 14
    # candidates
    a, b, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12 = list(range(num_cand))
    # reversed because c should be removed first in case of ties
    profile = Profile(num_cand)
    profile.add_voters([{a, b, c1}] * 2)
    profile.add_voters([{a, b, c2}] * 2)
    profile.add_voters([{c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12}] * 6)
    profile.add_voters([{c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12}] * 5)
    profile.add_voters([{c3, c4, c5, c6, c7, c8, c9, c10, c11, c12}] * 9)
    assert len(profile) == 24
    assert abcrules.compute_seqphragmen(profile, 12) == [
        {c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12}
    ]


@pytest.mark.slow
@pytest.mark.parametrize("filename", abc_yaml_filenames)
def test_abc_yaml_instances_use_only_main_rule_ids(filename):
    profile, committeesize, compute_instances, _ = fileio.read_abcvoting_yaml_file(filename)
    for compute_instance in compute_instances:
        # If this assertation fails, _load_abc_yaml_compute_instances() has to be adapted
        # so that it actually loads the .abc.yaml files and extracts the rule_id's.
        # However, this would be rather slow.
        assert compute_instance["rule_id"] in abcrules.MAIN_RULE_IDS


@pytest.mark.parametrize(
    "filename, rule_id, algorithm", abc_yaml_compute_instances, ids=id_function
)
def test_selection_of_abc_yaml_instances(filename, rule_id, algorithm):
    profile, committeesize, compute_instances, _ = fileio.read_abcvoting_yaml_file(filename)
    for compute_instance in compute_instances:
        if compute_instance["rule_id"] == rule_id:
            if compute_instance["result"] is None:
                return  # not applicable or too slow
            abcrules.compute(**compute_instance, algorithm=algorithm)
            return
    else:
        pytest.skip(
            f"{rule_id} ({algorithm}) not precomputed for {filename},\n"
            "re-run tests/test_instances/generate.py?"
        )


@pytest.mark.parametrize("rule_id, algorithm, resolute", testrules.rule_algorithm_resolute)
@pytest.mark.parametrize("verbosity", VERBOSITY_TO_NAME.keys())
def test_output(capfd, rule_id, algorithm, resolute, verbosity):
    if algorithm == "fastest":
        return
        # not necessary, output for "fastest" is the same as
        # whatever algorithm is selected as fastest
        # (and "fastest" depends on the available solvers)

    output.set_verbosity(verbosity=verbosity)

    try:
        profile = Profile(2)
        profile.add_voters([[0], [1]])
        committeesize = 2

        committees = abcrules.compute(
            rule_id, profile, committeesize, algorithm=algorithm, resolute=resolute
        )
        out = str(capfd.readouterr().out)

        # remove unwanted solver output
        out = remove_solver_output(out)

        if verbosity >= WARNING:
            assert out == ""
        else:
            assert len(out) > 0
            rule = abcrules.get_rule(rule_id)
            start_output = misc.header(rule.longname) + "\n"
            if resolute and rule.resolute_values[0] == False:
                # only if irresolute is default but resolute is chosen
                start_output += "Computing only one winning committee (resolute=True)\n\n"
            if not resolute and rule.resolute_values[0] == True:
                # only if resolute is default but resolute=False is chosen
                start_output += (
                    "Computing all possible winning committees for any tiebreaking order\n"
                    " (aka parallel universes tiebreaking) (resolute=False)\n\n"
                )
            if verbosity <= DETAILS:
                start_output += "Algorithm: " + abcrules.ALGORITHM_NAMES[algorithm] + "\n"
            if verbosity <= DEBUG:
                assert start_output in out
            else:
                print(out, start_output)
                assert out.startswith(start_output)
            end_output = (
                misc.str_committees_with_header(
                    committees, cand_names=profile.cand_names, winning=True
                )
                + "\n"
            )
            if verbosity == INFO:
                assert out.endswith(end_output)
            else:
                assert end_output in out

    finally:
        output.set_verbosity(verbosity=WARNING)


@pytest.mark.parametrize("rule_id, algorithm", testrules.rule_algorithm_onlyresolute)
@pytest.mark.parametrize("max_num_of_committees", [-1, 0, 1, "None"])
def test_resolute_and_max_num_of_committees(rule_id, algorithm, max_num_of_committees):
    num_cand = 6
    profile = Profile(num_cand)
    profile.add_voters([[cand] for cand in range(num_cand)])
    committeesize = 2
    committees = abcrules.compute(
        rule_id,
        profile,
        committeesize,
        resolute=True,
        algorithm=algorithm,
    )
    assert len(committees) == 1
    with pytest.raises(ValueError):
        committees = abcrules.compute(
            rule_id,
            profile,
            committeesize,
            resolute=True,
            algorithm=algorithm,
            max_num_of_committees=max_num_of_committees,
        )


@pytest.mark.parametrize("rule_id, algorithm", testrules.rule_algorithm_onlyirresolute)
@pytest.mark.parametrize("max_num_of_committees", [1, 3, 5, 7])
def test_resolute_and_max_num_of_committees(rule_id, algorithm, max_num_of_committees):
    num_cand = 5
    profile = Profile(num_cand)
    profile.add_voters([[cand] for cand in range(num_cand)])
    committeesize = 1
    total_num_of_committees = 5
    committees = abcrules.compute(
        rule_id,
        profile,
        committeesize,
        resolute=False,
        algorithm=algorithm,
        max_num_of_committees=max_num_of_committees,
    )
    if max_num_of_committees <= total_num_of_committees:
        assert len(committees) == max_num_of_committees
    else:
        assert len(committees) == total_num_of_committees


@pytest.mark.parametrize("rule_id, algorithm", testrules.rule_algorithm_onlyresolute)
def test_natural_tiebreaking_order_resolute(rule_id, algorithm):
    # test if rules use the natural tiebreaking orders, i.e.,
    # candidates with smaller indices are preferred
    num_cand = 6
    profile = Profile(num_cand)
    for approval_sets in [
        reversed([[cand] for cand in range(num_cand)]),
        reversed([list(range(num_cand))] * 4),
    ]:
        profile.add_voters(approval_sets)
        committeesize = 2
        if algorithm in ["gurobi", "ortools-cp", "mip-cbc", "mip-gurobi", "fastest"]:
            return  # ILP solvers do not guarantee a specific solution
        if rule_id in ["rsd"]:
            return  # RSD is randomized
        committees = abcrules.compute(
            rule_id,
            profile,
            committeesize,
            resolute=True,
            algorithm=algorithm,
        )
        assert committees == [{0, 1}]


@pytest.mark.parametrize("rule_id, algorithm", testrules.rule_algorithm_onlyirresolute)
@pytest.mark.parametrize(
    "approval_sets",
    [
        list(reversed([[cand] for cand in range(6)])),
        [list(range(6))] * 4,
        [[]],
    ],
)
def test_natural_tiebreaking_order_max_num_of_committees(rule_id, algorithm, approval_sets):
    # test if rules use the natural tiebreaking orders, i.e.,
    # candidates with smaller indices are preferred
    profile = Profile(num_cand=6)
    profile.add_voters(approval_sets)
    print(profile)
    committeesize = 2
    if algorithm in ["gurobi", "ortools-cp", "mip-cbc", "mip-gurobi", "fastest"]:
        return  # ILP solvers do not guarantee a specific solution
    if rule_id in ["rsd"]:
        return  # RSD is randomized
    committees = abcrules.compute(
        rule_id,
        profile,
        committeesize,
        resolute=False,
        algorithm=algorithm,
        max_num_of_committees=6,
    )
    assert committees == [{0, 1}, {0, 2}, {0, 3}, {0, 4}, {0, 5}, {1, 2}]
