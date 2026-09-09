"""Holds "which organization is this request for" for the duration of a
request. A contextvar rather than a thread-local so it stays correct
under async views/ASGI, where multiple requests can interleave on one
thread.
"""

import contextvars

_current_organization_id = contextvars.ContextVar("anvil_current_organization_id", default=None)


def get_current_organization_id():
    return _current_organization_id.get()


def set_current_organization_id(organization_id):
    return _current_organization_id.set(organization_id)


def reset_current_organization_id(token):
    _current_organization_id.reset(token)
