from flask import Response
from base64 import b64decode, b64encode
from werkzeug.http import parse_options_header
import sys
import io


def add_body(environ, body, content_type):
    environ['CONTENT_TYPE'] = content_type
    if body:
        environ['wsgi.input'] = io.BytesIO(body)
        environ['CONTENT_LENGTH'] = str(len(body))
    else:
        environ['wsgi.input'] = None


block = set(['x-client-ip', 'x-forwarded-for',
             'x-forwarded-proto', 'x-global-transaction-id'])


def add_headers(environ, headers):
    for header in headers:
        if header not in block:
            wsgi_name = "HTTP_" + header.upper().replace('-', '_')
            environ[wsgi_name] = str(headers[header])


def invoke(app, args):
    headers = args.get('__ow_headers', {})
    environ = {
       'REQUEST_METHOD': args.get('__ow_method', 'GET').upper(),
       'SCRIPT_NAME': '',
       'PATH_INFO': args.get('__ow_path', '/'),
       'QUERY_STRING': args.get('__ow_query', None),
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '5000',
       'SERVER_PROTOCOL': 'HTTP/1.1',
       'SERVER_SOFTWARE': 'flask-openwhisk',
       'REMOTE_ADDR': headers.get('x-client-ip', '127.0.0.1'),
       'wsgi.version': (1, 0),
       'wsgi.url_scheme': headers.get('x-forwarded-proto', 'http'),
       'wsgi.input': None,
       'wsgi.errors': sys.stderr,
       'wsgi.multiprocess': True,
       'wsgi.multithread': False,
       'wsgi.run_once': True
    }

    if environ['REQUEST_METHOD'] in ('POST', 'PUT'):
        content_type = headers.get('content-type', 'application/octet-stream')
        parsed_content_type = parse_options_header(content_type)
        raw = args.get('__ow_body')
        if parsed_content_type[0][0:5] == 'text/':
            body = raw.encode(parsed_content_type[1].get('charset', 'utf-8'))
        else:
            body = b64decode(raw) if raw is not None else None
        add_body(environ, body, content_type)

    add_headers(environ, headers)

    response = Response.from_app(app.wsgi_app, environ)

    response_type = parse_options_header(
        response.headers.get('Content-Type', 'application/octet-stream'))
    if response_type[0][0:response_type[0].find('/')] != 'octet-stream':
        body = response.data.decode(response_type[1].get('charset', 'utf-8'))
    else:
        body = b64encode(response.data)

    return {
        'headers': dict(response.headers),
        'statusCode': response.status_code,
        'body': body
    }
