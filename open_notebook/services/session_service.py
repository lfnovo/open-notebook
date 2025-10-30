from fastapi import Request

class SessionService:
    def __init__(self, request: Request):
        self.session = request.session

    def set(self, key: str, value: any):
        self.session[key] = value

    def get(self, key: str, default: any = None) -> any:
        return self.session.get(key, default)

    def pop(self, key: str, default: any = None) -> any:
        return self.session.pop(key, default)
