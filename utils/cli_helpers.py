"""
CLI helper utilities for Sync2NAS, including context injection for Click commands.
"""
import click

def pass_sync2nas_context(func):
    """
    Click decorator to inject and verify the CLI context object (`ctx.obj`) for Sync2NAS.

    Args:
        func: The function to decorate.

    Returns:
        function: Wrapped function with context injection and validation.
    """
    @click.pass_context
    def wrapper(ctx, *args, **kwargs):
        if ctx.obj is None:
            raise click.UsageError("Context object (ctx.obj) is not initialized.")
        return func(ctx, *args, **kwargs)
    return wrapper
