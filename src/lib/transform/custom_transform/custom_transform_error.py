"""Custom exception for failures in user-provided transform/hook code."""

from typing import Any


class CustomTransformError(Exception):
    """
    Raised when an error occurs inside the user's custom transform or hook code.

    Use this in a try/except around user code so callers can distinguish
    user-script failures from transformer codebase failures. When re-raising,
    pass the original exception as the cause to preserve the traceback::

        try:
            result = user_transform(value)
        except Exception as e:
            raise CustomTransformError(
                "Field transformation failed",
                function_name="clean_phone",
                row_index=row_index,
                cause=e,
            ) from e

    Context parameters (function_name, row_index, stage, etc.) are stored and
    included in the exception message to help users debug their custom code.
    """

    def __init__(
        self,
        message: str,
        *,
        function_name: str | None = None,
        row_index: int | None = None,
        stage: str | None = None,
        cause: BaseException | None = None,
        **context: Any,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.function_name = function_name
        self.row_index = row_index
        self.stage = stage
        self.cause = cause
        self.context = context

    def __str__(self) -> str:
        parts = [
            "Error in user-provided custom transform code.",
            self.message,
        ]
        if self.function_name is not None:
            parts.append(f"Function: {self.function_name!r}.")
        if self.row_index is not None:
            parts.append(f"Row index: {self.row_index}.")
        if self.stage is not None:
            parts.append(f"Stage: {self.stage!r}.")
        for key, value in self.context.items():
            parts.append(f"{key}: {value}.")
        if self.cause is not None:
            parts.append(f"Caused by: {type(self.cause).__name__}: {self.cause}.")
        return " ".join(parts)
