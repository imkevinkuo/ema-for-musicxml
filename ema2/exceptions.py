class MXMLException(Exception):
    def __init__(self, message):
        self.message = message


class BadApiRequest(MXMLException):
    pass


class UnsupportedEncoding(MXMLException):
    pass
