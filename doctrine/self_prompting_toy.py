"""Doctrine 004 toy: SELF drives V(CCD) -> A -> return feed.

Run: python self_prompting_toy.py --target 7 --max-steps 10 --horizon 2
Standard library only. The deterministic counter makes the flow inspectable.
Stage implementations illustrate the ontology; they do not redefine it.
"""

import argparse
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Signal:
    position: int


@dataclass(frozen=True)
class Forecast:
    step: int
    predicted_gap: int
    immediate_gap: int


@dataclass
class CounterEnvironment:
    position: int = 0

    def act(self, step: int) -> Signal:
        self.position += step
        return Signal(self.position)


@dataclass
class ToySelf:
    name: str
    target: int
    horizon: int = 2
    memory: list[dict] = field(default_factory=list)
    committed_step: int | None = None

    def load_variables(self, signal: Signal) -> tuple[int, tuple[int, ...]]:
        # V: combine incoming state with the goal retained within SELF.
        gap = self.target - signal.position
        return gap, tuple(step for step in (1, 2, 3) if step <= gap)

    def predictive_model(self, gap: int, options: tuple[int, ...]) -> list[Forecast]:
        # C1: recursively model possible continuations before taking action.
        def predict(remaining: int, depth: int) -> int:
            if remaining == 0 or depth == 0:
                return remaining
            return min(predict(remaining - step, depth - 1)
                       for step in (1, 2, 3) if step <= remaining)

        return [Forecast(step, predict(gap - step, self.horizon - 1), gap - step)
                for step in options]

    def choose(self, forecasts: list[Forecast]) -> Forecast:
        # C2: prune to one option. This ranking is a toy implementation choice.
        return min(forecasts, key=lambda f: (f.predicted_gap, f.immediate_gap))

    def decide(self, selected: Forecast) -> int:
        # D: act on the selection by committing it as the next operation.
        self.committed_step = selected.step
        return self.committed_step

    def pump(self, output: Signal) -> Signal:
        # Feed only: no selection, interpretation, or goal change here.
        return output

    def run(self, env: CounterEnvironment, max_steps: int) -> str:
        if self.target < env.position or not 1 <= self.horizon <= 6 or max_steps < 1:
            raise ValueError('Require target >= starting position, horizon 1..6, max_steps >= 1')
        signal = Signal(env.position)  # Initial input; no further human input.
        for cycle in range(1, max_steps + 1):
            if signal.position == self.target:
                return 'complete'
            gap, options = self.load_variables(signal)
            forecasts = self.predictive_model(gap, options)
            selected = self.choose(forecasts)
            decision = self.decide(selected)
            output = env.act(decision)  # A: carry the committed step into the task.
            self.memory.append(dict(cycle=cycle, input=signal.position,
                                    selected=decision, output=output.position))
            print(f'{self.name}: {signal.position} -> choose/commit +{decision}'
                  f' -> output {output.position} -> feed back')
            signal = self.pump(output)  # The result becomes the next input.
        return 'complete' if signal.position == self.target else 'step_limit'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=int, default=7)
    parser.add_argument('--max-steps', type=int, default=10)
    parser.add_argument('--horizon', type=int, default=2)
    args = parser.parse_args()
    if args.target < 0 or args.max_steps < 1 or not 1 <= args.horizon <= 6:
        parser.error('target must be >= 0, max-steps >= 1, and horizon between 1 and 6')
    myself = ToySelf('Toy SELF', args.target, args.horizon)
    env = CounterEnvironment()
    status = myself.run(env, args.max_steps)
    print(f'status={status}; position={env.position}; target={myself.target};'
          f' passes={len(myself.memory)}')


if __name__ == '__main__':
    main()
