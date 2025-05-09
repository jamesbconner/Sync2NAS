import click

def pass_sync2nas_context(func):
    """
    Click decorator to inject and verify the CLI context object (`ctx.obj`) for Sync2NAS.
    """
    @click.pass_context
    def wrapper(ctx, *args, **kwargs):
        if ctx.obj is None:
            raise click.UsageError("Context object (ctx.obj) is not initialized.")
        return func(ctx, *args, **kwargs)
    return wrapper
