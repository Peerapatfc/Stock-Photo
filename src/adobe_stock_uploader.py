import logging
from pathlib import Path

import paramiko

SFTP_HOST = "sftp.contributor.adobestock.com"
SFTP_PORT = 22
log = logging.getLogger(__name__)


def upload(file_path: Path, sftp_user: str, sftp_pass: str) -> None:
    log.info(f"Uploading {file_path.name} to Adobe Stock SFTP...")
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    try:
        transport.connect(username=sftp_user, password=sftp_pass)
        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            sftp.put(str(file_path), file_path.name)
            log.info(f"Uploaded: {file_path.name}")
        finally:
            sftp.close()
    finally:
        transport.close()
