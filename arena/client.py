import time
import uuid

import httpx

RESULTS = ("miss", "hit", "killed")


class ServiceError(Exception):
    pass


class ServiceClient:
    def __init__(self, name, base_url=None, http=None, timeout=1.0):
        self.name = name
        self.timeout = timeout
        self.http = http or httpx.Client(base_url=base_url, timeout=timeout, trust_env=False)
        self.session_id = None
        self.slowest = 0.0

    def call(self, path, body=None, expected_code=200):
        started = time.perf_counter()
        try:
            if body is None:
                response = self.http.post(path)
            else:
                response = self.http.post(path, json=body)
        except httpx.TimeoutException:
            raise ServiceError(f"{path}: нет ответа за {self.timeout} с")
        except httpx.HTTPError as error:
            raise ServiceError(f"{path}: сервис недоступен ({error.__class__.__name__})")

        elapsed = time.perf_counter() - started
        self.slowest = max(self.slowest, elapsed)
        if elapsed > self.timeout:
            raise ServiceError(f"{path}: ответ за {elapsed:.2f} с, а лимит {self.timeout} с")
        if response.status_code != expected_code:
            raise ServiceError(f"{path}: код ответа {response.status_code}, а по контракту {expected_code}")

        try:
            return response.json()
        except ValueError:
            raise ServiceError(f"{path}: ответ не в формате JSON")

    def start(self):
        data = self.call("/game", expected_code=201)
        if not isinstance(data, dict) or "session_id" not in data or "ships" not in data:
            raise ServiceError("/game: ответ не по контракту")
        try:
            uuid.UUID(str(data["session_id"]))
        except ValueError:
            raise ServiceError(f"/game: session_id {data['session_id']!r} не UUID")
        self.session_id = data["session_id"]
        return data["ships"]

    def shot(self):
        data = self.call(f"/game/{self.session_id}/shot")
        if not isinstance(data, dict) or not isinstance(data.get("coordinate"), str):
            raise ServiceError("/shot: ответ не по контракту")
        return data["coordinate"]

    def send_result(self, result):
        data = self.call(f"/game/{self.session_id}/shot/result", {"result": result})
        if data != {"status": "accepted"}:
            raise ServiceError("/shot/result: ответ не по контракту")

    def opponent_shot(self, coordinate):
        data = self.call(f"/game/{self.session_id}/opponent-shot", {"coordinate": coordinate})
        if not isinstance(data, dict) or data.get("result") not in RESULTS:
            raise ServiceError("/opponent-shot: ответ не по контракту")
        return data["result"]

    def close(self):
        if self.session_id is None:
            return False
        try:
            data = self.call(f"/game/{self.session_id}/close")
        except ServiceError:
            return False
        return data == {"status": "closed"}
