def addBearerAuthHeader(token, headers=None):
    headers = headers or {}
    headers['Authorization'] = f'Bearer {token}'
    return headers
