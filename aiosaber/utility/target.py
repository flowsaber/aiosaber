class Target(object):
    """Target represents item emitted by Channel. Theoretically all item emitted by Channel should be wrapped by a Target
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                setattr(self, k, v)


class End(Target):
    """End signal of a Channel.
    """

    def __repr__(self):
        return "[END]"

    def __copy__(self):
        return self

    def __hash__(self):
        return hash("[END]")


END = End()
