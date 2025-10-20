from benedict import benedict


type ProcessingResult = tuple[benedict, list[str]]


class FatalError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors

    def __str__(self):
        return f'There were {len(self.errors)} errors. One was fatal.'
