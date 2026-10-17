"""SCCD prompt run: symbolic behavior, without numerical scoring.

Run: python sccd_realization_toy.py
This models a document task with read, draft, check and archive actions.
"""
from dataclasses import dataclass, field
import json


@dataclass(frozen=True)
class Action:
    name: str
    requires: frozenset[str]
    adds: str
    blocked_by: frozenset[str] = frozenset()

    def available(self, state):
        return (self.requires <= state and self.adds not in state
                and not self.blocked_by.intersection(state))

    def result(self, state):
        return state | {self.adds}


@dataclass
class FunctionalSelf:
    state: frozenset[str]
    goal: frozenset[str]
    actions: tuple[Action, ...]
    history: list[dict] = field(default_factory=list)

    def consciousness(self, state):
        # Predictive recursion over possible actions and their resulting states.
        if self.goal <= state:
            return [()], []
        successful, dead_ends = [], []
        for action in self.actions:
            if action.available(state):
                tails, failed = self.consciousness(action.result(state))
                successful.extend((action.name,) + tail for tail in tails)
                dead_ends.extend((action.name,) + tail for tail in failed)
        if not successful and not dead_ends:
            dead_ends.append(())
        return successful, dead_ends

    def choice(self, paths):
        # Prune paths containing another successful path's actions plus extras.
        # This is a toy policy; remaining ties use the listed order.
        kept = [path for path in paths
                if not any(set(other) < set(path) for other in paths)]
        return kept[0][0] if kept else None

    def decision(self, selected):
        # The action of choice: execute the selected state transition.
        action = next(a for a in self.actions if a.name == selected)
        assert action.available(self.state)
        return action.result(self.state)

    def pump(self, output):
        return output  # Feed only.

    def run(self):
        while not self.goal <= self.state:
            paths, dead_ends = self.consciousness(self.state)
            selected = self.choice(paths)
            if selected is None:
                return 'no_path'
            output = self.decision(selected)
            self.history.append(dict(input=sorted(self.state),
                                     predicted_paths=paths, dead_ends=dead_ends,
                                     selected=selected, output=sorted(output)))
            self.state = self.pump(output)
        return 'complete'


ACTIONS = (
    Action('read', frozenset({'source_available'}), 'source_read'),
    # Archiving before drafting provides a tempting but unsuccessful branch.
    Action('archive', frozenset({'source_read'}), 'archived'),
    Action('draft', frozenset({'source_read'}), 'draft_written', frozenset({'archived'})),
    Action('check', frozenset({'draft_written'}), 'checked'),
)


def demonstrate():
    results = []
    for name, initial, goal in (
        ('full_task', {'source_available'}, {'checked'}),
        ('already_read', {'source_available', 'source_read'}, {'checked'}),
        ('missing_source', set(), {'checked'}),
        ('archive_task', {'source_available'}, {'archived'}),
    ):
        myself = FunctionalSelf(frozenset(initial), frozenset(goal), ACTIONS)
        status = myself.run()
        results.append(dict(case=name, status=status, state=sorted(myself.state),
                            actions=[h['selected'] for h in myself.history],
                            trace=myself.history))
    return results


if __name__ == '__main__':
    print(json.dumps(demonstrate(), indent=2))
