"""Remove the :code:`tags` field in notebook cell metadata if it is empty."""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Sequence, TypeVar

import attr
import nbformat
from nbformat import NotebookNode

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Filenames to check.")
    args = parser.parse_args(argv)

    errors: list[PrecommitError] = []
    for filename in args.filenames:
        try:
            remove_empty_tags(filename)
        except PrecommitError as exception:
            errors.append(exception)
    if errors:
        for error in errors:
            error_msg = "\n ".join(error.args)
            print(error_msg)  # noqa: T201
        return 1
    return 0


def remove_empty_tags(filename: str) -> None:
    notebook = load_notebook(filename)
    if not __has_python_kernel(notebook):
        return
    is_modified = False
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        tags = cell["metadata"].get("tags")
        if tags is None:
            continue
        if tags:
            continue
        cell["metadata"].pop("tags")
        is_modified = True
    if is_modified:
        nbformat.write(notebook, filename)
        msg = f"Removed empty tags field from cell metadata in {filename}"
        raise PrecommitError(msg)


def __has_python_kernel(notebook: dict) -> bool:
    # cspell:ignore kernelspec
    metadata = notebook.get("metadata", {})
    kernel_specification = metadata.get("kernelspec", {})
    kernel_language = kernel_specification.get("language", "")
    return "python" in kernel_language


def load_notebook(path: str) -> NotebookNode:
    return nbformat.read(path, as_version=nbformat.NO_CONVERT)


T = TypeVar("T")
P = ParamSpec("P")


@attr.s(on_setattr=attr.setters.frozen)
class Executor:
    # https://github.com/ComPWA/policy/blob/359331f/src/compwa_policy/utilities/executor.py
    error_messages: list[str] = attr.ib(factory=list, init=False)

    def __call__(
        self, function: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T | None:
        """Execute a function and collect any `.PrecommitError` exceptions."""
        try:
            result = function(*args, **kwargs)
        except PrecommitError as exception:
            error_message = str("\n".join(exception.args))
            self.error_messages.append(error_message)
            return None
        else:
            return result

    def finalize(self, exception: bool = True) -> int:
        error_msg = self.merge_messages()
        if error_msg:
            if exception:
                raise PrecommitError(error_msg)
            print(error_msg)  # noqa: T201
            return 1
        return 0

    def merge_messages(self) -> str:
        stripped_messages = (s.strip() for s in self.error_messages)
        return "\n--------------------\n".join(stripped_messages)


class PrecommitError(RuntimeError): ...


if __name__ == "__main__":
    raise SystemExit(main())
