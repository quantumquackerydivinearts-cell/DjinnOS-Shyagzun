class ConformanceError(Exception):
    pass

class AssertionFailure(ConformanceError):
    def __init__(self, message: str):
        super().__init__(message)

class HttpError(ConformanceError):
    pass
