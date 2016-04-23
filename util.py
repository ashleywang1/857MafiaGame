"""
Utility function + classes file
"""

from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import json, requests
from time import sleep

from tornado.httpclient import AsyncHTTPClient

from common import *

# TODO: Create appropriate custom exception subclasses

"""
Handle serialization of enums
Source: https://stackoverflow.com/a/24482806
"""
class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return {"__enum__": str(obj)}
        return json.JSONEncoder.default(self, obj)

def as_enum(d):
    if "__enum__" in d:
        name, member = d["__enum__"].split(".")
        return getattr(globals()[name], member)
    return d

"""
Request handling
"""
def load_request_body(body):
    """Unserializes the body of a JSON response that is in bytes."""
    return json.loads(body.decode(ENCODING), object_hook=as_enum)

ASYNC_HTTP_CLIENT = AsyncHTTPClient()

def send_to_player(player, endpoint, data=None, callback=None,
                   connect_timeout=CONNECT_TIMEOUT, request_timeout=REQUEST_TIMEOUT, GET=True):
    """Sends a request to the specified player at the specified endpoint"""

    url = '{server_url}:{player}/{endpoint}'.format(
        server_url=SERVER_URL,
        player=player,
        endpoint=endpoint
    )

    # Use default callback that only checks for timeouts and raises anything else
    if not callback: callback = check_response_error(player)
    if not GET and data is not None: data = json.dumps(data, cls=EnumEncoder)

    method = 'GET' if GET else 'POST'
    return ASYNC_HTTP_CLIENT.fetch(url, body=data, method=method, callback=callback,
                                   connect_timeout=connect_timeout, request_timeout=request_timeout)


def query_endpoint(ME, PLAYERS, endpoint, callback=None, check= lambda x: x != None):
    """Scans all the messages and the endpoints from all the other players, returns a list of those messages"""
    results = []
    print("Querying endpoint {}".format(endpoint))
    for i, player in enumerate(PLAYERS):
        if i == ME: continue
        r = send_to_player(player, endpoint, callback=callback , GET=True)
    return results

def check_response_error(player, request_name='Request', raise_error=True):
    """
    Callback that checks for certain exceptions and simply prints
    helpful messages (rather than throwing the exception).

    Returns 'handled' True if there was an error,
                      but it was handled by this function
    """
    def check(response):
        if response.error is not None:
            try:
                if isinstance(response.error, ConnectionRefusedError):
                    print('{} to player {} failed! Connection refused.'.format(request_name, player))
                    return True

                if response.error.message == 'Timeout':
                    print('{} to player {} timed out!'.format(request_name, player))
                    return True

            # Not all errors have the message attribute
            except AttributeError:
                pass

            if raise_error: response.rethrow()
            return

    return check

"""
Asynchronous Helper Classes + Functions
"""
class BackgroundTaskRunner():
    """
    Runs a background task repeatedly based on the specified
    repeat interval.
    """
    running = False

    def __init__(self, task, repeat_interval):
        self.task = task
        self.repeat_interval = repeat_interval
        self.executor = ThreadPoolExecutor(max_workers=1)

    def start(self):
        if not self.running:
            self.running = True
            self.__run()

    def stop(self, wait=True):
        if self.running:
            self.executor.shutdown(wait=wait)
            self.running = False

    def set_task(self, task):
        self.task = task

    def handle_errors(self, future):
        exception = future.exception()
        if exception:
            print(exception)

    def __run(self):
        try:
            future = self.executor.submit(self.task)
            future.add_done_callback(self.handle_errors)
            self.executor.submit(sleep, self.repeat_interval)
            self.executor.submit(self.__run)

        # Raised upon attempt to submit after shutdown of executor
        except RuntimeError:
            return
