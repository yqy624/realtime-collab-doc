from fastapi import Header, HTTPException, Request


def get_current_user_id(request: Request) -> int:
    """Extract user ID from request state (set by JWT middleware)."""
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(status_code=401, detail="未授权访问")
    return user_id


def get_current_username(request: Request) -> str:
    username = getattr(request.state, "username", None)
    if username is None:
        raise HTTPException(status_code=401, detail="未授权访问")
    return username
