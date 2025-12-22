from functools import partial
from typing import Any, Callable, Dict, Generator

from patchagent.agent.base import BaseAgent
from patchagent.task import PatchTask

from cold.agent.backdoor import BackDoorCLikeAgent


def _create_agent_generator(
    patchtask: PatchTask,
    model: str = "gpt-4o",
    hint: str = "",
    stop_indicator: Callable[[], bool] = lambda: False,
) -> Generator["BaseAgent", None, None]:

    kwargs: Dict[str, Any] = {}
    for counterexample_num in [0, 3]:
        for temperature in [0, 0.3, 0.7, 1]:
            for auto_hint in [True, False]:
                if stop_indicator():
                    return

                kwargs["auto_hint"] = auto_hint
                kwargs["counterexample_num"] = counterexample_num
                kwargs["temperature"] = temperature
                yield BackDoorCLikeAgent(patchtask, model=model, hint=hint, **kwargs)


def backdoor_agent_generator(
    model: str = "gpt-4o",
    hint: str = "",
) -> Callable[[PatchTask], Generator["BaseAgent", None, None]]:
    return partial(_create_agent_generator, model=model, hint=hint)
