class UnauthorizedException(Exception):

    def __init__(self, message="Token is expired or user is unauthorized."):
        self.message = message
        super().__init__(self.message)