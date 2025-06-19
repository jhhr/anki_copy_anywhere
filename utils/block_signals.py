from contextlib import contextmanager


@contextmanager
def block_signals(*widgets):
    try:
        for widget in widgets:
            widget.blockSignals(True)
        yield
    finally:
        for widget in widgets:
            widget.blockSignals(False)
